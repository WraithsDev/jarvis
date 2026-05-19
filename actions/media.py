"""
Medya oynatma - Windows uyumlu YouTube/Spotify akisi.
"""

from __future__ import annotations

from actions.browser import browser_control
from actions.spotify_control import play_spotify_query
from actions.youtube_music_control import play_youtube_music_query
from actions.windows_utils import open_url, spotify_search_url


def _play_youtube(query: str) -> str:
    return browser_control("play_youtube", query=query)


def _play_youtube_music(query: str, autoplay: bool = True) -> str:
    if not autoplay:
        from actions.youtube_music_control import _youtube_music_search_url

        open_url(_youtube_music_search_url(query))
        return f"YouTube Music icinde '{query}' aramasi acildi."
    return play_youtube_music_query(query)


def _play_spotify(query: str, autoplay: bool = True) -> str:
    try:
        open_url(spotify_search_url(query))
    except Exception as exc:
        return f"Spotify acilamadi: {exc}"

    if not autoplay:
        return f"Spotify icinde '{query}' aramasi acildi."

    return play_spotify_query(query)


def _play_apple_music(query: str) -> str:
    # Windows'ta Apple Music icin en guvenilir genel yol web aramasidir.
    return browser_control("search", query=f"Apple Music {query}")


def play_media(query: str, provider: str = "auto", autoplay: bool = True) -> str:
    if not query or not query.strip():
        return "Calinacak icerik belirtilmedi."

    normalized_provider = (provider or "auto").strip().lower()
    if normalized_provider in {"yt", "youtube"}:
        normalized_provider = "youtube"
    elif normalized_provider in {"youtube music", "youtube_music", "yt music", "ytmusic", "music.youtube"}:
        normalized_provider = "youtube_music"
    elif normalized_provider in {"apple music", "music", "apple_music"}:
        normalized_provider = "apple_music"

    if normalized_provider == "spotify":
        return _play_spotify(query, autoplay=autoplay)
    if normalized_provider == "youtube_music":
        return _play_youtube_music(query, autoplay=autoplay)
    if normalized_provider == "apple_music":
        return _play_apple_music(query)
    if normalized_provider == "youtube":
        return _play_youtube(query)

    spotify_result = _play_spotify(query, autoplay=autoplay)
    if "acilamadi" not in spotify_result.lower():
        return spotify_result
    return _play_youtube(query)
