"""
ui_holo.py — J.A.R.V.I.S. MARK LVI 3D Holographic Neural Core Desktop Window
Renders the full React + Three.js 3D Holographic Neural Core as a native, hardware-accelerated
desktop application using pywebview and Microsoft Edge WebView2.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import webview
from memory.config_manager import get_assistant_name, is_configured

BASE_DIR = Path(__file__).resolve().parent
PORT = 8000

# HTML bootstrap page displayed immediately while FastAPI/uvicorn binds port 8000
BOOTSTRAP_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>J.A.R.V.I.S. // MARK LVI</title>
<style>
  body {
    margin: 0;
    padding: 0;
    background: #030712;
    color: #38bdf8;
    font-family: 'Courier New', monospace;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    user-select: none;
    overflow: hidden;
  }
  .core {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    border: 2px solid rgba(56, 189, 248, 0.15);
    border-top: 2px solid #38bdf8;
    border-right: 2px solid #0284c7;
    animation: spin 1s infinite linear;
    box-shadow: 0 0 35px rgba(56, 189, 248, 0.25);
  }
  @keyframes spin { 100% { transform: rotate(360deg); } }
  .title {
    margin-top: 26px;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.35em;
    color: #f8fafc;
  }
  .status {
    margin-top: 10px;
    font-size: 11px;
    letter-spacing: 0.18em;
    color: #64748b;
  }
</style>
</head>
<body>
  <div class="core"></div>
  <div class="title">J.A.R.V.I.S. NEURAL CORE</div>
  <div class="status" id="st">CONNECTING TO MARK-56 SUBSYSTEMS...</div>
  <script>
    let tries = 0;
    async function checkServer() {
      tries++;
      try {
        const res = await fetch('http://127.0.0.1:8000/api/system-metrics', { mode: 'cors' });
        if (res.ok) {
          const st = document.getElementById('st');
          if (st) st.textContent = 'NEURAL CORE ONLINE. ENGAGING 3D PARTICLE SWARM...';
          window.location.replace('http://127.0.0.1:8000/');
          return;
        }
      } catch(e) {}
      if (tries > 5) {
        const st = document.getElementById('st');
        if (st) st.textContent = 'CONNECTING TO MARK-56 SUBSYSTEMS (ATTEMPT ' + tries + ')...';
      }
      setTimeout(checkServer, 150);
    }
    setTimeout(checkServer, 80);
  </script>
</body>
</html>
"""

class HoloJsApi:
    """Methods exposed to JavaScript as window.pywebview.api."""

    def __init__(self, ui: "JarvisHoloUI"):
        self._ui = ui

    def send_command(self, cmd: str) -> bool:
        c = str(cmd or "").strip()
        if c and self._ui.on_text_command:
            self._ui.on_text_command(c)
            return True
        return False

    def wake(self) -> bool:
        if self._ui.on_wake_manual:
            self._ui.on_wake_manual()
            return True
        return False

    def toggle_mute(self) -> bool:
        self._ui.muted = not self._ui.muted
        return self._ui.muted

    def interrupt(self) -> bool:
        if self._ui.on_interrupt:
            self._ui.on_interrupt()
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self._ui.state,
            "muted": self._ui.muted,
            "assistant_name": self._ui.assistant_name,
        }


class _HoloRootShim:
    def __init__(self, ui: "JarvisHoloUI"):
        self._ui = ui

    def mainloop(self):
        self._ui.run()

    def protocol(self, *_):
        pass


class JarvisHoloUI:
    """
    Desktop Holographic Neural Core UI wrapper for J.A.R.V.I.S. MARK LVI.
    Replaces software QPainter with full 3D WebGL Three.js inside Edge WebView2.
    """

    def __init__(self, face_path: str = "face.png", size=None):
        self._assistant_name: str = get_assistant_name()
        self.state: str = "LISTENING"
        self._muted: bool = False
        self._window: Optional[webview.Window] = None
        self._api = HoloJsApi(self)
        self.root = _HoloRootShim(self)
        self._last_audio_send: float = 0.0

        # Callbacks expected by JarvisLive
        self.on_text_command: Optional[Callable[[str], None]] = None
        self.on_push_to_talk: Optional[Callable[[bool], None]] = None
        self.ptt_hold: Optional[Callable[[bool], None]] = None
        self.on_interrupt: Optional[Callable[[], None]] = None
        self.on_voice_change: Optional[Callable[[str], None]] = None
        self.on_audio_device_change: Optional[Callable[[str, str], None]] = None
        self.on_remote_clicked: Optional[Callable[[], None]] = None
        self.on_wake_toggle: Optional[Callable[[bool], str]] = None
        self.on_wake_manual: Optional[Callable[[], None]] = None
        self.on_wake_install: Optional[Callable[[], tuple]] = None
        self.on_state_changed: Optional[Callable[[str], None]] = None
        self.get_plugins: Optional[Callable[[], Any]] = None
        self.get_plugin_settings: Optional[Callable[[], Any]] = None
        self.wake_is_ready: Optional[Callable[[], bool]] = None
        self.wake_get_state: Optional[Callable[[], dict]] = None
        self.request_say: Optional[Callable[[str], None]] = None

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, val: bool):
        self._muted = bool(val)
        self._dispatch("jarvis-mute", {"muted": self._muted})

    @property
    def current_file(self) -> Optional[str]:
        return None

    @property
    def assistant_name(self) -> str:
        return self._assistant_name

    def wait_for_api_key(self):
        while not is_configured():
            time.sleep(0.2)

    def set_state(self, state: str) -> None:
        self.state = state
        self._dispatch("jarvis-state", {"state": state})
        if self.on_state_changed and callable(self.on_state_changed):
            try:
                self.on_state_changed(state)
            except Exception:
                pass

    def set_audio_level(self, level: float) -> None:
        now = time.time()
        if now - self._last_audio_send >= 0.04:  # ~25fps throttle
            self._last_audio_send = now
            self._dispatch("jarvis-audio", {"level": float(level)})

    def write_log(self, text: str) -> None:
        print(text)
        self._dispatch("jarvis-log", {"text": str(text)})

    def show_content(self, title: str, text: str) -> None:
        self._dispatch("jarvis-content", {"title": title, "text": text})

    def show_quiz(self, topic: str, questions, grade=None) -> None:
        self._dispatch("jarvis-quiz", {"topic": topic, "questions": questions})

    def hide_quiz(self) -> None:
        self._dispatch("jarvis-hide-quiz", {})

    def show_confirm(self, title: str, detail: str) -> None:
        self._dispatch("jarvis-confirm", {"title": title, "detail": detail})

    def hide_confirm(self) -> None:
        self._dispatch("jarvis-hide-confirm", {})

    def show_review(self, title: str, summary: str, findings, unclear=None) -> None:
        self._dispatch("jarvis-review", {"title": title, "summary": summary, "findings": findings})

    def prompt_reconfig(self) -> None:
        self._dispatch("jarvis-reconfig", {})

    def show_camera_frame(self, img_bytes: bytes) -> None:
        pass

    def start_camera_stream(self) -> None:
        pass

    def stop_camera_stream(self) -> None:
        pass

    def push_visemes(self, frames, hop: float, at: float) -> None:
        pass

    def glance(self, dx: float, dy: float, hold: float = 1.1) -> None:
        pass

    def notify_phone_connected(self) -> None:
        self.write_log("SYS: Remote Dashboard connected.")

    def start_speaking(self) -> None:
        self.set_state("SPEAKING")

    def stop_speaking(self) -> None:
        if not self.muted:
            self.set_state("LISTENING")

    def _dispatch(self, event_name: str, detail: dict) -> None:
        if self._window is not None:
            try:
                js_detail = json.dumps(detail)
                code = f"window.dispatchEvent(new CustomEvent('{event_name}', {{ detail: {js_detail} }}));"
                self._window.evaluate_js(code)
            except Exception:
                pass

    def close(self) -> None:
        if self._window is not None:
            try:
                self._window.destroy()
            except Exception:
                pass

    def run(self) -> None:
        """Main thread entrypoint for desktop pywebview window."""
        is_ready = False
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.2):
                is_ready = True
        except Exception:
            is_ready = False

        if is_ready:
            print(f"[HoloUI] Server active on port {PORT}. Opening 3D Holographic UI directly...")
            self._window = webview.create_window(
                title="J.A.R.V.I.S. // MARK LVI — HOLOGRAPHIC NEURAL CORE",
                url=f"http://127.0.0.1:{PORT}/",
                width=1280,
                height=820,
                min_size=(960, 620),
                background_color="#030712",
                js_api=self._api,
            )
        else:
            print(f"[HoloUI] Launching bootstrap window, waiting for port {PORT}...")
            self._window = webview.create_window(
                title="J.A.R.V.I.S. // MARK LVI — HOLOGRAPHIC NEURAL CORE",
                html=BOOTSTRAP_HTML,
                width=1280,
                height=820,
                min_size=(960, 620),
                background_color="#030712",
                js_api=self._api,
            )

            def _watch():
                for _ in range(120):
                    try:
                        with socket.create_connection(("127.0.0.1", PORT), timeout=0.25):
                            time.sleep(0.15)
                            if self._window is not None:
                                print(f"[HoloUI] Mark-56 server ready on port {PORT}. Connecting...")
                                try:
                                    self._window.load_url(f"http://127.0.0.1:{PORT}/")
                                except Exception:
                                    pass
                            break
                    except Exception:
                        time.sleep(0.15)

            threading.Thread(target=_watch, daemon=True).start()

        webview.start(debug=False)
