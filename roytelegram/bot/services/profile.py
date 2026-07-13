import logging
import os

from aiogram import Bot

from bot.texts import BOT_DESCRIPTION, BOT_SHORT_DESCRIPTION

logger = logging.getLogger(__name__)


def _sync_photos_enabled() -> bool:
    return os.getenv("SYNC_PROFILE_PHOTOS", "").lower() in ("1", "true", "yes")


async def sync_bot_profile(bot: Bot, token: str) -> None:
    await bot.set_my_description(description=BOT_DESCRIPTION)
    await bot.set_my_short_description(short_description=BOT_SHORT_DESCRIPTION)

    if not _sync_photos_enabled():
        logger.info("Profil metni güncellendi (görsel atlandı — düşük RAM modu).")
        return

    from bot.services.profile_photos import upload_profile_photos

    await upload_profile_photos(token)
