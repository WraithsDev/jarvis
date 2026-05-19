"""
Spotify control helpers using media keys and Spotify URI search.
"""

from __future__ import annotations

import time

from actions.windows_utils import click_point, focus_window, get_window_rect, hotkey, open_url, press_key, spotify_search_url


def _press(key: str) -> str:
    ok, detail = hotkey(key)
    return "ok" if ok else detail


def _focus_spotify(delay: float = 1.0) -> None:
    time.sleep(max(0.0, delay))
    focus_window("Spotify")


def _click_first_search_result() -> tuple[bool, str]:
    ok, rect, detail = get_window_rect("Spotify")
    if not ok or not rect:
        return False, detail
    left, top, right, bottom = rect
    width = max(1, right - left)
    height = max(1, bottom - top)
    # Spotify desktop search results usually place the first playable result
    # under the header, left of the central content area.
    x = left + int(width * 0.34)
    y = top + int(height * 0.39)
    return click_point(x, y, clicks=2, delay=0.2)


def play_spotify_query(query: str) -> str:
    if not query.strip():
        return "Spotify icin sarki veya arama metni belirtilmedi."
    try:
        open_url(spotify_search_url(query))
    except Exception as exc:
        return f"Spotify acilamadi: {exc}"

    _focus_spotify(1.6)
    steps: list[str] = []
    ok, detail = _click_first_search_result()
    steps.append("first_result_click" if ok else f"click: {detail}")
    if not ok:
        fallback_keys = (
            ("esc", 0.0),
            ("tab", 0.05),
            ("tab", 0.05),
            ("tab", 0.05),
            ("tab", 0.05),
            ("tab", 0.05),
            ("enter", 0.25),
        )
        for key, delay in fallback_keys:
            key_ok, key_detail = press_key(key, delay=delay)
            steps.append(key_detail if key_ok else f"{key}: {key_detail}")
    return f"Spotify'da parca acildi ve oynatma baslatildi: {query} ({', '.join(steps)})"


def spotify_control(action: str, query: str = "", volume_steps: int = 2) -> str:
    normalized = (action or "play_pause").strip().lower()

    if normalized in {"search", "play", "cal", "oynat"}:
        if not query.strip():
            return "Spotify icin sarki veya arama metni belirtilmedi."
        if normalized in {"play", "cal", "oynat"}:
            return play_spotify_query(query)
        try:
            open_url(spotify_search_url(query))
        except Exception as exc:
            return f"Spotify acilamadi: {exc}"
        return f"Spotify aramasi acildi: {query}"

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
        result = _press(key_map[normalized])
        return f"Spotify komutu gonderildi: {normalized}" if result == "ok" else result

    if normalized in {"volume_up", "ses_artir"}:
        for _ in range(max(1, int(volume_steps or 1))):
            _press("volumeup")
            time.sleep(0.04)
        return "Ses artirma komutu gonderildi."

    if normalized in {"volume_down", "ses_azalt"}:
        for _ in range(max(1, int(volume_steps or 1))):
            _press("volumedown")
            time.sleep(0.04)
        return "Ses azaltma komutu gonderildi."

    return "Spotify action: play | search | play_pause | next | previous | volume_up | volume_down | mute"
