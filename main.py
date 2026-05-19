#!/usr/bin/env python3
import asyncio
import datetime
import threading
import traceback
import os
import re
import sys
import time
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import pyaudio  # type: ignore[reportMissingModuleSource]
from google import genai  # type: ignore[reportMissingImports]
from google.genai import types  # type: ignore[reportMissingImports]

from app_config import get_app_config_value
from ui import JarvisUI
from memory.memory_manager import load_memory, update_memory, delete_memory, format_memory_for_prompt
from actions.open_app import open_app
from actions.sys_info  import sys_info
from actions.calendar import get_calendar_events, add_calendar_event, delete_calendar_event
from actions.reminders import get_reminders, add_reminder
from actions.browser   import browser_control
from actions.shell     import shell_run
from actions.whatsapp  import send_whatsapp_message, save_whatsapp_contact
from actions.discord import send_discord_message
from actions.media     import play_media
from actions.weather   import get_weather_summary
from actions.screen_vision import analyze_screen
from actions.youtube_stats import get_youtube_channel_report
from actions.file_organizer import file_organizer
from actions.game_mode import game_performance_mode
from actions.spotify_control import spotify_control
from actions.youtube_music_control import youtube_music_control

# â”€â”€ Paths â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BASE_DIR        = Path(__file__).resolve().parent
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"


CONTROL_TOKEN_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

# â”€â”€ Model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
LIVE_MODEL = "models/gemini-2.5-flash-native-audio-latest"

# â”€â”€ Audio â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FORMAT           = pyaudio.paInt16
CHANNELS         = 1
SEND_SAMPLE_RATE = 16000
RECV_SAMPLE_RATE = 24000
CHUNK_SIZE       = 1024
pya              = pyaudio.PyAudio()

# â”€â”€ Tool tanÄ±mlarÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Windows'ta herhangi bir uygulamayÄ± aÃ§ar. Spotify, Edge, Terminal, Explorer, VS Code vb.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Uygulama adÄ± (Ã¶rn. 'Spotify', 'Edge', 'Terminal')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "sys_info",
        "description": "Sistem bilgisi alÄ±r: pil durumu, CPU, RAM, disk, saat, tarih, aÄŸ baÄŸlantÄ±sÄ±.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "battery | cpu | ram | disk | time | date | network | all"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_weather",
        "description": (
            "Anlik hava durumunu ozetler. Varsayilan konum Istanbul'dur. "
            "Kullanici hava durumunu, sicakligi veya yagmur durumunu sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "location": {
                    "type": "STRING",
                    "description": "Sehir veya konum. Bos birakilirsa Istanbul kullanilir."
                }
            }
        }
    },
    {
        "name": "get_calendar_events",
        "description": (
            "Apple Calendar takvimini okur. "
            "Bugun, yarin, siradaki etkinlik veya yaklasan ajandayi ozetler. "
            "Kullanici toplanti, takvim, ajanda, etkinlik veya gunluk programini sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "today | tomorrow | next | agenda | week veya dogal dilde "
                        "'onumuzdeki 30 gun', '2 hafta', 'bu ay', 'gelecek ay'"
                    )
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum etkinlik sayisi"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_calendar_event",
        "description": (
            "Apple Calendar takvimine yeni etkinlik ekler. "
            "Kullanici toplanti, randevu, takvime ekleme veya etkinlik olusturma isterse kullan. "
            "Baslangic tarihini gercek tarih/saat olarak ver; bitis verilmezse varsayilan sure kullanilir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Etkinlik basligi. Ornek: 'Disci Randevusu'"
                },
                "start_iso": {
                    "type": "STRING",
                    "description": "Baslangic tarih/saat. ISO veya yyyy-MM-dd HH:mm formatinda."
                },
                "end_iso": {
                    "type": "STRING",
                    "description": "Bitis tarih/saat. Opsiyonel."
                },
                "location": {
                    "type": "STRING",
                    "description": "Etkinlik konumu. Opsiyonel."
                },
                "notes": {
                    "type": "STRING",
                    "description": "Etkinlik notlari. Opsiyonel."
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "Eklenecek takvim adi. Opsiyonel."
                },
                "all_day": {
                    "type": "BOOLEAN",
                    "description": "true ise tum gun etkinligi olusturur."
                }
            },
            "required": ["title", "start_iso"]
        }
    },
    {
        "name": "delete_calendar_event",
        "description": (
            "Apple Calendar takviminden etkinlik siler. "
            "Kullanici bir toplantiyi, randevuyu veya takvim kaydini silmek istediginde kullan. "
            "Ayni ada birden fazla etkinlik varsa dogru kaydi bulmak icin baslangic tarihini gercek tarih/saat olarak ver."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Silinecek etkinlik basligi. Ornek: 'Disci Randevusu'"
                },
                "start_iso": {
                    "type": "STRING",
                    "description": "Opsiyonel tarih/saat. Ayni isimli birden fazla etkinligi ayirt etmek icin kullan."
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "Opsiyonel takvim adi"
                },
                "delete_all_matches": {
                    "type": "BOOLEAN",
                    "description": "true ise eslesen tum etkinlikleri siler"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "get_reminders",
        "description": (
            "Apple Animsaticilar listesini okur. "
            "Bugunku, yaklasan, geciken veya tum acik animsaticilari ozetler. "
            "Kullanici hatirlatma, animsatici, reminder veya yapilacaklar listesini sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "today | upcoming | overdue | all | next"
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum animsatici sayisi"
                },
                "list_name": {
                    "type": "STRING",
                    "description": "Istenirse belirli bir animsatici listesi adi"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_reminder",
        "description": (
            "Apple Animsaticilar uygulamasina yeni bir animsatici ekler. "
            "Kullanici 'hatirlat', 'animsatici ekle', 'reminder kur' dediginde kullan. "
            "Goreli zaman ifadelerini bugunku tarih baglamina gore due_iso alanina ISO formatinda cevir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Animsatici basligi"
                },
                "due_iso": {
                    "type": "STRING",
                    "description": "Opsiyonel tarih/saat. Ornek: 2026-04-13T09:00 veya tum gun icin 2026-04-13"
                },
                "notes": {
                    "type": "STRING",
                    "description": "Opsiyonel not"
                },
                "list_name": {
                    "type": "STRING",
                    "description": "Opsiyonel animsatici listesi"
                },
                "priority": {
                    "type": "STRING",
                    "description": "low | medium | high"
                },
                "all_day": {
                    "type": "BOOLEAN",
                    "description": "Tum gun animsatici ise true"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "browser_control",
        "description": "TarayÄ±cÄ±da URL aÃ§ar, Google'da arama yapar veya YouTube'da ilk sonucu doÄŸrudan oynatÄ±r.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "open_url | search | play_youtube"},
                "url":    {"type": "STRING", "description": "AÃ§Ä±lacak URL (open_url iÃ§in)"},
                "query":  {"type": "STRING", "description": "Arama sorgusu (search veya play_youtube iÃ§in)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "shell_run",
        "description": "Windows terminal komutu Ã§alÄ±ÅŸtÄ±rÄ±r. Dosya iÅŸlemleri, sistem yÃ¶netimi.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "Ã‡alÄ±ÅŸtÄ±rÄ±lacak PowerShell/cmd komutu"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "play_media",
        "description": (
            "YouTube, YouTube Music, Spotify veya Apple Music/Music uygulamasÄ±nda ÅŸarkÄ±, mÃ¼zik veya video aÃ§ar. "
            "KullanÄ±cÄ± belirli bir platform sÃ¶ylerse onu kullan. "
            "Belirtmezse uygun olanÄ± dene. "
            "KullanÄ±cÄ± 'Ã§al', 'oynat', 'aÃ§' diyorsa autoplay=true kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "ÅarkÄ±, sanatÃ§Ä±, albÃ¼m veya video arama ifadesi"
                },
                "provider": {
                    "type": "STRING",
                    "description": "auto | youtube | youtube_music | spotify | apple_music"
                },
                "autoplay": {
                    "type": "BOOLEAN",
                    "description": "true ise mÃ¼mkÃ¼nse doÄŸrudan oynatÄ±r"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "spotify_control",
        "description": (
            "Spotify'i kontrol eder: sarki arama/calma, duraklat/devam et, sonraki/onceki parca, ses artirma/azaltma. "
            "Kullanici Spotify'da muzik kontrolu isterse kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "play | search | play_pause | next | previous | volume_up | volume_down | mute"
                },
                "query": {
                    "type": "STRING",
                    "description": "play/search icin sarki, sanatci veya playlist aramasi"
                },
                "volume_steps": {
                    "type": "NUMBER",
                    "description": "Ses artirma/azaltma tusuna kac kez basilacak"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "youtube_music_control",
        "description": (
            "YouTube Music uygulamasini/PWA'yi kontrol eder: sarki arama/calma, duraklat/devam et, sonraki/onceki parca, ses artirma/azaltma. "
            "Kullanici ozellikle YouTube Music derse bunu kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "play | search | play_pause | next | previous | volume_up | volume_down | mute"
                },
                "query": {
                    "type": "STRING",
                    "description": "play/search icin sarki, sanatci veya playlist aramasi"
                },
                "volume_steps": {
                    "type": "NUMBER",
                    "description": "Ses artirma/azaltma tusuna kac kez basilacak"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_organizer",
        "description": (
            "Guvendeki kullanici klasorlerinde dosya bulur, buyuk dosyalari listeler, klasoru duzenler veya bos klasorleri temizler. "
            "Desteklenen klasorler: downloads, desktop, documents, pictures, videos, music. "
            "Dosya tasima/temizleme icin emin degilsen dry_run=true kullan ve once onizleme ver."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "organize | large_files | find | clean_empty"
                },
                "folder": {
                    "type": "STRING",
                    "description": "downloads | desktop | documents | pictures | videos | music"
                },
                "query": {
                    "type": "STRING",
                    "description": "find icin dosya adi aramasi"
                },
                "dry_run": {
                    "type": "BOOLEAN",
                    "description": "true ise sadece onizleme yapar, dosyalari tasimaz/silmez"
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum sonuc veya islenecek dosya sayisi"
                },
                "min_mb": {
                    "type": "NUMBER",
                    "description": "large_files icin minimum dosya boyutu MB"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_performance_mode",
        "description": (
            "Windows oyun/performans modunu yonetir. Yuksek performans guc planini acar, dengeli moda alir veya durum gosterir. "
            "Arka plan uygulamalarini kapatma yalnizca kullanici acikca isterse close_background=true ile kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "activate | deactivate | status"
                },
                "close_background": {
                    "type": "BOOLEAN",
                    "description": "true ise secili/varsayilan arka plan uygulamalarini kapatmayi dener"
                },
                "processes": {
                    "type": "STRING",
                    "description": "Virgulle ayrilmis kapatilacak process adlari. Bos ise guvenli varsayilanlar denenir."
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "get_youtube_channel_report",
        "description": (
            "YouTube kanalinin public istatistiklerini ve son videolarin performansini raporlar. "
            "Kullanici kanal istatistiklerini, abone sayisini, son videolarini, buyume hizini "
            "veya YouTube analizini sordugunda kullan. Bu arac Studio yerine public YouTube Data API verisini kullanir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "Dogal dilde analiz istegi. Ornek: "
                        "'YouTube istatistiklerim nasil', 'son videolarimi analiz et', "
                        "'kanal buyumemi ozetle'"
                    )
                },
                "handle": {
                    "type": "STRING",
                    "description": (
                        "Opsiyonel kanal handle'i, kanal linki veya kanal ID'si. "
                        "Bos birakilirsa ayarlardaki youtube_channel_handle kullanilir."
                    )
                },
                "video_limit": {
                    "type": "NUMBER",
                    "description": "Analize dahil edilecek son video sayisi. Varsayilan 6."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_screen",
        "description": (
            "Aktif pencerenin ekran goruntusunu alip Gemini vision ile analiz eder. "
            "Kullanici ekranda ne oldugunu, bir hatayi, gorunen metni, butonlari veya pencere icerigini sordugunda kullan. "
            "Bu surum yalnizca aktif pencereyi destekler."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Kullanicinin ekranla ilgili sorusu. Ornek: 'Bu hatayi oku', 'Ekranda ne var?'"
                },
                "target": {
                    "type": "STRING",
                    "description": "Su an sadece active_window desteklenir."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "save_memory",
        "description": "KullanÄ±cÄ± hakkÄ±nda Ã¶nemli bilgiyi kalÄ±cÄ± belleÄŸe kaydeder. Ä°sim, tercihler, projeler vb. duyunca sessizce Ã§aÄŸÄ±r.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "identity | preferences | projects | notes"
                },
                "key":   {"type": "STRING", "description": "KÄ±sa anahtar (Ã¶rn. 'name')"},
                "value": {"type": "STRING", "description": "DeÄŸer (Ä°ngilizce)"}
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "delete_memory",
        "description": (
            "Kalici hafizadaki bir kaydi siler. "
            "Kullanici 'bunu hafizandan kaldir', 'unut', 'sil' gibi bir sey derse kullan. "
            "Mumkunse category ve key ile sil; emin degilsen match_text ile ilgili kaydi bulup kaldir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "Kaydin kategorisi. Ornek: notes | identity | preferences | projects"
                },
                "key": {
                    "type": "STRING",
                    "description": "Silinecek anahtar. Ornek: claude_limit_refresh"
                },
                "match_text": {
                    "type": "STRING",
                    "description": "Kaydi bulmak icin kullanilacak dogal dil parcasi. Ornek: 'claude ai limit yenilenmesi'"
                }
            }
        }
    },
    {
        "name": "send_whatsapp_message",
        "description": (
            "WhatsApp Desktop veya WhatsApp Web Ã¼zerinden mesaj taslaÄŸÄ± aÃ§ar veya mesajÄ± gÃ¶nderir. "
            "KiÅŸi adÄ± veya telefon numarasÄ±yla Ã§alÄ±ÅŸabilir. "
            "Telefon numarasÄ± verilmemiÅŸse kiÅŸi adÄ±nÄ± Ã¶nce kayÄ±tlÄ± WhatsApp kiÅŸileri ve iÃ§e aktarÄ±lan telefon rehberinde ara. "
            "KullanÄ±cÄ± 'gÃ¶nder', 'yolla', 'ile', 'hemen gÃ¶nder' gibi aÃ§Ä±k bir gÃ¶nderme niyeti sÃ¶ylÃ¼yorsa "
            "ekstra onay istemeden send_now=true kullan. "
            "YalnÄ±zca 'hazÄ±rla', 'taslak aÃ§', 'yaz ama gÃ¶nderme' diyorsa send_now=false kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient_name": {
                    "type": "STRING",
                    "description": "KiÅŸi adÄ±. Ã–rn: 'Anne', 'Ahmet', 'Ece'"
                },
                "phone_number": {
                    "type": "STRING",
                    "description": "Uluslararasi telefon numarasi. Ornek format: +<ulke_kodu><numara>"
                },
                "message": {
                    "type": "STRING",
                    "description": "GÃ¶nderilecek mesaj iÃ§eriÄŸi"
                },
                "app_target": {
                    "type": "STRING",
                    "description": "desktop | web | auto. VarsayÄ±lan auto, tercihen desktop."
                },
                "send_now": {
                    "type": "BOOLEAN",
                    "description": "true ise sohbet aÃ§Ä±ldÄ±ktan sonra mesajÄ± otomatik gÃ¶nderir"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "send_discord_message",
        "description": (
            "Discord Desktop veya Discord Web uzerinden kisiye, DM'e, sunucuya ya da kanala mesaj taslagi acar veya mesaj gonderir. "
            "Discord resmi kisisel hesap API'si vermedigi icin bu arac Discord uygulamasinda Ctrl+K hizli gecis ve pano yapistirma kullanir. "
            "Kullanici 'gonder', 'yolla', 'hemen at' gibi acik gonderme niyeti soylerse send_now=true kullan. "
            "Yalnizca 'hazirla', 'taslak yaz', 'yaz ama gonderme' diyorsa send_now=false kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient_name": {
                    "type": "STRING",
                    "description": "DM/kisi/hedef adi. Ornek: 'Ahmet', 'Ece', 'Tasarim ekibi'"
                },
                "server_name": {
                    "type": "STRING",
                    "description": "Sunucu adi. Kanal hedefleniyorsa opsiyonel olarak ver."
                },
                "channel_name": {
                    "type": "STRING",
                    "description": "Kanal adi. Ornek: 'genel', 'duyurular'. # isareti olmadan da verilebilir."
                },
                "message": {
                    "type": "STRING",
                    "description": "Gonderilecek Discord mesaji"
                },
                "app_target": {
                    "type": "STRING",
                    "description": "desktop | web. Varsayilan desktop."
                },
                "send_now": {
                    "type": "BOOLEAN",
                    "description": "true ise mesaji otomatik Enter ile gonderir; false ise taslak olarak birakir"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "save_whatsapp_contact",
        "description": (
            "SÄ±k kullanÄ±lan bir WhatsApp kiÅŸisini adÄ± ve telefon numarasÄ±yla kalÄ±cÄ± belleÄŸe kaydeder. "
            "KullanÄ±cÄ± bir kiÅŸiyi 'annem', 'Ahmet', 'iÅŸ ortaÄŸÄ±m' gibi tekrar kullanÄ±lacak ÅŸekilde tanÄ±mladÄ±ÄŸÄ±nda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "display_name": {
                    "type": "STRING",
                    "description": "Kaydedilecek kiÅŸi adÄ±. Ã–rn: 'Annem', 'Ahmet'"
                },
                "phone_number": {
                    "type": "STRING",
                    "description": "Uluslararasi telefon numarasi. Ornek format: +<ulke_kodu><numara>"
                },
                "aliases": {
                    "type": "STRING",
                    "description": "VirgÃ¼lle ayrÄ±lmÄ±ÅŸ alternatif hitaplar. Ã–rn: 'anne, annem, mom'"
                }
            },
            "required": ["display_name", "phone_number"]
        }
    }
]


def get_api_key() -> str:
    return str(get_app_config_value("gemini_api_key", "") or "")


def load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "Sen JARVIS'sin â€” Windows'ta Ã§alÄ±ÅŸan kiÅŸisel AI asistanÄ±. "
            "TÃ¼rkÃ§e konuÅŸ. KÄ±sa ve net yanÄ±tlar ver. "
            "AraÃ§larÄ± kullanarak gÃ¶revleri tamamla, asla taklit etme."
        )


class JarvisLive:
    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self._last_connection_error = ""
        self._last_connection_error_at = 0.0

        self.ui.on_text_command  = self._on_text_command
        self.ui.on_pause_toggle  = self._on_pause_toggle
        self.ui.on_effects_state_change = self._on_effects_state_change
        self._paused             = False

    def _on_pause_toggle(self, paused: bool):
        self._paused = paused

    def _on_effects_state_change(self, enabled: bool):
        pass

    def _focus_ui_section_for_tool(self, tool_name: str, args: dict):
        if tool_name == "sys_info":
            query = str(args.get("query", "")).strip().lower()
            if query in {"time", "saat", "zaman", "date", "tarih"}:
                self.ui.focus_panel("time", duration_ms=5200)
            else:
                self.ui.focus_panel("system", duration_ms=5200)
        elif tool_name == "get_weather":
            self.ui.focus_panel("weather", duration_ms=5600)

    def _on_text_command(self, text: str):
        if self._paused:
            return
        self.ui.write_log(f"You: {text}")
        if not self._loop or not self.session:
            self.ui.write_log("ERR: JARVIS connection is not ready yet.")
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    async def _interrupt_audio(self):
        try:
            if self.audio_in_queue:
                while not self.audio_in_queue.empty():
                    try:
                        self.audio_in_queue.get_nowait()
                    except Exception:
                        break
            if self.session:
                await self.session.send_realtime_input(audio_stream_end=True)
            self.set_speaking(False)
        except Exception:
            pass


    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        else:
            self.ui.set_state("LISTENING")

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} - {short}")
        self.ui.write_debug(f"{tool_name}: {short}", level="ERROR")
        self.ui.set_state("ERROR")

    @staticmethod
    def _normalize_command_text(text: str) -> str:
        table = str.maketrans({
            "ı": "i",
            "İ": "i",
            "ğ": "g",
            "Ğ": "g",
            "ü": "u",
            "Ü": "u",
            "ş": "s",
            "Ş": "s",
            "ö": "o",
            "Ö": "o",
            "ç": "c",
            "Ç": "c",
        })
        return " ".join(str(text or "").translate(table).lower().split())

    async def _handle_local_voice_command(self, text: str) -> bool:
        normalized = self._normalize_command_text(text)
        compact = normalized.replace(" ", "")
        mentions_music = any(token in normalized for token in ("muzik", "sarki", "spotify", "calan")) or "spotify" in compact
        wants_stop = any(token in normalized for token in ("durdur", "duraklat", "pause", "kapat", "stop"))
        wants_next = any(token in normalized for token in ("sonraki", "gec", "next"))
        wants_prev = any(token in normalized for token in ("onceki", "geri", "previous"))

        action = ""
        if mentions_music and wants_stop:
            action = "play_pause"
        elif mentions_music and wants_next:
            action = "next"
        elif mentions_music and wants_prev:
            action = "previous"
        if not action:
            return False

        result = await asyncio.to_thread(spotify_control, action)
        self.ui.write_log(f"SYS: {result}")
        self.ui.set_state("LISTENING")
        return True

    @staticmethod
    def _leaf_errors(error: BaseException) -> list[BaseException]:
        if isinstance(error, BaseExceptionGroup):
            leaves = []
            for child in error.exceptions:
                leaves.extend(JarvisLive._leaf_errors(child))
            return leaves
        return [error]

    @staticmethod
    def _clean_error_text(text: str) -> str:
        text = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
        if not text:
            return "unknown error"
        return text[:180]

    def _format_connection_error(self, error: BaseException) -> str:
        leaves = [e for e in self._leaf_errors(error) if not isinstance(e, asyncio.CancelledError)]
        leaf = leaves[0] if leaves else error
        raw = self._clean_error_text(str(leaf) or leaf.__class__.__name__)
        low = raw.lower()

        if any(token in low for token in ("api key", "permission", "unauthorized", "forbidden")):
            return f"Gemini API key veya izin sorunu var. Detay: {raw}"
        if any(token in low for token in ("quota", "resource exhausted", "rate limit", "429")):
            return f"Gemini kota/rate limit hatasi verdi. Detay: {raw}"
        if any(token in low for token in ("microphone", "input device", "invalid input", "paerror", "audio")):
            return f"Mikrofon/ses aygiti baglantisi koptu. Detay: {raw}"
        if any(token in low for token in (
            "connection",
            "connect",
            "disconnect",
            "reset",
            "timeout",
            "timed out",
            "unavailable",
            "network",
            "dns",
            "ssl",
            "websocket",
        )):
            return f"JARVIS baglantisi koptu; yeniden baglaniyor. Detay: {raw}"
        return f"JARVIS yeniden baglaniyor. Detay: {raw}"

    def _write_connection_error(self, message: str):
        now = time.monotonic()
        if message == self._last_connection_error and now - self._last_connection_error_at < 20:
            self.ui.write_debug(f"Connection retry: {message}", level="WARN")
            return
        self._last_connection_error = message
        self._last_connection_error_at = now
        self.ui.write_log(f"ERR: {message}")

    @staticmethod
    def _result_looks_like_error(result) -> bool:
        text = str(result or "").strip().lower()
        if not text:
            return False
        error_markers = (
            "hata",
            "error",
            "alinamadi",
            "alinamadi",
            "bulunamadi",
            "bulunamadi",
            "acilamadi",
            "acilamadi",
            "tamamlanamadi",
            "tamamlanamadi",
            "gecersiz",
            "gecersiz",
            "izin gerekiyor",
            "izin gerekli",
            "baglanti",
            "baglanti",
            "gerekli.",
        )
        return any(marker in text for marker in error_markers)

    @staticmethod
    def _should_play_success_sfx(tool_name: str, args: dict, result) -> bool:
        action_tools = {
            "open_app",
            "add_calendar_event",
            "add_reminder",
            "delete_calendar_event",
            "remove_calendar_event",
            "send_discord_message",
        }
        if tool_name in action_tools:
            return True

        if tool_name == "send_whatsapp_message":
            text = str(result or "").lower()
            if bool(args.get("send_now", False)):
                return "gonderildi" in text or "sent" in text
            return False

        return False

    @staticmethod
    def _clean_transcript_text(text: str) -> tuple[str, bool]:
        raw = str(text or "")
        had_noise = False
        if CONTROL_TOKEN_RE.search(raw):
            had_noise = True
            raw = CONTROL_TOKEN_RE.sub(" ", raw)
        cleaned = []
        for ch in raw:
            if ch in "\n\r\t" or ord(ch) >= 32:
                cleaned.append(ch)
            else:
                had_noise = True
        normalized = " ".join("".join(cleaned).split())
        return normalized.strip(), had_noise

    def _build_config(self) -> types.LiveConnectConfig:
        memory  = load_memory()
        mem_str = format_memory_for_prompt(memory)
        sys_p   = load_system_prompt()
        now     = datetime.datetime.now()
        time_ctx = f"[CURRENT TIME]\n{now.strftime('%Y-%m-%d %H:%M')}\n\n"

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str + "\n\n")
        parts.append(sys_p)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=str(get_app_config_value("voice", "Charon") or "Charon")
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})
        print(f"[JARVIS] tool: {name} {args}")
        self.ui.set_state("THINKING")

        loop   = asyncio.get_event_loop()
        result = "Tamam."
        had_exception = False

        try:
            if name == "save_memory":
                cat = args.get("category", "notes")
                key = args.get("key", "")
                val = args.get("value", "")
                if key and val:
                    update_memory({cat: {key: {"value": val}}})
                    print(f"[Memory] {cat}/{key} = {val}")
                result = "ok"

            elif name == "delete_memory":
                result = delete_memory(
                    args.get("category", ""),
                    args.get("key", ""),
                    args.get("match_text", ""),
                )

            elif name == "open_app":
                r = await loop.run_in_executor(
                    None, lambda: open_app(args.get("app_name", "")))
                result = r or f"{args.get('app_name')} opened."

            elif name == "sys_info":
                self._focus_ui_section_for_tool(name, args)
                r = await loop.run_in_executor(
                    None, lambda: sys_info(args.get("query", "all")))
                result = r or "Information received."

            elif name == "get_weather":
                self._focus_ui_section_for_tool(name, args)
                r = await loop.run_in_executor(
                    None, lambda: get_weather_summary(args.get("location") or None))
                result = r or "Hava durumu bilgisi alindi."

            elif name == "get_calendar_events":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_calendar_events(
                        args.get("query", "today"),
                        int(args.get("limit", 6) or 6),
                    ),
                )
                result = r or "Takvim bilgisi alindi."

            elif name == "add_calendar_event":
                r = await loop.run_in_executor(
                    None,
                    lambda: add_calendar_event(
                        args.get("title", ""),
                        args.get("start_iso", ""),
                        args.get("end_iso", ""),
                        args.get("notes", ""),
                        args.get("location", ""),
                        args.get("calendar_name", ""),
                        bool(args.get("all_day", False)),
                    ),
                )
                result = r or "Takvim etkinligi eklendi."

            elif name == "delete_calendar_event":
                r = await loop.run_in_executor(
                    None,
                    lambda: delete_calendar_event(
                        args.get("title", ""),
                        args.get("start_iso", ""),
                        args.get("calendar_name", ""),
                        bool(args.get("delete_all_matches", False)),
                    ),
                )
                result = r or "Takvim etkinligi silindi."

            elif name == "get_reminders":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_reminders(
                        args.get("query", "upcoming"),
                        int(args.get("limit", 8) or 8),
                        args.get("list_name", ""),
                    ),
                )
                result = r or "Animsatici bilgisi alindi."

            elif name == "add_reminder":
                r = await loop.run_in_executor(
                    None,
                    lambda: add_reminder(
                        args.get("title", ""),
                        args.get("due_iso", ""),
                        args.get("notes", ""),
                        args.get("list_name", ""),
                        args.get("priority", ""),
                        bool(args.get("all_day", False)),
                    ),
                )
                result = r or "Animsatici eklendi."

            elif name == "browser_control":
                r = await loop.run_in_executor(
                    None, lambda: browser_control(
                        args.get("action"),
                        args.get("url"),
                        args.get("query")
                    ))
                result = r or "Tamam."

            elif name == "shell_run":
                r = await loop.run_in_executor(
                    None, lambda: shell_run(args.get("command", "")))
                result = r or "Command executed."

            elif name == "play_media":
                r = await loop.run_in_executor(
                    None,
                    lambda: play_media(
                        args.get("query", ""),
                        args.get("provider", "auto"),
                        bool(args.get("autoplay", True)),
                    ),
                )
                result = r or "Media playback started."

            elif name == "spotify_control":
                r = await loop.run_in_executor(
                    None,
                    lambda: spotify_control(
                        args.get("action", "play_pause"),
                        args.get("query", ""),
                        int(args.get("volume_steps", 2) or 2),
                    ),
                )
                result = r or "Spotify komutu gonderildi."

            elif name == "youtube_music_control":
                r = await loop.run_in_executor(
                    None,
                    lambda: youtube_music_control(
                        args.get("action", "play_pause"),
                        args.get("query", ""),
                        int(args.get("volume_steps", 2) or 2),
                    ),
                )
                result = r or "YouTube Music komutu gonderildi."

            elif name == "file_organizer":
                r = await loop.run_in_executor(
                    None,
                    lambda: file_organizer(
                        args.get("action", ""),
                        args.get("folder", "downloads"),
                        args.get("query", ""),
                        bool(args.get("dry_run", True)),
                        int(args.get("limit", 20) or 20),
                        float(args.get("min_mb", 100) or 100),
                    ),
                )
                result = r or "Dosya islemi tamamlandi."

            elif name == "game_performance_mode":
                r = await loop.run_in_executor(
                    None,
                    lambda: game_performance_mode(
                        args.get("action", "activate"),
                        bool(args.get("close_background", False)),
                        args.get("processes", ""),
                    ),
                )
                result = r or "Oyun modu guncellendi."

            elif name == "get_youtube_channel_report":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_youtube_channel_report(
                        args.get("query", "overview"),
                        args.get("handle", ""),
                        int(args.get("video_limit", 6) or 6),
                    ),
                )
                result = r or "YouTube kanal raporu alindi."

            elif name == "analyze_screen":
                r = await loop.run_in_executor(
                    None,
                    lambda: analyze_screen(
                        args.get("query", "Ekranda ne var?"),
                        args.get("target", "active_window"),
                    ),
                )
                result = r or "Ekran analizi tamamlandi."

            elif name == "send_whatsapp_message":
                r = await loop.run_in_executor(
                    None,
                    lambda: send_whatsapp_message(
                        args.get("message", ""),
                        args.get("phone_number", ""),
                        args.get("recipient_name", ""),
                        bool(args.get("send_now", False)),
                        args.get("app_target", "auto"),
                    ),
                )
                result = r or "WhatsApp action completed."

            elif name == "send_discord_message":
                r = await loop.run_in_executor(
                    None,
                    lambda: send_discord_message(
                        args.get("message", ""),
                        args.get("recipient_name", ""),
                        args.get("server_name", ""),
                        args.get("channel_name", ""),
                        bool(args.get("send_now", False)),
                        args.get("app_target", "desktop"),
                    ),
                )
                result = r or "Discord action completed."

            elif name == "save_whatsapp_contact":
                r = await loop.run_in_executor(
                    None,
                    lambda: save_whatsapp_contact(
                        args.get("display_name", ""),
                        args.get("phone_number", ""),
                        args.get("aliases", ""),
                    ),
                )
                result = r or "WhatsApp contact saved."

            else:
                result = f"Unknown tool: {name}"

        except Exception as e:
            result = f"Hata: {e}"
            had_exception = True
            traceback.print_exc()
            self.speak_error(name, e)

        tool_failed = self._result_looks_like_error(result)
        if tool_failed:
            if not had_exception:
                self.ui.set_state("ERROR")
        elif self._should_play_success_sfx(name, args, result):
            self.ui.play_success_sfx()

        if not tool_failed and not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[JARVIS] result: {name} -> {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[JARVIS] microphone started")
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT, channels=CHANNELS,
            rate=SEND_SAMPLE_RATE, input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        try:
            while True:
                data = await asyncio.to_thread(
                    stream.read, CHUNK_SIZE, exception_on_overflow=False)
                with self._speaking_lock:
                    jarvis_speaking = self._is_speaking
                if not jarvis_speaking and not self.ui.muted and not self._paused:
                    await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
        except Exception as e:
            print(f"[JARVIS] microphone error: {e}")
            raise
        finally:
            stream.close()

    async def _receive_audio(self):
        print("[JARVIS] receiver started")
        out_buf, in_buf = [], []
        output_noise = False
        output_noise_samples = []
        try:
            while True:
                async for response in self.session.receive():
                    if response.data:
                        self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            self.set_speaking(True)
                            raw_txt = sc.output_transcription.text.strip()
                            if raw_txt:
                                txt, had_noise = self._clean_transcript_text(raw_txt)
                                if had_noise:
                                    output_noise = True
                                    if len(output_noise_samples) < 4:
                                        output_noise_samples.append(raw_txt)
                                if txt:
                                    out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                in_buf.append(txt)
                                self.ui.mark_user_activity(True)

                        if sc.turn_complete:
                            self.set_speaking(False)

                            full_in = " ".join(in_buf).strip()
                            local_handled = False
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                                local_handled = await self._handle_local_voice_command(full_in)
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if local_handled:
                                out_buf = []
                            elif full_out:
                                self.ui.write_log(f"JARVIS: {full_out}")
                                if output_noise_samples:
                                    self.ui.write_debug(
                                        "Partially filtered audio transcript: " + " | ".join(output_noise_samples),
                                        level="WARN",
                                    )
                            elif output_noise:
                                if output_noise_samples:
                                    self.ui.write_debug(
                                        "Filtered undecodable voice transcript: " + " | ".join(output_noise_samples),
                                        level="WARN",
                                    )
                                self.ui.set_state("LISTENING")
                            out_buf = []
                            output_noise = False
                            output_noise_samples = []

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] function call: {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses)

        except Exception as e:
            print(f"[JARVIS] receiver error: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[JARVIS] audio playback started")
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT, channels=CHANNELS,
            rate=RECV_SAMPLE_RATE, output=True,
        )
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                self.set_speaking(True)
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[JARVIS] audio error: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.close()

    async def run(self):
        client = genai.Client(
            api_key=get_api_key(),
            http_options={"api_version": "v1alpha"}
        )

        while True:
            # DuraklatÄ±lmÄ±ÅŸsa baÄŸlanma, bekle
            if self._paused:
                await asyncio.sleep(1)
                continue

            try:
                print("[JARVIS] connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=10)

                    print("[JARVIS] connected.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: JARVIS ready. Listening...")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())

            except Exception as e:
                print(f"[JARVIS] warning: {e}")
                traceback.print_exc()
                self.set_speaking(False)
                self.session = None
                self.audio_in_queue = None
                self.out_queue = None
                self._write_connection_error(self._format_connection_error(e))
                self.ui.set_state("ERROR")
                print("[JARVIS] reconnecting in 3 seconds...")
                await asyncio.sleep(3)


def main():
    if os.environ.get("TERM_PROGRAM") == "vscode":
        print("[JARVIS] VS Code icinden baslatildi.")

    ui = JarvisUI()

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\nShutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()
