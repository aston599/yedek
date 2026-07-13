import json
import logging
from pathlib import Path

import aiohttp

from bot.config import BASE_DIR
from bot.texts import AVATAR_IMAGE, PROFILE_COVER_IMAGE

logger = logging.getLogger(__name__)


def avatar_path() -> Path:
    return BASE_DIR / AVATAR_IMAGE


def profile_cover_path() -> Path:
    return BASE_DIR / PROFILE_COVER_IMAGE


async def upload_profile_photo(token: str, image_path: Path) -> bool:
    if not image_path.is_file():
        logger.warning("Profil görseli bulunamadı: %s", image_path)
        return False

    data = aiohttp.FormData()
    data.add_field(
        "photo",
        json.dumps({"type": "static", "photo": "attach://profile"}),
        content_type="application/json",
    )
    data.add_field(
        "profile",
        image_path.read_bytes(),
        filename="profile.jpg",
        content_type="image/jpeg",
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://api.telegram.org/bot{token}/setMyProfilePhoto",
            data=data,
        ) as response:
            result = await response.json()
            if not result.get("ok"):
                logger.warning("Profil görseli yüklenemedi: %s", result)
                return False
            return True


async def upload_profile_photos(token: str) -> None:
    if await upload_profile_photo(token, profile_cover_path()):
        logger.info("Başlat ekranı kapak görseli güncellendi.")
    elif await upload_profile_photo(token, avatar_path()):
        logger.info("Profil resmi (avatar) yüklendi (kapak yok).")
