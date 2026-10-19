"""
tests/test_whatsapp_telegram_browser.py — Tests for WhatsApp and Telegram Autonomous Browser Automation & Persistent Common Session.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from actions.browser_control import (
    _BrowserSession,
    _registry,
    browser_control,
    get_jarvis_common_profile_dir,
    open_url,
)
from actions.send_message import _send_whatsapp, _send_telegram, send_message
from core import outcome


class TestCommonSessionDirectory:
    def test_common_profile_path_is_persistent(self):
        target = get_jarvis_common_profile_dir()
        assert isinstance(target, Path)
        assert target.name == "common_session"
        assert target.parent.name == ".jarvis_profiles"
        assert target.exists()


class TestBrowserControlWhatsAppTelegramRouting:
    def test_open_url_routes_whatsapp_to_persistent_registry(self):
        mock_sess = MagicMock()
        mock_sess.run.return_value = "navigated_whatsapp"
        with patch.object(_registry, "get", return_value=mock_sess), \
             patch("actions.browser_control._open_native") as mock_native:
            res = open_url("https://web.whatsapp.com")
            assert res == "navigated_whatsapp"
            mock_native.assert_not_called()

    def test_open_url_routes_telegram_to_persistent_registry(self):
        mock_sess = MagicMock()
        mock_sess.run.return_value = "navigated_telegram"
        with patch.object(_registry, "get", return_value=mock_sess), \
             patch("actions.browser_control._open_native") as mock_native:
            res = open_url("https://web.telegram.org/a/")
            assert res == "navigated_telegram"
            mock_native.assert_not_called()

    def test_browser_control_action_open_whatsapp(self):
        mock_sess = MagicMock()
        mock_sess.run.return_value = "status=done action=browser_control status=logged_in"
        with patch.object(_registry, "get", return_value=mock_sess):
            res = browser_control({"action": "open_whatsapp"})
            assert "logged_in" in res
            mock_sess.run.assert_called_once()

    def test_browser_control_action_open_telegram(self):
        mock_sess = MagicMock()
        mock_sess.run.return_value = "status=done action=browser_control status=logged_in"
        with patch.object(_registry, "get", return_value=mock_sess):
            res = browser_control({"action": "open_telegram"})
            assert "logged_in" in res
            mock_sess.run.assert_called_once()

    def test_browser_control_action_whatsapp_send(self):
        mock_sess = MagicMock()
        mock_sess.run.return_value = outcome.done("send_message", platform="WhatsApp", to="John", verified=True)
        with patch.object(_registry, "get", return_value=mock_sess):
            res = browser_control({"action": "whatsapp_send", "receiver": "John", "text": "Hello"})
            assert "status=done" in res
            assert "John" in res

    def test_browser_control_action_telegram_send(self):
        mock_sess = MagicMock()
        mock_sess.run.return_value = outcome.done("send_message", platform="Telegram", to="Alex", verified=True)
        with patch.object(_registry, "get", return_value=mock_sess):
            res = browser_control({"action": "telegram_send", "receiver": "Alex", "text": "Hey"})
            assert "status=done" in res
            assert "Alex" in res


class TestSendMessageIntegration:
    def test_send_whatsapp_uses_browser_driver(self):
        mock_sess = MagicMock()
        mock_sess.run.return_value = outcome.done("send_message", platform="WhatsApp", to="Mom", verified=True)
        with patch("actions.browser_control._registry.get", return_value=mock_sess):
            res = _send_whatsapp("Mom", "Love you")
            assert outcome.is_done(res)
            mock_sess.run.assert_called_once()

    def test_send_telegram_uses_browser_driver(self):
        mock_sess = MagicMock()
        mock_sess.run.return_value = outcome.done("send_message", platform="Telegram", to="Boss", verified=True)
        with patch("actions.browser_control._registry.get", return_value=mock_sess):
            res = _send_telegram("Boss", "Report ready")
            assert outcome.is_done(res)
            mock_sess.run.assert_called_once()

    def test_send_whatsapp_qr_code_reported_clearly(self):
        mock_sess = MagicMock()
        mock_sess.run.return_value = outcome.unverified(
            "send_message",
            "WhatsApp Web QR code is showing. Please scan the QR code in the browser to log in once.",
            platform="WhatsApp",
            to="Dad"
        )
        with patch("actions.browser_control._registry.get", return_value=mock_sess):
            res = _send_whatsapp("Dad", "Hi")
            assert "qr code" in res.lower()
