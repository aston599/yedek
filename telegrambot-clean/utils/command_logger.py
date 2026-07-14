#!/usr/bin/env python3
"""
📝 Komut Log Sistemi - Tüm komutları ve işlemleri loglar
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from aiogram import types
from aiogram.types import Message, CallbackQuery

from utils.logger import log_system, log_error, log_warning, log_info

# Global komut log sistemi
_command_logger = None

class CommandLogger:
    """Komut log sistemi"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def log_command_execution(self, message: Message, command: str, success: bool = True, error: str = None):
        """Komut çalıştırma logu"""
        try:
            user_id = message.from_user.id
            username = message.from_user.username or "Unknown"
            chat_type = message.chat.type
            chat_id = message.chat.id
            
            if success:
                log_system(f"✅ Komut çalıştırıldı: {command} - User: {user_id} (@{username}) - Chat: {chat_type} ({chat_id})")
            else:
                log_error(f"❌ Komut hatası: {command} - User: {user_id} (@{username}) - Error: {error}")
                
        except Exception as e:
            log_error(f"Komut log hatası: {e}")
    
    async def log_callback_execution(self, callback: CallbackQuery, action: str, success: bool = True, error: str = None):
        """Callback çalıştırma logu"""
        try:
            user_id = callback.from_user.id
            username = callback.from_user.username or "Unknown"
            chat_type = callback.message.chat.type if callback.message else "Unknown"
            chat_id = callback.message.chat.id if callback.message else "Unknown"
            
            if success:
                log_system(f"🔍 Callback çalıştırıldı: {action} - User: {user_id} (@{username}) - Chat: {chat_type} ({chat_id})")
            else:
                log_error(f"❌ Callback hatası: {action} - User: {user_id} (@{username}) - Error: {error}")
                
        except Exception as e:
            log_error(f"Callback log hatası: {e}")
    
    async def log_admin_action(self, user_id: int, username: str, action: str, success: bool = True, error: str = None):
        """Admin işlem logu"""
        try:
            if success:
                log_system(f"🛡️ Admin işlem: {action} - User: {user_id} (@{username})")
            else:
                log_error(f"❌ Admin işlem hatası: {action} - User: {user_id} (@{username}) - Error: {error}")
                
        except Exception as e:
            log_error(f"Admin log hatası: {e}")
    
    async def log_user_action(self, user_id: int, username: str, action: str, details: str = None):
        """Kullanıcı işlem logu"""
        try:
            detail_text = f" - {details}" if details else ""
            log_info(f"👤 Kullanıcı işlem: {action} - User: {user_id} (@{username}){detail_text}")
                
        except Exception as e:
            log_error(f"Kullanıcı log hatası: {e}")
    
    async def log_system_action(self, action: str, details: str = None, success: bool = True):
        """Sistem işlem logu"""
        try:
            detail_text = f" - {details}" if details else ""
            if success:
                log_system(f"🔧 Sistem işlem: {action}{detail_text}")
            else:
                log_error(f"❌ Sistem işlem hatası: {action}{detail_text}")
                
        except Exception as e:
            log_error(f"Sistem log hatası: {e}")
    
    async def log_database_operation(self, operation: str, table: str, success: bool = True, error: str = None):
        """Database işlem logu"""
        try:
            if success:
                log_system(f"🗄️ Database işlem: {operation} - Tablo: {table}")
            else:
                log_error(f"❌ Database hatası: {operation} - Tablo: {table} - Error: {error}")
                
        except Exception as e:
            log_error(f"Database log hatası: {e}")

# Global instance
_command_logger = CommandLogger()

def get_command_logger():
    """Komut logger'ı al"""
    return _command_logger

# Decorator fonksiyonları
def log_command(func):
    """Komut log decorator'ı"""
    async def wrapper(message: Message, *args, **kwargs):
        command = message.text.split()[0] if message.text else "Unknown"
        
        try:
            # Komut başlangıç logu
            await _command_logger.log_command_execution(message, command, success=True)
            
            # Fonksiyonu çalıştır
            result = await func(message, *args, **kwargs)
            
            # Başarılı sonuç logu
            await _command_logger.log_command_execution(message, command, success=True)
            
            return result
            
        except Exception as e:
            # Hata logu
            await _command_logger.log_command_execution(message, command, success=False, error=str(e))
            raise
            
    return wrapper

def log_callback(func):
    """Callback log decorator'ı"""
    async def wrapper(callback: CallbackQuery, *args, **kwargs):
        action = callback.data or "Unknown"
        
        try:
            # Callback başlangıç logu
            await _command_logger.log_callback_execution(callback, action, success=True)
            
            # Fonksiyonu çalıştır
            result = await func(callback, *args, **kwargs)
            
            # Başarılı sonuç logu
            await _command_logger.log_callback_execution(callback, action, success=True)
            
            return result
            
        except Exception as e:
            # Hata logu
            await _command_logger.log_callback_execution(callback, action, success=False, error=str(e))
            raise
            
    return wrapper

def log_admin(func):
    """Admin işlem log decorator'ı"""
    async def wrapper(message: Message, *args, **kwargs):
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        action = func.__name__
        
        try:
            # Admin işlem başlangıç logu
            await _command_logger.log_admin_action(user_id, username, action, success=True)
            
            # Fonksiyonu çalıştır
            result = await func(message, *args, **kwargs)
            
            # Başarılı sonuç logu
            await _command_logger.log_admin_action(user_id, username, action, success=True)
            
            return result
            
        except Exception as e:
            # Hata logu
            await _command_logger.log_admin_action(user_id, username, action, success=False, error=str(e))
            raise
            
    return wrapper 