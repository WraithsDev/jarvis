"""
Discord message helper using the desktop app quick switcher.

This uses UI automation because Discord does not provide a normal API for
sending messages from a personal account.
"""

from __future__ import annotations

import time

from actions.windows_utils import copy_to_clipboard, find_windows_app, focus_window, hotkey, open_url, start_process


DISCORD_ALIASES = {
    "discord": "Discord",
    "discord desktop": "Discord",
}


def _open_discord(app_target: str = "desktop") -> tuple[bool, str]:
    target = (app_target or "desktop").strip().lower()
    if target == "web":
        open_url("https://discord.com/app")
        time.sleep(2.5)
        return True, "Discord Web acildi."

    resolved = find_windows_app("discord", DISCORD_ALIASES)
    try:
        result = start_process(resolved)
    except Exception as exc:
        return False, f"Discord acilamadi: {exc}"
    time.sleep(2.0)
    if result is None or result.returncode == 0:
        return True, "Discord acildi."
    detail = (result.stderr or result.stdout or "").strip()
    return False, detail or "Discord acilamadi."


def _quick_switch(target: str) -> tuple[bool, str]:
    if not target.strip():
        return False, "Discord hedefi belirtilmedi."

    focus_window("Discord")
    ok, detail = hotkey("ctrl", "k")
    if not ok:
        return False, detail
    time.sleep(0.25)
    copy_to_clipboard(target)
    ok, detail = hotkey("ctrl", "v")
    if not ok:
        return False, detail
    time.sleep(0.65)
    ok, detail = hotkey("enter")
    if not ok:
        return False, detail
    time.sleep(0.8)
    return True, "Hedef acildi."


def _target_query(recipient_name: str = "", server_name: str = "", channel_name: str = "") -> str:
    recipient = (recipient_name or "").strip()
    server = (server_name or "").strip()
    channel = (channel_name or "").strip().lstrip("#")
    if recipient:
        return recipient
    if server and channel:
        return f"{server} {channel}"
    if channel:
        return f"#{channel}"
    return server


def send_discord_message(
    message: str,
    recipient_name: str = "",
    server_name: str = "",
    channel_name: str = "",
    send_now: bool = False,
    app_target: str = "desktop",
) -> str:
    if not message or not message.strip():
        return "Discord mesaji bos olamaz."

    target = _target_query(recipient_name, server_name, channel_name)
    if not target:
        return "Discord icin kisi adi, sunucu adi veya kanal adi belirt."

    ok, detail = _open_discord(app_target)
    if not ok:
        return detail

    ok, detail = _quick_switch(target)
    if not ok:
        return f"Discord hedefi acilamadi: {detail}"

    copy_to_clipboard(message)
    ok, detail = hotkey("ctrl", "v")
    if not ok:
        return f"Discord mesaji yazilamadi: {detail}"

    if send_now:
        time.sleep(0.15)
        ok, detail = hotkey("enter")
        if not ok:
            return f"Discord mesaji hazirlandi ama gonderilemedi: {detail}"
        return f"Discord mesaji gonderildi: {target}"

    return f"Discord mesaji taslak olarak hazirlandi: {target}"
