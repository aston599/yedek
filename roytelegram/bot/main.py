import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import load_settings
from bot.database import Database
from bot.handlers import admin, catch_all, start
from bot.middleware import AppMiddleware
from bot.services.profile import sync_bot_profile

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    settings = load_settings()
    db = Database(settings.database_path)
    await db.connect()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    try:
        await sync_bot_profile(bot, settings.bot_token)
        logging.info("Bot profil açıklaması ve görseli güncellendi.")
    except Exception as exc:
        logging.warning("Profil güncellenemedi: %s", exc)

    dp = Dispatcher()
    middleware = AppMiddleware(db, settings.admin_ids, settings.setup_secret)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)

    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(catch_all.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
