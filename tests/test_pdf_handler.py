"""
tests/test_pdf_handler.py — Automated Unit Tests for core/pdf_handler.py
Verifies pre-flight checks, canonical path validation, command injection defenses,
zero shell=True execution, and cross-platform dispatch across Windows, macOS, and Linux.
"""

import os
import platform
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.pdf_handler import validate_pdf_path, is_pdf, open_pdf


@pytest.fixture
def temp_pdf_file():
    """Create a temporary valid PDF file with standard magic header."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.5\n%Mock PDF Content for Testing\n%%EOF")
        path = Path(f.name)
    yield path
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


@pytest.fixture
def temp_txt_file():
    """Create a temporary text file that is not a PDF."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"Plain text content without PDF header")
        path = Path(f.name)
    yield path
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


class TestPdfValidation:
    """Tests path canonicalization, pre-flight existence, and magic byte validation."""

    def test_empty_and_none_paths(self):
        ok, reason, canonical = validate_pdf_path("")
        assert not ok
        assert "empty" in reason.lower()
        assert canonical is None

        ok2, reason2, _ = validate_pdf_path("   ")
        assert not ok2
        assert "whitespace" in reason2.lower()

    def test_nonexistent_file(self):
        fake_path = Path("D:/nonexistent_dir/ghost_document.pdf")
        ok, reason, canonical = validate_pdf_path(fake_path)
        assert not ok
        assert "does not exist" in reason.lower()
        assert canonical is None

    def test_directory_rejected(self):
        curr_dir = Path(__file__).parent
        ok, reason, canonical = validate_pdf_path(curr_dir)
        assert not ok
        assert "not a regular file" in reason.lower()

    def test_valid_pdf_file(self, temp_pdf_file):
        ok, reason, canonical = validate_pdf_path(temp_pdf_file)
        assert ok
        assert canonical is not None
        assert canonical.exists()
        assert is_pdf(temp_pdf_file)

    def test_non_pdf_file_rejected(self, temp_txt_file):
        ok, reason, _ = validate_pdf_path(temp_txt_file)
        assert not ok
        assert "not a valid pdf" in reason.lower()
        assert not is_pdf(temp_txt_file)


class TestCommandInjectionDefense:
    """Verifies that command injection payloads and control characters are safely rejected."""

    def test_null_byte_rejection(self):
        payload = "legit.pdf\0; calc.exe"
        ok, reason, _ = validate_pdf_path(payload)
        assert not ok
        assert "illegal character" in reason.lower()

    def test_newline_and_carriage_return_rejection(self):
        payload1 = "report.pdf\nrm -rf /"
        ok1, reason1, _ = validate_pdf_path(payload1)
        assert not ok1
        assert "illegal character" in reason1.lower()

        payload2 = "report.pdf\rcalc.exe"
        ok2, reason2, _ = validate_pdf_path(payload2)
        assert not ok2
        assert "illegal character" in reason2.lower()

    def test_shell_metacharacters_handled_as_literal_path(self):
        # A file path with shell chars that doesn't exist will fail existence check,
        # never execute through shell=True
        malicious = "report.pdf; calc.exe && echo pwned"
        ok, reason, _ = validate_pdf_path(malicious)
        assert not ok
        assert "does not exist" in reason.lower()


class TestCrossPlatformDispatch:
    """Verifies OS-specific dispatch tables without shell execution."""

    def test_windows_dispatch_uses_startfile(self, temp_pdf_file):
        with patch("platform.system", return_value="Windows"), \
             patch("os.startfile", create=True) as mock_startfile:
            ok, msg = open_pdf(temp_pdf_file)
            assert ok
            assert "default windows viewer" in msg.lower()
            mock_startfile.assert_called_once_with(str(temp_pdf_file.resolve()))

    def test_windows_dispatch_fallback_when_startfile_fails(self, temp_pdf_file):
        with patch("platform.system", return_value="Windows"), \
             patch("os.startfile", side_effect=OSError("No association")), \
             patch("core.pdf_handler._find_windows_pdf_viewer", return_value=r"C:\Program Files\Edge\msedge.exe"), \
             patch("subprocess.Popen") as mock_popen:
            ok, msg = open_pdf(temp_pdf_file)
            assert ok
            mock_popen.assert_called_once_with(
                [r"C:\Program Files\Edge\msedge.exe", str(temp_pdf_file.resolve())],
                shell=False
            )

    def test_macos_dispatch(self, temp_pdf_file):
        with patch("platform.system", return_value="Darwin"), \
             patch("subprocess.Popen") as mock_popen:
            ok, msg = open_pdf(temp_pdf_file)
            assert ok
            assert "macos viewer" in msg.lower()
            mock_popen.assert_called_once_with(
                ["open", str(temp_pdf_file.resolve())],
                shell=False
            )

    def test_linux_dispatch_xdg_open(self, temp_pdf_file):
        with patch("platform.system", return_value="Linux"), \
             patch("shutil.which", side_effect=lambda bin: "/usr/bin/xdg-open" if bin == "xdg-open" else None), \
             patch("subprocess.Popen") as mock_popen:
            ok, msg = open_pdf(temp_pdf_file)
            assert ok
            assert "xdg-open" in msg.lower()
            mock_popen.assert_called_once_with(
                ["/usr/bin/xdg-open", str(temp_pdf_file.resolve())],
                shell=False
            )

    def test_custom_viewer_override(self, temp_pdf_file):
        with patch("shutil.which", return_value="/usr/bin/custom-pdf-viewer"), \
             patch("subprocess.Popen") as mock_popen:
            ok, msg = open_pdf(temp_pdf_file, viewer="custom-pdf-viewer")
            assert ok
            assert "custom-pdf-viewer" in msg
            mock_popen.assert_called_once_with(
                ["/usr/bin/custom-pdf-viewer", str(temp_pdf_file.resolve())],
                shell=False
            )
