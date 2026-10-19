"""
Unit tests for core/voice_processor.py (VoiceStreamManager).
"""
import asyncio
import time
import pytest
from core.voice_processor import VoiceStreamManager


class MockSession:
    def __init__(self, delay: float = 0.0, fail_with: Exception | None = None):
        self.delay = delay
        self.fail_with = fail_with
        self.sent_blobs = []

    async def send_realtime_input(self, audio):
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self.fail_with:
            raise self.fail_with
        self.sent_blobs.append(audio)


@pytest.mark.anyio
async def test_enqueue_threadsafe_and_drop_stale():
    loop = asyncio.get_running_loop()
    manager = VoiceStreamManager(
        session_provider=lambda: None,
        max_queue_size=3,
    )
    manager.attach_loop(loop)

    # Push 5 frames into queue of maxsize 3
    for i in range(5):
        manager.enqueue_frame_threadsafe(f"frame_{i}".encode("utf-8"))

    # Yield control so loop callbacks execute
    await asyncio.sleep(0.01)

    health = manager.get_health()
    assert health["queue_size"] <= 3
    assert health["dropped_frames"] >= 2


@pytest.mark.anyio
async def test_run_sender_transmits_frames():
    loop = asyncio.get_running_loop()
    mock_session = MockSession()
    manager = VoiceStreamManager(
        session_provider=lambda: mock_session,
        max_queue_size=10,
    )
    manager.attach_loop(loop)

    sender_task = asyncio.create_task(manager.run_sender())

    # Send 2 frames
    manager.enqueue_frame_threadsafe(b"audio_chunk_1")
    manager.enqueue_frame_threadsafe(b"audio_chunk_2")

    await asyncio.sleep(0.1)

    manager.stop()
    await asyncio.sleep(0.02)
    sender_task.cancel()
    try:
        await sender_task
    except asyncio.CancelledError:
        pass

    assert len(mock_session.sent_blobs) == 2
    assert mock_session.sent_blobs[0].data == b"audio_chunk_1"
    assert mock_session.sent_blobs[1].data == b"audio_chunk_2"
    health = manager.get_health()
    assert health["frames_sent"] == 2


@pytest.mark.anyio
async def test_frame_timeout_triggers_stall():
    loop = asyncio.get_running_loop()
    # Mock session hangs for 2.0s
    mock_session = MockSession(delay=2.0)
    stall_called = []

    manager = VoiceStreamManager(
        session_provider=lambda: mock_session,
        frame_timeout=0.1,  # Fast timeout
        on_stall=lambda: stall_called.append(True),
    )
    manager.attach_loop(loop)

    sender_task = asyncio.create_task(manager.run_sender())
    manager.enqueue_frame_threadsafe(b"hanging_frame")

    await asyncio.sleep(0.3)

    manager.stop()
    sender_task.cancel()
    try:
        await sender_task
    except asyncio.CancelledError:
        pass

    assert len(stall_called) > 0
    health = manager.get_health()
    assert health["stall_count"] > 0


@pytest.mark.anyio
async def test_connection_reset_handled_cleanly():
    loop = asyncio.get_running_loop()
    mock_session = MockSession(fail_with=ConnectionResetError("Socket closed [WinError 10054]"))
    errors_reported = []

    manager = VoiceStreamManager(
        session_provider=lambda: mock_session,
        on_error=lambda err: errors_reported.append(err),
    )
    manager.attach_loop(loop)

    sender_task = asyncio.create_task(manager.run_sender())
    manager.enqueue_frame_threadsafe(b"reset_frame")

    await asyncio.sleep(0.3)

    manager.stop()
    sender_task.cancel()
    try:
        await sender_task
    except asyncio.CancelledError:
        pass

    assert len(errors_reported) > 0
    assert isinstance(errors_reported[0], ConnectionResetError)
