"""
🔐 Gizli Komutlar Handler - KirveHub Bot
Sadece bot sahibi için gizli komutlar
"""

import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram import Bot

from config import get_config
from database import delete_user_account
from utils.logger import logger

router = Router()

# Bot sahibinin ID'si (config'den al)
config = get_config()
OWNER_ID = config.OWNER_ID  # Config'den OWNER_ID'yi al

@router.message(Command("selfdestruct"))
async def self_destruct_handler(message: Message):
    """Kendi hesabını silme komutu - Sadece bot sahibi"""
    try:
        # Sadece bot sahibi kullanabilir
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
            return
        
        # Onay mesajı
        await message.reply(
            "⚠️ **DİKKAT: Kendi hesabınızı silmek üzeresiniz!**\n\n"
            "Bu işlem geri alınamaz. Devam etmek istiyor musunuz?\n\n"
            "✅ Devam etmek için: `/confirm_selfdestruct`\n"
            "❌ İptal etmek için: `/cancel_selfdestruct`",
            parse_mode="Markdown"
        )
        
        logger.warning(f"🔐 Self-destruct komutu çalıştırıldı - Owner: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Self-destruct handler hatası: {e}")

@router.message(Command("confirm_selfdestruct"))
async def confirm_self_destruct_handler(message: Message):
    """Self-destruct onayı"""
    try:
        # Sadece bot sahibi kullanabilir
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
            return
        
        # Hesabı sil
        logger.info(f"🔐 Self-destruct başlatılıyor - User: {message.from_user.id}")
        success = await delete_user_account(message.from_user.id)
        
        if success:
            await message.reply(
                "✅ **Hesabınız başarıyla silindi!**\n\n"
                "Artık bot sisteminde kaydınız yok.\n"
                "Yeni kayıt için `/start` komutunu kullanabilirsiniz.",
                parse_mode="Markdown"
            )
            
            logger.critical(f"🚨 OWNER ACCOUNT DELETED - User: {message.from_user.id}")
        else:
            await message.reply(
                "❌ **Hata: Hesap silinemedi!**\n\n"
                "Teknik bir sorun oluştu. Lütfen daha sonra tekrar deneyin.",
                parse_mode="Markdown"
            )
            
            logger.error(f"❌ Self-destruct başarısız - User: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Confirm self-destruct handler hatası: {e}")

@router.message(Command("cancel_selfdestruct"))
async def cancel_self_destruct_handler(message: Message):
    """Self-destruct iptali"""
    try:
        # Sadece bot sahibi kullanabilir
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
            return
        
        await message.reply(
            "✅ **İşlem iptal edildi!**\n\n"
            "Hesabınız güvende. Hiçbir şey silinmedi.",
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Self-destruct iptal edildi - Owner: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Cancel self-destruct handler hatası: {e}")

@router.message(Command("deleteme"))
async def delete_me_handler(message: Message):
    """Direkt hesap silme komutu - Sadece bot sahibi"""
    try:
        # Sadece bot sahibi kullanabilir
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
            return
        
        # Direkt silme işlemi
        logger.info(f"🔐 Direct delete başlatılıyor - User: {message.from_user.id}")
        success = await delete_user_account(message.from_user.id)
        
        if success:
            await message.reply(
                "✅ **Hesabınız başarıyla silindi!**\n\n"
                "Artık bot sisteminde kaydınız yok.\n"
                "Yeni kayıt için `/start` komutunu kullanabilirsiniz.",
                parse_mode="Markdown"
            )
            
            logger.critical(f"🚨 DIRECT DELETE COMPLETED - User: {message.from_user.id}")
        else:
            await message.reply(
                "❌ **Hata: Hesap silinemedi!**\n\n"
                "Teknik bir sorun oluştu. Lütfen daha sonra tekrar deneyin.",
                parse_mode="Markdown"
            )
            
            logger.error(f"❌ Direct delete başarısız - User: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Direct delete handler hatası: {e}")

@router.message(Command("owner_status"))
async def owner_status_handler(message: Message):
    """Bot sahibi durumu kontrolü"""
    try:
        # Sadece bot sahibi kullanabilir
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Bu komutu kullanma yetkiniz yok!")
            return
        
        await message.reply(
            "🔐 **Bot Sahibi Durumu**\n\n"
            f"👤 **User ID:** `{message.from_user.id}`\n"
            f"📝 **Username:** @{message.from_user.username or 'Yok'}\n"
            f"📅 **Kayıt Tarihi:** {message.from_user.first_name}\n\n"
            "✅ **Durum:** Bot sahibi yetkilerine sahipsiniz",
            parse_mode="Markdown"
        )
        
        logger.info(f"🔐 Owner status kontrolü - Owner: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Owner status handler hatası: {e}")

# Bot instance setter
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance 