"""
🗑️ Safe Message Delete - Rate Limiter ile korumalı mesaj silme
"""

import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from aiogram.types import Message

logger = logging.getLogger(__name__)

# Rate limiter - Son silme zamanları
_last_delete_times = {}
_delete_limit = 30  # Dakikada maksimum 30 silme
_delete_window = 60  # 60 saniye pencere

async def safe_delete_message(message: Message, reason: str = "") -> bool:
    """
    Rate limiter ile korumalı mesaj silme
    
    Args:
        message: Silinecek mesaj
        reason: Silme sebebi (log için)
        
    Returns:
        bool: Başarılı olursa True
    """
    try:
        chat_id = message.chat.id
        current_time = datetime.now()
        
        # Rate limit kontrolü
        if chat_id in _last_delete_times:
            recent_deletes = [t for t in _last_delete_times[chat_id] 
                            if (current_time - t).total_seconds() < _delete_window]
            
            if len(recent_deletes) >= _delete_limit:
                logger.warning(
                    f"⚠️ Message delete rate limit aşıldı - "
                    f"Chat: {chat_id}, Son {_delete_window}s'de {len(recent_deletes)} silme"
                )
                return False
            
            _last_delete_times[chat_id] = recent_deletes + [current_time]
        else:
            _last_delete_times[chat_id] = [current_time]
        
        # Mesajı sil
        await message.delete()
        logger.debug(f"✅ Mesaj silindi - Chat: {chat_id}, Reason: {reason or 'N/A'}")
        return True
        
    except Exception as e:
        logger.debug(f"❌ Mesaj silinemedi - Chat: {message.chat.id}, Error: {e}")
        return False


async def cleanup_delete_history():
    """Eski silme geçmişini temizle (Memory leak önleme)"""
    current_time = datetime.now()
    to_delete = []
    
    for chat_id, times in _last_delete_times.items():
        # 5 dakikadan eski kayıtları temizle
        recent = [t for t in times if (current_time - t).total_seconds() < 300]
        if not recent:
            to_delete.append(chat_id)
        else:
            _last_delete_times[chat_id] = recent
    
    for chat_id in to_delete:
        del _last_delete_times[chat_id]
    
    if to_delete:
        logger.info(f"🧹 {len(to_delete)} chat'in eski silme geçmişi temizlendi")





