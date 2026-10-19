"""
tests/test_browser_termination.py — Automated Unit Tests for actions/browser_control.py
Verifies the 3-tier escalation for browser tab termination:
  Tier 1: Graceful Playwright/CDP close (page.close())
  Tier 2: Raw CDP Target.closeTarget
  Tier 3: Process-tree PID resolution and OS-level forceful termination (taskkill on Windows, kill -9 on Unix)
"""

import asyncio
import os
import platform
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from actions.browser_control import _BrowserSession, _os_force_kill


class FakePage:
    """Mock Playwright Page that accurately simulates lifecycle and is_closed state."""
    def __init__(self, url="https://example.com", title_text="Mock Page"):
        self.url = url
        self._title_text = title_text
        self._closed = False
        self.context = MagicMock()

    def is_closed(self) -> bool:
        return self._closed

    async def close(self, run_before_unload: bool = False):
        self._closed = True

    async def title(self) -> str:
        return self._title_text


class TestOsForceKill:
    """Verifies that OS-level process termination is executed safely with own_pids protection."""

    def test_refuse_kill_own_process(self):
        current_pid = os.getpid()
        with patch("core.appidentity.own_pids", return_value={current_pid}):
            killed = _os_force_kill(current_pid)
            assert not killed, "Should refuse to kill the assistant's own PID"

    def test_windows_taskkill_execution(self):
        target_pid = 99999
        with patch("core.appidentity.own_pids", return_value={100}), \
             patch("platform.system", return_value="Windows"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            killed = _os_force_kill(target_pid)
            assert killed
            mock_run.assert_called_once_with(
                ["taskkill", "/F", "/T", "/PID", str(target_pid)],
                capture_output=True,
                check=False
            )

    def test_posix_sigkill_execution(self):
        target_pid = 88888
        with patch("core.appidentity.own_pids", return_value={100}), \
             patch("platform.system", return_value="Linux"), \
             patch("os.kill") as mock_kill:
            killed = _os_force_kill(target_pid)
            assert killed
            mock_kill.assert_called_once_with(target_pid, 9)


class TestMultiStageTabTermination:
    """Verifies 3-tier escalation behavior in _BrowserSession.close_tab."""

    @pytest.mark.anyio
    async def test_no_active_session(self):
        sess = _BrowserSession("chrome")
        sess._context = None
        result = await sess.close_tab()
        assert "no active browser session" in result.lower()

    @pytest.mark.anyio
    async def test_tier1_graceful_close_success(self):
        sess = _BrowserSession("chrome")
        mock_ctx = MagicMock()
        page = FakePage(url="https://example.com/test")
        mock_ctx.pages = [page]

        sess._context = mock_ctx
        sess._page = page

        result = await sess.close_tab(timeout=0.5)
        assert "tier 1: graceful close" in result.lower()
        assert page.is_closed()
        assert sess._page is None

    @pytest.mark.anyio
    async def test_tier2_cdp_close_when_tier1_times_out(self):
        sess = _BrowserSession("chrome")
        mock_ctx = MagicMock()
        page = FakePage(url="https://hung-site.com")

        # Tier 1 page.close hangs/times out
        async def hang_close(*args, **kwargs):
            await asyncio.sleep(5.0)

        page.close = hang_close

        # Mock CDP session on the page's context
        mock_cdp = MagicMock()
        mock_cdp.send = AsyncMock(side_effect=[
            {"targetInfo": {"targetId": "TARGET-123"}},  # Target.getTargetInfo
            {"success": True},                          # Target.closeTarget
        ])
        page.context.new_cdp_session = AsyncMock(return_value=mock_cdp)
        mock_ctx.pages = [page]

        sess._context = mock_ctx
        sess._page = page

        result = await sess.close_tab(timeout=0.1)
        assert "tier 2: raw cdp target.closetarget" in result.lower()
        mock_cdp.send.assert_any_await("Target.closeTarget", {"targetId": "TARGET-123"})

    @pytest.mark.anyio
    async def test_tier3_forceful_kill_when_tier1_and_2_fail(self):
        sess = _BrowserSession("chrome")
        mock_ctx = MagicMock()
        page = FakePage(url="https://frozen-renderer.com")

        # Tier 1 fails
        page.close = AsyncMock(side_effect=RuntimeError("Page close deadlocked"))

        # Tier 2 fails
        page.context.new_cdp_session = AsyncMock(side_effect=RuntimeError("CDP connection failed"))
        mock_ctx.pages = [page]

        sess._context = mock_ctx
        sess._page = page

        # Mock resolving renderer PID and killing it
        with patch.object(sess, "_get_tab_renderer_pid", AsyncMock(return_value=54321)), \
             patch("actions.browser_control._os_force_kill", return_value=True) as mock_kill:
            result = await sess.close_tab(timeout=0.1)
            assert "tier 3: os process kill, pid 54321" in result.lower()
            mock_kill.assert_called_once_with(54321)

    @pytest.mark.anyio
    async def test_close_tab_matching_url_filter(self):
        sess = _BrowserSession("chrome")
        mock_ctx = MagicMock()

        p1 = FakePage(url="https://keep-open.com")
        p2 = FakePage(url="https://target-to-close.com/deep/path")

        mock_ctx.pages = [p1, p2]
        sess._context = mock_ctx
        sess._page = p1

        result = await sess.close_tab(url="target-to-close")
        assert "tier 1: graceful close" in result.lower()
        assert "target-to-close.com" in result
        assert p2.is_closed()
        assert not p1.is_closed()
        assert sess._page == p1


class TestNativeTabClosure:
    """Verifies native browser tab closure fallback for un-instrumented browsers."""

    def test_close_native_tab_success(self):
        from actions.browser_control import _close_native_tab
        with patch("actions.browser_control._get_window_list", return_value=[]), \
             patch("subprocess.run") as mock_run, \
             patch("pyautogui.hotkey") as mock_hotkey:
            mock_run.return_value = MagicMock(stdout="True\n", returncode=0)
            res = _close_native_tab(title="YouTube")
            assert "closed native browser tab" in res.lower()
            assert "youtube" in res.lower()
            mock_hotkey.assert_called_once()

    def test_close_native_tab_via_hwnd(self):
        import ctypes
        from actions.browser_control import _close_native_tab
        fake_windows = [{"hwnd": 9999, "pid": 1234, "title": "YouTube - Brave"}]
        with patch("actions.browser_control._get_window_list", return_value=fake_windows), \
             patch.object(ctypes.windll.user32, "ShowWindow") as mock_show, \
             patch.object(ctypes.windll.user32, "SetForegroundWindow") as mock_fg, \
             patch("pyautogui.hotkey") as mock_hotkey:
            res = _close_native_tab(title="YouTube")
            assert "closed native browser tab" in res.lower()
            assert "youtube" in res.lower()
            mock_show.assert_called_once_with(9999, 9)
            mock_fg.assert_called_once_with(9999)
            mock_hotkey.assert_called_once()

    def test_close_native_tab_window_not_found(self):
        from actions.browser_control import _close_native_tab
        with patch("actions.browser_control._get_window_list", return_value=[]), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="False\n", returncode=0)
            res = _close_native_tab(title="NonExistentTab")
            assert "no active browser session or window found" in res.lower()


class TestComputerControlWebInterception:
    """Verifies that computer_control.close_app gracefully handles web applications."""

    def test_close_app_intercepts_youtube(self):
        from actions.computer_control import _close_app
        with patch("core.appidentity.running", return_value=[]), \
             patch("actions.browser_control._close_native_tab", return_value="Closed native browser tab (YouTube).") as mock_close:
            res = _close_app("youtube")
            assert "status=done" in res.lower()
            assert "web tab" in res.lower()
            mock_close.assert_called_once_with(title="youtube")

    def test_close_app_non_web_reports_not_running(self):
        from actions.computer_control import _close_app
        with patch("core.appidentity.running", return_value=[]):
            res = _close_app("some_random_offline_app")
            assert "failed" in res.lower()
            assert "no running application" in res.lower()


class TestNativeTabTrackerAndOpenUrl:
    """Verifies that direct URLs are tracked, canonicalized, and listed correctly."""

    def test_tracker_record_find_and_pop(self):
        from actions.browser_control import NativeTabTracker
        tracker = NativeTabTracker()
        rec = tracker.record(url="https://github.com/deepmind", browser="brave", title="GitHub DeepMind")
        assert rec.domain == "github"
        assert rec.url == "https://github.com/deepmind"

        candidates = tracker.find_candidates("github")
        assert len(candidates) == 1
        assert candidates[0].domain == "github"

        popped = tracker.pop_latest("github")
        assert popped is not None
        assert popped.url == "https://github.com/deepmind"
        assert len(tracker.find_candidates("github")) == 0

    def test_open_url_records_and_dispatches(self):
        from actions.browser_control import open_url, _native_tracker
        with patch("actions.browser_control._open_native", return_value="Opened in default browser: https://example.org") as mock_open:
            res = open_url("https://example.org")
            assert "opened" in res.lower()
            mock_open.assert_called_once_with("https://example.org", "chrome")
            candidates = _native_tracker.find_candidates("example")
            assert len(candidates) >= 1

    def test_open_app_routes_web_destination(self):
        from actions.open_app import open_app
        with patch("actions.browser_control.open_url", return_value="Opened in default browser: https://reddit.com") as mock_open:
            res = open_app({"app_name": "https://reddit.com"})
            assert "status=done" in res.lower()
            assert "reddit.com" in res.lower()
            mock_open.assert_called_once_with("https://reddit.com")

    def test_youtube_video_open_url_delegates(self):
        from actions.youtube_video import _open_url
        with patch("actions.browser_control.open_url") as mock_open:
            _open_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            mock_open.assert_called_once_with("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_browser_control_list_tabs(self):
        from actions.browser_control import browser_control, _native_tracker
        _native_tracker.record("https://news.ycombinator.com", "brave", "Hacker News")
        res = browser_control({"action": "list_tabs"})
        assert "tracked native tabs" in res.lower()
        assert "news.ycombinator.com" in res.lower()


