"""
core/antigravity_engine.py — Antigravity Agent & Prompt Orchestrator for JARVIS

Empowers JARVIS to formulate high-impact, prompt-engineered directives specifically
for Google Antigravity, save them, copy them to clipboard, focus the running Antigravity
IDE window, and paste the prompt directly into Antigravity's chat input.
"""

from __future__ import annotations

import os
import sys
import re
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

from core import gemini
from core.lazyimport import LazyModule, installed

_PYAUTOGUI = installed("pyautogui")
_PYPERCLIP = installed("pyperclip")
pyautogui = LazyModule("pyautogui")
pyperclip = LazyModule("pyperclip")

# Default Antigravity installation paths on Windows
DEFAULT_EXE_PATH = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "antigravity" / "Antigravity.exe"
DESKTOP_SHORTCUT = Path.home() / "Desktop" / "Antigravity.lnk"
PROMPTS_DIR = Path.home() / "Desktop" / "Antigravity_Prompts"


def get_antigravity_exe() -> Optional[Path]:
    """Finds the Antigravity executable on disk."""
    if DEFAULT_EXE_PATH.exists():
        return DEFAULT_EXE_PATH
    if DESKTOP_SHORTCUT.exists():
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            sc = shell.CreateShortCut(str(DESKTOP_SHORTCUT))
            target = Path(sc.TargetPath)
            if target.exists():
                return target
        except Exception:
            pass
    return None


def is_antigravity_running() -> bool:
    """Checks whether Antigravity process is active."""
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if "antigravity" in name:
                return True
    except Exception:
        pass
    return False


def launch_antigravity() -> bool:
    """Launches Antigravity IDE if not already running."""
    exe = get_antigravity_exe()
    if exe and exe.exists():
        try:
            subprocess.Popen([str(exe)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"[antigravity_engine] Launch error: {e}")
    if DESKTOP_SHORTCUT.exists():
        try:
            os.startfile(str(DESKTOP_SHORTCUT))
            return True
        except Exception as e:
            print(f"[antigravity_engine] Startfile shortcut error: {e}")
    return False


def focus_antigravity_window() -> bool:
    """
    Brings the Antigravity IDE window to the foreground on Windows.
    """
    try:
        import win32gui
        import win32con
        import win32process
        import psutil

        target_hwnds = []

        # Find processes matching Antigravity
        ag_pids = set()
        for proc in psutil.process_iter(["pid", "name"]):
            if "antigravity" in (proc.info.get("name") or "").lower():
                ag_pids.add(proc.info["pid"])

        def enum_cb(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                title = win32gui.GetWindowText(hwnd)
                # Match either by PID or window title
                if pid in ag_pids or "antigravity" in title.lower():
                    # Ignore tooltips or zero-size background windows
                    rect = win32gui.GetWindowRect(hwnd)
                    w = rect[2] - rect[0]
                    h = rect[3] - rect[1]
                    if w > 300 and h > 200:
                        target_hwnds.append(hwnd)

        win32gui.EnumWindows(enum_cb, None)

        if target_hwnds:
            hwnd = target_hwnds[0]
            # Restore if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
            return True
    except Exception as e:
        print(f"[antigravity_engine] Window focus error: {e}")

    # Fallback using pygetwindow
    try:
        import pygetwindow as gw
        for w in gw.getAllWindows():
            if "antigravity" in w.title.lower():
                w.activate()
                return True
    except Exception:
        pass
    return False


def engineer_antigravity_prompt(user_intent: str, slash_command: Optional[str] = None) -> str:
    """
    Formulates a masterfully engineered prompt tailored specifically for Google Antigravity agents.
    Incorporates relevant Antigravity slash commands (/goal, /plan, /boost, /grill-me, etc.),
    system guidelines, explicit context framing, and clear constraints.
    """
    instruction = f"""
You are an expert prompt engineer specializing in Google Antigravity (the agentic AI coding environment).
Transform this user request into an optimal, high-signal, production-grade Antigravity prompt.

User Goal / Intent:
"{user_intent}"

Antigravity Capabilities & Slash Commands to leverage:
- /goal: For long-running, autonomous tasks where the agent shouldn't stop until fully accomplished.
- /plan: For complex multi-step tasks requiring explicit architecture breakdown before code execution.
- /boost: For challenging coding/refactoring tasks demanding deep reasoning, multi-perspective verification.
- /grill-me: When there are critical architectural tradeoffs that need proactive interview alignment.
- /schedule: For automated recurring jobs or timers.
- /learn: For persisting newly learned conventions or rules.

Structure the generated prompt with:
1. Recommended Slash Command header (if suitable, e.g. `/plan` or `/boost` or `/goal`)
2. <objective> — Clear, unambiguous end-state statement.
3. <context> — Workspace assumptions, technologies, and architecture.
4. <requirements> — Explicit functional requirements, edge case handling.
5. <implementation_steps> — Phased, step-by-step guidance.
6. <verification_standards> — Testing commands, lint checks, or manual validation procedures.
7. <guidelines> — No placeholder code, maintain docstring integrity, link code symbols.

Output ONLY the final, complete prompt ready to be pasted into Antigravity.
"""
    try:
        prompt = gemini.text(instruction, tier=gemini.SMART, timeout_ms=45000)
        if prompt and len(prompt.strip()) > 30:
            return prompt.strip()
    except Exception as e:
        print(f"[antigravity_engine] Prompt synthesis failed: {e}")

    # Fallback structured template
    cmd_prefix = f"/{slash_command.lstrip('/')} " if slash_command else ""
    return (
        f"{cmd_prefix}<objective>\n"
        f"Implement: {user_intent}\n"
        f"</objective>\n\n"
        f"<requirements>\n"
        f"- Full, production-ready implementation without placeholders.\n"
        f"- Preserve existing comments and docstrings.\n"
        f"- Include thorough validation and unit tests.\n"
        f"</requirements>\n"
    )


def save_prompt(prompt_text: str, title: Optional[str] = None) -> Path:
    """Saves the engineered prompt to a markdown file on Desktop."""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w\s-]", "", (title or "antigravity_prompt").lower()).strip()
    slug = re.sub(r"[\s_-]+", "_", slug)[:40] or "prompt"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = PROMPTS_DIR / f"{slug}_{timestamp}.md"
    file_path.write_text(prompt_text, encoding="utf-8")
    return file_path


def paste_to_antigravity(prompt_text: str, auto_submit: bool = False) -> Tuple[bool, str]:
    """
    Copies the prompt to clipboard, ensures Antigravity is running, focuses the IDE,
    and pastes the prompt into the input bar.
    """
    # 1. Copy to clipboard
    if _PYPERCLIP:
        try:
            pyperclip.copy(prompt_text)
        except Exception as e:
            return False, f"Clipboard copy failed: {e}"

    # 2. Ensure Antigravity is running
    if not is_antigravity_running():
        launched = launch_antigravity()
        if launched:
            time.sleep(3.0)  # Wait for process initialization
        else:
            return False, "Antigravity is not running and could not be launched automatically."

    # 3. Focus window
    focused = focus_antigravity_window()
    if not focused:
        # Still copied to clipboard!
        return True, "Antigravity prompt copied to clipboard, but could not focus window automatically."

    time.sleep(0.4)

    # 4. Paste via PyAutoGUI
    if _PYAUTOGUI:
        try:
            pyautogui.hotkey("ctrl", "v")
            if auto_submit:
                time.sleep(0.2)
                pyautogui.press("enter")
                return True, "Prompt pasted into Antigravity and submitted."
            return True, "Prompt pasted into Antigravity input bar, ready for your review."
        except Exception as e:
            return True, f"Prompt copied to clipboard, but automated paste encountered: {e}"

    return True, "Prompt copied to clipboard."
