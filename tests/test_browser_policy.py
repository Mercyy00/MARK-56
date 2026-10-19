"""
tests/test_browser_policy.py — Automated Unit Tests for the JARVIS Default Browser Policy.
Verifies that:
  1. The internal policy overrides the host OS default (e.g. Brave) with the configured browser (e.g. Google Chrome).
  2. Executables are resolved directly and launched via subprocess.Popen (no os.startfile leakage).
  3. Explicit parameters supersede configuration defaults.
  4. Missing configured browsers fall back gracefully to the host default.
  5. Configuration persistence via config_manager and browser_control actions works seamlessly.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from actions.browser_control import (
    _open_native,
    _resolve_browser_executable,
    browser_control,
    get_jarvis_browser,
    is_browser_available,
    open_url,
    _native_tracker,
)
from memory import config_manager


class TestJarvisBrowserPolicyResolution:
    """Verifies priority resolution between explicit args, config policy, and host default."""

    def test_default_policy_resolves_chrome_over_host_brave(self):
        with patch("memory.config_manager.get_default_browser", return_value="chrome"), \
             patch("actions.browser_control._detect_default_browser", return_value="brave"), \
             patch("actions.browser_control.is_browser_available", return_value=True):
            resolved = get_jarvis_browser()
            assert resolved == "chrome", "Configured JARVIS browser must supersede host OS default"

    def test_explicit_argument_overrides_configured_policy(self):
        with patch("memory.config_manager.get_default_browser", return_value="chrome"), \
             patch("actions.browser_control.is_browser_available", return_value=True):
            assert get_jarvis_browser(preferred="firefox") == "firefox"
            assert get_jarvis_browser(preferred="edge") == "edge"
            assert get_jarvis_browser(preferred="Microsoft Edge") == "edge"

    def test_fallback_to_host_default_when_configured_browser_unavailable(self):
        def fake_available(name):
            return name == "brave"

        with patch("memory.config_manager.get_default_browser", return_value="chrome"), \
             patch("actions.browser_control.is_browser_available", side_effect=fake_available), \
             patch("actions.browser_control._detect_default_browser", return_value="brave"):
            resolved = get_jarvis_browser()
            assert resolved == "brave", "Should fall back gracefully to host default if configured browser is not installed"

    def test_system_config_explicitly_delegates_to_host_default(self):
        with patch("memory.config_manager.get_default_browser", return_value="system"), \
             patch("actions.browser_control._detect_default_browser", return_value="brave"), \
             patch("actions.browser_control.is_browser_available", return_value=True):
            resolved = get_jarvis_browser()
            assert resolved == "brave", "'system' setting must defer to host OS detection"


class TestConfigManagerBrowserPersistence:
    """Verifies roundtrip reading and writing of browser preferences."""

    def test_browser_config_persistence(self, tmp_path):
        fake_config_file = tmp_path / "api_keys.json"
        with patch("memory.config_manager.CONFIG_FILE", fake_config_file), \
             patch("memory.config_manager.CONFIG_DIR", tmp_path):
            assert config_manager.get_default_browser() == "chrome"

            config_manager.save_default_browser("edge")
            assert config_manager.get_default_browser() == "edge"

            config_manager.save_default_browser("brave")
            assert config_manager.get_default_browser() == "brave"

            # Unknown browser collapses safely to default
            config_manager.save_default_browser("nonexistent_browser_xyz")
            assert config_manager.get_default_browser() == "chrome"

    def test_custom_executable_path_persistence(self, tmp_path):
        fake_config_file = tmp_path / "api_keys.json"
        custom_exe = r"D:\custom\chrome.exe"
        with patch("memory.config_manager.CONFIG_FILE", fake_config_file), \
             patch("memory.config_manager.CONFIG_DIR", tmp_path):
            assert config_manager.get_browser_executable_path("chrome") is None
            config_manager.save_browser_executable_path("chrome", custom_exe)
            assert config_manager.get_browser_executable_path("chrome") == custom_exe


class TestBrowserExecutableResolution:
    """Verifies accurate probing of browser binaries on disk."""

    def test_custom_override_path_takes_precedence(self):
        fake_path = r"C:\fake\browser\chrome.exe"
        with patch("memory.config_manager.get_browser_executable_path", return_value=fake_path), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.resolve", return_value=Path(fake_path)):
            resolved = _resolve_browser_executable("chrome")
            assert resolved == fake_path

    def test_windows_registry_and_filesystem_probing(self):
        with patch("actions.browser_control._OS", "Windows"), \
             patch("memory.config_manager.get_browser_executable_path", return_value=None), \
             patch("actions.browser_control._find_exe_windows", return_value=r"C:\Program Files\Google\Chrome\Application\chrome.exe"), \
             patch("pathlib.Path.exists", return_value=True):
            resolved = _resolve_browser_executable("chrome")
            assert "chrome.exe" in resolved.lower()


class TestNativeLaunchPolicyEnforcement:
    """Verifies that native navigation routes to the target browser executable without host leakage."""

    def test_open_native_launches_chrome_binary_directly(self):
        fake_chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        with patch("actions.browser_control.get_jarvis_browser", return_value="chrome"), \
             patch("actions.browser_control._resolve_browser_executable", return_value=fake_chrome_exe), \
             patch("subprocess.Popen") as mock_popen, \
             patch("os.startfile") as mock_startfile:
            res = _open_native("https://youtube.com")
            assert "opened in chrome" in res.lower()
            mock_popen.assert_called_once()
            called_cmd = mock_popen.call_args[0][0]
            assert called_cmd[0] == fake_chrome_exe
            assert called_cmd[1] == "https://youtube.com"
            mock_startfile.assert_not_called()

    def test_open_url_tracks_configured_browser(self):
        fake_chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        with patch("actions.browser_control.get_jarvis_browser", return_value="chrome"), \
             patch("actions.browser_control._resolve_browser_executable", return_value=fake_chrome_exe), \
             patch("subprocess.Popen"):
            res = open_url("https://news.ycombinator.com")
            assert "opened in chrome" in res.lower()
            candidates = _native_tracker.find_candidates("ycombinator")
            assert len(candidates) >= 1
            assert candidates[0].browser == "chrome"


class TestBrowserControlActions:
    """Verifies set_default_browser and get_browser_config actions in browser_control."""

    def test_set_default_browser_action(self):
        with patch("memory.config_manager.save_default_browser") as mock_save:
            res = browser_control({"action": "set_default_browser", "browser": "edge"})
            assert "jarvis default browser set to: edge" in res.lower()
            mock_save.assert_called_once_with("edge")

    def test_get_browser_config_action(self):
        with patch("memory.config_manager.get_default_browser", return_value="chrome"), \
             patch("actions.browser_control._detect_default_browser", return_value="brave"), \
             patch("actions.browser_control.get_jarvis_browser", return_value="chrome"), \
             patch("actions.browser_control._resolve_browser_executable", return_value=r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
            res = browser_control({"action": "get_browser_config"})
            assert "configured: chrome" in res.lower()
            assert "host os default: brave" in res.lower()
            assert "active effective: chrome" in res.lower()
            assert "chrome.exe" in res.lower()
