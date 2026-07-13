from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.database import Database
from bot.labels import ADMIN_PANEL_TEXT


async def build_start_inline_keyboard(db: Database) -> InlineKeyboardMarkup:
    text = await db.get_setting("inline_button_text")
    url = await db.get_setting("inline_button_url")
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, url=url)]]
    )


async def build_menu_keyboard(db: Database) -> ReplyKeyboardMarkup:
    text = await db.get_setting("menu_button_text")
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Hoş Geldin Mesajı",
                    callback_data="admin:edit:welcome_text",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📷 Profil Resmi (Avatar)",
                    callback_data="admin:edit:profile_image",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼 Kapak Görseli (Başla Öncesi)",
                    callback_data="admin:edit:profile_cover",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼 Promo Görseli (Sohbet)",
                    callback_data="admin:edit:welcome_image",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Üst Reklam Banner",
                    callback_data="admin:edit:ad_banner",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎫 Promo Kodu",
                    callback_data="admin:edit:promo_code",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔘 Inline Buton",
                    callback_data="admin:edit:inline_button",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⌨️ Alt Menü Butonu",
                    callback_data="admin:edit:menu_button",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👁 Önizleme",
                    callback_data="admin:preview",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📣 Toplu Mesaj",
                    callback_data="admin:broadcast",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 İstatistik",
                    callback_data="admin:stats",
                )
            ],
        ]
    )


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ Admin Paneline Dön",
                    callback_data="admin:panel",
                ),
                InlineKeyboardButton(
                    text="👁 Önizleme",
                    callback_data="admin:preview",
                ),
            ]
        ]
    )


def admin_panel_message() -> str:
    return ADMIN_PANEL_TEXT
