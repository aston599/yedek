"""
/getid komutu: Kullanılan bağlamın ID bilgisini döndürür.

Kullanım senaryoları:
- Özel sohbet: Mevcut chat id'si döner.
- Bir mesaja reply yapıldıysa: reply edilen mesajın chat.id ve varsa forward_from_chat.id döner.
- Kanal mesajını bot'a iletip reply ederseniz, kanalın chat.id'ini yakalar.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("getid"))
async def get_id_command(message: Message):
    try:
        lines = []

        # Mevcut sohbet
        chat = message.chat
        if chat:
            lines.append(f"🆔 Bu sohbet (chat.id): <code>{chat.id}</code>")
            if getattr(chat, "username", None):
                lines.append(f"@{chat.username}")

        # Reply edilen mesaj varsa
        if getattr(message, "reply_to_message", None):
            r = message.reply_to_message
            if getattr(r, "chat", None):
                lines.append(f"\n↩️ Yanıtlanan mesajın chat.id: <code>{r.chat.id}</code>")
            # Kanaldan iletim kontrolü
            if getattr(r, "forward_from_chat", None):
                fchat = r.forward_from_chat
                uname = f"@{fchat.username}" if getattr(fchat, "username", None) else ""
                lines.append(f"📣 İletilen kanal chat.id: <code>{fchat.id}</code> {uname}")

        # Mesajın forward bilgisi (nadiren doğrudan gelebilir)
        if getattr(message, "forward_from_chat", None):
            fchat = message.forward_from_chat
            uname = f"@{fchat.username}" if getattr(fchat, "username", None) else ""
            lines.append(f"📣 Forward kanal chat.id: <code>{fchat.id}</code> {uname}")

        if not lines:
            lines.append("Bulunamadı. Bir kanal gönderisini bana iletip bu mesaja /getid yazarak yanıtlayın.")

        await message.reply("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Hata: {e}")


