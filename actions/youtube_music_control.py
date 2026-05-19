"""
YouTube Music playback helpers for the Windows app/PWA or browser.
"""

from __future__ import annotations

import time
import urllib.parse

from actions.windows_utils import click_point, focus_window, get_window_rect, hotkey, open_url, press_key


def _youtube_music_search_url(query: str) -> str:
    return "https://music.youtube.com/search?q=" + urllib.parse.quote_plus(query.strip())


def _focus_youtube_music(delay: float = 1.4) -> None:
    time.sleep(max(0.0, delay))
    focus_window("YouTube Music")


def _click_first_music_result() -> tuple[bool, str]:
    ok, rect, detail = get_window_rect("YouTube Music")
    if not ok or not rect:
        return False, detail
    left, top, right, bottom = rect
    width = max(1, right - left)
    height = max(1, bottom - top)
    # First song/result row in YouTube Music usually sits below the search tabs.
    x = left + int(width * 0.34)
    y = top + int(height * 0.36)
    return click_point(x, y, clicks=2, delay=0.2)


def play_youtube_music_query(query: str) -> str:
    if not query or not query.strip():
        return "YouTube Music icin sarki veya arama metni belirtilmedi."
    try:
        open_url(_youtube_music_search_url(query))
    except Exception as exc:
        return f"YouTube Music acilamadi: {exc}"

    _focus_youtube_music(1.8)
    steps: list[str] = []
    ok, detail = _click_first_music_result()
    steps.append("first_result_click" if ok else f"click: {detail}")
    if not ok:
        for key, delay in (("tab", 0.0), ("tab", 0.05), ("tab", 0.05), ("enter", 0.25)):
            key_ok, key_detail = press_key(key, delay=delay)
            steps.append(key_detail if key_ok else f"{key}: {key_detail}")
    return f"YouTube Music'te parca acildi ve oynatma baslatildi: {query} ({', '.join(steps)})"


def youtube_music_control(action: str, query: str = "", volume_steps: int = 2) -> str:
    normalized = (action or "play_pause").strip().lower()
    if normalized in {"search", "play", "cal", "oynat"}:
        if normalized == "search":
            if not query.strip():
                return "YouTube Music icin arama metni belirtilmedi."
            open_url(_youtube_music_search_url(query))
            return f"YouTube Music aramasi acildi: {query}"
        return play_youtube_music_query(query)

    key_map = {
        "play_pause": "playpause",
        "pause": "playpause",
        "resume": "playpause",
        "next": "nexttrack",
        "skip": "nexttrack",
        "previous": "prevtrack",
        "prev": "prevtrack",
        "mute": "volumemute",
    }
    if normalized in key_map:
        ok, detail = hotkey(key_map[normalized])
        return f"YouTube Music komutu gonderildi: {normalized}" if ok else detail

    if normalized in {"volume_up", "ses_artir"}:
        for _ in range(max(1, int(volume_steps or 1))):
            hotkey("volumeup")
            time.sleep(0.04)
        return "Ses artirma komutu gonderildi."

    if normalized in {"volume_down", "ses_azalt"}:
        for _ in range(max(1, int(volume_steps or 1))):
            hotkey("volumedown")
            time.sleep(0.04)
        return "Ses azaltma komutu gonderildi."

    return "YouTube Music action: play | search | play_pause | next | previous | volume_up | volume_down | mute"
