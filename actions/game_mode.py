"""
Windows gaming/performance mode helpers.
"""

from __future__ import annotations

import subprocess
import sys


NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


def _run(command: list[str], timeout: int = 8) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=NO_WINDOW,
        )
        detail = (result.stdout or result.stderr or "").strip()
        return result.returncode == 0, detail
    except Exception as exc:
        return False, str(exc)


def _set_power_scheme(scheme: str) -> tuple[bool, str]:
    aliases = {
        "high": "SCHEME_MIN",
        "performance": "SCHEME_MIN",
        "balanced": "SCHEME_BALANCED",
        "power_saver": "SCHEME_MAX",
    }
    return _run(["powercfg", "/setactive", aliases.get(scheme, scheme)])


def _close_processes(names: list[str]) -> list[str]:
    closed = []
    for name in names:
        clean = name.strip().removesuffix(".exe")
        if not clean:
            continue
        ok, _ = _run(
            ["powershell", "-NoProfile", "-Command", "Stop-Process", "-Name", clean, "-Force", "-ErrorAction", "SilentlyContinue"],
            timeout=5,
        )
        if ok:
            closed.append(clean)
    return closed


def game_performance_mode(action: str = "activate", close_background: bool = False, processes: str = "") -> str:
    normalized = (action or "activate").strip().lower()
    notes = []

    if normalized in {"activate", "on", "enable", "ac"}:
        ok, detail = _set_power_scheme("high")
        notes.append("Guc plani yuksek performansa alindi." if ok else f"Guc plani degistirilemedi: {detail}")
        if close_background:
            requested = [p for p in processes.replace(";", ",").split(",") if p.strip()]
            safe_defaults = ["OneDrive", "Teams", "Discord", "Steam", "EpicGamesLauncher"]
            closed = _close_processes(requested or safe_defaults)
            if closed:
                notes.append("Kapatilan arka plan uygulamalari: " + ", ".join(closed))
            else:
                notes.append("Arka plan uygulamasi kapatilmadi.")
        notes.append("Oyun modu aktif. Gereksiz uygulamalari kapatmadan once onay istemek daha guvenli.")
        return "\n".join(notes)

    if normalized in {"deactivate", "off", "disable", "kapat"}:
        ok, detail = _set_power_scheme("balanced")
        return "Guc plani dengeli moda alindi." if ok else f"Guc plani degistirilemedi: {detail}"

    if normalized in {"status", "durum"}:
        ok, detail = _run(["powercfg", "/getactivescheme"])
        return detail if ok and detail else "Guc plani okunamadi."

    return "Oyun modu action: activate | deactivate | status"
