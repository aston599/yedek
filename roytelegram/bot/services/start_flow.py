from aiogram.types import Message

from bot.database import Database
from bot.keyboards import build_start_inline_keyboard


async def send_start_flow(message: Message, db: Database) -> None:
    settings = await db.get_all_settings()
    ad_banner = settings["ad_banner"].strip()
    welcome_text = settings["welcome_text"].strip()

    parts: list[str] = []
    if ad_banner:
        parts.append(f"<b>{ad_banner}</b>")
    if welcome_text:
        parts.append(welcome_text)

    full_text = "\n\n".join(parts) if parts else "Hoş geldiniz!"

    inline_kb = await build_start_inline_keyboard(db)
    await message.answer(full_text, reply_markup=inline_kb)
