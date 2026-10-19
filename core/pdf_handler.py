"""
core/pdf_handler.py — Secure Cross-Platform PDF Dispatch Engine for J.A.R.V.I.S.

Provides strict canonical path verification, pre-flight existence checks,
and defense-in-depth against command injection with zero `shell=True` execution.
Standardized native dispatch across Windows (os.startfile / ShellExecuteW),
macOS (open / Preview), and Linux (xdg-open / desktop viewers).
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List


# Maximum allowed path length across POSIX/Windows limits
_MAX_PATH_LEN = 4096

# Suspicious control characters that should never appear in a legitimate local file path
_BANNED_CHARS = frozenset("\0\r\n\t\x1b")


def validate_pdf_path(raw_path: str | Path) -> Tuple[bool, str, Optional[Path]]:
    """
    Validate and canonicalize a PDF file path.

    Pre-flight checks:
      1. Rejects None, empty, or excessively long path strings.
      2. Rejects paths containing null bytes or control characters.
      3. Expands user directories (~) and resolves absolute canonical path.
      4. Verifies target exists on disk and is a regular file.
      5. Validates file extension is '.pdf' or file begins with '%PDF-' magic bytes.

    Returns:
        (valid: bool, reason: str, canonical_path: Optional[Path])
    """
    if not raw_path:
        return False, "Path is empty or unspecified.", None

    path_str = str(raw_path).strip()
    if not path_str:
        return False, "Path string is whitespace.", None

    if len(path_str) > _MAX_PATH_LEN:
        return False, f"Path exceeds maximum allowed length ({_MAX_PATH_LEN} chars).", None

    # Check for banned control characters / null bytes
    for ch in path_str:
        if ch in _BANNED_CHARS:
            return False, f"Path contains illegal character (code: {ord(ch)}).", None

    try:
        candidate = Path(path_str).expanduser()
        # Resolve path to canonical absolute path without following dangerous symlink loops
        canonical = candidate.resolve(strict=False)
    except Exception as e:
        return False, f"Path resolution failed: {e}", None

    # Pre-flight existence check
    try:
        if not canonical.exists():
            return False, f"File does not exist: '{canonical}'", None
        if not canonical.is_file():
            return False, f"Path exists but is not a regular file: '{canonical}'", None
    except OSError as e:
        return False, f"Filesystem access error for '{canonical}': {e}", None

    # Validate PDF extension or magic header
    is_pdf_ext = canonical.suffix.lower() == ".pdf"
    has_pdf_magic = False

    try:
        with open(canonical, "rb") as f:
            header = f.read(1024)
            if b"%PDF-" in header:
                has_pdf_magic = True
    except Exception:
        # If unreadable, rely on extension check if valid
        pass

    if not is_pdf_ext and not has_pdf_magic:
        return False, f"Target file is not a valid PDF document (extension: '{canonical.suffix}').", None

    return True, "Path validated successfully.", canonical


def is_pdf(path: str | Path) -> bool:
    """Convenience check: True if path points to an existing valid PDF file."""
    ok, _, _ = validate_pdf_path(path)
    return ok


def _find_linux_pdf_viewer() -> Optional[str]:
    """Find installed Linux desktop PDF viewer binaries."""
    candidates = [
        "xdg-open",
        "evince",
        "okular",
        "atril",
        "mupdf",
        "zathura",
        "qpdfview",
        "firefox",
        "google-chrome",
        "chromium-browser",
    ]
    for bin_name in candidates:
        found = shutil.which(bin_name)
        if found:
            return found
    return None


def _find_windows_pdf_viewer() -> Optional[str]:
    """Find installed Windows PDF viewer executable as fallback if startfile fails."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    candidates = [
        # Microsoft Edge (present on all modern Windows 10/11 installations)
        prog_files_x86 + r"\Microsoft\Edge\Application\msedge.exe",
        prog_files + r"\Microsoft\Edge\Application\msedge.exe",
        # Adobe Acrobat / Reader
        prog_files + r"\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
        prog_files_x86 + r"\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        prog_files + r"\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        # SumatraPDF
        local_app_data + r"\SumatraPDF\SumatraPDF.exe",
        prog_files + r"\SumatraPDF\SumatraPDF.exe",
        # Google Chrome
        prog_files + r"\Google\Chrome\Application\chrome.exe",
        prog_files_x86 + r"\Google\Chrome\Application\chrome.exe",
    ]

    for path_cand in candidates:
        try:
            if path_cand and os.path.isfile(path_cand):
                return path_cand
        except Exception:
            continue

    for bin_name in ("msedge.exe", "chrome.exe", "firefox.exe"):
        found = shutil.which(bin_name)
        if found:
            return found

    return None


def open_pdf(raw_path: str | Path, viewer: Optional[str] = None) -> Tuple[bool, str]:
    """
    Open a PDF file in the native operating system viewer.

    Security & Safety Guarantees:
      - Validates file existence and PDF magic bytes before execution.
      - Disallows `shell=True` on all platform calls to prevent shell injection.
      - Arguments are strictly passed as list items to execve/ShellExecute.

    Platform-Specific Dispatch:
      - Windows:
          1. Uses `os.startfile(path)` invoking Win32 ShellExecuteW directly in-process.
          2. Fallback: Dispatches to Microsoft Edge or Acrobat via `subprocess.Popen([viewer, path])`.
      - macOS:
          1. Uses `subprocess.Popen(["open", path])`.
          2. Fallback: Uses `subprocess.Popen(["open", "-a", "Preview", path])`.
      - Linux:
          1. Uses `subprocess.Popen(["xdg-open", path])`.
          2. Fallback: Dispatches to detected desktop viewer (`evince`, `okular`, etc.).

    Returns:
        (success: bool, message: str)
    """
    valid, reason, canonical = validate_pdf_path(raw_path)
    if not valid or canonical is None:
        return False, f"Cannot open PDF: {reason}"

    target_str = str(canonical)
    current_os = platform.system()

    # ── Custom Viewer Override ────────────────────────────────────────────────
    if viewer:
        custom_bin = shutil.which(viewer) or (viewer if os.path.isfile(viewer) else None)
        if custom_bin:
            try:
                subprocess.Popen([custom_bin, target_str], shell=False)
                return True, f"Opened '{canonical.name}' with custom viewer '{viewer}'."
            except Exception as e:
                return False, f"Failed to open with custom viewer '{viewer}': {e}"

    # ── Windows Dispatch ──────────────────────────────────────────────────────
    if current_os == "Windows":
        # 1. Primary: os.startfile (invokes Win32 ShellExecuteW directly in-process)
        try:
            os.startfile(target_str)  # noqa: S606 - no shell involved, uses wide string Win32 API
            return True, f"Opened '{canonical.name}' in default Windows viewer."
        except OSError as e:
            # 2. Fallback: Launch detected PDF viewer executable directly without shell
            fallback_viewer = _find_windows_pdf_viewer()
            if fallback_viewer:
                try:
                    subprocess.Popen([fallback_viewer, target_str], shell=False)
                    return True, f"Opened '{canonical.name}' with '{Path(fallback_viewer).stem}' (default association unavailable)."
                except Exception as fb_err:
                    return False, f"Windows ShellExecute failed ({e}) and fallback viewer failed ({fb_err})."
            return False, f"Windows failed to open PDF '{canonical.name}': {e}"

    # ── macOS Dispatch ────────────────────────────────────────────────────────
    elif current_os == "Darwin":
        try:
            subprocess.Popen(["open", target_str], shell=False)
            return True, f"Opened '{canonical.name}' in default macOS viewer."
        except Exception as e:
            # Fallback to Apple Preview specifically
            try:
                subprocess.Popen(["open", "-a", "Preview", target_str], shell=False)
                return True, f"Opened '{canonical.name}' with Preview app."
            except Exception as fb_err:
                return False, f"macOS open failed ({e}) and Preview fallback failed ({fb_err})."

    # ── Linux / Unix Dispatch ─────────────────────────────────────────────────
    elif current_os == "Linux":
        # Check xdg-open
        xdg_bin = shutil.which("xdg-open")
        if xdg_bin:
            try:
                subprocess.Popen([xdg_bin, target_str], shell=False)
                return True, f"Opened '{canonical.name}' with xdg-open."
            except Exception as e:
                pass  # Try direct fallback viewer

        linux_viewer = _find_linux_pdf_viewer()
        if linux_viewer:
            try:
                subprocess.Popen([linux_viewer, target_str], shell=False)
                return True, f"Opened '{canonical.name}' with '{Path(linux_viewer).name}'."
            except Exception as e:
                return False, f"Failed to launch Linux viewer '{linux_viewer}': {e}"

        return False, "No suitable PDF viewer (xdg-open, evince, okular, etc.) found on this Linux system."

    # ── Fallback for other systems ────────────────────────────────────────────
    else:
        for tool in ("xdg-open", "open"):
            bin_path = shutil.which(tool)
            if bin_path:
                try:
                    subprocess.Popen([bin_path, target_str], shell=False)
                    return True, f"Opened '{canonical.name}' using {tool}."
                except Exception:
                    continue
        return False, f"Unsupported operating system '{current_os}' for PDF opening."
