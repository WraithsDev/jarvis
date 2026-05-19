"""
Uygulama acma - Windows uyumlu.
"""

from actions.windows_utils import find_windows_app, start_process


APP_ALIASES = {
    "edge": "Microsoft Edge",
    "safari": "Microsoft Edge",
    "chrome": "Google Chrome",
    "firefox": "Firefox",
    "terminal": "Windows Terminal",
    "cmd": "cmd",
    "powershell": "powershell",
    "finder": "explorer",
    "explorer": "explorer",
    "spotify": "Spotify",
    "youtube music": "YouTube Music",
    "yt music": "YouTube Music",
    "youtubemusic": "YouTube Music",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "xcode": "Visual Studio",
    "notion": "Notion",
    "slack": "Slack",
    "discord": "Discord",
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "zoom": "Zoom",
    "mail": "Outlook",
    "calendar": "Outlook",
    "takvim": "Outlook",
    "notes": "OneNote",
    "notlar": "OneNote",
    "music": "Spotify",
    "muzik": "Spotify",
    "photos": "Photos",
    "fotograflar": "Photos",
    "maps": "Maps",
    "haritalar": "Maps",
    "calculator": "calc",
    "hesap makinesi": "calc",
    "system preferences": "ms-settings:",
    "system settings": "ms-settings:",
    "ayarlar": "ms-settings:",
    "activity monitor": "Task Manager",
    "aktivite monitoru": "Task Manager",
    "gorev yoneticisi": "Task Manager",
    "preview": "Photos",
    "onizleme": "Photos",
    "textedit": "notepad",
    "notepad": "notepad",
    "numbers": "Excel",
    "pages": "Word",
    "keynote": "PowerPoint",
    "figma": "Figma",
    "postman": "Postman",
    "docker": "Docker Desktop",
    "tableplus": "TablePlus",
}


def open_app(app_name: str) -> str:
    if not app_name:
        return "Uygulama adi belirtilmedi."

    resolved = find_windows_app(app_name, APP_ALIASES)
    try:
        result = start_process(resolved)
    except Exception as exc:
        return f"Hata: {exc}"

    if result is None or result.returncode == 0:
        return f"{resolved} acildi."

    detail = (result.stderr or result.stdout or "").strip()
    if detail:
        return f"'{app_name}' bulunamadi veya acilamadi: {detail}"
    return f"'{app_name}' bulunamadi veya acilamadi."
