#!/usr/bin/env python3
"""
🌐 Evrensel Log Sistemi - Tüm işlemleri loglar
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from aiogram import types
from aiogram.types import Message, CallbackQuery

from utils.logger import log_system, log_error, log_warning, log_info

class UniversalLogger:
    """Evrensel log sistemi"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def log_everything(self, message: Message, action: str = "message_received"):
        """Her şeyi logla"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or "Unknown"
            chat_type = message.chat.type
            chat_id = message.chat.id
            text = message.text or "No text"
            
            log_system(f"📝 {action} - User: {user_id} (@{username}) - Chat: {chat_type} ({chat_id}) - Text: '{text}'")
            
        except Exception as e:
            log_error(f"Universal log hatası: {e}")
    
    async def log_command_attempt(self, message: Message, command: str):
        """Komut denemesi logla"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or "Unknown"
            
            log_system(f"⚡ Komut denemesi: {command} - User: {user_id} (@{username})")
            
        except Exception as e:
            log_error(f"Komut log hatası: {e}")
    
    async def log_command_success(self, message: Message, command: str):
        """Komut başarı logu"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or "Unknown"
            
            log_system(f"✅ Komut başarılı: {command} - User: {user_id} (@{username})")
            
        except Exception as e:
            log_error(f"Komut başarı log hatası: {e}")
    
    async def log_command_failure(self, message: Message, command: str, error: str):
        """Komut hata logu"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or "Unknown"
            
            log_error(f"❌ Komut hatası: {command} - User: {user_id} (@{username}) - Error: {error}")
            
        except Exception as e:
            log_error(f"Komut hata log hatası: {e}")
    
    async def log_handler_attempt(self, handler_name: str, message: Message):
        """Handler denemesi logla"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or "Unknown"
            text = message.text or "No text"
            
            log_system(f"🔍 Handler denemesi: {handler_name} - User: {user_id} (@{username}) - Text: '{text}'")
            
        except Exception as e:
            log_error(f"Handler log hatası: {e}")
    
    async def log_handler_success(self, handler_name: str, message: Message):
        """Handler başarı logu"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or "Unknown"
            
            log_system(f"✅ Handler başarılı: {handler_name} - User: {user_id} (@{username})")
            
        except Exception as e:
            log_error(f"Handler başarı log hatası: {e}")
    
    async def log_handler_failure(self, handler_name: str, message: Message, error: str):
        """Handler hata logu"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or "Unknown"
            
            log_error(f"❌ Handler hatası: {handler_name} - User: {user_id} (@{username}) - Error: {error}")
            
        except Exception as e:
            log_error(f"Handler hata log hatası: {e}")

# Global instance
_universal_logger = UniversalLogger()

def get_universal_logger():
    """Evrensel logger'ı al"""
    return _universal_logger

# Decorator fonksiyonları
def log_everything(func):
    """Her şeyi logla decorator'ı"""
    async def wrapper(message: Message, *args, **kwargs):
        try:
            # Başlangıç logu
            await _universal_logger.log_everything(message, f"FUNCTION_START_{func.__name__}")
            
            # Fonksiyonu çalıştır
            result = await func(message, *args, **kwargs)
            
            # Başarı logu
            await _universal_logger.log_everything(message, f"FUNCTION_SUCCESS_{func.__name__}")
            
            return result
            
        except Exception as e:
            # Hata logu
            await _universal_logger.log_everything(message, f"FUNCTION_ERROR_{func.__name__}")
            log_error(f"❌ {func.__name__} hatası: {e}")
            raise
            
    return wrapper

def log_command_attempt(func):
    """Komut denemesi logla decorator'ı"""
    async def wrapper(message: Message, *args, **kwargs):
        command = message.text.split()[0] if message.text else "Unknown"
        
        try:
            # Komut denemesi logu
            await _universal_logger.log_command_attempt(message, command)
            
            # Fonksiyonu çalıştır
            result = await func(message, *args, **kwargs)
            
            # Başarı logu
            await _universal_logger.log_command_success(message, command)
            
            return result
            
        except Exception as e:
            # Hata logu
            await _universal_logger.log_command_failure(message, command, str(e))
            raise
            
    return wrapper 