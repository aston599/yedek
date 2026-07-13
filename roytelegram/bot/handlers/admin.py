from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import Database, SETTING_KEYS
from bot.keyboards import admin_back_keyboard, admin_main_keyboard, admin_panel_message
from bot.labels import (
    EDIT_PROMPTS,
    HELP_TEXT,
    SAVE_SUCCESS,
    SETTING_LABELS,
    UNAUTHORIZED,
)
from bot.services.profile_photos import avatar_path, profile_cover_path, upload_profile_photo
from bot.services.start_flow import send_start_flow
from bot.states import AdminEdit

router = Router()


def is_admin(user_id: int | None, admin_ids: tuple[int, ...]) -> bool:
    return user_id is not None and user_id in admin_ids


def _truncate(text: str, limit: int = 500) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


async def _send_panel(message: Message) -> None:
    await message.answer(
        admin_panel_message(),
        reply_markup=admin_main_keyboard(),
    )


async def _send_saved(message: Message, label: str) -> None:
    await message.answer(
        SAVE_SUCCESS.format(label=label),
        reply_markup=admin_back_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("whoami"))
async def cmd_whoami(message: Message) -> None:
    if message.from_user is None:
        return
    await message.answer(
        f"🆔 Telegram ID: <code>{message.from_user.id}</code>\n"
        f"👤 Kullanıcı: @{message.from_user.username or '-'}"
    )


@router.message(Command("claim"))
async def cmd_claim(
    message: Message,
    db: Database,
    setup_secret: str,
    admin_ids: tuple[int, ...],
) -> None:
    if message.from_user is None:
        return

    if is_admin(message.from_user.id, admin_ids):
        await message.answer("✅ Zaten admin yetkiniz var. /admin ile panele girin.")
        return

    if not setup_secret:
        await message.answer("Kurulum kodu tanımlı değil. ADMIN_IDS kullanın.")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or parts[1].strip() != setup_secret:
        await message.answer("❌ Geçersiz kurulum kodu.")
        return

    await db.add_admin(message.from_user.id)
    await message.answer(
        "✅ Admin yetkisi verildi.\n"
        "Artık /admin ile botu yönetebilirsiniz."
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, admin_ids: tuple[int, ...]) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        await message.answer(UNAUTHORIZED)
        return
    await _send_panel(message)


@router.callback_query(F.data == "admin:panel")
async def admin_panel_callback(
    callback: CallbackQuery,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(callback.from_user.id, admin_ids):
        await callback.answer("Yetkisiz", show_alert=True)
        return
    if callback.message is None:
        return
    await _send_panel(callback.message)
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(
    callback: CallbackQuery,
    db: Database,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(callback.from_user.id, admin_ids):
        await callback.answer("Yetkisiz", show_alert=True)
        return
    if callback.message is None:
        return

    users = await db.count_users()
    clicks = await db.count_clicks()
    by_source = await db.count_clicks_by_source()

    lines = [
        "📊 <b>İstatistik</b>\n",
        f"👥 Toplam kullanıcı: <b>{users}</b>",
        f"🖱 Toplam tıklama: <b>{clicks}</b>",
    ]
    if by_source:
        lines.append("\n<b>Tıklama detayı:</b>")
        for source, count in by_source.items():
            label = "Alt Menü Butonu" if source == "menu_button" else source
            lines.append(f"• {label}: <b>{count}</b>")

    await callback.message.answer("\n".join(lines), reply_markup=admin_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:preview")
async def admin_preview(
    callback: CallbackQuery,
    db: Database,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(callback.from_user.id, admin_ids):
        await callback.answer("Yetkisiz", show_alert=True)
        return
    if callback.message is None:
        return

    await callback.message.answer("👁 <b>Önizleme</b> — kullanıcılar bunu görür:")
    await send_start_flow(callback.message, db)
    await callback.message.answer(
        "Önizleme tamamlandı.",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(
    callback: CallbackQuery,
    state: FSMContext,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(callback.from_user.id, admin_ids):
        await callback.answer("Yetkisiz", show_alert=True)
        return

    await state.set_state(AdminEdit.waiting_broadcast)
    if callback.message:
        await callback.message.answer(EDIT_PROMPTS["broadcast"])
    await callback.answer()


@router.callback_query(F.data.startswith("admin:edit:"))
async def admin_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(callback.from_user.id, admin_ids):
        await callback.answer("Yetkisiz", show_alert=True)
        return

    if callback.data is None or callback.message is None:
        return

    field = callback.data.removeprefix("admin:edit:")

    if field == "welcome_image":
        await state.set_state(AdminEdit.waiting_image)
        current = await db.get_setting("welcome_image")
        current_text = (
            "✅ Sohbet görseli yüklü."
            if current
            else "❌ Varsayılan banner kullanılıyor."
        )
        await callback.message.answer(
            EDIT_PROMPTS["welcome_image"].format(current=current_text)
        )
        await callback.answer()
        return

    if field == "profile_image":
        await state.set_state(AdminEdit.waiting_profile_image)
        current_text = (
            "✅ Profil resmi (avatar) yüklü."
            if avatar_path().is_file()
            else "❌ Henüz profil resmi yok."
        )
        await callback.message.answer(
            EDIT_PROMPTS["profile_image"].format(current=current_text)
        )
        await callback.answer()
        return

    if field == "profile_cover":
        await state.set_state(AdminEdit.waiting_profile_cover)
        current_text = (
            "✅ Kapak görseli mevcut."
            if profile_cover_path().is_file()
            else "❌ Henüz kapak görseli yok."
        )
        await callback.message.answer(
            EDIT_PROMPTS["profile_cover"].format(current=current_text)
        )
        await callback.answer()
        return

    if field == "inline_button":
        await state.set_state(AdminEdit.waiting_inline_button)
        text = await db.get_setting("inline_button_text")
        url = await db.get_setting("inline_button_url")
        current = f"{text} → {url}"
        await callback.message.answer(
            EDIT_PROMPTS["inline_button"].format(current=_truncate(current))
        )
        await callback.answer()
        return

    if field == "menu_button":
        await state.set_state(AdminEdit.waiting_menu_button)
        text = await db.get_setting("menu_button_text")
        url = await db.get_setting("menu_button_url")
        current = f"{text} → {url}"
        await callback.message.answer(
            EDIT_PROMPTS["menu_button"].format(current=_truncate(current))
        )
        await callback.answer()
        return

    if field not in SETTING_KEYS:
        await callback.answer("Geçersiz alan", show_alert=True)
        return

    await state.set_state(AdminEdit.waiting_value)
    await state.update_data(setting_key=field)
    current = await db.get_setting(field)
    prompt_key = field if field in EDIT_PROMPTS else "welcome_text"
    label = SETTING_LABELS.get(field, field)
    prompt = EDIT_PROMPTS.get(prompt_key, EDIT_PROMPTS["welcome_text"])
    await callback.message.answer(
        prompt.format(current=_truncate(current or "—"))
    )
    await callback.answer()


def _looks_like_admin_prompt(text: str) -> bool:
    markers = ("Mevcut değer:", "Yeni metni gönderin", "İptal: /cancel")
    return sum(marker in text for marker in markers) >= 2


@router.message(Command("cancel"))
@router.message(Command("iptal"))
async def admin_cancel(message: Message, state: FSMContext, admin_ids: tuple[int, ...]) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return
    await state.clear()
    await message.answer("İşlem iptal edildi.", reply_markup=admin_back_keyboard())


@router.message(Command("clear_image"))
async def admin_clear_image(
    message: Message,
    db: Database,
    state: FSMContext,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return

    await db.set_setting("welcome_image", "")
    await state.clear()
    await message.answer(
        "✅ Promo görseli silindi. Varsayılan sohbet banner'ı kullanılacak.",
        reply_markup=admin_back_keyboard(),
    )


@router.message(AdminEdit.waiting_profile_image, F.photo)
async def admin_save_profile_image(
    message: Message,
    state: FSMContext,
    bot: Bot,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return

    tg_file = await bot.get_file(message.photo[-1].file_id)
    if tg_file.file_path is None:
        await message.answer("Dosya indirilemedi. Tekrar deneyin.")
        return

    dest = avatar_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    await bot.download_file(tg_file.file_path, dest)

    ok = await upload_profile_photo(bot.token, dest)
    await state.clear()

    if ok:
        await message.answer(
            "✅ <b>Profil Resmi (Avatar)</b> güncellendi.\n"
            "Sohbet listesinde yuvarlak ikon olarak görünür.",
            reply_markup=admin_back_keyboard(),
        )
    else:
        await message.answer(
            "⚠️ Dosya kaydedildi ama Telegram profiline yüklenemedi. "
            "JPG formatında kare görsel deneyin.",
            reply_markup=admin_back_keyboard(),
        )


@router.message(AdminEdit.waiting_profile_cover, F.photo)
async def admin_save_profile_cover(
    message: Message,
    state: FSMContext,
    bot: Bot,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return

    tg_file = await bot.get_file(message.photo[-1].file_id)
    if tg_file.file_path is None:
        await message.answer("Dosya indirilemedi. Tekrar deneyin.")
        return

    dest = profile_cover_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    await bot.download_file(tg_file.file_path, dest)

    ok = await upload_profile_photo(bot.token, dest)
    await state.clear()

    if ok:
        await message.answer(
            "✅ <b>Kapak Görseli (Başla Öncesi)</b> güncellendi.\n"
            "Botu yeni sekmede açarak kontrol edin.",
            reply_markup=admin_back_keyboard(),
        )
    else:
        await message.answer(
            "⚠️ Dosya kaydedildi ama Telegram'a yüklenemedi. JPG kare görsel deneyin.",
            reply_markup=admin_back_keyboard(),
        )


@router.message(AdminEdit.waiting_profile_cover)
async def admin_profile_cover_invalid(
    message: Message,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return
    await message.answer("❌ Lütfen fotoğraf gönderin. İptal: /cancel")


@router.message(AdminEdit.waiting_profile_image)
async def admin_profile_image_invalid(
    message: Message,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return
    await message.answer("❌ Lütfen fotoğraf gönderin. İptal: /cancel")


@router.message(AdminEdit.waiting_value)
async def admin_save_value(
    message: Message,
    state: FSMContext,
    db: Database,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return
    if message.text is None:
        await message.answer("Metin gönderin.")
        return

    if message.text.startswith("/"):
        await message.answer("Komut kaydedilmez. Yeni metni yazın veya /cancel ile iptal edin.")
        return

    data = await state.get_data()
    key = data.get("setting_key")
    if key not in SETTING_KEYS:
        await state.clear()
        await message.answer("Ayar anahtarı bulunamadı. /admin ile tekrar deneyin.")
        return

    value = message.text.strip()
    if key == "welcome_text" and _looks_like_admin_prompt(value):
        await message.answer(
            "❌ Bu admin panel metni kaydedilemez.\n"
            "Sadece kullanıcılara görünecek promo metnini gönderin.\n"
            "İptal: /cancel"
        )
        return

    await db.set_setting(key, value)
    await state.clear()
    label = SETTING_LABELS.get(key, key)
    await _send_saved(message, label)


@router.message(AdminEdit.waiting_image, F.photo)
async def admin_save_image(
    message: Message,
    state: FSMContext,
    db: Database,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return

    file_id = message.photo[-1].file_id
    await db.set_setting("welcome_image", file_id)
    await state.clear()
    await _send_saved(message, SETTING_LABELS["welcome_image"])


@router.message(AdminEdit.waiting_image)
async def admin_image_invalid(
    message: Message,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return
    await message.answer(
        "❌ Lütfen fotoğraf gönderin.\n"
        "Silmek için: <code>/clear_image</code> | İptal: /cancel"
    )


@router.message(AdminEdit.waiting_inline_button)
async def admin_save_inline_button(
    message: Message,
    state: FSMContext,
    db: Database,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return
    if message.text is None or "|" not in message.text:
        await message.answer("Format: <code>Metin | https://link</code>")
        return

    text, url = [part.strip() for part in message.text.split("|", 1)]
    if not text or not url.startswith("http"):
        await message.answer("Geçerli bir metin ve http(s) linki girin.")
        return

    await db.set_setting("inline_button_text", text)
    await db.set_setting("inline_button_url", url)
    await state.clear()
    await _send_saved(message, "Inline Buton")


@router.message(AdminEdit.waiting_menu_button)
async def admin_save_menu_button(
    message: Message,
    state: FSMContext,
    db: Database,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return
    if message.text is None or "|" not in message.text:
        await message.answer("Format: <code>Metin | https://link</code>")
        return

    text, url = [part.strip() for part in message.text.split("|", 1)]
    if not text or not url.startswith("http"):
        await message.answer("Geçerli bir metin ve http(s) linki girin.")
        return

    await db.set_setting("menu_button_text", text)
    await db.set_setting("menu_button_url", url)
    await state.clear()
    await _send_saved(message, "Alt Menü Butonu")


@router.message(AdminEdit.waiting_broadcast, F.photo)
async def admin_send_broadcast_photo(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return

    caption = message.caption or ""
    file_id = message.photo[-1].file_id
    user_ids = await db.all_user_ids()
    sent = 0
    failed = 0

    for user_id in user_ids:
        try:
            await bot.send_photo(user_id, file_id, caption=caption)
            sent += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        f"📣 Gönderildi: <b>{sent}</b> | Başarısız: <b>{failed}</b>",
        reply_markup=admin_back_keyboard(),
    )


@router.message(AdminEdit.waiting_broadcast)
async def admin_send_broadcast(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
    admin_ids: tuple[int, ...],
) -> None:
    if not is_admin(message.from_user.id if message.from_user else None, admin_ids):
        return
    if message.text is None:
        await message.answer("Metin veya fotoğraf gönderin.")
        return

    user_ids = await db.all_user_ids()
    sent = 0
    failed = 0
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, message.text)
            sent += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        f"📣 Gönderildi: <b>{sent}</b> | Başarısız: <b>{failed}</b>",
        reply_markup=admin_back_keyboard(),
    )
