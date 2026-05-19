"""
TTS (Text-to-Speech) - Windows SAPI uzerinden calisir.
"""

import subprocess
import threading
import sys


VOICE = ""
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


def _sapi_script(text: str) -> str:
    escaped = text.replace("'", "''")
    voice_filter = ""
    if VOICE:
        voice_name = VOICE.replace("'", "''")
        voice_filter = (
            f"$v=$s.GetVoices() | Where-Object {{$_.VoiceInfo.Name -like '*{voice_name}*'}} | Select-Object -First 1; "
            "if($v){$s.SelectVoice($v.VoiceInfo.Name)}; "
        )
    return (
        "Add-Type -AssemblyName System.Speech; "
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.Rate=0; "
        f"{voice_filter}"
        f"$s.Speak('{escaped}'); "
        "$s.Dispose()"
    )


def speak_text(text: str, on_done=None, blocking: bool = False):
    if not text or not text.strip():
        if on_done:
            on_done()
        return

    max_len = 500
    if len(text) > max_len:
        text = text[:max_len] + "..."

    def _run():
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _sapi_script(text)],
                check=False,
                timeout=90,
                creationflags=NO_WINDOW,
            )
        except Exception:
            pass
        if on_done:
            on_done()

    if blocking:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()


def get_available_voices() -> list[str]:
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Add-Type -AssemblyName System.Speech; "
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$s.GetInstalledVoices() | ForEach-Object {$_.VoiceInfo.Name}; $s.Dispose()",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
            creationflags=NO_WINDOW,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []
