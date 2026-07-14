"""
💬 Sohbet Sistemi - Kirve Rebekka Bot
Bot'un grup sohbetlerinde doğal konuşabilmesi için
Kirve Rebekka karakteri - Nazik ve samimi
"""

import random
import asyncio
import time
import re
from typing import Optional, Dict
from collections import deque
from aiogram import Bot
from aiogram.types import Message
from utils.logger import logger
from utils.cooldown_manager import cooldown_manager
from database import is_user_registered
from config import get_config
from aiogram import types
from .smart_response_system import get_smart_response

# Bot başlangıç koruması - CHAT SİSTEMİ İÇİN
bot_startup_time = time.time()
STARTUP_PROTECTION_DURATION = 180  # 3 dakika koruma (chat sistemini devre dışı bırakır, komutlar çalışır)
MAX_MESSAGE_AGE_SECONDS = 300  # 5 dakikadan eski mesajlara cevap verme

# Chat sistemi ayarları - SPAM KORUMASI: Daha sıkı ayarlar
chat_system_active = True
chat_probability = 0.002   # Genel rastgele cevap olasılığı (%0.2 - çok nadir - daha da azaltıldı)
min_message_length = 10   # Minimum 10 karakter (daha uzun mesajlar - artırıldı)

# Global bot instance (main.py set eder)
_bot_instance = None

def set_bot_instance(bot):
    global _bot_instance
    _bot_instance = bot

# Kayıt olmayan kullanıcılar için teşvik sistemi - İYİLEŞTİRİLDİ
unregistered_users_last_message = {}  # {user_id: timestamp}
REGISTRATION_REMINDER_INTERVAL = 1800  # 30 dakika (1800 saniye) - Spam önleme için artırıldı

# Son cevapları takip ederek tekrarlı yanıtları azaltma
recent_responses_by_chat: Dict[int, deque] = {}

# Bot'un yönlendirilmemiş (genel) mesajlara çok sık yanıt vermesini önlemek için - SPAM KORUMASI
NON_ADDRESSED_MIN_INTERVAL_SEC = 3600  # Aynı sohbette iki genel yanıt arası minimum süre (60 dk - artırıldı)
last_non_addressed_reply_by_chat: Dict[int, float] = {}

# Çoğul/grup sorularına özel, nadir yanıt olasılığı - SPAM KORUMASI
GROUP_QUESTION_PROBABILITY = 0.005  # %0.5 (çok nadir - daha da azaltıldı)

# "kirve/kirvem" hitaplarına özel ayarlar - SPAM KORUMASI
KIRVE_MENTION_PROBABILITY = 0.01  # %1 (çok nadir - daha da azaltıldı)
KIRVE_MENTION_MIN_INTERVAL_SEC = 3600  # 60 dakika (daha uzun cooldown - artırıldı)
last_kirve_mention_reply_by_chat: Dict[int, float] = {}

# Çoğul/grup soru kalıpları ve cevapları
GROUP_QUESTION_PATTERNS = [
    r"\bnapıyorsunuz\b",
    r"\bne yapıyorsunuz\b",
    r"\bnasılsınız\b",
    r"\biyi misiniz\b",
    r"\bne var ne yok arkadaşlar\b",
    r"\barkadaşlar\b.*\?(?:\s|$)",
]

GROUP_QUESTION_RESPONSES = [
    "Buradayız; siz nasılsınız?",
    "İyiyiz; sizde neler var?",
    "Devam; sizde durumlar nasıl?",
    "Sohbetteyiz; keyifler yerinde mi?",
    "Buradayız; sizde neler oluyor?",
]

# Varlık/yoklama (burada mısın?) kalıpları ve cevapları
PRESENCE_PATTERNS = [
    r"\bburada mısın\b",
    r"\bburda mısın\b",
    r"\bburalarda mısın\b",
    r"\bvar mısın\b",
    r"\bonline mısın\b",
    r"\bçevrimiçi misin\b",
    r"\baktif misin\b",
    r"\bayakta mısın\b",
    r"\buyanık mısın\b",
    r"\borsada mısın\b",  # olası yazım varyantı
    r"\bneredesin\b",
    r"\bnerelerdesin\b",
    r"\bduyuyor musun\b",
    r"\bgörüyor musun\b",
]

PRESENCE_RESPONSES = [
    "Buradayım, merak etme.",
    "Her daim buralardayım.",
    "Aktifim, buradayım.",
    "Online’ım, hazır.",
    "Buradayım; sorun mu var?",
    "Hazırım, buradayım.",
    "Buralardayım, sakin.",
    "Kontroldeyim, buradayım.",
    "Evet, buradayım.",
    "Buradayım; devam edebiliriz.",
    "Görüyorum, buradayım.",
    "Takipteyim, buradayım.",
    "Aktifteyim; buradayım.",
    "Çevrimiçiyim, buradayım.",
    "Buralardayım; sorun değil.",
    "Hazır ve buradayım.",
    "Ulaşılabilir durumdayım.",
    "Buradayım; dinamik kalıyorum.",
    "Evet; bağlantı açık.",
    "Buradayım; odaklandım.",
    "Her an buradayım.",
    "Erişilebilir durumdayım.",
    "Gözüm üzerinizde, buradayım.",
]

def should_suppress_duplicate_response(chat_id: int, response: str, window_seconds: int = 3600) -> bool:
    """Aynı sohbette kısa süre içinde aynı metni tekrarlamayı engelle - SPAM KORUMASI: 60 dakika (artırıldı)"""
    now_ts = time.time()
    if chat_id not in recent_responses_by_chat:
        recent_responses_by_chat[chat_id] = deque(maxlen=50)  # Daha fazla kayıt tut (artırıldı)
    # Eski kayıtları temizle ve tekrar kontrol et
    filtered = deque(maxlen=50)
    duplicate_found = False
    for old_resp, ts in list(recent_responses_by_chat[chat_id]):
        if now_ts - ts <= window_seconds:
            filtered.append((old_resp, ts))
        # Aynı metin pencerede zaten gönderilmiş mi? (daha sıkı kontrol)
        if old_resp == response and now_ts - ts <= window_seconds:
            duplicate_found = True
        # Benzer metin kontrolü (kayıt mesajları için) - daha sıkı
        elif "kayıt ol" in response.lower() and "kayıt ol" in old_resp.lower() and now_ts - ts <= window_seconds:
            duplicate_found = True
        # Benzer mesaj kontrolü (flame koruması) - yeni eklendi
        elif len(response) > 10 and len(old_resp) > 10:
            # Mesajların %80'i aynıysa duplicate say
            similarity = sum(a == b for a, b in zip(response[:50], old_resp[:50])) / min(len(response[:50]), len(old_resp[:50]))
            if similarity > 0.8 and now_ts - ts <= window_seconds:
                duplicate_found = True
    recent_responses_by_chat[chat_id] = filtered
    if not duplicate_found:
        recent_responses_by_chat[chat_id].append((response, now_ts))
    return duplicate_found

def choose_diverse_response(chat_id: int, candidates):
    """Yakın zamanda aynı sohbette gönderilmeyen bir cevabı seç"""
    if not candidates:
        return ""
    shuffled = list(candidates)
    random.shuffle(shuffled)
    recent_texts = {r for (r, _ts) in recent_responses_by_chat.get(chat_id, [])}
    for text in shuffled:
        if text not in recent_texts:
            return text
    # Hepsi yakın zamanda kullanılmışsa yine de rastgele birini dön
    return random.choice(candidates)

def should_throttle_non_addressed(chat_id: int) -> bool:
    now_ts = time.time()
    last_ts = last_non_addressed_reply_by_chat.get(chat_id, 0)
    return (now_ts - last_ts) < NON_ADDRESSED_MIN_INTERVAL_SEC

def mark_non_addressed_reply(chat_id: int):
    last_non_addressed_reply_by_chat[chat_id] = time.time()

def should_throttle_kirve_mention(chat_id: int) -> bool:
    now_ts = time.time()
    last_ts = last_kirve_mention_reply_by_chat.get(chat_id, 0)
    return (now_ts - last_ts) < KIRVE_MENTION_MIN_INTERVAL_SEC

def mark_kirve_mention_reply(chat_id: int):
    last_kirve_mention_reply_by_chat[chat_id] = time.time()

def _contains_emoji(text: str) -> bool:
    try:
        return any(ord(ch) > 127 for ch in text)
    except Exception:
        return False

def humanize_response(text: str) -> str:
    """Yanıtı daha doğal ve sıcak hale getirir; abartmadan ufak dokunuşlar yapar."""
    try:
        if not text:
            return text

        output = text.strip()

        # Aşırı ünlemleri yumuşat ("!!!" -> "!")
        output = re.sub(r"!{2,}", "!", output)

        # Üslubu ağırlaştırabilecek tamamen büyük harfleri yumuşat (kısa kelimeleri etkileme)
        def _soften_caps(match):
            word = match.group(0)
            return word.capitalize()
        output = re.sub(r"\b[A-ZÇĞİÖŞÜ]{3,}\b", _soften_caps, output)

        # Zaten emoji varsa ekleme; yoksa düşük ihtimalle tek, küçük bir emoji ekle
        if not _contains_emoji(output):
            # %35 ihtimalle küçük bir emoji ekle, aksi halde ekleme (Rebekka karakteri için)
            if random.random() < 0.35:
                soft_emojis = ["🙂", "😊", "😉", "✨", "💕", "🌸"]
                # Soru cümlesinde aşırı coşkulu emoji kullanma
                if output.endswith("?"):
                    soft_emojis = ["🙂", "😊", "💕"]
                output = output + " " + random.choice(soft_emojis)

        return output
    except Exception:
        return text

# Flörtleşme cevapları (nadir, abartmadan)
FLIRT_RESPONSES = [
    "Haha, şakacı seni 😊",
    "Ay, ne tatlısın 😉",
    "Vay be, iltifat mı bu? 😄",
    "Teşekkürler, sen de çok naziksin 😊",
    "Haha, güzel konuşuyorsun 😉",
    "Ay, böyle konuşma beni utandırıyorsun 😊",
    "Teşekkürler, sen de harikasın 😄",
    "Haha, ne kadar tatlısın 😉"
]

# Flörtleşme tetikleyicileri (nadir kullanılacak)
FLIRT_TRIGGERS = [
    "güzel", "tatlı", "seksi", "harika", "mükemmel", "çok güzel", "çok tatlı",
    "aşkım", "bebeğim", "canım", "tatlım", "güzelim", "sevgilim"
]

# Selamlaşma kalıpları - Sohbet için genişletildi (Rebekka karakteri)
GREETINGS = {
    "selam": [
        "Selam! 😊 Nasılsın?",
        "Selam! 💎 Keyifler nasıl?",
        "Aleyküm selam! 😊",
        "Selam! Bugün nasılsın?",
        "Selam! Umarım günün güzel geçiyordur."
    ],
    "merhaba": [
        "Selam! 😊 Nasılsın?",
        "Hey! 💎 Keyifler nasıl?",
        "Hoş geldin! 😊",
        "Selamlar! Neler yapıyorsun?",
        "Merhaba! Güzel bir gün dilerim.",
        "Selam! Nasıl gidiyor?",
        "Hey! Ne var ne yok?",
        "Selamlar! Keyifler yerinde mi?",
        "Merhaba! Sohbete hoş geldin!",
        "Hey! Nasılsın bugün?",
        "Selam! Neler yapıyorsun?",
        "Merhaba! Güzel bir gün geçiriyor musun?",
        "Hey! Sohbete katıldığın için teşekkürler!",
        "Selamlar! Nasıl gidiyor hayat?",
        "Merhaba! Bugün nasıl geçiyor?",
        "Hey! Keyifler nasıl?",
        "Selam! Ne haber?",
        "Merhaba! Sohbete hoş geldin! 😊",
        "Hey! Nasılsın?",
        "Selamlar! Güzel bir gün dilerim."
    ],
    "sa": [
        "Aleyküm selam! 😊",
        "Selam! 💎 Nasıl gidiyor?",
        "Selam! 😊",
        "Aleyküm selam, hoş geldin!"
    ],
    "günaydın": [
        "Günaydın! 😊 Nasılsın?",
        "Günaydın! 💎 Harika bir gün olsun!",
        "Günaydın! Hoş geldin! 😊",
        "Günaydın! Kahveni aldın mı?"
    ],
    "iyi akşamlar": [
        "İyi akşamlar! 😊 Nasılsın?",
        "İyi akşamlar! 💎 Nasıl gidiyor?",
        "İyi akşamlar! Hoş geldin! 😊",
        "İyi akşamlar! Umarım günün güzel geçmiştir."
    ],
    "iyi geceler": [
        "İyi geceler! 😊",
        "İyi geceler! 💎 Tatlı rüyalar!",
        "İyi geceler! Dinlenmeyi unutma!",
        "İyi geceler! Yarın görüşürüz."
    ],
    "hey": [
        "Selam! 😊 Nasılsın?",
        "Hey! 💎 Nasıl gidiyor?",
        "Merhaba! Hoş geldin! 😊",
        "Selamlar! Ne var ne yok?",
        "Hey! Keyifler nasıl?",
        "Selam! Neler yapıyorsun?",
        "Hey! Güzel bir gün dilerim!",
        "Selamlar! Nasıl gidiyor?",
        "Hey! Sohbete hoş geldin!",
        "Selam! Bugün nasıl geçiyor?"
    ],
    "hi": [
        "Hi! 😊 How’s it going?",
        "Hi! 💎 Welcome!",
        "Hi! Glad to see you! 😊"
    ]
}

# Soru kalıpları - Sadece gerçek sorular
QUESTIONS = {
    "nasılsın": [
        "İyiyim, teşekkürler! Sen nasılsın? 😊",
        "İyiyim! Sen nasılsın? 💎",
        "İyiyim canım, sen nasılsın? 😊",
        "Çok iyiyim, teşekkürler! Sen? 💎"
    ],
    "ne yapıyorsun": [
        "Sohbete katılıyorum! Sen ne yapıyorsun? 😊",
        "Burada sohbet ediyorum! Sen ne yapıyorsun? 💎"
    ],
    "ne haber": [
        "İyiyim, senden ne haber? 😊",
        "Fena değil; senden ne haber? 💎"
    ],
    "naber": [
        "İyidir, senden naber? 😊",
        "Fena değil; sende naber? 💎"
    ],
    "nabıyon": [
        "İyidir! Sen nabıyon? 😊",
        "İyi haber! Sen nabıyon? 💎"
    ],
    "ne var ne yok": [
        "Aynı, sende ne var ne yok? 😊",
        "Fena değil; sende neler var ne yok? 💎"
    ],
    "ne oluo": [
        "İdare, sende ne oluo? 😊",
        "Sende ne oluo, nasıl gidiyor? 💎"
    ],
    "ne oluyor": [
        "Sende neler oluyor? 😊",
        "Neler oluyor, nasıl gidiyor? 💎"
    ],
    "nasıl gidiyor": [
        "İyi gidiyor! Sen nasıl? 😊",
        "Harika! Sen nasıl? 💎"
    ],
    "keyfin nasıl": [
        "Çok iyi! Sen nasıl? 😊",
        "Harika! Sen nasıl? 💎"
    ],
    "halin nasıl": [
        "İyidir! Sen nasılsın? 😊",
        "İyi! Sen nasılsın? 💎"
    ],
    "halin ne": [
        "İyidir! Sen nasılsın? 😊",
        "İyi! Sen nasılsın? 💎"
    ],
    "ne yapıyon": [
        "Sohbete katılıyorum! Sen ne yapıyon? 😊",
        "Burada sohbet ediyorum! Sen ne yapıyon? 💎"
    ],
    "ne yapıyorsun": [
        "Sohbete katılıyorum! Sen ne yapıyorsun? 😊",
        "Burada sohbet ediyorum! Sen ne yapıyorsun? 💎"
    ]
}

# Günlük konuşma kalıpları - Sadece gerçek tepkiler
DAILY_CHAT = {
    "evet": [
        "Evet! 😊",
        "Evet! 💎"
    ],
    "hayır": [
        "Hayır! 😊",
        "Hayır! 💎"
    ],
    "tamam": [
        "Tamam! 😊",
        "Tamam! 💎"
    ],
    "olur": [
        "Olur! 😊",
        "Olur! 💎"
    ],
    "yok": [
        "Yok! 😊",
        "Yok! 💎"
    ],
    "var": [
        "Var! 😊",
        "Var! 💎"
    ],
    "biliyorum": [
        "Biliyorum! 😊",
        "Evet, biliyorum! 💎"
    ],
    "bilmiyorum": [
        "Bilmiyorum! 😊",
        "Bilmiyorum, söyle! 💎"
    ],
    "anladım": [
        "Anladım! 😊",
        "Evet, anladım! 💎"
    ],
    "anlamadım": [
        "Anlamadım! 😊",
        "Anlamadım, açıkla! 💎"
    ],
    "güzel": [
        "Güzel! 😊",
        "Evet, güzel! 💎"
    ],
    "kötü": [
        "Kötü! 😊",
        "Evet, kötü! 💎"
    ],
    "iyi": [
        "İyi! 😊",
        "Evet, iyi! 💎"
    ],
    "harika": [
        "Harika! 😊",
        "Evet, harika! 💎"
    ],
    "mükemmel": [
        "Mükemmel! 😊",
        "Evet, mükemmel! 💎"
    ],
    "süper": [
        "Süper! 😊",
        "Evet, süper! 💎"
    ],
    "muhteşem": [
        "Muhteşem! 😊",
        "Evet, muhteşem! 💎"
    ],
    "berbat": [
        "Berbat! 😊",
        "Evet, berbat! 💎"
    ],
    "korkunç": [
        "Korkunç! 😊",
        "Evet, korkunç! 💎"
    ],
    "ah": [
        "Ah! 😊",
        "Ah, evet! 💎"
    ],
    "oh": [
        "Oh! 😊",
        "Oh, evet! 💎"
    ],
    "wow": [
        "Wow! 😊",
        "Wow, evet! 💎"
    ],
    "vay": [
        "Vay! 😊",
        "Vay, evet! 💎"
    ],
    "aferin": [
        "Aferin! 😊",
        "Evet, aferin! 💎"
    ],
    "bravo": [
        "Bravo! 😊",
        "Evet, bravo! 💎"
    ],
    "tebrikler": [
        "Tebrikler! 😊",
        "Evet, tebrikler! 💎"
    ]
}

# KirveHub ile ilgili cevaplar - Sadece gerçekten KirveHub hakkında konuşulduğunda
KIRVEHUB_RESPONSES = [
    "KirveHub’da samimi bir ortam var. 💎",
    "Sohbetler burada keyifli gidiyor. 🎯",
    "Topluluk güzel, sohbet hep akıyor. 😊",
    "Yeni gelenler için de sıcak bir ortam. 🚀",
    "Gündem hep canlı, katılmak serbest. ✨"
]

# Point sistemi ile ilgili cevaplar - Sadece point hakkında konuşulduğunda
POINT_RESPONSES = [
    "Mesajların puana dönüşür, keyifle sohbet et. 💎",
    "Günlük limit dolmadan sohbetle KP biriktirirsin. 🎯",
    "Her mesaj bir adım; sohbet ettikçe ilerlersin. 😊",
    "Katılımın puan demek; düzenli yaz, düzenli kazan. 🚀"
]

# Kısaltma ve argo sözlüğü - Sadece gerçek kısaltmalar
SHORTCUTS = {
    "ab": ("abi", "Erkeklere hitap"),
    "abl": ("abla", "Kadınlara hitap"),
    "aeo": ("allah'a emanet ol", "Vedalaşma sözü"),
    "as": ("aleyküm selam", "Selamlaşmaya cevap"),
    "bknz": ("bakınız", "İmla/dalga geçme amaçlı"),
    "brn": ("ben", "Kısaltma"),
    "cnm": ("canım", "Hitap"),
    "cvp": ("cevap", "Genelde soru-cevapta"),
    "fln": ("falan", "Belirsizlik"),
    "grş": ("görüşürüz", "Veda"),
    "hşr": ("hoşçakal", "Vedalaşma"),
    "knk": ("kanka", "Arkadaşça hitap"),
    "krdş": ("kardeş", "Hitap"),
    "mrb": ("merhaba", "Selam"),
    "msl": ("mesela", "Örnek vermek için"),
    "nbr": ("ne haber", "Selamlaşma"),
    "sa": ("selamünaleyküm", "Selam"),
    "slm": ("selam", "Kısaca selam"),
    "tmm": ("tamam", "Onay"),
    "tşk": ("teşekkür", "Teşekkür etme"),
    "tşkrlr": ("teşekkürler", "Daha resmi"),
    "yk": ("yok", "Red cevabı")
}

# Küfür/argo kelimeler
BAD_WORDS = ["aq", "amk", "oç", "lan"]

# Veda kısaltmaları
FAREWELLS = ["aeo", "grş", "hşr"]

# Selamlaşma kısaltmaları
GREET_SHORTS = ["mrb", "slm", "sa", "nbr", "as"]

# Jargonlara özel hazır cevaplar - Günlük konuşma jargonları
JARGON_REPLIES = {
    "mrb": "Selam! Nasılsın?",
    "slm": "Selam! Nasılsın?",
    "sa": "Aleyküm selam! Hoş geldin!",
    "nbr": "İyiyim, sen nasılsın?",
    "as": "Aleyküm selam!",
    "aeo": "Allah'a emanet ol, kendine dikkat et! 👋",
    "grş": "Görüşürüz, kendine iyi bak!",
    "hşr": "Hoşçakal! Görüşmek üzere!",
    "tşk": "Rica ederim!",
    "tşkrlr": "Rica ederim, her zaman!",
    "cvp": "Cevap veriyorum!",
    "kdn": "Kanka dedin ne? 😂",
    "kbs": "K.bakma, sorun yok; devam!",
    "kanka": "Kanka, nasılsın?",
    "knk": "Kanka, ne var ne yok?",
    "krdş": "Kardeşim, ne var ne yok?",
    "yk": "Başka bir şey var mı?",
    "naber": "İyidir! Sen naber?",
    "nabıyon": "İdare, sen?",
    "ne var ne yok": "Fena değil, sende ne var ne yok?",
    "ne oluo": "Aynı, sende ne oluo?",
    "ne oluyor": "Sakin, sende ne var?",
    "nasıl gidiyor": "Fena değil; sende nasıl?",
    "keyfin nasıl": "İyi, sende?",
    "halin nasıl": "İyi sayılır, sen nasılsın?",
    "halin ne": "İyi, sen?",
    "ne yapıyon": "Takılıyorum; sen?",
    "ne yapıyorsun": "Buradayım; sen ne yapıyorsun?",
    "ne yapıyorsunuz": "Sohbete eşlik ediyorum; siz?"
}

import re

def find_shortcuts(text):
    found = []
    for k in SHORTCUTS:
        # kelime olarak geçiyorsa
        if re.search(rf"\b{k}\b", text):
            found.append(k)
    return found

def find_jargon_reply(text):
    # En son geçen ve baskın jargon için cevap döndür
    found = []
    for k in JARGON_REPLIES:
        if re.search(rf"\b{k}\b", text):
            found.append(k)
    if found:
        # En son geçen jargonun cevabını döndür
        return JARGON_REPLIES[found[-1]]
    return None

def is_bot_startup_protection_active():
    """Bot başlangıç koruması aktif mi kontrol et"""
    return (time.time() - bot_startup_time) < STARTUP_PROTECTION_DURATION

async def send_registration_reminder(user_id: int, user_name: str):
    """Kayıt olmayan kullanıcıya hatırlatma mesajı gönder - İYİLEŞTİRİLDİ"""
    # ÖNEMLİ: Kayıt kontrolü - Kayıtlı kullanıcılara mesaj gönderme!
    try:
        is_registered = await is_user_registered(user_id)
        if is_registered:
            logger.debug(f"⏸️ Kayıtlı kullanıcı - Kayıt mesajı gönderilmedi - User: {user_name} ({user_id})")
            return
    except Exception as reg_check_error:
        logger.error(f"❌ Kayıt kontrolü hatası - User: {user_id}, Error: {reg_check_error}")
        # Hata durumunda da mesaj gönderme (güvenli taraf)
        return
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Bot username'ini al (deep link için)
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        bot_deep_link = f"https://t.me/{bot_username}?start=register" if bot_username else None
        
        # İyileştirilmiş, daha samimi ve etkili mesajlar
        reminder_messages = [
            f"""
👋 **Merhaba {user_name}!**

Grupta yazıyorsun ama henüz kayıtlı değilsin! 😊

💎 **Kayıt ol ve neler kazanacaksın:**
• Her mesajın **0.20 KP** kazandırır
• Günlük **5.00 KP** limitin var
• Market'te **freespin** ve **bakiye** alabilirsin
• **Çekilişlere** ve **etkinliklere** katılabilirsin
• **Sıralamada** yer alabilirsin

🎯 **Hemen kayıt ol ve point kazanmaya başla!**
            """,
            f"""
🚀 **{user_name}, Kayıt Olma Zamanı!**

Grupta aktifsin ama henüz kayıtlı değilsin! 😅

❌ **Şu anda:**
• Point kazanamıyorsun
• Market'e erişemiyorsun
• Etkinliklere katılamıyorsun

✅ **Kayıt olduktan sonra:**
• Her mesajın **0.20 KP** kazandırır
• Günlük **5.00 KP** limitin olur
• Market'ten ürün alabilirsin
• Çekilişlere katılabilirsin

⬇️ **Hemen kayıt ol!**
            """,
            f"""
💡 **{user_name}, Son Fırsat!**

Grupta yazıyorsun ama kayıt olmayı unuttun! 😊

💎 **Kayıt ol ve şunları yap:**
• Her mesajın **0.20 KP** kazandırır
• Market'ten **freespin** alabilirsin
• **Çekilişlere** katılabilirsin
• **Sıralamada** yer alabilirsin
• **Etkinliklerde** ödüller kazanabilirsin

🎯 **Hemen kayıt ol ve sisteme katıl!**
            """
        ]
        
        # Rastgele bir mesaj seç
        registration_message = random.choice(reminder_messages)
        
        # İyileştirilmiş butonlar - Deep link ile kayıt
        keyboard_buttons = []
        if bot_deep_link:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🎯 KAYIT OL", url=bot_deep_link)
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🎯 KAYIT OL - /start yazın", callback_data="register_user")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="📋 Komutlar", callback_data="show_commands")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        # Özelden gönder
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        try:
            await bot.send_message(
                chat_id=user_id,
                text=registration_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            logger.info(f"✅ Kayıt olmayan kullanıcıya hatırlatma mesajı gönderildi - User: {user_id}")
        except Exception as e:
            # DM başlatamama durumunu log'u sakinleştir
            if "bot can't initiate conversation" in str(e).lower():
                logger.info(f"ℹ️ Kullanıcı DM başlatmamış, hatırlatma atlanıyor - User: {user_id}")
            else:
                logger.error(f"❌ Hatırlatma mesajı gönderme hatası: {e}")
        finally:
            try:
                await bot.session.close()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"❌ Hatırlatma mesajı genel hata: {e}")

def should_send_registration_reminder(user_id: int) -> bool:
    """Kayıt olmayan kullanıcıya hatırlatma gönderilmeli mi kontrol et"""
    current_time = time.time()
    
    # Kullanıcının son mesaj zamanını kontrol et
    if user_id in unregistered_users_last_message:
        last_message_time = unregistered_users_last_message[user_id]
        # 10 dakika geçmişse hatırlatma gönder
        if current_time - last_message_time >= REGISTRATION_REMINDER_INTERVAL:
            unregistered_users_last_message[user_id] = current_time
            return True
    
    return False

def cleanup_unregistered_user(user_id: int):
    """Kullanıcı gruptan çıktığında veya kayıt olduğunda temizlik yap"""
    if user_id in unregistered_users_last_message:
        del unregistered_users_last_message[user_id]
        logger.info(f"🧹 Kayıt olmayan kullanıcı temizlendi - User: {user_id}")

def is_user_in_unregistered_list(user_id: int) -> bool:
    """Kullanıcı kayıt olmayan kullanıcılar listesinde mi kontrol et"""
    return user_id in unregistered_users_last_message
        
async def handle_chat_message(message: Message) -> Optional[str]:
    """
    Sohbet mesajını analiz et ve uygun cevabı döndür
    """
    # ÖNEMLİ: Eski mesajlara cevap verme - Mesaj yaşını kontrol et
    try:
        message_date = message.date
        if message_date:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if message_date.tzinfo is None:
                # Eğer timezone yoksa, UTC olarak kabul et
                message_date = message_date.replace(tzinfo=timezone.utc)
            
            message_age_seconds = (now - message_date).total_seconds()
            
            # Eğer mesaj 5 dakikadan eskiyse cevap verme
            if message_age_seconds > MAX_MESSAGE_AGE_SECONDS:
                logger.debug(f"⏰ Eski mesaj atlandı - Age: {message_age_seconds:.0f}s, Max: {MAX_MESSAGE_AGE_SECONDS}s")
                return None
            
            # Bot başlangıç koruması - İlk 5 dakika içinde eski mesajlara cevap verme
            time_since_startup = time.time() - bot_startup_time
            if time_since_startup < STARTUP_PROTECTION_DURATION:
                # Eğer mesaj bot başlamadan önce gönderilmişse cevap verme
                if message_age_seconds > time_since_startup:
                    logger.debug(f"⏰ Bot başlangıç koruması - Eski mesaj atlandı")
                    return None
    except Exception as age_check_error:
        logger.debug(f"⏰ Mesaj yaşı kontrolü hatası (kritik değil): {age_check_error}")
        # Hata durumunda devam et (güvenli taraf)
    
    try:
        user_id = message.from_user.id
        
        # PRIVACY MODE DISABLED OPTİMİZASYONU: Bot'a hitap kontrolünü en başta yap
        # Tüm mesajlar geliyor, bu yüzden bot'a hitap edilmeyen mesajları hızlıca filtrele
        text = message.text or ""
        text_lower = text.lower().strip()
        
        # Hızlı bot'a hitap kontrolü (mention/reply) - EN ÖNCE
        reply_to_bot = bool(getattr(message, 'reply_to_message', None) and 
                            getattr(message.reply_to_message, 'from_user', None) and 
                            message.reply_to_message.from_user.is_bot)
        bot_mentions = ["bot", "kirve", "kirvehub", "@kirvehub_bot", "@kirvelastbot"]
        is_addressed_to_bot = reply_to_bot or any(mention in text_lower for mention in bot_mentions)
        
        # ÖNEMLİ: Bot'a hitap edilmediyse çok erken çık (performans için)
        if not is_addressed_to_bot:
            # Sadece varlık/yoklama soruları için kontrol et (çok nadir)
            try:
                if any(re.search(pat, text_lower) for pat in PRESENCE_PATTERNS):
                    # Varlık sorularına sadece çok nadir cevap ver (throttle kontrolü ile)
                    if not should_throttle_non_addressed(message.chat.id):
                        response = choose_diverse_response(message.chat.id, PRESENCE_RESPONSES)
                        mark_non_addressed_reply(message.chat.id)
                        logger.info(f"✅ Yoklama cevabı: {response}")
                        return humanize_response(response)
            except Exception:
                pass
            
            # Bot'a hitap edilmediyse hiçbir şey yapma (hızlı çıkış)
            return None
        
        # Bot'a hitap edildi, devam et (artık detaylı kontroller yapılabilir)
        
        # Bot başlangıç koruması kontrolü - CHAT SİSTEMİ İÇİN (komutlar çalışmaya devam eder)
        if is_bot_startup_protection_active():
            logger.debug(f"🛡️ Bot başlangıç koruması aktif - Chat sistemi devre dışı (3 dakika) - User: {user_id}")
            return None
        
        # Temel kontroller
        if not chat_system_active:
            logger.debug("❌ Chat system inactive")
            return None
            
        if message.chat.type == "private":
            logger.debug("❌ Private message, skipping")
            return None
            
        if not text or len(text) < min_message_length:
            logger.debug("❌ Text too short or empty")
            return None
        
        # +18 sohbet algılama ve yönlendirme (ÖNCELİK)
        adult_keywords = [
            "+18", "18+", "artı 18", "artı18", "plus 18", "plus18",
            "yetiskin", "yetişkin", "erotik", "seks", "sex", "porno",
            "nsfw", "adult", "mature", "yasak", "yasaklı içerik"
        ]
        
        if any(keyword in text_lower for keyword in adult_keywords):
            logger.info(f"🔞 +18 sohbet algılandı - User: {user_id}, Text: '{text[:50]}'")
            return (
                "🔞 **+18 İçerik**\n\n"
                "Bu tür içerikler için özel kanalımızı kullanabilirsiniz:\n\n"
                "👉 [Kirvehub +18](https://t.me/+fZZcRtudqpxjNDEy)\n\n"
                "💡 Bu kanalda +18 içerikler paylaşılabilir."
            )
            
        # Cooldown kontrolü (grup ID ile - iyileştirilmiş)
        group_id = message.chat.id if message.chat.type in ["group", "supergroup"] else None
        can_respond = await cooldown_manager.can_respond_to_user(user_id, group_id)
        if not can_respond:
            logger.debug(f"❌ Cooldown aktif - User: {user_id}, Group: {group_id}")
            return None

        # Bot'a hitap kontrolü zaten yukarıda yapıldı (774-789. satırlar)
        # Buraya geldiyse bot'a hitap edilmiş demektir, devam et
            
        # Kayıt kontrolü
        is_registered = await is_user_registered(user_id)
        
        # Kayıt olmayan kullanıcılar için teşvik sistemi
        if not is_registered:
            # Sadece grupta çalış
            if message.chat.type in ["group", "supergroup"]:
                current_time = time.time()
                
                # Kullanıcının son mesaj zamanını kaydet
                if user_id not in unregistered_users_last_message:
                    unregistered_users_last_message[user_id] = current_time
                    # İlk mesaj - hemen teşvik gönder
                    await send_registration_reminder(user_id, message.from_user.first_name)
                    logger.info(f"✅ Kayıt olmayan kullanıcıya ilk teşvik mesajı gönderildi - User: {user_id}")
                    return None  # Grupta hiçbir şey yazma
                else:
                    # Son mesaj zamanını güncelle
                    unregistered_users_last_message[user_id] = current_time
                    
                    # 30 dakika geçmişse hatırlatma gönder (spam önleme)
                    if should_send_registration_reminder(user_id):
                        await send_registration_reminder(user_id, message.from_user.first_name)
                        logger.info(f"✅ Kayıt olmayan kullanıcıya hatırlatma mesajı gönderildi - User: {user_id}")
                        return None  # Grupta hiçbir şey yazma
            
            # Kayıtsız kullanıcı özelde yazıyorsa da hiçbir şey yapma
            return None
        
        # Mesajı kaydet (grup ID ile)
        group_id = message.chat.id if message.chat.type in ["group", "supergroup"] else None
        await cooldown_manager.record_user_message(user_id, group_id)
        
        # Jargonlara özel cevap (sadece bot'a hitap edilirse)
        temp_bot_mentions = ["bot", "kirve", "kirvehub", "@kirvehub_bot", "@kirvelastbot"]
        temp_is_addressed = bool(getattr(message, 'reply_to_message', None) and 
                                 getattr(message.reply_to_message, 'from_user', None) and 
                                 message.reply_to_message.from_user.is_bot) or any(m in text for m in temp_bot_mentions)
        if temp_is_addressed:
            jargon_reply = find_jargon_reply(text)
            if jargon_reply:
                # Aşırı kişisel ve "dinliyorum" benzeri cevapları nötrle
                blocked_fragments = [
                    "dinliyorum",
                ]
                if any(fragment in jargon_reply.lower() for fragment in blocked_fragments):
                    logger.info("♻️ Aşırı kişisel jargon cevabı nötrleniyor")
                else:
                    logger.info(f"✅ Jargon cevabı: {jargon_reply}")
                    return humanize_response(jargon_reply)

        # Kısaltma tespiti (sadece bot'a hitap edilirse)
        if temp_is_addressed:
            found_shortcuts = find_shortcuts(text)
            if found_shortcuts:
                responses = []
                for sc in found_shortcuts:
                    acilim, anlam = SHORTCUTS[sc]
                    if sc in BAD_WORDS:
                        responses.append(f"⚠️ '{sc}' argo/küfürdür, dikkatli kullan! ({acilim})")
                    elif sc in FAREWELLS:
                        responses.append(f"{acilim.capitalize()}! 👋 ({anlam})")
                    elif sc in GREET_SHORTS:
                        responses.append(f"{acilim.capitalize()}! ({anlam})")
                    else:
                        responses.append(f"'{sc}' = {acilim} ({anlam})")
                yanit = "\n".join(responses)
                logger.info(f"✅ Kısaltma cevabı: {yanit}")
                return humanize_response(yanit)

        # Akıllı yanıt sistemi
        smart_response = await get_smart_response(message)
        if smart_response:
            logger.info(f"✅ Akıllı yanıt: {smart_response}")
            return humanize_response(smart_response)
        
        # Bot'a hitap kontrolü - Sadece bot'a hitap eden mesajlara cevap ver
        bot_mentions = ["bot", "kirve", "kirvehub", "@kirvehub_bot", "@kirvelastbot"]
        text_lower = text.lower()
        # reply_to_bot durumu da yönlendirme sayılır
        reply_to_bot = bool(getattr(message, 'reply_to_message', None) and 
                            getattr(message.reply_to_message, 'from_user', None) and 
                            message.reply_to_message.from_user.is_bot)
        is_addressed_to_bot = reply_to_bot or any(mention in text_lower for mention in bot_mentions)
        
        # ÖNEMLİ: Bot'a hitap edilmemişse hiçbir şeye cevap verme (spam önleme)
        # Bot sadece kendisine doğrudan hitap edildiğinde cevap verir
        if not is_addressed_to_bot:
            logger.debug(f"⏸️ Bot'a hitap etmeyen mesaj, yanıt verilmiyor (spam önleme) - User: {user_id}")
            return None
        
        # Selamlaşma kontrolü - Sadece bot'a hitap eden selamlamalar - SPAM KORUMASI: Daha sıkı
        bot_mentions = ["bot", "kirve", "kirvehub", "rebekka", "rebekah", "@kirvehub_bot", "@kirvelastbot"]
        text_lower = text.lower()
        is_addressed_to_bot = any(mention in text_lower for mention in bot_mentions)
        
        # Selamlaşma için özel cooldown kontrolü - SPAM KORUMASI
        if is_addressed_to_bot:
            # Greeting cooldown kontrolü (grup bazlı)
            greeting_cooldown_key = f"greeting_{message.chat.id}"
            if greeting_cooldown_key not in last_non_addressed_reply_by_chat:
                last_non_addressed_reply_by_chat[greeting_cooldown_key] = 0
            
            last_greeting_time = last_non_addressed_reply_by_chat.get(greeting_cooldown_key, 0)
            time_since_last_greeting = time.time() - last_greeting_time
            
            # Greeting için minimum 15 dakika cooldown - SPAM KORUMASI
            GREETING_COOLDOWN_SEC = 900  # 15 dakika
            if time_since_last_greeting < GREETING_COOLDOWN_SEC:
                logger.debug(f"⏸️ Greeting cooldown aktif - {GREETING_COOLDOWN_SEC - time_since_last_greeting:.0f}s kaldı")
                return None
            
            for greeting, responses in GREETINGS.items():
                if greeting in text:
                    response = choose_diverse_response(message.chat.id, responses)
                    # Greeting cooldown'u güncelle
                    last_non_addressed_reply_by_chat[greeting_cooldown_key] = time.time()
                    logger.info(f"✅ Bot'a hitap eden selamlaşma cevabı: {response}")
                    return humanize_response(response)
                
        # Soru kontrolü - Sadece bot'a hitap eden sorular
        if is_addressed_to_bot:
            for question, responses in QUESTIONS.items():
                if question in text:
                    response = choose_diverse_response(message.chat.id, responses)
                    logger.info(f"✅ Bot'a hitap eden soru cevabı: {response}")
                    return humanize_response(response)
                
        # Günlük konuşma kalıpları kontrolü - Sadece bot'a hitap eden tepkiler
        if is_addressed_to_bot:
            for phrase, responses in DAILY_CHAT.items():
                if phrase in text:
                    response = choose_diverse_response(message.chat.id, responses)
                    logger.info(f"✅ Bot'a hitap eden günlük konuşma cevabı: {response}")
                    return humanize_response(response)
                
        # KirveHub kelimesi kontrolü - Sadece gerçekten KirveHub hakkında konuşulduğunda
        if "kirvehub" in text or "kirve hub" in text:
            response = choose_diverse_response(message.chat.id, KIRVEHUB_RESPONSES)
            logger.info(f"✅ KirveHub cevabı: {response}")
            return humanize_response(response)
            
        # Point kelimesi kontrolü - Sadece gerçekten point hakkında konuşulduğunda
        if "point" in text or "puan" in text or "kp" in text:
            response = choose_diverse_response(message.chat.id, POINT_RESPONSES)
            logger.info(f"✅ Point cevabı: {response}")
            return humanize_response(response)
            
        # Flörtleşme cevapları (çok nadir, abartmadan) - Sadece bot'a hitap edildiğinde
        if is_addressed_to_bot and random.random() < 0.08:  # %8 ihtimalle (çok nadir)
            text_lower_for_flirt = text_lower
            if any(trigger in text_lower_for_flirt for trigger in FLIRT_TRIGGERS):
                response = choose_diverse_response(message.chat.id, FLIRT_RESPONSES)
                logger.info(f"✅ Flörtleşme cevabı: {response}")
                return humanize_response(response)
        
        # Çok nadir genel cevaplar - Sadece çok pozitif mesajlarda
        if random.random() < 0.002:  # %0.2 ihtimalle (çok nadir)
            # Sadece çok pozitif mesajlarda cevap ver
            positive_words = ["güzel", "harika", "mükemmel", "süper", "muhteşem", "çok iyi"]
            if any(word in text for word in positive_words):
                response = choose_diverse_response(message.chat.id, [
                    "Evet, gerçekten güzel! 😊",
                    "Haklısın! 💎",
                    "Aynen öyle! 🎯",
                    "Kesinlikle! 🚀"
                ])
                logger.info(f"✅ Pozitif mesaj cevabı: {response}")
                return humanize_response(response)
            
        logger.info("❌ Uygun cevap bulunamadı")
        return None
        
    except Exception as e:
        logger.error(f"❌ Chat message handler hatası: {e}")
        return None

async def send_chat_response(message: Message, response: str):
    """Sohbet cevabını gönder"""
    bot = None
    try:
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        
        # Text validasyonu
        if not response or len(response.strip()) == 0:
            logger.warning("⚠️ Boş veya geçersiz mesaj - gönderilmedi")
            return
        
        # Kayıt kontrolü ve yönlendirme
        user_id = message.from_user.id
        is_registered = await is_user_registered(user_id)

        # ÖNEMLİ: Kayıtsız kullanıcılara grupta değil, özelden mesaj gönder (spam önleme)
        if not is_registered:
            # Kayıt mesajını özelden gönder (grupta spam yapma)
            try:
                from handlers.chat_system import send_registration_reminder
                await send_registration_reminder(user_id, message.from_user.first_name)
                logger.debug(f"✅ Kayıt mesajı özelden gönderildi - User: {user_id}")
            except Exception as reminder_error:
                logger.debug(f"⏸️ Kayıt mesajı gönderme hatası (kritik değil): {reminder_error}")
            
            # Grupta hiçbir şey yazma (spam önleme)
            logger.debug(f"⏸️ Kayıtsız kullanıcı - Grupta mesaj gönderilmedi (spam önleme)")
            return None

        # Aynı cevabı kısa sürede tekrar etme - FLAME KORUMASI
        if should_suppress_duplicate_response(message.chat.id, response):
            logger.info("♻️ Tekrarlı cevap bastırıldı (aynı metin kısa sürede) - FLAME KORUMASI")
            return None
        
        # SPAM KORUMASI: Bot'un son mesajından bu yana geçen süreyi kontrol et
        group_id = message.chat.id if message.chat.type in ["group", "supergroup"] else None
        if group_id:
            can_respond = await cooldown_manager.can_respond_to_user(user_id, group_id)
            if not can_respond:
                logger.info(f"⏸️ Spam koruması - Mesaj gönderilmedi - User: {user_id}, Group: {group_id}")
                return None
            
            # ÖNEMLİ: Son mesaj kontrolü - Eğer son mesaj bot ise, gönderme (FLAME KORUMASI)
            try:
                from handlers.group_activity_monitor import check_group_activity
                should_send, reason = await check_group_activity(group_id)
                if not should_send:
                    logger.debug(f"⏸️ Chat response - Grup {group_id}: Mesaj gönderilmedi - {reason}")
                    return None
            except Exception as check_error:
                logger.debug(f"⏸️ Grup aktivite kontrolü hatası (kritik değil): {check_error}")
                # Hata durumunda devam et (güvenli taraf)
        
        # Kayıtlı kullanıcılara normal cevap ver
        sent_msg = await bot.send_message(
            chat_id=message.chat.id,
            text=response,
            reply_to_message_id=message.message_id
        )
        
        # SPAM KORUMASI: Mesaj gönderildikten sonra cooldown kaydet
        if group_id:
            await cooldown_manager.record_user_message(user_id, group_id)
        
        # ÖNEMLİ: Bot mesajını grup aktivite izleyicisine kaydet (FLAME KORUMASI)
        # Bu, zamanlanmış mesajlar algoritması için kritik!
        if message.chat.type in ["group", "supergroup"]:
            try:
                from handlers.group_activity_monitor import record_bot_message
                bot_info = await bot.get_me()
                await record_bot_message(message.chat.id, bot_info.id)
            except Exception as record_error:
                logger.debug(f"⏸️ Bot mesajı kaydetme hatası (kritik değil): {record_error}")
        
        logger.debug(f"💬 Chat response gönderildi - User: {message.from_user.id}, Registered: {is_registered}")
        
    except Exception as e:
        logger.error(f"❌ Chat response hatası: {e}")
    finally:
        # Bot session'ını her durumda kapat
        if bot:
            try:
                await bot.session.close()
            except Exception:
                pass

# Admin panel fonksiyonları
def toggle_chat_system(enable: bool):
    """Sohbet sistemini aç/kapat"""
    global chat_system_active
    chat_system_active = enable
    
    status = "✅ Açıldı" if enable else "❌ Kapatıldı"
    logger.info(f"💬 Chat system {status}")
    
    return chat_system_active

def get_chat_status() -> bool:
    """Sohbet sistemi durumunu al"""
    return chat_system_active

def set_chat_probability(probability: float):
    """Sohbet cevap verme ihtimalini ayarla"""
    global chat_probability
    chat_probability = max(0.0, min(1.0, probability))
    logger.info(f"💬 Chat probability: {chat_probability}")

def set_min_message_length(length: int):
    """Minimum mesaj uzunluğunu ayarla"""
    global min_message_length
    min_message_length = max(1, length)
    logger.info(f"💬 Min message length: {min_message_length}")

# İstatistik fonksiyonları
def get_chat_stats() -> Dict:
    """Sohbet sistemi istatistiklerini al"""
    return {
        "active": chat_system_active,
        "probability": chat_probability,
        "min_length": min_message_length,
        "startup_protection_active": is_bot_startup_protection_active(),
        "startup_protection_remaining": max(0, STARTUP_PROTECTION_DURATION - (time.time() - bot_startup_time)),
        "greetings_count": len(GREETINGS),
        "questions_count": len(QUESTIONS),
        "daily_chat_count": len(DAILY_CHAT),
        "kirvehub_responses_count": len(KIRVEHUB_RESPONSES),
        "point_responses_count": len(POINT_RESPONSES)
    }

# Bot yazma komutu
async def bot_write_command(message: Message):
    """Bot'un ağzından yazı yazma komutu"""
    try:
        user_id = message.from_user.id
        config = get_config()
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Botyaz komutu mesajı silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_bot_write_privately(user_id, message.text)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        # Komut metnini/altyazıyı parse et (fotoğraf/doküman desteği)
        command_text = (message.caption or message.text or "").strip()
        parts = command_text.split(' ', 2)  # En fazla 2 parçaya böl
        
        if len(parts) < 3:
            await message.reply("❌ Kullanım: `/botyaz <grup_id> <mesaj>`\nÖrnek: `/botyaz -1001234567890 Merhaba kirvem!`")
            return
        
        try:
            group_id = int(parts[1])
            bot_message = parts[2]
        except ValueError:
            await message.reply("❌ Geçersiz grup ID! Örnek: `/botyaz -1001234567890 Merhaba kirvem!`")
            return
        
        # Bot instance'ını al
        from config import get_config
        bot_config = get_config()
        bot = Bot(token=bot_config.BOT_TOKEN)
        
        try:
            # İçeriğe göre gönderim
            if getattr(message, 'photo', None):
                await bot.send_photo(chat_id=group_id, photo=message.photo[-1].file_id, caption=bot_message)
            elif getattr(message, 'document', None):
                await bot.send_document(chat_id=group_id, document=message.document.file_id, caption=bot_message)
            else:
                await bot.send_message(chat_id=group_id, text=bot_message)
            
            # Başarı mesajı
            await message.reply(
                f"✅ Bot mesajı gönderildi!\n\n**Grup ID:** {group_id}\n**İçerik:** "
                f"{'Fotoğraf' if getattr(message,'photo',None) else ('Doküman' if getattr(message,'document',None) else 'Metin')}\n"
                f"**Mesaj:** {bot_message}"
            )
            
            logger.info(f"🤖 Bot mesajı gönderildi - Group: {group_id}, Message: {bot_message[:50]}...")
            
        except Exception as e:
            await message.reply(f"❌ Mesaj gönderilemedi: {str(e)}")
            logger.error(f"❌ Bot mesaj gönderme hatası: {e}")
            
        finally:
            await bot.session.close()
            
    except Exception as e:
        logger.error(f"❌ Bot write command hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

# Callback handler'ları
async def chat_callback_handler(callback: types.CallbackQuery):
    """Chat sistemi callback handler'ı"""
    try:
        user_id = callback.from_user.id
        data = callback.data
        
        logger.info(f"🔍 Chat callback alındı - User: {user_id} - Data: {data}")
        
        if data == "register_user":
            # Kayıt işlemi başlat
            from handlers.register_handler import register_user_command
            await register_user_command(callback.message)
            
            # Kayıt olmayan kullanıcılar listesinden temizle
            cleanup_unregistered_user(user_id)
            
            await callback.answer("🎯 Kayıt işlemi başlatıldı!")
            
        elif data == "show_commands":
            # Komut listesi göster
            from handlers.register_handler import komutlar_command
            await komutlar_command(callback.message)
            await callback.answer("📋 Komutlar gösterildi!")
            
        elif data == "close_message":
            # Mesajı sil
            try:
                await callback.message.delete()
                await callback.answer("❌ Mesaj kapatıldı!")
            except Exception as e:
                logger.error(f"❌ Mesaj silme hatası: {e}")
                await callback.answer("❌ Mesaj silinemedi!")
                
    except Exception as e:
        logger.error(f"❌ Chat callback handler hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!")

async def _send_bot_write_privately(user_id: int, command_text: str):
    """Botyaz mesajını özel mesajla gönder"""
    try:
        if not _bot_instance:
            logger.error("❌ Bot instance bulunamadı!")
            return
        
        # Admin kontrolü
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await _bot_instance.send_message(user_id, "❌ Bu komutu sadece admin kullanabilir!")
            return
        
        # Komut metnini/altyazıyı parse et
        parts = command_text.strip().split(' ', 2)  # En fazla 2 parçaya böl
        
        if len(parts) < 3:
            await _bot_instance.send_message(
                user_id,
                "❌ Kullanım: `/botyaz <grup_id> <mesaj>`\nÖrnek: `/botyaz -1001234567890 Merhaba kirvem!`"
            )
            return
        
        try:
            group_id = int(parts[1])
            bot_message = parts[2]
        except ValueError:
            await _bot_instance.send_message(
                user_id,
                "❌ Geçersiz grup ID! Örnek: `/botyaz -1001234567890 Merhaba kirvem!`"
            )
            return
        
        # Bot instance'ını al
        from config import get_config
        bot_config = get_config()
        bot = Bot(token=bot_config.BOT_TOKEN)
        
        try:
            # Özel mesajdan tetiklenen sürümde medya forward edilmiyor; metin gönder
            await bot.send_message(chat_id=group_id, text=bot_message)
            
            # Başarı mesajı
            await _bot_instance.send_message(user_id, f"✅ Bot mesajı gönderildi!\n\n**Grup ID:** {group_id}\n**İçerik:** Metin\n**Mesaj:** {bot_message}")
            
            logger.info(f"🤖 Bot mesajı gönderildi - Group: {group_id}, Message: {bot_message[:50]}...")
            
        except Exception as e:
            await _bot_instance.send_message(user_id, f"❌ Mesaj gönderilemedi: {str(e)}")
            logger.error(f"❌ Bot mesaj gönderme hatası: {e}")
            
        finally:
            await bot.session.close()
            
    except Exception as e:
        logger.error(f"❌ Private bot write hatası: {e}")
        await _bot_instance.send_message(user_id, "❌ Bot yazma mesajı gönderilemedi!") 