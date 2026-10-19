"""
tests/test_presentation_mode.py — Unit tests for presentation_mode action & PDF generator
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from actions.presentation_mode import (
    TOOL,
    generate_college_pdf,
    presentation_action,
    _speak_line,
    _run_full_presentation,
    _stop_event,
)


def test_tool_declaration_structure():
    assert TOOL["name"] == "presentation_mode"
    assert "parameters" in TOOL
    assert "handler" in TOOL
    assert callable(TOOL["handler"])
    assert "properties" in TOOL["parameters"]
    assert "action" in TOOL["parameters"]["properties"]


def test_generate_college_pdf(tmp_path):
    target_pdf = tmp_path / "test_report.pdf"
    res = generate_college_pdf(target_pdf)
    assert res.exists()
    assert res.is_file()
    assert res.stat().st_size > 500


def test_presentation_action_stop():
    mock_player = MagicMock()
    msg = presentation_action({"action": "stop"}, player=mock_player)
    assert "stopped" in msg.lower()
    assert _stop_event.is_set()


def test_presentation_action_emergency():
    mock_player = MagicMock()
    with patch("actions.presentation_mode._speak_line") as mock_speak:
        res = presentation_action({"action": "emergency"}, player=mock_player)
        assert len(res) > 0
        mock_speak.assert_called_once()


def test_presentation_action_start_spawns_thread():
    mock_player = MagicMock()
    with patch("threading.Thread.start") as mock_start:
        res = presentation_action({"action": "start"}, player=mock_player)
        assert "presentation mode" in res.lower()
        mock_start.assert_called_once()
