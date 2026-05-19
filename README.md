# JARVIS Windows Kurulum Rehberi

Bu proje Windows üzerinde çalışan sesli/arayüzlü kişisel asistan uygulamasıdır. Gemini Live API ile konuşur, mikrofon dinler, uygulama açabilir, Spotify/YouTube Music/Discord/WhatsApp gibi araçları otomasyonla kontrol edebilir.

## Destek ve Kurulum Videosu

Kurulumda takılırsan veya güncellemeleri takip etmek istersen Discord sunucusuna katılabilirsin:
Discord: https://discord.gg/vsc

Adım adım kurulum videosu için:
YouTube: https://www.youtube.com/watch?v=WiYbVYGKxO8


## 1. Gerekenler

- Windows 10 veya Windows 11
- Python 3.12.x
- Mikrofon
- Gemini API key
- İnternet bağlantısı

Önerilen Python sürümü:

```text
Python 3.12.10 veya Python 3.12.x
```

Python 3.13 yerine 3.12 kullanman daha iyi olur. `pyaudio`, `tkinter` ve bazı Windows paketleri 3.12 ile daha sorunsuz çalışır.

## 2. Python Kurulumu

Python'u resmi siteden indir:

```text
https://www.python.org/downloads/windows/
```

Kurulum ekranında şunları işaretle:

```text
Add python.exe to PATH
Install launcher for all users
pip
tcl/tk and IDLE
```

Kurulumdan sonra CMD açıp kontrol et:

```cmd
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" --version
```

Şuna benzer bir çıktı görmelisin:

```text
Python 3.12.x
```

## 3. Proje Klasörüne Git

CMD kullanıyorsan:

```cmd
cd /d path\to\jarvis
```

PowerShell kullanıyorsan:

```powershell
cd "path\to\jarvis"
```

## 4. Paketleri Kur

CMD:

```cmd
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

PowerShell:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

Kurulan ana paketler:

```text
google-genai
SpeechRecognition
pyaudio
psutil
Pillow
requests
pyautogui
```

## 5. Gemini API Key Ayarla

İlk açılışta JARVIS senden Gemini API key isteyebilir. UI üzerinden girebilirsin.

İstersen elle de ayarlayabilirsin. Şu dosyayı oluştur veya düzenle:

```text
config/api_keys.json
```

Örnek:

```json
{
    "gemini_api_key": "BURAYA_GEMINI_API_KEY",
    "voice": "Charon",
    "youtube_api_key": "",
    "youtube_channel_handle": ""
}
```

Gemini API key almak için Google AI Studio kullan:

```text
https://aistudio.google.com/app/apikey
```

## 6. JARVIS'i Çalıştır

CMD:

```cmd
cd /d path\to\jarvis
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" main.py
```

PowerShell:

```powershell
cd "path\to\jarvis"
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" main.py
```

Pencere açılmadan arka planda başlatmak istersen PowerShell:

```powershell
Start-Process -FilePath "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe" -ArgumentList "main.py" -WorkingDirectory "$PWD"
```

## 7. Kullanım Örnekleri

Sesli veya yazılı olarak şunları söyleyebilirsin:

```text
Spotify'da Şebnem Ferah Mayın Tarlası aç
YouTube Music'te Duman çal
Discord'da bir arkadaşıma merhaba yaz ve gönder
WhatsApp'ta kayıtlı kişime geliyorum yaz
Downloads klasöründeki büyük dosyaları listele
Oyun modunu aç
Ekranda ne var analiz et
Bugün takvimimde ne var?
```

## 8. Kısayollar

```text
F4   Mikrofonu kapat/aç
F5   JARVIS'i duraklat/devam ettir
F11  Tam ekran / küçük asistan penceresi
ESC  Çıkış
```

## 9. Önemli Notlar

- CMD içinde PowerShell komutu çalıştırma.
- PowerShell komutları genelde `& "$env:..."` ile başlar.
- CMD komutları genelde `"%LOCALAPPDATA%\..."` şeklindedir.
- `python` komutu Windows Store alias yüzünden bozuk olabilir. Bu yüzden tam Python yolunu kullanmak daha garantidir.
- Discord ve WhatsApp mesajları UI otomasyonu ile çalışır. İlk denemelerde “hazırla ama gönderme” demek daha güvenlidir.
- SFX dosyaları opsiyoneldir. `SFX/*.mp3` eklersen kısa ses efektleri kullanılır; paylaşmak istediğin ses dosyaları repoda kalabilir.
- Kişisel dosyalar (`config/api_keys.json`, `memory/*.json`) GitHub için yok sayılır. Paylaşılabilir font ve ses assetleri (`Fonts/`, `SFX/`) repoda tutulabilir.

## 10. Sık Hatalar

### `& was unexpected at this time`

CMD içinde PowerShell komutu yazmışsın. CMD'de şunu kullan:

```cmd
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" main.py
```

### `python` Microsoft Store açıyor

Tam Python yolunu kullan:

```cmd
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" --version
```

### `ModuleNotFoundError`

Paketleri tekrar kur:

```cmd
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

### Mikrofon çalışmıyor

Windows Ayarları > Gizlilik ve güvenlik > Mikrofon bölümünden Python/Terminal/VS Code için mikrofon izni ver.

### Gemini bağlantı hatası

Şunları kontrol et:

```text
İnternet var mı?
config/api_keys.json içinde gemini_api_key dolu mu?
API key geçerli mi?
Google AI Studio kotan dolmuş olabilir mi?
```

### Tkinter / `init.tcl` hatası

Python kurulurken `tcl/tk and IDLE` bileşeni eksik kurulmuş olabilir. Python 3.12'yi yeniden kur ve bu bileşeni seç.

## 11. Dosya Yapısı

```text
main.py                 Ana uygulama ve Gemini bağlantısı
ui.py                   JARVIS arayüzü
actions/                Spotify, Discord, WhatsApp, dosya, oyun modu vb. araçlar
memory/                 Hafıza, rehber ve reminder verileri
config/api_keys.example.json  API key ve ayar örneği
SFX/                    Opsiyonel yerel ses efektleri (git'e dahil değil)
core/prompt.txt         Sistem prompt'u
```

## 12. Kapatma

Arayüzden `ESC` ile çıkabilirsin.

Eğer kapanmazsa CMD/PowerShell üzerinden Python sürecini kapat:

```cmd
taskkill /IM python.exe /F
taskkill /IM pythonw.exe /F
```
