"""
Sistem bilgisi - Windows uyumlu psutil + PowerShell/netsh fallback.
"""

import datetime
import shutil
import subprocess
import sys

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0


def sys_info(query: str) -> str:
    query = (query or "").lower().strip()
    results = []

    if query in ("battery", "pil", "all"):
        results.append(_battery())
    if query in ("cpu", "islemci", "işlemci", "all"):
        results.append(_cpu())
    if query in ("ram", "bellek", "memory", "all"):
        results.append(_ram())
    if query in ("disk", "depolama", "all"):
        results.append(_disk())
    if query in ("time", "saat", "zaman", "all"):
        results.append(f"Saat: {datetime.datetime.now().strftime('%H:%M:%S')}")
    if query in ("date", "tarih", "all"):
        results.append(f"Tarih: {datetime.datetime.now().strftime('%d.%m.%Y, %A')}")
    if query in ("network", "ag", "ağ", "wifi", "all"):
        results.append(_network())

    if not results:
        results.append(f"Bilinmeyen sorgu: {query}. battery/cpu/ram/disk/time/date/network/all kullanin.")
    return "\n".join(r for r in results if r)


def _battery() -> str:
    if HAS_PSUTIL:
        bat = psutil.sensors_battery()
        if bat:
            status = "Sarj oluyor" if bat.power_plugged else "Pilde"
            return f"Pil: %{bat.percent:.0f} - {status}"
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Battery | Select-Object -First 1).EstimatedChargeRemaining"],
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
            creationflags=NO_WINDOW,
        ).strip()
        if out:
            return f"Pil: %{out}"
    except Exception:
        pass
    return "Pil bilgisi alinamadi."


def _cpu() -> str:
    if HAS_PSUTIL:
        usage = psutil.cpu_percent(interval=0.5)
        count = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        freq_str = f", {freq.current:.0f} MHz" if freq else ""
        return f"CPU: %{usage:.1f} kullanim - {count} cekirdek{freq_str}"
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"],
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
            creationflags=NO_WINDOW,
        ).strip()
        if out:
            return f"CPU: %{float(out):.1f} kullanim"
    except Exception:
        pass
    return "CPU bilgisi alinamadi."


def _ram() -> str:
    if HAS_PSUTIL:
        vm = psutil.virtual_memory()
        total = vm.total / (1024**3)
        used = vm.used / (1024**3)
        return f"RAM: {used:.1f}GB / {total:.1f}GB kullanimda (%{vm.percent:.0f})"
    return "RAM bilgisi alinamadi."


def _disk() -> str:
    if HAS_PSUTIL:
        du = psutil.disk_usage("/")
        total = du.total / (1024**3)
        used = du.used / (1024**3)
        free = du.free / (1024**3)
        return f"Disk: {used:.1f}GB kullanildi, {free:.1f}GB bos (toplam {total:.1f}GB)"
    try:
        total, used, free = shutil.disk_usage("/")
        return f"Disk: {used/(1024**3):.1f}GB kullanildi, {free/(1024**3):.1f}GB bos (toplam {total/(1024**3):.1f}GB)"
    except Exception:
        return "Disk bilgisi alinamadi."


def _network() -> str:
    try:
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            errors="ignore",
            creationflags=NO_WINDOW,
        )
        for line in out.splitlines():
            if "SSID" in line and "BSSID" not in line and ":" in line:
                ssid = line.split(":", 1)[-1].strip()
                if ssid:
                    return f"WiFi: {ssid} bagli"
    except Exception:
        pass
    try:
        out = subprocess.check_output(
            ["ipconfig"],
            text=True,
            timeout=3,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            errors="replace",
            creationflags=NO_WINDOW,
        )
        for line in out.splitlines():
            if "IPv4" in line and ":" in line:
                return f"Ag: IP {line.split(':', 1)[-1].strip()}"
    except Exception:
        pass
    return "Ag baglantisi bulunamadi."
