"""
❓ Bilinmeyen Komutlar Handler - KirveHub Bot
Kayıtlı kullanıcılar için bilinmeyen komut uyarısı
"""

import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from config import get_config
from database import is_user_registered
from utils.logger import logger

router = Router()

@router.message(F.text.startswith("/"))
async def unknown_command_handler(message: Message):
    """Bilinmeyen komutlar için handler"""
    try:
        # Grup chatindeyse komut mesajını sil (tüm komutlar için)
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
            return
        
        # Sadece kayıtlı kullanıcılar için
        if not await is_user_registered(message.from_user.id):
            return
        
        # Komut metnini al
        command = message.text.split()[0].lower()
        
        # Bilinen komutlar listesi (Sadece oyuncuların kullanabileceği komutlar)
        known_commands = [
            "/start", "/menu", "/kirvekayit", "/kayitsil", "/yardim", "/komutlar",
            "/etkinlikler", "/market", "/siparislerim", "/siralama", "/profil"
        ]
        
        # Eğer bilinmeyen bir komut ise
        if command not in known_commands:
            # Özel mesajda uyarı gönder
            await message.reply(
                f"❌ **HATA: Bilinmeyen komut!**\n\n"
                f"`{command}` diye bir komut yok.\n\n"
                f"Komutları görmek için `/yardim` yazın.",
                parse_mode="Markdown"
            )
            
            logger.info(f"❓ Bilinmeyen komut: {command} - User: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Unknown command handler hatası: {e}")

# Bot instance setter
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance 