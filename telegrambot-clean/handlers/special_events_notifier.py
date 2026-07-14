"""
📢 Özel Etkinlik Kanal Bildirimi Modülü

Amaç: Belirli bir Telegram kanalına (ör. t.me/kirveozel) yeni bir gönderi geldiğinde,
kayıtlı tüm gruplara davet bildirimi düşmek.
"""

import asyncio
import os
from typing import List

from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot, F

from utils.logger import logger
from config import get_config
from database import get_registered_groups

router = Router()

# Hedef kanal kullanıcı adı ("t.me/" kısmı olmadan). Gerekirse listeye alternatifler eklenebilir
TARGET_CHANNEL_USERNAMES = {"kirveozel", "KirveOzel", "KIRVEOZEL"}
# Başlık ile tespit: Bot admin olduğu ve başlığı aşağıdakilerden biri olan chat'ler
TARGET_CHAT_TITLES = {"kirve özel etkinlik"}

# Ortam değişkeninden kanal ID'leri (virgülle ayrılmış) okunur
def _load_target_channel_ids() -> set:
    ids_env = os.getenv("SPECIAL_EVENT_CHANNEL_IDS", "").strip()
    ids: set = set()
    if ids_env:
        for part in ids_env.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ids.add(int(part))
            except ValueError:
                logger.warning(f"⚠️ Geçersiz kanal ID (yok sayıldı): {part}")
    return ids

TARGET_CHANNEL_IDS = _load_target_channel_ids()

# Davet bağlantısı
SPECIAL_CHANNEL_LINK = "https://t.me/kirveozel"


async def _get_group_ids() -> List[int]:
    try:
        groups = await get_registered_groups()
        return [g["group_id"] for g in groups]
    except Exception as e:
        logger.error(f"❌ Kayıtlı gruplar alınamadı: {e}")
        return []


async def _broadcast_special_event_invite(bot: Bot, text: str, button_text: str = "🔔 Kanala Katıl") -> int:
    """Metni tüm kayıtlı gruplara gönder; başarı sayısını döndür."""
    sent = 0
    group_ids = await _get_group_ids()
    if not group_ids:
        logger.warning("⚠️ Kayıtlı grup yok; özel etkinlik bildirimi atlanıyor")
        return 0

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text, url=SPECIAL_CHANNEL_LINK)]
    ])

    for gid in group_ids:
        # Yalnızca grup/süpergrup ID'leri (negatif) hedeflenir
        if isinstance(gid, int) and gid > 0:
            continue
        try:
            await bot.send_message(chat_id=gid, text=text, parse_mode="Markdown", reply_markup=keyboard)
            sent += 1
            await asyncio.sleep(0.05)  # Nazik hız limiti
        except Exception as e:
            # Erişim yok/forbidden durumlarını sakin logla
            if "forbidden" in str(e).lower() or "bot can't initiate conversation" in str(e).lower():
                logger.info(f"ℹ️ Bildirim atlanıyor (erişim yok) - Grup: {gid}")
            else:
                logger.error(f"❌ Bildirim gönderilemedi - Grup: {gid}, Hata: {e}")
    return sent


def _normalize(text: str) -> str:
    return (text or "").strip().lower()

async def _bot_is_admin_in_chat(bot: Bot, chat_id: int) -> bool:
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)
        return str(getattr(member, "status", "")).lower() in {"administrator", "creator"}
    except Exception:
        return False

async def _is_from_target_special_chat(bot: Bot, message: types.Message) -> bool:
    chat = message.chat
    if not chat:
        return False
    # 1) Username/ID ile kanal eşleşmesi
    username = (chat.username or "").strip().lstrip("@")
    if chat.type == "channel":
        if username in TARGET_CHANNEL_USERNAMES:
            return True
        try:
            if chat.id in TARGET_CHANNEL_IDS:
                return True
        except Exception:
            pass
    # 2) Başlık eşleşmesi + bot admin kontrolü (grup/süpergrup/kanal)
    title_norm = _normalize(getattr(chat, "title", ""))
    if title_norm in TARGET_CHAT_TITLES:
        return await _bot_is_admin_in_chat(bot, chat.id)
    return False


@router.channel_post()
async def handle_special_channel_post(message: types.Message):
    """Hedef özel kanal gönderisini yakala ve gruplara davet bildirimi gönder."""
    try:
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        if not await _is_from_target_special_chat(bot, message):
            await bot.session.close()
            return

        # Sabit davet metni (Markdown)
        notify_text = (
            "Kirvem, tam şu an özel bir etkinlik yayınlandı!\n\n"
            "Hemen görmek için kanalımıza dahil ol!\n"
            "Dahil olmak için bağlantı aşağıda."
        )

        # Ek buton: gönderi linki (sadece public username varsa)
        try:
            post_url = None
            if message.chat and message.chat.username:
                post_url = f"https://t.me/{message.chat.username}/{message.message_id}"
            # Varsayılan davet butonları
            sent = 0
            group_ids = await _get_group_ids()
            if group_ids:
                base_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔔 Kanala Katıl", url=SPECIAL_CHANNEL_LINK)]])
                if post_url:
                    base_keyboard.inline_keyboard.append([InlineKeyboardButton(text="📌 Gönderiyi Aç", url=post_url)])
                for gid in group_ids:
                    if isinstance(gid, int) and gid > 0:
                        continue
                    try:
                        await bot.send_message(chat_id=gid, text=notify_text, parse_mode="Markdown", reply_markup=base_keyboard)
                        sent += 1
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        if "forbidden" in str(e).lower() or "bot can't initiate conversation" in str(e).lower():
                            logger.info(f"ℹ️ Bildirim atlanıyor (erişim yok) - Grup: {gid}")
                        else:
                            logger.error(f"❌ Bildirim gönderilemedi - Grup: {gid}, Hata: {e}")
        except Exception as e:
            logger.error(f"❌ Özel butonlu gönderi hazırlanamadı: {e}")
            sent = await _broadcast_special_event_invite(bot, notify_text, button_text="🔔 Kanala Katıl")
        await bot.session.close()

        logger.info(f"✅ Özel etkinlik bildirimi gönderildi - Toplam: {sent}")
    except Exception as e:
        logger.error(f"❌ Özel etkinlik bildirimi hatası: {e}")


# Alternatif olarak, mesaj akışında channel mesajlarını yakalamak için güvence
@router.message(F.chat.type == "channel")
async def handle_special_channel_message(message: types.Message):
    try:
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        if not await _is_from_target_special_chat(bot, message):
            await bot.session.close()
            return
        await bot.session.close()
        await handle_special_channel_post(message)
    except Exception as e:
        logger.error(f"❌ Kanal mesajı işleme hatası: {e}")

# Grup/Süpergrup için de aynı mantık (başlık + admin)
@router.message((F.chat.type == "supergroup") | (F.chat.type == "group"))
async def handle_special_group_message(message: types.Message):
    try:
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        if not await _is_from_target_special_chat(bot, message):
            await bot.session.close()
            return
        await bot.session.close()
        # Kanal akışındaki mantığı kullan
        await handle_special_channel_post(message)
    except Exception as e:
        logger.error(f"❌ Grup mesajı işleme hatası: {e}")


