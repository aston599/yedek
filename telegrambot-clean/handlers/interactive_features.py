"""
🎭 Interactive Features - Emoji reaksiyonları ve eğlenceli özellikler
"""

import logging
import random
import re
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import Message

logger = logging.getLogger(__name__)

# Bot instance
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

# Emoji reaksiyon cooldown'ları (spam koruması)
_emoji_user_cooldowns: Dict[int, datetime] = {}  # Kullanıcı bazlı cooldown
_emoji_group_cooldowns: Dict[int, datetime] = {}  # Grup bazlı cooldown
_emoji_reacted_messages: Dict[int, set] = {}  # Emoji atılan mesajlar (grup bazlı)

# Ayarlar
EMOJI_REACTION_PROBABILITY = 0.35  # %35 ihtimalle emoji reaksiyonu (ayarlanabilir)
RANDOM_EMOJI_PROBABILITY = 0.15  # %15 ihtimalle rastgele emoji (ayarlanabilir)
EMOJI_USER_COOLDOWN_SEC = 30  # Aynı kullanıcıya 30 saniyede bir emoji (ayarlanabilir)
EMOJI_GROUP_COOLDOWN_SEC = 10  # Aynı gruba 10 saniyede bir emoji (ayarlanabilir)
MIN_MESSAGE_LENGTH_FOR_EMOJI = 3  # Emoji için minimum mesaj uzunluğu (ayarlanabilir)

# Emoji reaksiyonları - Mesaj içeriğine göre
EMOJI_REACTIONS = {
    # Pozitif duygular
    "mutlu": ["👍", "❤️", "😊", "🎉", "✨", "🌟"],
    "güzel": ["👍", "❤️", "🔥", "💯", "✨"],
    "harika": ["🔥", "💯", "🚀", "👏", "🎯"],
    "teşekkür": ["👍", "❤️", "😊", "🙏"],
    "selam": ["👋", "😊", "👋", "🙂"],
    
    # Komik/Şaka
    "komik": ["😂", "🤣", "😆", "😄"],
    "şaka": ["😂", "😄", "😆"],
    
    # İlham verici
    "başarı": ["🔥", "💪", "🚀", "👏", "🎯"],
    "motivasyon": ["💪", "🔥", "🚀", "💎"],
    
    # Genel pozitif
    "iyi": ["👍", "😊", "✨"],
    "evet": ["👍", "✅", "👌"],
    "tamam": ["👍", "✅", "👌"],
    
    # Soru
    "soru": ["🤔", "💭", "❓"],
    
    # Özel durumlar
    "gece": ["🌙", "⭐", "😴", "🌃"],
    "sabah": ["☀️", "🌅", "🌄", "😊"],
    "akşam": ["🌆", "🌇", "😊"],
}

# Rastgele emoji reaksiyonları (herhangi bir mesaja)
RANDOM_EMOJIS = ["👍", "❤️", "😊", "🔥", "✨", "💯", "👏", "🎯", "🚀", "💪", "😄", "😂", "👋", "🙂", "🌟"]

# Sticker ID'leri (Telegram sticker set'lerinden)
# Not: Bu ID'ler örnek, gerçek sticker ID'lerini eklemelisiniz
STICKER_IDS = [
    # Komik sticker'lar
    "CAACAgIAAxkBAAIBY2Z...",  # Örnek - gerçek sticker ID'leri eklenmeli
]

# Günün sözleri
DAILY_QUOTES = [
    "💎 Her gün yeni bir başlangıç!",
    "🚀 Hedeflerine odaklan, başarı seni bekliyor!",
    "🔥 Bugün harika bir gün olacak!",
    "💪 Zorluklar seni daha güçlü yapar!",
    "🎯 Küçük adımlar büyük sonuçlar getirir!",
    "✨ Her şey mümkün, sadece inan!",
    "🌟 Sen özelsin, unutma!",
    "🎉 Bugün de harika bir gün!",
    "💯 Mükemmellik bir yolculuk, varış değil!",
    "🔥 Tutkunu takip et, başarı seni bulacak!",
]

# Komik cevaplar
FUNNY_RESPONSES = [
    "Hahaha! 😂",
    "Güldürdün! 😄",
    "Çok iyi! 😆",
    "Hahaha! 🤣",
    "Güzel! 😊",
    "Aynen! 👍",
    "Haklısın! 💯",
    "Kesinlikle! 🔥",
    "Mükemmel! ✨",
    "Süper! 🚀",
]

# Mesaj içeriğine göre emoji reaksiyonu seç
def choose_emoji_reaction(text: str) -> Optional[str]:
    """Mesaj içeriğine göre uygun emoji reaksiyonu seç"""
    try:
        text_lower = text.lower()
        
        # Pozitif kelimeler
        if any(word in text_lower for word in ["güzel", "harika", "mükemmel", "süper", "muhteşem", "çok iyi"]):
            return random.choice(EMOJI_REACTIONS["güzel"])
        
        if any(word in text_lower for word in ["teşekkür", "sağol", "sağ ol", "tşk", "thanks"]):
            return random.choice(EMOJI_REACTIONS["teşekkür"])
        
        if any(word in text_lower for word in ["selam", "merhaba", "hey", "hi", "hello"]):
            return random.choice(EMOJI_REACTIONS["selam"])
        
        if any(word in text_lower for word in ["komik", "güldürdü", "hahaha", "lol", "haha"]):
            return random.choice(EMOJI_REACTIONS["komik"])
        
        if any(word in text_lower for word in ["başarı", "kazandım", "kazandı", "başardım"]):
            return random.choice(EMOJI_REACTIONS["başarı"])
        
        if any(word in text_lower for word in ["evet", "tamam", "ok", "olur"]):
            return random.choice(EMOJI_REACTIONS["evet"])
        
        if "?" in text or any(word in text_lower for word in ["nasıl", "neden", "ne zaman", "kim"]):
            return random.choice(EMOJI_REACTIONS["soru"])
        
        # Zaman bazlı
        current_hour = datetime.now().hour
        if 22 <= current_hour or current_hour < 6:
            return random.choice(EMOJI_REACTIONS["gece"])
        elif 6 <= current_hour < 12:
            return random.choice(EMOJI_REACTIONS["sabah"])
        elif 18 <= current_hour < 22:
            return random.choice(EMOJI_REACTIONS["akşam"])
        
        # Rastgele emoji (ayarlanabilir ihtimal)
        if random.random() < RANDOM_EMOJI_PROBABILITY:
            return random.choice(RANDOM_EMOJIS)
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Emoji reaksiyon seçimi hatası: {e}")
        return None

# Mesaj içeriğine göre komik cevap seç
def choose_funny_response(text: str) -> Optional[str]:
    """Mesaj içeriğine göre komik cevap seç"""
    try:
        text_lower = text.lower()
        
        # Komik mesajlara cevap
        if any(word in text_lower for word in ["komik", "güldürdü", "hahaha", "lol", "şaka"]):
            if random.random() < 0.3:  # %30 ihtimalle
                return random.choice(FUNNY_RESPONSES)
        
        # Pozitif mesajlara cevap
        if any(word in text_lower for word in ["güzel", "harika", "mükemmel", "süper"]):
            if random.random() < 0.2:  # %20 ihtimalle
                return random.choice(["Aynen! 👍", "Haklısın! 🔥", "Kesinlikle! 💯", "Mükemmel! ✨"])
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Komik cevap seçimi hatası: {e}")
        return None

# Günün sözü
def get_daily_quote() -> str:
    """Günün sözünü döndür"""
    try:
        # Günün tarihine göre sabit bir söz seç (her gün aynı)
        day_of_year = datetime.now().timetuple().tm_yday
        quote_index = day_of_year % len(DAILY_QUOTES)
        return DAILY_QUOTES[quote_index]
    except Exception:
        return random.choice(DAILY_QUOTES)

async def add_emoji_reaction(message: Message, emoji: str):
    """Mesaja emoji reaksiyonu ekle (spam koruması ile)"""
    try:
        if not _bot_instance:
            logger.warning("⚠️ Bot instance yok, emoji reaksiyonu eklenemedi")
            return
        
        # Emoji validasyonu
        if not emoji or len(emoji.strip()) == 0:
            logger.warning("⚠️ Geçersiz emoji - boş emoji")
            return
        
        # Emoji'nin tek karakter olup olmadığını kontrol et (emoji'ler genelde 1-2 karakter)
        if len(emoji) > 10:  # Çok uzun emoji string'i geçersiz
            logger.warning(f"⚠️ Geçersiz emoji - çok uzun: {emoji}")
            return
        
        # Mesaj varlığını kontrol et
        if not message or not message.message_id or not message.chat:
            logger.warning("⚠️ Geçersiz mesaj - emoji reaksiyonu eklenemedi")
            return
        
        # SPAM KORUMASI: Kullanıcı bazlı cooldown kontrolü
        user_id = message.from_user.id if message.from_user else None
        if user_id:
            if user_id in _emoji_user_cooldowns:
                last_reaction_time = _emoji_user_cooldowns[user_id]
                time_diff = (datetime.now() - last_reaction_time).total_seconds()
                if time_diff < EMOJI_USER_COOLDOWN_SEC:
                    logger.debug(f"⏸️ Emoji reaksiyonu cooldown'da - User: {user_id}, Remaining: {EMOJI_USER_COOLDOWN_SEC - time_diff:.1f}s")
                    return
            _emoji_user_cooldowns[user_id] = datetime.now()
        
        # SPAM KORUMASI: Grup bazlı cooldown kontrolü
        group_id = message.chat.id
        if group_id in _emoji_group_cooldowns:
            last_reaction_time = _emoji_group_cooldowns[group_id]
            time_diff = (datetime.now() - last_reaction_time).total_seconds()
            if time_diff < EMOJI_GROUP_COOLDOWN_SEC:
                logger.debug(f"⏸️ Emoji reaksiyonu grup cooldown'da - Group: {group_id}, Remaining: {EMOJI_GROUP_COOLDOWN_SEC - time_diff:.1f}s")
                return
        _emoji_group_cooldowns[group_id] = datetime.now()
        
        # SPAM KORUMASI: Aynı mesaja birden fazla emoji atılmasını engelle
        if group_id not in _emoji_reacted_messages:
            _emoji_reacted_messages[group_id] = set()
        
        if message.message_id in _emoji_reacted_messages[group_id]:
            logger.debug(f"⏸️ Bu mesaja zaten emoji reaksiyonu eklendi - Message: {message.message_id}")
            return
        
        _emoji_reacted_messages[group_id].add(message.message_id)
        
        # Eski mesaj ID'lerini temizle (bellek optimizasyonu)
        if len(_emoji_reacted_messages[group_id]) > 100:
            # En eski 50 mesajı sil
            _emoji_reacted_messages[group_id] = set(list(_emoji_reacted_messages[group_id])[-50:])
        
        # Aiogram 3.x için set_message_reaction kullan
        # Emoji string'ini direkt gönder
        try:
            from aiogram.types import ReactionTypeEmoji
            reaction = ReactionTypeEmoji(emoji=emoji)
            await _bot_instance.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[reaction]
            )
            logger.debug(f"✅ Emoji reaksiyonu eklendi - Emoji: {emoji}, Message: {message.message_id}")
        except ImportError:
            # Eğer ReactionTypeEmoji yoksa, alternatif yöntem dene
            try:
                # Basit emoji string olarak dene
                await _bot_instance.set_message_reaction(
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    reaction=[{"type": "emoji", "emoji": emoji}]
                )
                logger.debug(f"✅ Emoji reaksiyonu eklendi - Emoji: {emoji}, Message: {message.message_id}")
            except Exception as alt_error:
                # Eğer set_message_reaction yoksa, sadece log yaz
                logger.warning(f"⚠️ set_message_reaction desteklenmiyor - Emoji: {emoji}, Error: {alt_error}")
                return
        except Exception as api_error:
            # Telegram API hatalarını yakala (REACTION_INVALID, mesaj silinmiş vs.)
            error_str = str(api_error).lower()
            if "reaction_invalid" in error_str or "bad request" in error_str:
                logger.debug(f"⚠️ Emoji reaksiyonu geçersiz veya mesaj silinmiş - Emoji: {emoji}, Message: {message.message_id}")
            else:
                logger.warning(f"⚠️ Emoji reaksiyonu ekleme hatası: {api_error}")
            return
        
    except Exception as e:
        logger.error(f"❌ Emoji reaksiyonu ekleme hatası: {e}")

async def send_random_sticker(message: Message):
    """Rastgele sticker gönder"""
    try:
        if not _bot_instance:
            return
        
        # Sticker ID'leri varsa ve geçerliyse gönder
        if not STICKER_IDS:
            return
        
        # Geçerli sticker ID'lerini filtrele (örnek ID'leri atla)
        valid_sticker_ids = [
            sid for sid in STICKER_IDS 
            if sid and len(sid) > 10 and not sid.endswith("...") and not "örnek" in sid.lower()
        ]
        
        if not valid_sticker_ids:
            # Geçerli sticker yoksa gönderme
            return
        
        sticker_id = random.choice(valid_sticker_ids)
        
        # Sticker ID validasyonu
        if not sticker_id or len(sticker_id.strip()) < 10:
            logger.warning(f"⚠️ Geçersiz sticker ID: {sticker_id}")
            return
        
        # Mesaj varlığını kontrol et
        if not message or not message.chat:
            logger.warning("⚠️ Geçersiz mesaj - sticker gönderilemedi")
            return
        
        try:
            await _bot_instance.send_sticker(
                chat_id=message.chat.id,
                sticker=sticker_id,
                reply_to_message_id=message.message_id
            )
            logger.debug(f"✅ Sticker gönderildi - Message: {message.message_id}")
        except Exception as api_error:
            # Telegram API hatalarını yakala (wrong HTTP URL vs.)
            error_str = str(api_error).lower()
            if "wrong http url" in error_str or "bad request" in error_str or "invalid" in error_str:
                logger.debug(f"⚠️ Geçersiz sticker ID veya URL - Sticker: {sticker_id[:20]}..., Message: {message.message_id}")
            else:
                logger.warning(f"⚠️ Sticker gönderme hatası: {api_error}")
        
    except Exception as e:
        logger.error(f"❌ Sticker gönderme hatası: {e}")

async def send_daily_quote(message: Message):
    """Günün sözünü gönder"""
    try:
        if not _bot_instance:
            return
        
        quote = get_daily_quote()
        
        # Text validasyonu
        if not quote or len(quote.strip()) == 0:
            logger.warning("⚠️ Boş günün sözü - gönderilmedi")
            return
        
        # Mesaj varlığını kontrol et
        if not message or not message.chat:
            logger.warning("⚠️ Geçersiz mesaj - günün sözü gönderilemedi")
            return
        
        try:
            await _bot_instance.send_message(
                chat_id=message.chat.id,
                text=quote,
                reply_to_message_id=message.message_id
            )
            logger.debug(f"✅ Günün sözü gönderildi - Message: {message.message_id}")
        except Exception as send_error:
            error_str = str(send_error).lower()
            if "text too short" in error_str or "empty" in error_str:
                logger.debug(f"⚠️ Mesaj çok kısa veya boş - gönderilmedi")
            else:
                logger.warning(f"⚠️ Günün sözü gönderme hatası: {send_error}")
        
    except Exception as e:
        logger.error(f"❌ Günün sözü gönderme hatası: {e}")

async def process_interactive_features(message: Message):
    """Mesaj için interaktif özellikleri işle (spam koruması ile)"""
    try:
        # Sadece grup mesajları
        if message.chat.type not in ["group", "supergroup"]:
            return
        
        # Bot mesajlarını yoksay
        if message.from_user and message.from_user.is_bot:
            return
        
        # Mesaj metni yoksa atla
        if not message.text:
            return
        
        text = message.text
        
        # SPAM KORUMASI: Minimum mesaj uzunluğu kontrolü
        if len(text.strip()) < MIN_MESSAGE_LENGTH_FOR_EMOJI:
            logger.debug(f"⏸️ Mesaj çok kısa, emoji reaksiyonu atlanıyor - Length: {len(text.strip())}")
            return
        
        # 1. Emoji reaksiyonu ekle (ayarlanabilir ihtimal)
        if random.random() < EMOJI_REACTION_PROBABILITY:
            emoji = choose_emoji_reaction(text)
            if emoji:
                await add_emoji_reaction(message, emoji)
        
        # 2. Komik cevap gönder (%10 ihtimalle)
        if random.random() < 0.10:
            funny_response = choose_funny_response(text)
            if funny_response and _bot_instance:
                # Text validasyonu
                if not funny_response or len(funny_response.strip()) == 0:
                    logger.warning("⚠️ Boş veya geçersiz mesaj - gönderilmedi")
                    return
                
                try:
                    await _bot_instance.send_message(
                        chat_id=message.chat.id,
                        text=funny_response,
                        reply_to_message_id=message.message_id
                    )
                    logger.debug(f"✅ Komik cevap gönderildi - Message: {message.message_id}")
                except Exception as send_error:
                    error_str = str(send_error).lower()
                    if "text too short" in error_str or "empty" in error_str:
                        logger.debug(f"⚠️ Mesaj çok kısa veya boş - gönderilmedi")
                    else:
                        logger.warning(f"⚠️ Mesaj gönderme hatası: {send_error}")
        
        # 3. Günün sözü (%1 ihtimalle)
        if random.random() < 0.01:
            await send_daily_quote(message)
        
        # 4. Rastgele sticker (%5 ihtimalle)
        if random.random() < 0.05:
            await send_random_sticker(message)
        
    except Exception as e:
        logger.error(f"❌ Interactive features hatası: {e}")


async def cleanup_emoji_cooldowns():
    """Eski cooldown kayıtlarını temizle (bellek optimizasyonu)"""
    try:
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=1)  # 1 saatten eski kayıtları sil
        
        # Kullanıcı cooldown'larını temizle
        users_to_remove = [
            user_id for user_id, last_time in _emoji_user_cooldowns.items()
            if last_time < cutoff_time
        ]
        for user_id in users_to_remove:
            del _emoji_user_cooldowns[user_id]
        
        # Grup cooldown'larını temizle
        groups_to_remove = [
            group_id for group_id, last_time in _emoji_group_cooldowns.items()
            if last_time < cutoff_time
        ]
        for group_id in groups_to_remove:
            del _emoji_group_cooldowns[group_id]
        
        if users_to_remove or groups_to_remove:
            logger.debug(f"🧹 Emoji cooldown temizliği - {len(users_to_remove)} kullanıcı, {len(groups_to_remove)} grup")
    except Exception as e:
        logger.debug(f"⏸️ Emoji cooldown temizleme hatası (kritik değil): {e}")

