
from __future__ import annotations

import asyncio
import concurrent.futures
import importlib.util
import os
import platform
import shutil
import signal
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import psutil
from core import appidentity, outcome

# Importing playwright cost 198 ms at every launch, paid by action discovery
# whether or not a browser was ever opened. It is the second-largest import in
# the project after pyautogui, and together the two were 78% of all module
# import time on the boot path.
#
# WHY THIS STILL RAISES WHEN PLAYWRIGHT IS MISSING
#     The eager import had a second job nobody wrote down: when playwright was
#     absent this module failed to load, action_loader dropped it, and the model
#     was never offered a browser tool it could not serve. Deferring the import
#     without keeping that would declare `browser_control` on a machine that
#     cannot run it — the model would call it, get an exception, and describe a
#     page it never opened. Exactly the failure mode this project spent Mark LVI
#     removing from local engines.
#
#     So the check stays at module scope and still stops the module loading; it
#     just asks find_spec instead of executing the package. 1 ms instead of 198,
#     same outcome, and a sentence that says what to install.
if importlib.util.find_spec("playwright") is None:      # pragma: no cover
    raise ImportError(
        "browser_control needs playwright, which is not installed. "
        "Run: pip install playwright  &&  playwright install chromium"
    )

# Annotations only — `from __future__ import annotations` above makes every one
# of them a string, so these names are never looked up at runtime and cost
# nothing outside a type checker.
if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page, Playwright

# WHY THIS FILE DOES NOT USE core/lazyimport.py's LazyModule LIKE THE OTHERS
#     Every other deferral in this project stands a proxy in for a whole module,
#     because the call sites say `pyautogui.press(...)` and a proxy answers that
#     the same way the module would. What this file needs are two SYMBOLS out of
#     a module: a factory function, and an exception class used in `except`.
#
#     `except` will not take a proxy. It requires a real class inheriting from
#     BaseException, checked by the interpreter at the moment the exception is
#     raised, and a LazyModule there raises TypeError instead of catching
#     anything — the original error then disappears underneath a complaint about
#     the except clause. So these two are bound as real globals instead.
#
# PlaywrightTimeout starts as a private class that is never raised, so an
# `except PlaywrightTimeout:` somehow reached before a session exists catches
# nothing rather than failing that same way.
class _PlaywrightNotLoaded(Exception):
    """Placeholder exception — declared so `except` clauses stay valid, and
    deliberately never raised anywhere."""


async_playwright = None
PlaywrightTimeout: type[BaseException] = _PlaywrightNotLoaded


def _load_playwright() -> None:
    """Import playwright and bind the two runtime symbols. Idempotent."""
    global async_playwright, PlaywrightTimeout
    if async_playwright is not None:
        return
    from playwright.async_api import (          # noqa: PLC0415 — deliberate
        async_playwright as _ap,
        TimeoutError as _timeout,
    )
    async_playwright = _ap
    PlaywrightTimeout = _timeout


_OS = platform.system()   # "Windows" | "Darwin" | "Linux"

if _OS == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _WIN_HIDE: dict = {}

def _normalize_url(url: str) -> str:
    """
    Bare words like "instagram" → "https://instagram.com"
    Domains like "instagram.com" → "https://instagram.com"
    Full URLs pass through unchanged.
    """
    url = url.strip()
    if not url:
        return "about:blank"
    if "://" in url:
        return url
    # No dot at all → assume .com  (e.g. "instagram" → "instagram.com")
    if "." not in url:
        url = url + ".com"
    return "https://" + url


def _user_agent() -> str:
    if _OS == "Windows":
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    if _OS == "Darwin":
        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    return (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )


def _real_profile_dir(browser: str) -> str:
    home  = Path.home()
    local = os.environ.get("LOCALAPPDATA", "")
    roam  = os.environ.get("APPDATA", "")

    candidates: list[Path] = []

    if _OS == "Windows":
        m = {
            "chrome":   [Path(local) / "Google"          / "Chrome"          / "User Data"],
            "edge":     [Path(local) / "Microsoft"        / "Edge"            / "User Data"],
            "brave":    [Path(local) / "BraveSoftware"    / "Brave-Browser"   / "User Data"],
            "vivaldi":  [Path(local) / "Vivaldi"          / "User Data"],
            "opera":    [Path(roam)  / "Opera Software"   / "Opera Stable",
                         Path(local) / "Opera Software"   / "Opera Stable"],
            "operagx":  [Path(roam)  / "Opera Software"   / "Opera GX Stable",
                         Path(local) / "Opera Software"   / "Opera GX Stable"],
        }
        candidates = m.get(browser, [])

    elif _OS == "Darwin":
        lib = home / "Library" / "Application Support"
        m = {
            "chrome":   [lib / "Google"             / "Chrome"],
            "edge":     [lib / "Microsoft Edge"],
            "brave":    [lib / "BraveSoftware"       / "Brave-Browser"],
            "vivaldi":  [lib / "Vivaldi"],
            "opera":    [lib / "com.operasoftware.Opera"],
            "operagx":  [lib / "com.operasoftware.OperaGX"],
        }
        candidates = m.get(browser, [])

    elif _OS == "Linux":
        cfg = home / ".config"
        m = {
            "chrome":   [cfg / "google-chrome", cfg / "chromium"],
            "edge":     [cfg / "microsoft-edge"],
            "brave":    [cfg / "BraveSoftware" / "Brave-Browser"],
            "vivaldi":  [cfg / "vivaldi"],
            "opera":    [cfg / "opera"],
            "operagx":  [cfg / "opera-gx"],
        }
        candidates = m.get(browser, [])

    for p in candidates:
        if p.exists():
            print(f"[Browser] ✅ Real profile found for {browser}: {p}")
            return str(p)

    fallback = home / ".jarvis_profiles" / browser
    fallback.mkdir(parents=True, exist_ok=True)
    print(f"[Browser] ⚠️  Real profile not found for {browser}, using: {fallback}")
    return str(fallback)

def get_jarvis_common_profile_dir() -> Path:
    """Returns the dedicated, persistent profile directory for JARVIS.
    All browser automation sessions (WhatsApp Web, Telegram Web, general browsing)
    share this persistent profile so cookies, logins, IndexedDB, and localStorage
    are NEVER reset across runs.
    """
    target = Path.home() / ".jarvis_profiles" / "common_session"
    target.mkdir(parents=True, exist_ok=True)
    old_chrome = Path.home() / ".jarvis_profiles" / "chrome"
    if old_chrome.exists() and not (target / "Default").exists():
        try:
            import shutil
            if (old_chrome / "Default").exists():
                shutil.copytree(str(old_chrome / "Default"), str(target / "Default"), dirs_exist_ok=True)
            for f in old_chrome.glob("*"):
                if f.is_file() and not (target / f.name).exists():
                    shutil.copy2(str(f), str(target / f.name))
            print(f"[Browser] Migrated existing profile from {old_chrome} to {target}")
        except Exception as e:
            print(f"[Browser] Note on profile migration: {e}")
    return target

def _firefox_profile_dir() -> Optional[str]:
    home = Path.home()

    if _OS == "Windows":
        base = Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox"
    elif _OS == "Darwin":
        base = home / "Library" / "Application Support" / "Firefox"
    else:
        base = home / ".mozilla" / "firefox"

    ini = base / "profiles.ini"
    if not ini.exists():
        return None

    current: dict[str, str] = {}
    default_path: Optional[str] = None

    for line in ini.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("["):
            p = current.get("Path", "")
            if p and current.get("Default") == "1":
                is_rel = current.get("IsRelative", "1") == "1"
                default_path = str(base / p) if is_rel else p
            current = {}
        elif "=" in line:
            k, _, v = line.partition("=")
            current[k.strip()] = v.strip()

    p = current.get("Path", "")
    if p and current.get("Default") == "1":
        is_rel = current.get("IsRelative", "1") == "1"
        default_path = str(base / p) if is_rel else p

    if default_path and Path(default_path).exists():
        print(f"[Browser] Firefox real profile: {default_path}")
        return default_path
    return None

def _find_opera_windows() -> Optional[str]:
    local  = os.environ.get("LOCALAPPDATA", "")
    prog   = os.environ.get("PROGRAMFILES", "")
    prog86 = os.environ.get("PROGRAMFILES(X86)", "")

    candidates = [
        Path(local)  / "Programs" / "Opera"    / "opera.exe",
        Path(local)  / "Programs" / "Opera GX" / "opera.exe",
        Path(prog)   / "Opera"    / "opera.exe",
        Path(prog86) / "Opera"    / "opera.exe",
    ]
    for p in candidates:
        if p.exists():
            print(f"[Browser] Opera found at: {p}")
            return str(p)

    try:
        import winreg
        keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\opera.exe",
            r"SOFTWARE\Clients\StartMenuInternet\OperaStable\shell\open\command",
            r"SOFTWARE\Clients\StartMenuInternet\OperaGXStable\shell\open\command",
            r"SOFTWARE\Clients\StartMenuInternet\opera\shell\open\command",
        ]
        for key_path in keys:
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    k   = winreg.OpenKey(hive, key_path)
                    val = winreg.QueryValue(k, None)
                    winreg.CloseKey(k)
                    exe = val.strip().strip('"').split('"')[0].split(" --")[0].strip()
                    if exe and Path(exe).exists():
                        print(f"[Browser] Opera found via registry: {exe}")
                        return exe
                except Exception:
                    continue
    except Exception:
        pass

    return shutil.which("opera") or None

def _find_exe_windows(prog_name: str) -> Optional[str]:
    try:
        import winreg
        paths_to_try = [
            rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{prog_name}.exe",
            rf"SOFTWARE\Clients\StartMenuInternet\{prog_name}\shell\open\command",
        ]
        for key_path in paths_to_try:
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    k   = winreg.OpenKey(hive, key_path)
                    val = winreg.QueryValue(k, None)
                    winreg.CloseKey(k)
                    exe = val.strip().strip('"').split('"')[0].split(" --")[0].strip()
                    if exe and Path(exe).exists():
                        return exe
                except Exception:
                    continue
    except Exception:
        pass
    return None

_BROWSER_SPECS: dict[str, dict] = {
    "Windows": {
        "chrome":   {"engine": "chromium", "channel": "chrome",  "bins": []},
        "edge":     {"engine": "chromium", "channel": "msedge",  "bins": []},
        "firefox":  {"engine": "firefox",  "channel": None,      "bins": ["firefox.exe"]},
        "opera":    {"engine": "chromium", "channel": None,      "bins": ["opera.exe"],  "special": "opera_windows"},
        "operagx":  {"engine": "chromium", "channel": None,      "bins": [],             "special": "opera_windows"},
        "brave":    {"engine": "chromium", "channel": None,      "bins": ["brave.exe"]},
        "vivaldi":  {"engine": "chromium", "channel": None,      "bins": ["vivaldi.exe"]},
        "safari":   None,
    },
    "Darwin": {
        "chrome":   {"engine": "chromium", "channel": "chrome",  "bins": []},
        "edge":     {"engine": "chromium", "channel": "msedge",  "bins": ["microsoft-edge"]},
        "firefox":  {"engine": "firefox",  "channel": None,      "bins": ["firefox"]},
        "opera":    {"engine": "chromium", "channel": None,      "bins": ["opera"]},
        "operagx":  {"engine": "chromium", "channel": None,      "bins": ["opera"]},
        "brave":    {"engine": "chromium", "channel": None,      "bins": ["brave browser", "brave"]},
        "vivaldi":  {"engine": "chromium", "channel": None,      "bins": ["vivaldi"]},
        "safari":   {"engine": "webkit",   "channel": None,      "bins": []},
    },
    "Linux": {
        "chrome":   {"engine": "chromium", "channel": None,
                     "bins": ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]},
        "edge":     {"engine": "chromium", "channel": None,
                     "bins": ["microsoft-edge", "microsoft-edge-stable"]},
        "firefox":  {"engine": "firefox",  "channel": None, "bins": ["firefox"]},
        "opera":    {"engine": "chromium", "channel": None, "bins": ["opera", "opera-stable"]},
        "operagx":  {"engine": "chromium", "channel": None, "bins": ["opera", "opera-stable"]},
        "brave":    {"engine": "chromium", "channel": None, "bins": ["brave-browser", "brave"]},
        "vivaldi":  {"engine": "chromium", "channel": None, "bins": ["vivaldi-stable", "vivaldi"]},
        "safari":   None,
    },
}

_ALIASES: dict[str, str] = {
    "google chrome":   "chrome",
    "google-chrome":   "chrome",
    "microsoft edge":  "edge",
    "ms edge":         "edge",
    "msedge":          "edge",
    "mozilla firefox": "firefox",
    "opera gx":        "operagx",
    "opera_gx":        "operagx",
}


def _resolve_browser(name: str) -> dict | None:
    name   = _ALIASES.get(name.lower().strip(), name.lower().strip())
    os_map = _BROWSER_SPECS.get(_OS, {})
    spec   = os_map.get(name)
    if spec is None:
        return None

    engine  = spec["engine"]
    channel = spec.get("channel")
    bins    = spec.get("bins", [])
    exe     = None

    if spec.get("special") == "opera_windows":
        exe = _find_opera_windows()
        if not exe:
            print(f"[Browser] ⚠️  Opera executable not found on Windows.")
        return {"engine": engine, "exe": exe, "channel": channel}

    for b in bins:
        found = shutil.which(b)
        if found:
            exe = found
            break

    if not exe and _OS == "Darwin":
        app_names = {
            "chrome":  ["Google Chrome.app"],
            "edge":    ["Microsoft Edge.app"],
            "firefox": ["Firefox.app"],
            "opera":   ["Opera.app", "Opera GX.app"],
            "brave":   ["Brave Browser.app"],
            "vivaldi": ["Vivaldi.app"],
        }
        for app in app_names.get(name, []):
            app_dir = Path("/Applications") / app / "Contents" / "MacOS"
            if app_dir.exists():
                found_bins = list(app_dir.iterdir())
                if found_bins:
                    exe = str(found_bins[0])
                    break

    if not exe and _OS == "Windows" and not channel:
        exe = _find_exe_windows(name)

    return {"engine": engine, "exe": exe, "channel": channel}


def _detect_default_browser() -> str:
    try:
        if _OS == "Windows":
            import winreg
            k = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\Shell\Associations"
                r"\UrlAssociations\http\UserChoice",
            )
            prog_id = winreg.QueryValueEx(k, "ProgId")[0].lower()
            winreg.CloseKey(k)
            for kw in ("edge", "firefox", "opera", "brave", "vivaldi", "chrome"):
                if kw in prog_id:
                    return kw
        elif _OS == "Darwin":
            out = subprocess.run(
                ["defaults", "read",
                 "com.apple.LaunchServices/com.apple.launchservices.secure",
                 "LSHandlers"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
            ).stdout.lower()
            for kw in ("firefox", "opera", "brave", "vivaldi", "safari", "chrome", "edge"):
                if kw in out:
                    return kw
        elif _OS == "Linux":
            out = subprocess.run(
                ["xdg-settings", "get", "default-web-browser"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
            ).stdout.lower()
            for kw in ("firefox", "opera", "brave", "vivaldi", "chrome", "edge"):
                if kw in out:
                    return kw
    except Exception:
        pass
    return "chrome"


def _resolve_browser_executable(browser_name: str) -> Optional[str]:
    """
    Resolves the absolute path to a browser's executable binary across Windows, macOS, and Linux.
    Probing order:
      1. Custom path override from memory.config_manager.
      2. Windows Registry (App Paths and StartMenuInternet).
      3. Standard well-known installation directories.
      4. System PATH via shutil.which().
    """
    if not browser_name:
        return None
    name = _ALIASES.get(browser_name.lower().strip(), browser_name.lower().strip())

    # 1. Check custom path configured in config_manager
    try:
        from memory import config_manager
        custom_path = config_manager.get_browser_executable_path(name)
        if custom_path and Path(custom_path).exists():
            return str(Path(custom_path).resolve())
    except Exception:
        pass

    # 2. Platform-specific resolution
    if _OS == "Windows":
        if name in ("opera", "operagx"):
            exe = _find_opera_windows()
            if exe and Path(exe).exists():
                return exe

        # Check Windows Registry App Paths and StartMenuInternet
        exe = _find_exe_windows(_WIN_EXE_HINTS.get(name, name))
        if exe and Path(exe).exists():
            return exe

        # Standard installation directories on Windows
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_appdata = os.environ.get("LOCALAPPDATA", "")

        candidate_paths: list[Path] = []
        if name == "chrome":
            candidate_paths = [
                Path(prog_files) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(prog_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(local_appdata) / "Google" / "Chrome" / "Application" / "chrome.exe",
            ]
        elif name == "brave":
            candidate_paths = [
                Path(prog_files) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
                Path(prog_files_x86) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
                Path(local_appdata) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
            ]
        elif name == "edge":
            candidate_paths = [
                Path(prog_files_x86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                Path(prog_files) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            ]
        elif name == "firefox":
            candidate_paths = [
                Path(prog_files) / "Mozilla Firefox" / "firefox.exe",
                Path(prog_files_x86) / "Mozilla Firefox" / "firefox.exe",
            ]
        elif name == "vivaldi":
            candidate_paths = [
                Path(local_appdata) / "Vivaldi" / "Application" / "vivaldi.exe",
                Path(prog_files) / "Vivaldi" / "Application" / "vivaldi.exe",
            ]

        for p in candidate_paths:
            try:
                if p and p.exists() and p.is_file():
                    return str(p)
            except Exception:
                continue

        # Check PATH with .exe
        found = shutil.which(f"{name}.exe") or shutil.which(name)
        if found and Path(found).exists():
            return found

    elif _OS == "Darwin":
        app = _MAC_APP_NAMES.get(name)
        if app:
            app_dir = Path("/Applications") / f"{app}.app" / "Contents" / "MacOS"
            if app_dir.exists():
                bins = list(app_dir.iterdir())
                if bins:
                    return str(bins[0])
        found = shutil.which(name)
        if found:
            return found

    elif _OS == "Linux":
        spec = _BROWSER_SPECS.get("Linux", {}).get(name, {})
        for b in spec.get("bins", []):
            found = shutil.which(b)
            if found:
                return found
        found = shutil.which(name)
        if found:
            return found

    return None


def is_browser_available(browser_name: str) -> bool:
    """Check if the specified browser is installed and resolvable on the current system."""
    if not browser_name:
        return False
    name = _ALIASES.get(browser_name.lower().strip(), browser_name.lower().strip())
    if _OS == "Darwin":
        app = _MAC_APP_NAMES.get(name)
        if app and (Path("/Applications") / f"{app}.app").exists():
            return True
    return _resolve_browser_executable(name) is not None


def get_jarvis_browser(preferred: Optional[str] = None) -> str:
    """
    Determines the effective browser to use under the JARVIS Default Browser Policy.

    Priority Order:
      1. Explicit runtime argument `preferred` (e.g. 'edge', 'firefox').
      2. Configured JARVIS default browser from memory.config_manager.get_default_browser() (defaults to 'chrome').
         - If configured as 'system', delegates to host OS detected browser.
         - If configured browser is installed/available, returns it.
      3. Fallback to Host OS detected default browser via _detect_default_browser().
      4. Safe ultimate fallback: 'chrome'.
    """
    if preferred and preferred.strip():
        norm = _ALIASES.get(preferred.lower().strip(), preferred.lower().strip())
        if norm != "system":
            return norm

    try:
        from memory import config_manager
        configured = config_manager.get_default_browser()
    except Exception:
        configured = "chrome"

    if configured and configured != "system":
        configured = _ALIASES.get(configured.lower().strip(), configured.lower().strip())
        if is_browser_available(configured):
            return configured

    # Host OS default fallback
    try:
        host_default = _detect_default_browser()
        if host_default and is_browser_available(host_default):
            return host_default
    except Exception:
        pass

    return "chrome"


_SEARCH_ENGINES: dict[str, str] = {
    "google":     "https://www.google.com/search?q=",
    "bing":       "https://www.bing.com/search?q=",
    "duckduckgo": "https://duckduckgo.com/?q=",
    "yandex":     "https://yandex.com/search/?text=",
}

_MAC_APP_NAMES: dict[str, str] = {
    "chrome":  "Google Chrome",
    "edge":    "Microsoft Edge",
    "firefox": "Firefox",
    "opera":   "Opera",
    "operagx": "Opera GX",
    "brave":   "Brave Browser",
    "vivaldi": "Vivaldi",
    "safari":  "Safari",
}

# Windows registry lookup names for browsers whose spec has no explicit binary
_WIN_EXE_HINTS: dict[str, str] = {"chrome": "chrome", "edge": "msedge"}


def _open_native(url: str, browser_name: Optional[str] = None) -> str:
    """
    Opens the user's REAL browser normally — with their own profile,
    logged-in accounts and extensions. Enforces the JARVIS Default Browser Policy
    (prioritizing Google Chrome / configured browser) over the host OS default.
    """
    url = _normalize_url(url) if url and url.strip() else ""
    if url == "about:blank":
        url = ""

    # Determine effective browser under JARVIS Policy
    name = get_jarvis_browser(browser_name)

    # 1. On macOS with .app bundle
    if _OS == "Darwin":
        app = _MAC_APP_NAMES.get(name)
        if app:
            cmd = ["open", "-a", app] + ([url] if url else [])
            try:
                subprocess.run(cmd, check=True, timeout=10)
                return f"Opened in {name}: {url}" if url else f"Opened {name}."
            except Exception as e:
                print(f"[Browser] 'open -a {app}' failed ({e}), trying binary…")

    # 2. Resolve executable path directly
    exe = _resolve_browser_executable(name)
    if exe:
        try:
            subprocess.Popen(
                [exe, url] if url else [exe],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                **_WIN_HIDE
            )
            return f"Opened in {name}: {url}" if url else f"Opened {name}."
        except Exception as e:
            print(f"[Browser] Native launch failed for {name} ({exe}): {e}")

    # 3. If target browser executable not found, try host default browser executable if different
    host_default = _detect_default_browser()
    if host_default and host_default != name:
        host_exe = _resolve_browser_executable(host_default)
        if host_exe:
            try:
                subprocess.Popen(
                    [host_exe, url] if url else [host_exe],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    **_WIN_HIDE
                )
                return f"Opened in fallback browser ({host_default}): {url}" if url else f"Opened {host_default}."
            except Exception:
                pass

    if not url:
        return outcome.failed(
            "browser_control",
            "no browser was found and no address was given to open")

    # 4. OS shell association fallback (only if no binary was found)
    try:
        if _OS == "Windows":
            os.startfile(url)                       # ShellExecute → default browser
        elif _OS == "Darwin":
            subprocess.run(["open", url], check=True, timeout=10)
        else:
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        return outcome.unverified(
            "browser_control",
            "the address was handed to the system's default browser, which "
            "does not report back - the page is not confirmed open",
            url=url)
    except Exception:
        try:
            if webbrowser.open(url):
                return outcome.unverified(
                    "browser_control",
                    "the address was handed to the default browser, which does "
                    "not report back - the page is not confirmed open",
                    url=url)
        except Exception:
            pass
        return outcome.failed(
            "browser_control",
            "no browser on this system could be opened", url=url)


def _os_force_kill(pid: int) -> bool:
    """Forcefully terminate an OS process by PID with safety checks."""
    if pid in appidentity.own_pids():
        print(f"[Browser] Refusing to kill PID {pid}: belongs to assistant.")
        return False

    current_os = platform.system()
    sigkill = getattr(signal, "SIGKILL", 9)
    try:
        if current_os == "Windows":
            res = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                check=False
            )
            return res.returncode == 0
        else:
            try:
                os.kill(pid, sigkill)
                return True
            except OSError:
                res = subprocess.run(["kill", "-9", str(pid)], capture_output=True, check=False)
                return res.returncode == 0
    except Exception as e:
        print(f"[Browser] OS kill failed for PID {pid}: {e}")
        return False


class NativeTabRecord:
    """Represents a natively opened browser tab with metadata for handle tracking."""
    def __init__(self, url: str, browser: Optional[str] = None, title: Optional[str] = None):
        self.url = url
        self.browser = browser or ""
        self.title = title or ""
        self.timestamp = time.time()
        clean = url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        self.domain = clean.split(".")[0] if clean else ""


class NativeTabTracker:
    """Thread-safe registry of natively opened browser tabs and URLs."""
    def __init__(self):
        self._lock = threading.RLock()
        self._tabs: list[NativeTabRecord] = []

    def record(self, url: str, browser: Optional[str] = None, title: Optional[str] = None) -> NativeTabRecord:
        with self._lock:
            rec = NativeTabRecord(url=url, browser=browser, title=title)
            self._tabs.append(rec)
            if len(self._tabs) > 50:
                self._tabs.pop(0)
            return rec

    def find_candidates(self, query: Optional[str] = None) -> list[NativeTabRecord]:
        with self._lock:
            if not query:
                return list(reversed(self._tabs))
            q = query.lower().strip()
            matches = []
            for rec in reversed(self._tabs):
                if (
                    q in rec.url.lower()
                    or q in rec.title.lower()
                    or (rec.domain and q in rec.domain.lower())
                    or (rec.browser and q in rec.browser.lower())
                ):
                    matches.append(rec)
            return matches

    def pop_latest(self, query: Optional[str] = None) -> Optional[NativeTabRecord]:
        with self._lock:
            candidates = self.find_candidates(query)
            if candidates:
                rec = candidates[0]
                if rec in self._tabs:
                    self._tabs.remove(rec)
                return rec
            return None

    def list_tabs(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "url": r.url,
                    "domain": r.domain,
                    "browser": r.browser,
                    "title": r.title,
                    "age_sec": round(time.time() - r.timestamp, 1)
                }
                for r in reversed(self._tabs)
            ]


_native_tracker = NativeTabTracker()


def open_url(url: str, browser: Optional[str] = None) -> str:
    """
    Standardized, lifecycle-tracked URL dispatcher across JARVIS.
    Records the navigation in NativeTabTracker, normalizes the address,
    and opens the page natively according to the JARVIS Default Browser Policy.

    NOTE: WhatsApp Web and Telegram Web URLs are ALWAYS routed to the persistent
    JARVIS browser session (~/.jarvis_profiles/common_session) so that logins and
    sessions persist permanently without QR code prompts on subsequent launches.
    """
    norm_url = _normalize_url(url)
    lower = norm_url.lower()
    if any(k in lower for k in ("web.whatsapp.com", "web.telegram.org", "whatsapp.com", "telegram.org")):
        sess = _registry.get(browser)
        return sess.run(sess.go_to(norm_url))

    effective_browser = get_jarvis_browser(browser)
    rec = _native_tracker.record(url=norm_url, browser=effective_browser)
    res = _open_native(norm_url, effective_browser)
    _registry.note_native_url(norm_url)
    return res


def _get_window_list() -> list[dict]:
    """Returns a list of visible top-level windows with HWND, PID, and title safely without hanging."""
    windows: list[dict] = []
    if _OS == "Windows":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            WM_GETTEXT = 0x000D
            SMTO_ABORTIFHUNG = 0x0002

            def _enum_cb(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    buf = ctypes.create_unicode_buffer(512)
                    res = ctypes.c_ulong()
                    # Safe timeout query: aborts in 50ms if window thread is hung
                    if user32.SendMessageTimeoutW(hwnd, WM_GETTEXT, 512, buf, SMTO_ABORTIFHUNG, 50, ctypes.byref(res)):
                        title = buf.value.strip()
                        if title:
                            pid = ctypes.c_ulong()
                            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                            windows.append({"hwnd": hwnd, "pid": pid.value, "title": title})
                return True

            CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(CB(_enum_cb), 0)
        except Exception:
            pass
    return windows


def _close_macos_tab(query: str, browser_name: str = "") -> bool:
    """Closes matching tab in macOS scriptable browsers via AppleScript."""
    browsers = [browser_name] if browser_name else ["Brave Browser", "Google Chrome", "Microsoft Edge", "Safari"]
    for b in browsers:
        if not b:
            continue
        script = f'''
        tell application "{b}"
            if it is running then
                repeat with w in windows
                    set tabIdx to 0
                    repeat with t in tabs of w
                        set tabIdx to tabIdx + 1
                        if (URL of t contains "{query}") or (title of t contains "{query}") then
                            close t
                            return "ok"
                        end if
                    end repeat
                end repeat
            end if
        end tell
        '''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
            if "ok" in res.stdout:
                return True
        except Exception:
            continue
    return False


def _close_native_tab(
    title: Optional[str] = None,
    url: Optional[str] = None,
    browser: Optional[str] = None,
    force: bool = False,
) -> str:
    """
    Closes a tab in the user's native desktop browser (e.g. Brave, Chrome, Edge, Firefox)
    when no Playwright automation session is active.

    Escalation:
      1. Identifies candidate window titles based on title, url, NativeTabTracker records, or browser name.
      2. On macOS: attempts direct AppleScript tab handle closure.
      3. On Windows: enumerates active window handles (HWND) to find matching window, restores & focuses, sends Ctrl+W.
         Fallback: Windows Script Host AppActivate.
      4. On Linux: wmctrl -a window activation + Ctrl+W.
      5. If force=True and standard closure fails, locates the browser process and terminates it safely.
    """
    activated = False
    focused_name = ""

    # Build prioritized candidate search strings
    candidates: list[str] = []
    if title:
        candidates.append(title.strip())
        candidates.append(title.strip().capitalize())
    if url:
        clean_url = url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
        if clean_url:
            domain_name = clean_url.split(".")[0]
            if domain_name and domain_name.lower() not in [c.lower() for c in candidates]:
                candidates.append(domain_name.capitalize())
                candidates.append(domain_name)

    # Check tracked native tabs
    tracked = _native_tracker.find_candidates(query=title or url)
    for rec in tracked:
        if rec.title and rec.title not in candidates:
            candidates.append(rec.title)
        if rec.domain and rec.domain.capitalize() not in candidates:
            candidates.append(rec.domain.capitalize())
            candidates.append(rec.domain)
        if rec.browser and rec.browser.capitalize() not in candidates:
            candidates.append(rec.browser.capitalize())

    if browser:
        candidates.append(browser.capitalize())
        candidates.append(browser)

    effective_b = get_jarvis_browser(browser)
    if effective_b:
        if effective_b.capitalize() not in candidates:
            candidates.append(effective_b.capitalize())
        if effective_b not in candidates:
            candidates.append(effective_b)

    for b in ["Brave", "Chrome", "Edge", "Firefox", "Opera", "Vivaldi"]:
        if b not in candidates:
            candidates.append(b)

    # ── macOS Tab Handle Execution ──
    if _OS == "Darwin":
        query_kw = title or (tracked[0].domain if tracked else "") or (url.split("//")[-1].split(".")[0] if url else "")
        if query_kw and _close_macos_tab(query_kw, browser or ""):
            _native_tracker.pop_latest(query=title or url)
            return f"Closed native browser tab ({query_kw})."

        for cand in candidates:
            if not cand:
                continue
            script = (
                f'tell application "System Events"\n'
                f'  set frontmost of (first process whose name contains "{cand}") to true\n'
                f'end tell'
            )
            try:
                r = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
                if r.returncode == 0:
                    activated = True
                    focused_name = cand
                    break
            except Exception:
                continue

    # ── Windows Window Handle & Activation Execution ──
    elif _OS == "Windows":
        # Strategy A: Window handle (HWND) enumeration
        win_list = _get_window_list()
        matching_hwnd = None
        for cand in candidates:
            if not cand:
                continue
            cand_l = cand.lower()
            for win in win_list:
                w_title = win.get("title", "").lower()
                if cand_l in w_title:
                    matching_hwnd = win.get("hwnd")
                    focused_name = win.get("title")
                    break
            if matching_hwnd:
                break

        if matching_hwnd:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                user32.ShowWindow(matching_hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(matching_hwnd)
                activated = True
            except Exception:
                pass

        # Strategy B: PowerShell AppActivate
        if not activated:
            for cand in candidates:
                if not cand:
                    continue
                try:
                    cmd = [
                        "powershell", "-NoProfile", "-NonInteractive", "-Command",
                        f'(New-Object -ComObject WScript.Shell).AppActivate("{cand}")'
                    ]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=3, **_WIN_HIDE)
                    if res.stdout and "True" in res.stdout:
                        activated = True
                        focused_name = cand
                        break
                except Exception:
                    continue

    # ── Linux wmctrl Execution ──
    elif _OS == "Linux":
        for cand in candidates:
            if not cand:
                continue
            try:
                r = subprocess.run(["wmctrl", "-a", cand], capture_output=True, timeout=2)
                if r.returncode == 0:
                    activated = True
                    focused_name = cand
                    break
            except Exception:
                continue

    if activated:
        time.sleep(0.25)
        try:
            import pyautogui
            close_key = "command" if _OS == "Darwin" else "ctrl"
            pyautogui.hotkey(close_key, "w")
            _native_tracker.pop_latest(query=title or url)
            target_desc = title or focused_name or "current tab"
            return f"Closed native browser tab ({target_desc})."
        except Exception as e:
            return f"Focused browser window ({focused_name}) but failed to send close tab shortcut: {e}"

    if force:
        target_browser = (browser or get_jarvis_browser() or "chrome").lower()
        exclude = appidentity.own_pids()
        for p in psutil.process_iter(['pid', 'name']):
            try:
                if p.pid in exclude:
                    continue
                if target_browser in p.name().lower():
                    if _os_force_kill(p.pid):
                        _native_tracker.pop_latest(query=title or url)
                        return f"Forcefully terminated native browser process ({p.name()}, PID {p.pid})."
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    return f"No active browser session or window found to close tabs from (searched: {', '.join(candidates[:3])})."


class _BrowserSession:
    """
    A full session for one browser instance.
    All browsers open on the real profile via launch_persistent_context.
    """

    def __init__(self, browser_name: str):
        self.browser_name = browser_name
        self._spec        = _resolve_browser(browser_name)

        self._loop:    asyncio.AbstractEventLoop | None = None
        self._thread:  threading.Thread | None          = None
        self._ready    = threading.Event()

        self._pw:      Playwright     | None = None
        self._context: BrowserContext | None = None
        self._page:    Page           | None = None
        # "real" when the user's own browser profile was opened, "separate"
        # when their browser was already running and a private automation
        # profile had to be used instead. The difference is every sign-in they
        # have, so it is reported rather than only printed.
        self.profile_kind: str = ""

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name=f"BrowserThread-{self.browser_name}",
        )
        self._thread.start()
        self._ready.wait(timeout=20)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_init())
        self._ready.set()
        self._loop.run_forever()

    async def _async_init(self):
        # The one door into a live session: nothing in this class reaches
        # async_playwright or PlaywrightTimeout without coming through here
        # first, so binding them at this point is enough for the whole file.
        _load_playwright()
        self._pw = await async_playwright().start()

    def run(self, coro, timeout: int = 60) -> str:
        if not self._loop:
            raise RuntimeError(f"Session for '{self.browser_name}' not started.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def close(self):
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._async_close(), self._loop).result(10)

    async def _async_close(self):
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass
        self._context = self._page = None

    async def _adopt_page(self) -> Page:
        """
        launch_persistent_context already opens a starting tab.
        Instead of opening a new blank tab (about:blank), it adopts that tab —
        so the user never sees an extra blank tab.
        """
        await asyncio.sleep(0.3)
        pages = self._context.pages
        return pages[0] if pages else await self._context.new_page()

    async def _launch(self):
        """
        Launches the browser with the real user profile.
        Does nothing if the context is already open.
        """
        if self._context is not None:
            return

        if self._spec is None:
            raise RuntimeError(
                f"'{self.browser_name}' bu platformda ({_OS}) desteklenmiyor."
            )

        engine_name = self._spec["engine"]
        exe         = self._spec["exe"]
        channel     = self._spec["channel"]
        engine_obj  = getattr(self._pw, engine_name)

        if engine_name == "firefox":
            profile = _firefox_profile_dir() or str(
                Path.home() / ".jarvis_profiles" / "firefox"
            )
            kwargs: dict = {
                "headless":    False,
                "slow_mo":     0,
                "viewport":    None,
                "no_viewport": True,
                "timeout":     25_000,
            }
            if exe:
                kwargs["executable_path"] = exe
            try:
                self._context = await engine_obj.launch_persistent_context(profile, **kwargs)
            except Exception as e:
                print(f"[Browser] Firefox real profile failed ({e}), using JARVIS profile")
                jarvis = str(Path.home() / ".jarvis_profiles" / "firefox_jarvis")
                Path(jarvis).mkdir(parents=True, exist_ok=True)
                self._context = await engine_obj.launch_persistent_context(jarvis, **kwargs)

            self._page = await self._adopt_page()
            print(f"[Browser] ✅ Firefox launched")
            return

        if engine_name == "webkit":
            safari_profile = str(Path.home() / ".jarvis_profiles" / "safari")
            Path(safari_profile).mkdir(parents=True, exist_ok=True)
            kwargs = {
                "headless":    False,
                "slow_mo":     0,
                "viewport":    None,
                "no_viewport": True,
                "timeout":     25_000,
            }
            self._context = await engine_obj.launch_persistent_context(safari_profile, **kwargs)
            self._page = await self._adopt_page()
            print(f"[Browser] ✅ Safari launched")
            return

        # JARVIS DEDICATED PERSISTENT PROFILE:
        # A single, consistent user data directory used across all JARVIS sessions.
        # This guarantees WhatsApp Web, Telegram Web, and all sign-ins persist
        # without ever resetting or presenting a new QR code on launch.
        profile = str(get_jarvis_common_profile_dir())

        kwargs = {
            "headless":    False,
            "slow_mo":     0,
            "viewport":    None,
            "no_viewport": True,
            "timeout":     30_000,
            "args": [
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--disable-default-apps",
                "--no-default-browser-check",
            ],
        }

        if exe:
            kwargs["executable_path"] = exe
        elif channel:
            kwargs["channel"] = channel

        label = (
            f"{self.browser_name}"
            + (f"/{channel}" if channel else "")
            + (f" @ {exe}" if exe else "")
        )

        try:
            self._context = await engine_obj.launch_persistent_context(profile, **kwargs)
            self._page = await self._adopt_page()
            self.profile_kind = "jarvis_common"
            print(f"[Browser] ✅ Launched [{label}] with JARVIS common profile (session persistent): {profile}")
            return
        except Exception as e:
            print(f"[Browser] ⚠️ Persistent context launch failed with {label}: {e}")
            if channel != "chrome" and engine_name == "chromium":
                try:
                    kwargs.pop("executable_path", None)
                    kwargs["channel"] = "chrome"
                    self._context = await engine_obj.launch_persistent_context(profile, **kwargs)
                    self._page = await self._adopt_page()
                    self.profile_kind = "jarvis_common"
                    print(f"[Browser] ✅ Launched Chrome channel fallback with JARVIS common profile: {profile}")
                    return
                except Exception as e2:
                    raise RuntimeError(f"Could not launch browser with JARVIS common profile: {e2}") from e2
            raise RuntimeError(f"Could not launch browser with JARVIS common profile: {e}") from e


    async def _get_page(self) -> Page:
        await self._launch()
        # If somehow page got closed, open a fresh one
        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()
            await asyncio.sleep(0.2)
        return self._page

    async def go_to(self, url: str) -> str:

        url      = _normalize_url(url)
        page     = await self._get_page()
        prev_url = page.url

        async def _do_goto(p: Page) -> str:
            """Attempt navigation and return the resulting URL (may still be blank)."""
            try:
                await p.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await asyncio.sleep(0.3)
            except PlaywrightTimeout:
                pass   # page may have partially loaded — check URL below
            except Exception as e:
                print(f"[Browser] goto exception (non-fatal): {e}")
            return p.url

        result_url = await _do_goto(page)

        if result_url in ("about:blank", "", None, prev_url) and prev_url in ("about:blank", "", None):
            print(f"[Browser] Still blank after goto — retrying on new tab: {url}")
            try:
                new_page   = await self._context.new_page()
                self._page = new_page
                result_url = await _do_goto(new_page)
            except Exception as e:
                print(f"[Browser] New-tab retry failed: {e}")

        if result_url and result_url not in ("about:blank", "", None):
            # Verified, and cheaply: this is the page's OWN url read back after
            # navigation, not the one we asked for. A redirect, a login wall or
            # a captive portal all show up here as a different address, which
            # is exactly what the user needs to hear about.
            #
            # The profile is reported for the same reason. When the user's
            # browser was already running its profile is locked, so the page
            # opens in a separate one where they are signed in to nothing —
            # and a Gmail that asks them to log in looks like a broken
            # assistant unless somebody says why.
            if self.profile_kind == "separate":
                return outcome.unverified(
                    "browser_control",
                    f"the page opened at {result_url}, but "
                    f"{self.browser_name} was already running so its profile "
                    f"was locked - this window uses a separate profile where "
                    f"the user is NOT signed in to anything. Closing "
                    f"{self.browser_name} first would let their own profile be "
                    f"used",
                    opened=result_url, profile="separate")
            return outcome.done("browser_control", opened=result_url,
                                profile=self.profile_kind or "real",
                                verified=True)
        return outcome.failed(
            "browser_control",
            "the page stayed blank - the address may be wrong, or the site may "
            "not have answered", url=url)

    async def search(self, query: str, engine: str = "google") -> str:
        base = _SEARCH_ENGINES.get(engine.lower(), _SEARCH_ENGINES["google"])
        return await self.go_to(base + query.replace(" ", "+"))

    async def click(self, selector: str = None, text: str = None) -> str:
        page = await self._get_page()
        try:
            if text:
                await page.get_by_text(text, exact=False).first.click(timeout=8_000)
                return f"Clicked text: '{text}'"
            if selector:
                await page.click(selector, timeout=8_000)
                return f"Clicked selector: {selector}"
            return outcome.failed("browser_control",
                                  "no element was named to click")
        except PlaywrightTimeout:
            return outcome.failed(
                "browser_control",
                "no element matching that appeared on the page in time",
                selector=selector or text)
        except Exception as e:
            return f"Click error: {e}"

    async def type_text(self, selector: str = None, text: str = "",
                        clear_first: bool = True) -> str:
        page = await self._get_page()
        try:
            el = page.locator(selector).first if selector else page.locator(":focus")
            if clear_first:
                await el.clear()
            await el.type(text, delay=50)
            # playwright raises when the field is not there, so reaching this
            # line means the text went into a real input.
            return outcome.done("browser_control", typed=True, verified=True)
        except Exception as e:
            return f"Type error: {e}"

    async def scroll(self, direction: str = "down", amount: int = 500) -> str:
        page = await self._get_page()
        try:
            y = amount if direction == "down" else -amount
            await page.mouse.wheel(0, y)
            return f"Scrolled {direction}."
        except Exception as e:
            return f"Scroll error: {e}"

    async def press(self, key: str) -> str:
        page = await self._get_page()
        try:
            await page.keyboard.press(key)
            return f"Pressed: {key}"
        except Exception as e:
            return f"Key error: {e}"

    async def get_text(self) -> str:
        page = await self._get_page()
        try:
            text = await page.inner_text("body")
            return text[:4_000]
        except Exception as e:
            return f"Could not get page text: {e}"

    async def get_url(self) -> str:
        page = await self._get_page()
        return page.url

    async def fill_form(self, fields: dict) -> str:
        page    = await self._get_page()
        results = []
        for selector, value in fields.items():
            try:
                el = page.locator(selector).first
                await el.clear()
                await el.type(str(value), delay=40)
                results.append(f"✓ {selector}")
            except Exception as e:
                results.append(f"✗ {selector}: {e}")
        return "Form filled: " + ", ".join(results)

    async def smart_click(self, description: str) -> str:
        page = await self._get_page()
        for role in ("button", "link", "searchbox", "textbox", "menuitem", "tab"):
            try:
                loc = page.get_by_role(role, name=description)
                if await loc.count() > 0:
                    await loc.first.click(timeout=5_000)
                    return f"Clicked ({role}): '{description}'"
            except Exception:
                pass
        for attempt in (
            lambda: page.get_by_text(description, exact=False).first.click(timeout=5_000),
            lambda: page.get_by_placeholder(description, exact=False).first.click(timeout=5_000),
            lambda: page.locator(
                f'[alt*="{description}" i],[title*="{description}" i],'
                f'[aria-label*="{description}" i]'
            ).first.click(timeout=5_000),
        ):
            try:
                await attempt()
                return f"Clicked: '{description}'"
            except Exception:
                pass
        return f"Could not find element: '{description}'"

    async def smart_type(self, description: str, text: str) -> str:
        page = await self._get_page()
        candidates = [
            ("placeholder", page.get_by_placeholder(description, exact=False)),
            ("label",       page.get_by_label(description, exact=False)),
            ("role",        page.get_by_role("textbox", name=description)),
            ("searchbox",   page.get_by_role("searchbox")),
            ("combobox",    page.get_by_role("combobox", name=description)),
        ]
        for method, loc in candidates:
            try:
                el = loc.first
                if await el.count() == 0:
                    continue
                await el.clear()
                await el.type(text, delay=50)
                return f"Typed into ({method}): '{description}'"
            except Exception:
                continue
        return f"Could not find input: '{description}'"

    async def new_tab(self, url: str = "") -> str:
        page = await self._get_page()
        ctx  = page.context
        new  = await ctx.new_page()
        self._page = new
        if url:
            return await self.go_to(url)
        return "New tab opened."

    def _update_active_page(self):
        """Update active page pointer to the most recent non-closed page."""
        try:
            pages = [p for p in (self._context.pages if self._context else []) if not p.is_closed()]
            self._page = pages[-1] if pages else None
        except Exception:
            self._page = None

    async def _get_browser_pid(self) -> Optional[int]:
        """Resolve the OS process ID for the browser parent process."""
        # 1. Try CDP SystemInfo if Chromium
        if self._context and self._page and not self._page.is_closed():
            try:
                cdp = await asyncio.wait_for(self._context.new_cdp_session(self._page), timeout=1.0)
                sys_info = await asyncio.wait_for(cdp.send("SystemInfo.getProcessInfo"), timeout=1.0)
                for proc in sys_info.get("processInfo", []):
                    if proc.get("type") == "browser":
                        return int(proc.get("id"))
            except Exception:
                pass

        # 2. Match active browser process via psutil while protecting own application
        try:
            exclude_pids = appidentity.own_pids()
            bname = (self.browser_name or "").lower()
            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if p.pid in exclude_pids:
                        continue
                    pname = p.name().lower()
                    if bname in pname or (bname == "edge" and "msedge" in pname) or (bname == "chrome" and "chrome" in pname):
                        cmd = p.cmdline()
                        if not any("--type=" in arg or "-contentproc" in arg for arg in cmd):
                            return p.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return None

    async def _get_tab_renderer_pid(self, page: Page) -> Optional[int]:
        """Find the specific OS renderer/content process ID for a given page/tab."""
        # 1. Try CDP SystemInfo on the page context
        try:
            cdp = await asyncio.wait_for(page.context.new_cdp_session(page), timeout=1.0)
            sys_info = await asyncio.wait_for(cdp.send("SystemInfo.getProcessInfo"), timeout=1.0)
            for proc in sys_info.get("processInfo", []):
                if proc.get("type") == "renderer":
                    return int(proc.get("id"))
        except Exception:
            pass

        # 2. Inspect child processes of browser via psutil
        browser_pid = await self._get_browser_pid()
        if browser_pid:
            try:
                exclude_pids = appidentity.own_pids()
                bp = psutil.Process(browser_pid)
                children = bp.children(recursive=True)
                for child in children:
                    try:
                        if child.pid in exclude_pids:
                            continue
                        cmd = child.cmdline()
                        # Chromium renderer or Firefox content process
                        if any("--type=renderer" in arg for arg in cmd) or any("-contentproc" in arg for arg in cmd):
                            return child.pid
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception:
                pass
        return None

    _os_force_kill = staticmethod(_os_force_kill)

    async def close_tab(
        self,
        url: Optional[str] = None,
        title: Optional[str] = None,
        force: bool = False,
        timeout: float = 2.0
    ) -> str:
        """
        Close a browser tab following a 3-tier escalation:
          Tier 1: Graceful Playwright/CDP close (page.close(run_before_unload=False))
          Tier 2: Raw CDP Target.closeTarget
          Tier 3: Process-tree PID resolution and OS-level forceful termination (taskkill on Windows, kill -9 on macOS/Linux)
        """
        if not self._context:
            return _close_native_tab(
                url=url,
                title=title,
                browser=self.browser_name,
                force=force,
            )

        pages = [p for p in self._context.pages if not p.is_closed()]
        if not pages:
            self._page = None
            return "No active tab to close."

        target_page: Optional[Page] = None
        if url or title:
            for p in pages:
                if url and url.lower() in p.url.lower():
                    target_page = p
                    break
                if title:
                    try:
                        t = await asyncio.wait_for(p.title(), timeout=0.5)
                        if title.lower() in t.lower():
                            target_page = p
                            break
                    except Exception:
                        pass
            if target_page is None:
                criteria = []
                if url:
                    criteria.append(f"url containing '{url}'")
                if title:
                    criteria.append(f"title containing '{title}'")
                return f"No open tab found matching {' and '.join(criteria)}."
        else:
            target_page = self._page if (self._page and not self._page.is_closed()) else pages[-1]

        target_url = target_page.url

        # ── Tier 1: Graceful Playwright close ─────────────────────────────────
        if not force:
            try:
                print(f"[Browser] Tier 1: Attempting graceful close on tab: {target_url}")
                await asyncio.wait_for(target_page.close(run_before_unload=False), timeout=timeout)
                if target_page.is_closed():
                    self._update_active_page()
                    return f"Tab closed successfully (Tier 1: graceful close): {target_url}"
            except Exception as t1_err:
                print(f"[Browser] Tier 1 close failed or timed out ({t1_err}). Escalating to Tier 2...")

        # ── Tier 2: Raw CDP Target.closeTarget ────────────────────────────────
        try:
            print(f"[Browser] Tier 2: Attempting raw CDP Target.closeTarget...")
            cdp = await asyncio.wait_for(target_page.context.new_cdp_session(target_page), timeout=1.5)
            info = await asyncio.wait_for(cdp.send("Target.getTargetInfo"), timeout=1.5)
            target_id = info.get("targetInfo", {}).get("targetId")
            if target_id:
                res = await asyncio.wait_for(
                    cdp.send("Target.closeTarget", {"targetId": target_id}),
                    timeout=1.5
                )
                if res.get("success", False):
                    try:
                        await asyncio.wait_for(target_page.close(run_before_unload=False), timeout=0.5)
                    except Exception:
                        pass
                    self._update_active_page()
                    return f"Tab closed successfully (Tier 2: raw CDP Target.closeTarget): {target_url}"
        except Exception as t2_err:
            print(f"[Browser] Tier 2 close failed ({t2_err}). Escalating to Tier 3...")

        # ── Tier 3: Process-tree PID resolution & OS forceful kill ────────────
        print(f"[Browser] Tier 3: Resolving renderer PID and applying OS-level forceful termination...")
        renderer_pid = await self._get_tab_renderer_pid(target_page)
        if renderer_pid:
            killed = _os_force_kill(renderer_pid)
            if killed:
                try:
                    await asyncio.wait_for(target_page.close(run_before_unload=False), timeout=0.5)
                except Exception:
                    pass
                self._update_active_page()
                return f"Tab forcefully terminated (Tier 3: OS process kill, PID {renderer_pid}): {target_url}"

        # If specific renderer PID could not be found, and only 1 tab exists or all tabs are hung
        remaining = [p for p in self._context.pages if not p.is_closed()]
        if len(remaining) <= 1:
            browser_pid = await self._get_browser_pid()
            if browser_pid:
                killed = _os_force_kill(browser_pid)
                if killed:
                    self._context = self._page = None
                    return f"Tab and browser process forcefully terminated (Tier 3: OS process kill, PID {browser_pid})."

        self._update_active_page()
        return f"Tab closure escalation completed for: {target_url}"

    async def screenshot(self, path: str = None) -> str:
        page = await self._get_page()
        try:
            save_path = path or str(Path.home() / "Desktop" / "jarvis_screenshot.png")
            await page.screenshot(path=save_path, full_page=False)
            return f"Screenshot saved: {save_path}"
        except Exception as e:
            return f"Screenshot error: {e}"

    async def back(self) -> str:
        page = await self._get_page()
        try:
            await page.go_back(timeout=10_000)
            return f"Navigated back: {page.url}"
        except Exception as e:
            return f"Back error: {e}"

    async def forward(self) -> str:
        page = await self._get_page()
        try:
            await page.go_forward(timeout=10_000)
            return f"Navigated forward: {page.url}"
        except Exception as e:
            return f"Forward error: {e}"

    async def reload(self) -> str:
        page = await self._get_page()
        try:
            await page.reload(timeout=15_000)
            return f"Page reloaded: {page.url}"
        except Exception as e:
            return f"Reload error: {e}"

    async def close_browser(self) -> str:
        await self._async_close()
        return f"{self.browser_name} closed."

    async def open_whatsapp(self) -> str:
        """Opens WhatsApp Web in JARVIS's persistent common session or switches to the active tab."""
        page = await self._get_page()
        target_page = None
        if self._context:
            for p in self._context.pages:
                if not p.is_closed() and "web.whatsapp.com" in p.url.lower():
                    target_page = p
                    break
        if target_page:
            self._page = target_page
            await target_page.bring_to_front()
            try:
                await target_page.wait_for_load_state("domcontentloaded", timeout=5_000)
            except Exception:
                pass
        else:
            if page.url and page.url != "about:blank":
                page = await self._context.new_page()
                self._page = page
            await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=30_000)

        return await self._check_whatsapp_state(self._page)

    async def _check_whatsapp_state(self, page: Page) -> str:
        """Determines if WhatsApp Web is logged in or waiting for QR code."""
        for _ in range(8):
            chat_indicators = [
                'div[contenteditable="true"][data-tab="3"]',
                '[aria-label="Search input textbox"]',
                '[aria-label="Search or start new chat"]',
                '[data-testid="chat-list-search"]',
                '#side',
                '#pane-side',
            ]
            for sel in chat_indicators:
                try:
                    if await page.locator(sel).count() > 0:
                        return outcome.done(
                            "browser_control",
                            action="open_whatsapp",
                            status="logged_in",
                            detail="WhatsApp Web is open and active (session loaded). Ready to use.",
                            verified=True,
                        )
                except Exception:
                    pass

            qr_indicators = [
                'canvas[aria-label="Scan me!"]',
                'div[data-ref]',
                'div[data-testid="qrcode"]',
                'canvas',
            ]
            for sel in qr_indicators:
                try:
                    if await page.locator(sel).count() > 0:
                        return outcome.unverified(
                            "browser_control",
                            "WhatsApp Web is open. A QR code is displayed on your screen — please scan it once with your phone. The session will be saved permanently in JARVIS common storage.",
                            action="open_whatsapp",
                            status="qr_code_required",
                        )
                except Exception:
                    pass
            await asyncio.sleep(0.5)

        return f"WhatsApp Web is open at {page.url}."

    async def open_telegram(self) -> str:
        """Opens Telegram Web in JARVIS's persistent common session or switches to the active tab."""
        page = await self._get_page()
        target_page = None
        if self._context:
            for p in self._context.pages:
                if not p.is_closed() and "web.telegram.org" in p.url.lower():
                    target_page = p
                    break
        if target_page:
            self._page = target_page
            await target_page.bring_to_front()
            try:
                await target_page.wait_for_load_state("domcontentloaded", timeout=5_000)
            except Exception:
                pass
        else:
            if page.url and page.url != "about:blank":
                page = await self._context.new_page()
                self._page = page
            await page.goto("https://web.telegram.org/a/", wait_until="domcontentloaded", timeout=30_000)

        return await self._check_telegram_state(self._page)

    async def _check_telegram_state(self, page: Page) -> str:
        """Determines if Telegram Web is logged in or waiting for QR/phone login."""
        for _ in range(8):
            chat_indicators = [
                'input.chatlist-search-input',
                'input.input-search-input',
                '.input-search input',
                '#telegram-search-input',
                '.chat-list',
                '#middle-column',
            ]
            for sel in chat_indicators:
                try:
                    if await page.locator(sel).count() > 0:
                        return outcome.done(
                            "browser_control",
                            action="open_telegram",
                            status="logged_in",
                            detail="Telegram Web is open and active (session loaded). Ready to use.",
                            verified=True,
                        )
                except Exception:
                    pass

            qr_indicators = [
                '.qr-container',
                '.auth-image',
                'button:has-text("Log in by QR Code")',
                'input[type="tel"]',
                '.login-page',
            ]
            for sel in qr_indicators:
                try:
                    if await page.locator(sel).count() > 0:
                        return outcome.unverified(
                            "browser_control",
                            "Telegram Web is open. Please log in on the browser window (via QR code or phone number). The session will be saved permanently in JARVIS common storage.",
                            action="open_telegram",
                            status="login_required",
                        )
                except Exception:
                    pass
            await asyncio.sleep(0.5)

        return f"Telegram Web is open at {page.url}."

    async def send_whatsapp_message(self, receiver: str, message: str) -> str:
        """Autonomously finds a contact, types a message, and sends it via WhatsApp Web."""
        if not receiver or not message:
            return outcome.failed("send_message", "Both recipient and message text are required.", platform="WhatsApp")

        await self.open_whatsapp()
        page = self._page
        if not page:
            return outcome.failed("send_message", "Could not acquire WhatsApp Web page.", platform="WhatsApp")

        try:
            if await page.locator('canvas, [data-testid="qrcode"], div[data-ref]').count() > 0:
                if await page.locator('#side [contenteditable="true"], [data-testid="chat-list-search"]').count() == 0:
                    return outcome.unverified(
                        "send_message",
                        "WhatsApp Web QR code is showing. Please scan the QR code in the browser to log in once.",
                        platform="WhatsApp",
                        to=receiver
                    )
        except Exception:
            pass

        search_selectors = [
            'div[contenteditable="true"][data-tab="3"]',
            '[aria-label="Search input textbox"]',
            '[aria-label="Search or start new chat"]',
            '[data-testid="chat-list-search"]',
            '#side div[contenteditable="true"]',
        ]
        search_el = None
        for sel in search_selectors:
            loc = page.locator(sel)
            if await loc.count() > 0:
                search_el = loc.first
                break

        if search_el is None:
            return outcome.failed(
                "send_message",
                "WhatsApp search bar could not be located. Ensure WhatsApp Web is logged in.",
                platform="WhatsApp",
                to=receiver
            )

        try:
            await search_el.click(timeout=5_000)
            await search_el.fill("")
            await search_el.type(receiver, delay=40)
            await asyncio.sleep(1.2)
        except Exception as e:
            return outcome.failed("send_message", f"Failed typing into WhatsApp search: {e}", platform="WhatsApp", to=receiver)

        try:
            contact_loc = page.locator(f'#pane-side span[title*="{receiver}" i], #side span[title*="{receiver}" i]')
            if await contact_loc.count() > 0:
                await contact_loc.first.click(timeout=5_000)
            else:
                list_items = page.locator('#pane-side div[role="listitem"]')
                if await list_items.count() > 0:
                    await list_items.first.click(timeout=5_000)
                else:
                    await page.keyboard.press("Enter")
        except Exception:
            await page.keyboard.press("Enter")

        await asyncio.sleep(1.0)

        msg_selectors = [
            'footer div[contenteditable="true"][data-tab="10"]',
            'footer div[contenteditable="true"]',
            'div[title="Type a message"]',
            '[data-testid="conversation-compose-box-input"]',
            '[aria-label="Type a message"]',
            'div[role="textbox"][data-tab="10"]',
        ]
        msg_el = None
        for sel in msg_selectors:
            loc = page.locator(sel)
            if await loc.count() > 0:
                msg_el = loc.first
                break

        if msg_el is None:
            return outcome.failed(
                "send_message",
                f"Could not open chat with '{receiver}' or find compose input.",
                platform="WhatsApp",
                to=receiver
            )

        try:
            await msg_el.click(timeout=5_000)
            await msg_el.fill(message)
            await asyncio.sleep(0.3)
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.8)

            send_btn = page.locator('[data-testid="send"], button span[data-icon="send"], button[aria-label="Send"]')
            if await send_btn.count() > 0:
                try:
                    await send_btn.first.click(timeout=2_000)
                    await asyncio.sleep(0.5)
                except Exception:
                    pass

            return outcome.done(
                "send_message",
                platform="WhatsApp",
                to=receiver,
                verified=True
            )
        except Exception as e:
            return outcome.failed("send_message", f"Failed sending WhatsApp message: {e}", platform="WhatsApp", to=receiver)

    async def send_telegram_message(self, receiver: str, message: str) -> str:
        """Autonomously finds a contact, types a message, and sends it via Telegram Web."""
        if not receiver or not message:
            return outcome.failed("send_message", "Both recipient and message text are required.", platform="Telegram")

        await self.open_telegram()
        page = self._page
        if not page:
            return outcome.failed("send_message", "Could not acquire Telegram Web page.", platform="Telegram")

        try:
            login_loc = page.locator('.qr-container, .auth-image, button:has-text("Log in by QR Code"), input[type="tel"]')
            if await login_loc.count() > 0:
                if await page.locator('input.chatlist-search-input, .input-search input').count() == 0:
                    return outcome.unverified(
                        "send_message",
                        "Telegram Web login is required. Please log in on the opened browser window once.",
                        platform="Telegram",
                        to=receiver
                    )
        except Exception:
            pass

        search_selectors = [
            'input.chatlist-search-input',
            'input.input-search-input',
            '.input-search input',
            'input[type="text"][placeholder*="Search"]',
            '#telegram-search-input',
        ]
        search_el = None
        for sel in search_selectors:
            loc = page.locator(sel)
            if await loc.count() > 0:
                search_el = loc.first
                break

        if search_el is None:
            return outcome.failed(
                "send_message",
                "Telegram search input could not be located. Ensure Telegram Web is logged in.",
                platform="Telegram",
                to=receiver
            )

        try:
            await search_el.click(timeout=5_000)
            await search_el.fill("")
            await search_el.type(receiver, delay=40)
            await asyncio.sleep(1.2)
        except Exception as e:
            return outcome.failed("send_message", f"Failed typing into Telegram search: {e}", platform="Telegram", to=receiver)

        try:
            res_item = page.locator(f'.chat-list .ListItem:has-text("{receiver}"), .search-group .chatlist-chat')
            if await res_item.count() > 0:
                await res_item.first.click(timeout=5_000)
            else:
                await page.keyboard.press("Enter")
        except Exception:
            await page.keyboard.press("Enter")

        await asyncio.sleep(1.0)

        msg_selectors = [
            'div.input-message-input[contenteditable="true"]',
            '.chat-input-main [contenteditable="true"]',
            'div[contenteditable="true"][data-peer-id]',
            '#editable-message-text',
            'div[contenteditable="true"]',
        ]
        msg_el = None
        for sel in msg_selectors:
            loc = page.locator(sel)
            if await loc.count() > 0:
                msg_el = loc.first
                break

        if msg_el is None:
            return outcome.failed(
                "send_message",
                f"Could not open chat with '{receiver}' or locate compose input.",
                platform="Telegram",
                to=receiver
            )

        try:
            await msg_el.click(timeout=5_000)
            await msg_el.fill(message)
            await asyncio.sleep(0.3)
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.8)

            send_btn = page.locator('.btn-send-container button, button.send')
            if await send_btn.count() > 0:
                try:
                    await send_btn.first.click(timeout=2_000)
                    await asyncio.sleep(0.5)
                except Exception:
                    pass

            return outcome.done(
                "send_message",
                platform="Telegram",
                to=receiver,
                verified=True
            )
        except Exception as e:
            return outcome.failed("send_message", f"Failed sending Telegram message: {e}", platform="Telegram", to=receiver)

    async def read_whatsapp_messages(self, contact: Optional[str] = None, limit: int = 5) -> str:
        """Reads recent messages from WhatsApp Web."""
        await self.open_whatsapp()
        page = self._page
        if not page:
            return "Could not acquire WhatsApp Web page."

        if contact:
            search_el = page.locator('div[contenteditable="true"][data-tab="3"], [aria-label="Search input textbox"], #side [contenteditable="true"]').first
            if await search_el.count() > 0:
                try:
                    await search_el.click(timeout=3_000)
                    await search_el.fill(contact)
                    await asyncio.sleep(1.2)
                    contact_item = page.locator(f'#pane-side span[title*="{contact}" i]').first
                    if await contact_item.count() > 0:
                        await contact_item.click(timeout=3_000)
                    else:
                        await page.keyboard.press("Enter")
                    await asyncio.sleep(1.0)
                except Exception:
                    pass

        try:
            containers = page.locator('div[data-testid="msg-container"], div.message-in, div.message-out')
            total = await containers.count()
            if total == 0:
                return f"No messages visible for {contact or 'current chat'} on WhatsApp."
            start_idx = max(0, total - limit)
            messages = []
            for i in range(start_idx, total):
                t = await containers.nth(i).inner_text()
                lines = [l.strip() for l in t.splitlines() if l.strip()]
                clean = " | ".join(lines)
                if clean:
                    messages.append(clean)
            return f"Recent WhatsApp messages ({contact or 'current chat'}):\n" + "\n".join(f"• {m}" for m in messages)
        except Exception as e:
            return f"Error reading WhatsApp messages: {e}"

    async def read_telegram_messages(self, contact: Optional[str] = None, limit: int = 5) -> str:
        """Reads recent messages from Telegram Web."""
        await self.open_telegram()
        page = self._page
        if not page:
            return "Could not acquire Telegram Web page."

        if contact:
            search_el = page.locator('input.chatlist-search-input, .input-search input, input[type="text"]').first
            if await search_el.count() > 0:
                try:
                    await search_el.click(timeout=3_000)
                    await search_el.fill(contact)
                    await asyncio.sleep(1.2)
                    res_item = page.locator(f'.chat-list .ListItem:has-text("{contact}")').first
                    if await res_item.count() > 0:
                        await res_item.click(timeout=3_000)
                    else:
                        await page.keyboard.press("Enter")
                    await asyncio.sleep(1.0)
                except Exception:
                    pass

        try:
            containers = page.locator('.message, .Message, .message-content')
            total = await containers.count()
            if total == 0:
                return f"No messages visible for {contact or 'current chat'} on Telegram."
            start_idx = max(0, total - limit)
            messages = []
            for i in range(start_idx, total):
                t = await containers.nth(i).inner_text()
                lines = [l.strip() for l in t.splitlines() if l.strip()]
                clean = " | ".join(lines)
                if clean:
                    messages.append(clean)
            return f"Recent Telegram messages ({contact or 'current chat'}):\n" + "\n".join(f"• {m}" for m in messages)
        except Exception as e:
            return f"Error reading Telegram messages: {e}"

class _SessionRegistry:
    """Manages all active browser sessions."""

    def __init__(self):
        self._sessions:        dict[str, _BrowserSession] = {}
        self._active_browser:  str                        = ""
        self._lock             = threading.Lock()
        self._last_native_url: str                        = ""

    def has(self, browser_name: str | None = None) -> bool:
        """Is there an active automation session for this browser (or any)?"""
        with self._lock:
            if not browser_name:
                return bool(self._sessions)
            name = _ALIASES.get(browser_name.lower().strip(), browser_name.lower().strip())
            return name in self._sessions

    def note_native_url(self, url: str) -> None:
        self._last_native_url = url

    def pop_native_url(self) -> str:
        """Returns the last natively-opened URL once (consumed to avoid repeats)."""
        url, self._last_native_url = self._last_native_url, ""
        return url

    def _get_or_create(self, browser_name: str) -> _BrowserSession:
        with self._lock:
            if browser_name not in self._sessions:
                sess = _BrowserSession(browser_name)
                sess.start()
                self._sessions[browser_name] = sess
                print(f"[Registry] New session: {browser_name}")
            return self._sessions[browser_name]

    def get(self, browser_name: str | None = None) -> _BrowserSession:
        if not browser_name:
            browser_name = self._active_browser or get_jarvis_browser()
        browser_name = _ALIASES.get(browser_name.lower().strip(), browser_name.lower().strip())
        sess = self._get_or_create(browser_name)
        self._active_browser = browser_name
        return sess

    def switch(self, browser_name: str) -> str:
        browser_name = _ALIASES.get(browser_name.lower().strip(), browser_name.lower().strip())
        self._get_or_create(browser_name)
        self._active_browser = browser_name
        return f"Active browser → {browser_name}"

    def close_one(self, browser_name: str) -> str:
        with self._lock:
            sess = self._sessions.pop(browser_name, None)
        if sess:
            sess.close()
            if self._active_browser == browser_name:
                self._active_browser = ""
            return f"{browser_name} closed."
        return f"No active session for: {browser_name}"

    def close_all(self) -> str:
        with self._lock:
            names    = list(self._sessions.keys())
            sessions = list(self._sessions.values())
            self._sessions.clear()
            self._active_browser = ""
        for s in sessions:
            try:
                s.close()
            except Exception:
                pass
        return "All browsers closed: " + (", ".join(names) if names else "none")

    def list_sessions(self) -> str:
        with self._lock:
            if not self._sessions:
                return "No active browser sessions."
            lines = []
            for name in self._sessions:
                marker = " ◀ active" if name == self._active_browser else ""
                lines.append(f"  • {name}{marker}")
            return "Open browsers:\n" + "\n".join(lines)


_registry = _SessionRegistry()

def browser_control(
    parameters:    dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params  = parameters or {}
    action  = params.get("action", "").lower().strip()
    browser = params.get("browser", "").lower().strip() or None
    result  = "Unknown action."

    if action == "switch":
        target = browser or params.get("target", "").lower().strip()
        result = _registry.switch(target) if target else "Please specify a browser."
        _log(player, result)
        return result

    if action == "list_browsers":
        result = _registry.list_sessions()
        _log(player, result)
        return result

    if action in ("list_tabs", "list_open_tabs"):
        tabs = _native_tracker.list_tabs()
        result = f"Tracked native tabs ({len(tabs)}):\n" + "\n".join(
            f"  • {t['domain'].capitalize() or 'Tab'}: {t['url']} ({t['age_sec']}s ago)" for t in tabs
        ) if tabs else "No active native tabs tracked."
        _log(player, result)
        return result

    if action == "close_all":
        result = _registry.close_all()
        _log(player, result)
        return result

    if action == "close":
        target = browser or _registry._active_browser
        if target and _registry.has(target):
            result = _registry.close_one(target)
        elif target:
            try:
                from actions.computer_control import _close_app
                outcome_res = _close_app(target)
                result = f"Closed {target}." if "done" in str(outcome_res).lower() else f"No active session for: {target}"
            except Exception:
                result = _registry.close_one(target)
        else:
            result = "No browser specified."
        _log(player, result)
        return result

    if action == "close_tab" and not _registry.has(browser):
        result = _close_native_tab(
            title=params.get("title"),
            url=params.get("url"),
            browser=browser,
            force=bool(params.get("force", False)),
        )
        _log(player, result)
        return result

    if action == "set_default_browser":
        target = (browser or params.get("browser") or params.get("name") or "").strip().lower()
        if not target:
            result = "No browser specified to set as default."
        else:
            norm = _ALIASES.get(target, target)
            try:
                from memory import config_manager
                config_manager.save_default_browser(norm)
                result = f"JARVIS default browser set to: {norm}"
            except Exception as e:
                result = f"Failed to save default browser: {e}"
        _log(player, result)
        return result

    if action in ("get_browser_config", "browser_config"):
        try:
            from memory import config_manager
            cfg_browser = config_manager.get_default_browser()
        except Exception:
            cfg_browser = "chrome"
        host_default = _detect_default_browser()
        active_effective = get_jarvis_browser()
        exe = _resolve_browser_executable(active_effective)
        result = (
            f"JARVIS Default Browser Policy:\n"
            f"  • Configured: {cfg_browser}\n"
            f"  • Active Effective: {active_effective}\n"
            f"  • Executable: {exe or 'Not Found (Will fallback to OS association)'}\n"
            f"  • Host OS Default: {host_default}"
        )
        _log(player, result)
        return result

    # ── WhatsApp and Telegram direct actions (Autonomous Browser Automation) ─
    if action in ("open_whatsapp", "whatsapp"):
        sess = _registry.get(browser)
        result = sess.run(sess.open_whatsapp())
        _log(player, result)
        return result

    if action in ("open_telegram", "telegram"):
        sess = _registry.get(browser)
        result = sess.run(sess.open_telegram())
        _log(player, result)
        return result

    if action in ("whatsapp_send", "send_whatsapp"):
        receiver = params.get("receiver") or params.get("to") or params.get("contact") or ""
        text = params.get("text") or params.get("message") or params.get("message_text") or ""
        sess = _registry.get(browser)
        result = sess.run(sess.send_whatsapp_message(receiver, text))
        _log(player, result)
        return result

    if action in ("telegram_send", "send_telegram"):
        receiver = params.get("receiver") or params.get("to") or params.get("contact") or ""
        text = params.get("text") or params.get("message") or params.get("message_text") or ""
        sess = _registry.get(browser)
        result = sess.run(sess.send_telegram_message(receiver, text))
        _log(player, result)
        return result

    if action in ("whatsapp_read", "read_whatsapp"):
        contact = params.get("contact") or params.get("receiver") or None
        limit = int(params.get("limit", 5))
        sess = _registry.get(browser)
        result = sess.run(sess.read_whatsapp_messages(contact, limit))
        _log(player, result)
        return result

    if action in ("telegram_read", "read_telegram"):
        contact = params.get("contact") or params.get("receiver") or None
        limit = int(params.get("limit", 5))
        sess = _registry.get(browser)
        result = sess.run(sess.read_telegram_messages(contact, limit))
        _log(player, result)
        return result

    # ── Navigation is ALWAYS native (except WhatsApp / Telegram / active automation) ─
    # go_to / search / new_tab open the site in the user's own browser —
    # their own profile, logged-in accounts and start page; exactly as if the
    # user had opened it themselves. A controlled window with about:blank never
    # opens here. The only exception: if an automation flow is already running,
    # or for WhatsApp/Telegram (which require persistent common session automation).
    if action in ("go_to", "search", "new_tab"):
        if _registry.has(browser):
            sess = _registry.get(browser)
            try:
                if action == "search":
                    result = sess.run(sess.search(params.get("query", ""),
                                                  params.get("engine", "google")))
                elif action == "new_tab":
                    result = sess.run(sess.new_tab(params.get("url", "")))
                else:
                    result = sess.run(sess.go_to(params.get("url", "")))
            except concurrent.futures.TimeoutError:
                result = f"Browser action '{action}' timed out (60s)."
            except Exception as e:
                result = f"Browser error ({action}): {e}"
            _log(player, result)
            return result

        if action == "search":
            base    = _SEARCH_ENGINES.get(params.get("engine", "google").lower(),
                                          _SEARCH_ENGINES["google"])
            nav_url = base + params.get("query", "").replace(" ", "+")
        else:
            nav_url = params.get("url", "").strip()

        # WhatsApp and Telegram ALWAYS route through JARVIS common automation session
        if any(k in nav_url.lower() for k in ("web.whatsapp.com", "web.telegram.org", "whatsapp.com", "telegram.org")):
            sess = _registry.get(browser)
            try:
                result = sess.run(sess.go_to(nav_url))
            except Exception as e:
                result = f"Browser error ({action}): {e}"
            _log(player, result)
            return result

        result = open_url(nav_url, browser)
        _log(player, result)
        return result

    # ── Interactive actions (click/type/read…) ───────────────────────────────
    # These require a physically controllable browser; the automation window
    # only opens here, and as soon as it opens it goes to the user's last
    # navigated page — it doesn't sit on a blank page.
    try:
        sess = _registry.get(browser)
    except Exception as e:
        result = f"Could not start browser session: {e}"
        _log(player, result)
        return result

    try:
        last = _registry.pop_native_url()
        if last:
            try:
                sess.run(sess.go_to(last))
            except Exception as e:
                print(f"[Browser] Could not resume last page ({last}): {e}")

        if action == "click":
            result = sess.run(sess.click(params.get("selector"), params.get("text")))
        elif action == "type":
            result = sess.run(sess.type_text(
                params.get("selector"), params.get("text", ""), params.get("clear_first", True)))
        elif action == "scroll":
            result = sess.run(sess.scroll(params.get("direction", "down"), int(params.get("amount", 500))))
        elif action == "fill_form":
            result = sess.run(sess.fill_form(params.get("fields", {})))
        elif action == "smart_click":
            result = sess.run(sess.smart_click(params.get("description", "")))
        elif action == "smart_type":
            result = sess.run(sess.smart_type(params.get("description", ""), params.get("text", "")))
        elif action == "get_text":
            result = sess.run(sess.get_text())
        elif action == "get_url":
            result = sess.run(sess.get_url())
        elif action == "press":
            result = sess.run(sess.press(params.get("key", "Enter")))
        elif action == "close_tab":
            result = sess.run(
                sess.close_tab(
                    url=params.get("url"),
                    title=params.get("title"),
                    force=bool(params.get("force", False)),
                )
            )
        elif action == "screenshot":
            result = sess.run(sess.screenshot(params.get("path")))
        elif action == "back":
            result = sess.run(sess.back())
        elif action == "forward":
            result = sess.run(sess.forward())
        elif action == "reload":
            result = sess.run(sess.reload())
        else:
            result = f"Unknown browser action: '{action}'"

    except concurrent.futures.TimeoutError:
        result = f"Browser action '{action}' timed out (60s)."
    except Exception as e:
        result = f"Browser error ({action}): {e}"

    _log(player, result)
    return result


def _log(player, text: str):
    short = str(text)[:80]
    print(f"[Browser] {short}")
    if player:
        print(f"[Browser] {short[:80]}")          # terminal, not the HUD


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "browser_control",
    "description": (
        "Controls the web browser: open an address, search, click, type, "
        "scroll, read the page, manage tabs, go back and forward. "
        "THIS TOOL OPENS THE BROWSER ITSELF. Never call open_app for the "
        "browser first - doing both launches it twice, the second copy on a "
        "different profile with none of the user's sign-ins. 'Open Chrome and "
        "go to YouTube' is ONE call to this tool. "
        "Read the status it returns. 'done' means it was confirmed - for an "
        "open, the url reported back is the page's OWN address, so if it "
        "differs from what was asked for the site redirected and the user "
        "should be told. 'unverified' means the address was handed to the "
        "system's default browser, which never reports back: say it was opened "
        "but not confirmed, never that the page is up. 'failed' means nothing "
        "happened."
    ),
    "brief": (
        "Controls the web browser: open a URL, navigate, click, read the page."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | get_url | press | new_tab | close_tab | list_tabs | screenshot | back | forward | reload | switch | list_browsers | close | close_all | open_whatsapp_web | open_telegram_web | whatsapp_send | telegram_send | whatsapp_read | telegram_read (NOTE: To open the WhatsApp app on the computer, use open_app('WhatsApp') - do NOT use browser_control)"
            },
            "browser": {
                "type": "STRING",
                "description": "Target browser: chrome | edge | firefox | opera | operagx | brave | vivaldi | safari. Omit to use the currently active browser."
            },
            "url": {
                "type": "STRING",
                "description": "URL for go_to / new_tab action"
            },
            "receiver": {
                "type": "STRING",
                "description": "Recipient name/contact for whatsapp_send, telegram_send, or message reading"
            },
            "message": {
                "type": "STRING",
                "description": "Message text to send for whatsapp_send or telegram_send"
            },
            "limit": {
                "type": "INTEGER",
                "description": "Max number of messages to read for whatsapp_read or telegram_read (default: 5)"
            },
            "query": {
                "type": "STRING",
                "description": "Search query for search action"
            },
            "engine": {
                "type": "STRING",
                "description": "Search engine: google | bing | duckduckgo | yandex (default: google)"
            },
            "selector": {
                "type": "STRING",
                "description": "CSS selector for click/type"
            },
            "text": {
                "type": "STRING",
                "description": "Text to click or type"
            },
            "description": {
                "type": "STRING",
                "description": "Element description for smart_click/smart_type"
            },
            "direction": {
                "type": "STRING",
                "description": "up | down for scroll"
            },
            "amount": {
                "type": "INTEGER",
                "description": "Scroll amount in pixels (default: 500)"
            },
            "key": {
                "type": "STRING",
                "description": "Key name for press action (e.g. Enter, Escape, F5)"
            },
            "path": {
                "type": "STRING",
                "description": "Save path for screenshot"
            },
            "incognito": {
                "type": "BOOLEAN",
                "description": "Open in private/incognito mode"
            },
            "clear_first": {
                "type": "BOOLEAN",
                "description": "Clear field before typing (default: true)"
            },
            "title": {
                "type": "STRING",
                "description": "Page or tab title filter for close_tab action"
            },
            "force": {
                "type": "BOOLEAN",
                "description": "Forcefully terminate uncooperative or frozen tabs via OS process termination (default: false)"
            }
        },
        "required": [
            "action"
        ]
    },
    "handler": browser_control,
}
