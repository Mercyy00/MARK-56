"""
Voice stream processor and isolation manager for JARVIS Live sessions.

Architecture:
  • Decouples microphone hardware callbacks from the asyncio network event loop.
  • Bounded realtime audio buffer with Zero-Backlog guarantee (discards stale frames on network hiccups).
  • Per-packet timeout protection against socket hang / SSL pipeline deadlocks.
  • 5.0s stream watchdog that detects frozen transports and initiates clean resets.
  • Graceful suppression of WinError 10054 (ConnectionResetError) on Windows Proactor event loops.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine

logger = logging.getLogger("JARVIS.VoiceProcessor")

DEFAULT_QUEUE_MAXSIZE = 30       # ~1.5s of 50ms audio frames
DEFAULT_FRAME_TIMEOUT = 3.0      # Timeout for individual frame send
DEFAULT_WATCHDOG_TIMEOUT = 5.0   # Watchdog threshold for stuck stream


class VoiceStreamManager:
    """
    Manages outbound realtime audio streaming to Gemini Live or local pipelines.
    Guarantees that audio ingestion never blocks the mic thread and that network
    stalls do not block or crash the asyncio main loop.
    """

    def __init__(
        self,
        session_provider: Callable[[], Any],
        on_error: Callable[[Exception], None] | None = None,
        on_stall: Callable[[], None] | None = None,
        max_queue_size: int = DEFAULT_QUEUE_MAXSIZE,
        frame_timeout: float = DEFAULT_FRAME_TIMEOUT,
        watchdog_timeout: float = DEFAULT_WATCHDOG_TIMEOUT,
    ):
        self._session_provider = session_provider
        self._on_error = on_error or (lambda _: None)
        self._on_stall = on_stall or (lambda: None)
        self._max_queue_size = max(1, max_queue_size)
        self._frame_timeout = max(0.01, frame_timeout)
        self._watchdog_timeout = max(0.05, watchdog_timeout)

        self._queue: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False
        self._last_send_time = time.monotonic()
        self._frames_sent = 0
        self._bytes_sent = 0
        self._dropped_frames = 0
        self._stall_count = 0
        self._consecutive_errors = 0

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Attach to the active event loop and initialize queue."""
        self._loop = loop
        self._queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._running = True
        self._last_send_time = time.monotonic()

    def enqueue_frame_threadsafe(self, data: bytes, mime_type: str = "audio/pcm") -> bool:
        """
        Thread-safe entrypoint called from microphone callback.
        Enforces Zero-Backlog: if buffer is full, drops the oldest stale packet.
        Never blocks the caller.
        """
        if not self._running or self._loop is None or self._queue is None:
            return False

        def _do_put():
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                    self._dropped_frames += 1
                except Exception:
                    pass
            try:
                self._queue.put_nowait({"data": data, "mime_type": mime_type})
            except Exception:
                pass

        try:
            self._loop.call_soon_threadsafe(_do_put)
            return True
        except Exception:
            return False

    async def run_sender(self) -> None:
        """
        Continuous worker that transmits audio frames to the active session.
        Guarded by per-frame timeouts and watchdog health checks.
        """
        self._running = True
        self._last_send_time = time.monotonic()

        while self._running:
            try:
                if self._queue is None:
                    await asyncio.sleep(0.05)
                    continue

                # Wait for next frame
                try:
                    msg = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # Idle timeout — check watchdog if frames are backing up
                    if self._queue.qsize() > 0 and (time.monotonic() - self._last_send_time) > self._watchdog_timeout:
                        self._trigger_stall()
                    continue

                session = self._session_provider()
                if session is None:
                    await asyncio.sleep(0.05)
                    continue

                data = msg.get("data")
                mime_type = msg.get("mime_type", "audio/pcm")
                if not data:
                    continue

                # Transmit with per-frame timeout
                t0 = time.monotonic()
                await asyncio.wait_for(
                    self._dispatch_audio(session, data, mime_type),
                    timeout=self._frame_timeout
                )
                self._last_send_time = time.monotonic()
                self._frames_sent += 1
                self._bytes_sent += len(data)
                self._consecutive_errors = 0

            except asyncio.TimeoutError:
                self._consecutive_errors += 1
                self._trigger_stall()
                await asyncio.sleep(0.1)

            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as conn_err:
                self._consecutive_errors += 1
                logger.warning(f"Voice stream transport reset: {conn_err}")
                self._on_error(conn_err)
                await asyncio.sleep(0.2)

            except Exception as e:
                # Filter benign connection closure errors during teardown
                err_str = str(e)
                if "10054" in err_str or "closed" in err_str.lower() or "shutdown" in err_str.lower():
                    logger.debug(f"Voice stream connection closed: {e}")
                else:
                    logger.error(f"Voice stream send error: {e}")
                self._consecutive_errors += 1
                self._on_error(e)
                await asyncio.sleep(0.1)

    async def _dispatch_audio(self, session: Any, data: bytes, mime_type: str) -> None:
        """Send audio blob through session according to API capabilities."""
        # Check for Google GenAI Blob / types interface
        from google.genai import types
        await session.send_realtime_input(
            audio=types.Blob(
                data=data,
                mime_type=mime_type,
            )
        )

    def _trigger_stall(self) -> None:
        """Handle detected stream stall."""
        self._stall_count += 1
        logger.warning(f"Voice stream stall detected (count={self._stall_count}). Resetting buffer.")
        self.drain_buffer()
        self._last_send_time = time.monotonic()
        try:
            self._on_stall()
        except Exception:
            pass

    def drain_buffer(self) -> int:
        """Drop all pending audio frames in buffer."""
        drained = 0
        if self._queue is not None:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                    drained += 1
                except Exception:
                    break
        return drained

    def reset(self) -> None:
        """Full reset of buffer and health tracking."""
        self.drain_buffer()
        self._last_send_time = time.monotonic()
        self._consecutive_errors = 0

    def stop(self) -> None:
        """Stop sender loop."""
        self._running = False
        self.drain_buffer()

    def get_health(self) -> dict[str, Any]:
        """Diagnostic snapshot."""
        now = time.monotonic()
        q_size = self._queue.qsize() if self._queue is not None else 0
        silence_sec = round(now - self._last_send_time, 2)
        is_healthy = self._running and (q_size < self._max_queue_size) and (self._consecutive_errors < 3)

        return {
            "is_healthy": is_healthy,
            "queue_size": q_size,
            "max_queue_size": self._max_queue_size,
            "frames_sent": self._frames_sent,
            "bytes_sent": self._bytes_sent,
            "dropped_frames": self._dropped_frames,
            "stall_count": self._stall_count,
            "silence_seconds": silence_sec,
            "consecutive_errors": self._consecutive_errors,
        }
