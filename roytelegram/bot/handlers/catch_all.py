import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.database import Database
from bot.services.start_flow import send_start_flow

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text, StateFilter(None))
async def handle_user_text(message: Message, db: Database) -> None:
    if message.from_user is None or message.text is None:
        return

    if message.text.startswith("/"):
        return

    menu_text = await db.get_setting("menu_button_text")

    if message.text == menu_text:
        await db.log_click(message.from_user.id, "menu_button")
        url = await db.get_setting("menu_button_url")
        inline_text = await db.get_setting("inline_button_text")
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=inline_text, url=url)]]
        )
        await message.answer(
            "✅ <b>Giriş linkiniz hazır!</b>\n\n"
            "Aşağıdaki butona tıklayarak devam edin.",
            reply_markup=keyboard,
        )
        return

    await db.upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    try:
        await send_start_flow(message, db)
    except Exception:
        logger.exception("Promo mesajı gönderilemedi")
        await message.answer("⚠️ Mesaj gönderilemedi. Lütfen tekrar deneyin.")
