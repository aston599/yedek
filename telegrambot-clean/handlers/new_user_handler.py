"""
👋 Yeni Kullanıcı Handler'ı - KirveHub Bot
Gruba yeni katılan kullanıcılara otomatik kayıt teşvik mesajı gönderir
"""

import logging
import asyncio
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import ChatMemberUpdatedFilter, KICKED, LEFT, MEMBER, ADMINISTRATOR, CREATOR
from database import save_user_info, is_user_registered, is_group_registered
from handlers.message_monitor import send_registration_encouragement

logger = logging.getLogger(__name__)

router = Router()

# Bot instance setter
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

@router.message(F.new_chat_members)
async def handle_new_chat_members(message: Message):
    """
    Gruba yeni katılan kullanıcıları yakala ve kayıt teşvik mesajı gönder
    """
    try:
        # Sadece grup/süper grup mesajlarını işle
        if message.chat.type not in ["group", "supergroup"]:
            return
        
        # Grup kayıtlı mı kontrol et
        if not await is_group_registered(message.chat.id):
            logger.info(f"❌ Grup kayıtlı değil - Chat: {message.chat.id}")
            return
        
        # Yeni katılan kullanıcıları işle
        new_members = message.new_chat_members
        
        for new_member in new_members:
            # Bot'ları yoksay
            if new_member.is_bot:
                logger.info(f"🤖 Bot yeni üye - User: {new_member.first_name} ({new_member.id})")
                continue
            
            user_id = new_member.id
            first_name = new_member.first_name or "Kullanıcı"
            username = new_member.username
            last_name = new_member.last_name
            
            logger.info(f"👋 Yeni kullanıcı gruba katıldı - User: {first_name} ({user_id}), Group: {message.chat.title}")
            
            # Kullanıcı bilgilerini kaydet
            await save_user_info(user_id, username, first_name, last_name)
            
            # Kullanıcı kayıtlı mı kontrol et
            is_registered = await is_user_registered(user_id)
            
            if is_registered:
                logger.info(f"✅ Yeni katılan kullanıcı zaten kayıtlı - User: {first_name} ({user_id})")
                # Kayıtlı kullanıcıya hoş geldin mesajı gönderebiliriz (isteğe bağlı)
                continue
            
            # Kayıtsız kullanıcı - Özelden kayıt teşvik mesajı gönder
            logger.info(f"🎯 Yeni katılan kullanıcı kayıtsız - User: {first_name} ({user_id}), Kayıt teşvik mesajı gönderiliyor...")
            
            # Kısa bir bekleme (bot'un mesajı işlemesi için)
            await asyncio.sleep(2)
            
            # Kayıt teşvik mesajı gönder
            try:
                await send_registration_encouragement(
                    user_id=user_id,
                    first_name=first_name,
                    group_name=message.chat.title or "Grup"
                )
                logger.info(f"✅ Yeni kullanıcıya kayıt teşvik mesajı gönderildi - User: {first_name} ({user_id})")
            except Exception as e:
                logger.error(f"❌ Yeni kullanıcıya kayıt teşvik mesajı gönderme hatası - User: {user_id}, Error: {e}")
        
    except Exception as e:
        logger.error(f"❌ New chat members handler hatası: {e}", exc_info=True)




