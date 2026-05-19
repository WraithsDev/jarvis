from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path


IS_WINDOWS = sys.platform.startswith("win")
NO_WINDOW = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0


def open_url(url: str) -> None:
    if not url:
        return
    if IS_WINDOWS:
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return
        except Exception:
            pass
    webbrowser.open(url)


def start_process(target: str) -> subprocess.CompletedProcess | None:
    if not target:
        return None
    if IS_WINDOWS:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Start-Process", target],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
            creationflags=NO_WINDOW,
        )
        return completed
    raise RuntimeError("Process launcher is implemented for Windows.")


def copy_to_clipboard(text: str) -> None:
    if IS_WINDOWS:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Set-Clipboard", "-Value", text],
            check=True,
            timeout=5,
            creationflags=NO_WINDOW,
        )
        return
    raise RuntimeError("Clipboard helper is implemented for Windows.")


def press_enter_after_delay(delay: float = 0.8) -> tuple[bool, str]:
    time.sleep(max(0.0, delay))
    try:
        import pyautogui

        pyautogui.FAILSAFE = False
        pyautogui.press("enter")
        return True, "ok"
    except Exception as exc:
        return False, f"Otomatik Enter gonderilemedi: {exc}"


def press_key(key: str, delay: float = 0.0) -> tuple[bool, str]:
    time.sleep(max(0.0, delay))
    try:
        import pyautogui

        pyautogui.FAILSAFE = False
        pyautogui.press(key)
        return True, "ok"
    except Exception as exc:
        return False, f"Tus gonderilemedi ({key}): {exc}"


def hotkey(*keys: str) -> tuple[bool, str]:
    try:
        import pyautogui

        pyautogui.FAILSAFE = False
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
        return True, "ok"
    except Exception as exc:
        return False, f"Kisayol gonderilemedi: {exc}"


def focus_window(title: str) -> tuple[bool, str]:
    if not IS_WINDOWS:
        return False, "Pencere odaklama sadece Windows icin hazirlandi."
    safe_title = (title or "").replace("'", "''")
    if not safe_title:
        return False, "Pencere basligi bos."
    script = (
        "$wshell = New-Object -ComObject WScript.Shell; "
        f"if ($wshell.AppActivate('{safe_title}')) {{ 'ok' }} else {{ 'not_found' }}"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=4,
            creationflags=NO_WINDOW,
        )
        output = (result.stdout or result.stderr or "").strip()
        if result.returncode == 0 and "ok" in output.lower():
            return True, "ok"
        return False, output or "Pencere bulunamadi."
    except Exception as exc:
        return False, f"Pencere odaklanamadi: {exc}"


def get_window_rect(title: str) -> tuple[bool, tuple[int, int, int, int] | None, str]:
    if not IS_WINDOWS:
        return False, None, "Pencere konumu sadece Windows icin hazirlandi."
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        needle = (title or "").lower()
        hwnd = user32.FindWindowW(None, title)
        if not hwnd and needle:
            found = []

            def _enum_proc(candidate, _):
                if not user32.IsWindowVisible(candidate):
                    return True
                length = user32.GetWindowTextLengthW(candidate)
                if length <= 0:
                    return True
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(candidate, buffer, length + 1)
                if needle in buffer.value.lower():
                    found.append(candidate)
                    return False
                return True

            callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(_enum_proc)
            user32.EnumWindows(callback, 0)
            hwnd = found[0] if found else 0
        if not hwnd:
            try:
                import pyautogui

                for win in pyautogui.getWindowsWithTitle(title):
                    if getattr(win, "width", 0) > 0 and getattr(win, "height", 0) > 0:
                        return True, (win.left, win.top, win.left + win.width, win.top + win.height), "ok"
            except Exception:
                pass
            return False, None, "Pencere bulunamadi."
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False, None, "Pencere konumu okunamadi."
        return True, (rect.left, rect.top, rect.right, rect.bottom), "ok"
    except Exception as exc:
        return False, None, f"Pencere konumu okunamadi: {exc}"


def click_point(x: int, y: int, clicks: int = 1, delay: float = 0.0) -> tuple[bool, str]:
    time.sleep(max(0.0, delay))
    try:
        import pyautogui

        pyautogui.FAILSAFE = False
        pyautogui.click(x=x, y=y, clicks=max(1, int(clicks)), interval=0.08)
        return True, "ok"
    except Exception as exc:
        return False, f"Tiklama gonderilemedi: {exc}"


def type_text(text: str) -> tuple[bool, str]:
    try:
        import pyautogui

        pyautogui.FAILSAFE = False
        pyautogui.write(text, interval=0.01)
        return True, "ok"
    except Exception as exc:
        return False, f"Metin yazilamadi: {exc}"


def find_windows_app(app_name: str, aliases: dict[str, str] | None = None) -> str:
    normalized = (app_name or "").strip().lower()
    resolved = (aliases or {}).get(normalized, app_name).strip()
    exe = resolved if resolved.lower().endswith(".exe") else f"{resolved}.exe"

    if shutil.which(resolved):
        return resolved
    if shutil.which(exe):
        return exe

    start_menu_roots = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]
    candidates = [resolved.casefold(), normalized.casefold()]
    for root in start_menu_roots:
        if not root.exists():
            continue
        for shortcut in root.rglob("*.lnk"):
            stem = shortcut.stem.casefold()
            if any(candidate and candidate in stem for candidate in candidates):
                return str(shortcut)
    return resolved


def spotify_search_url(query: str) -> str:
    return f"spotify:search:{urllib.parse.quote(query.strip())}"


def play_mp3_process(path: Path, volume: float = 0.2) -> subprocess.Popen:
    if IS_WINDOWS:
        safe_uri = path.resolve().as_uri().replace("'", "''")
        safe_volume = max(0.0, min(1.0, volume))
        script = (
            "Add-Type -AssemblyName PresentationCore; "
            "$p=New-Object System.Windows.Media.MediaPlayer; "
            f"$p.Open([Uri]'{safe_uri}'); "
            f"$p.Volume={safe_volume}; "
            "$p.Play(); "
            "$deadline=(Get-Date).AddSeconds(3); "
            "while($p.NaturalDuration.HasTimeSpan -eq $false -and (Get-Date) -lt $deadline){Start-Sleep -Milliseconds 50}; "
            "if($p.NaturalDuration.HasTimeSpan){$d=$p.NaturalDuration.TimeSpan.TotalMilliseconds}else{$d=1800}; "
            "Start-Sleep -Milliseconds ([Math]::Min(8000,[Math]::Max(250,[int]$d))); "
            "$p.Close()"
        )
        return subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=NO_WINDOW,
        )
    raise RuntimeError("MP3 playback helper is implemented for Windows.")
