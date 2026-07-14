"""
🛡️ Spam Koruması Sistemi - KirveHub Bot
Arka arkaya mesaj atanlara otomatik mute/ban uygular
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from aiogram import Router, Bot, types
from aiogram.types import Message, ChatPermissions
from aiogram.filters import Command

from database import get_db_pool
from config import get_config, is_owner
from utils.logger import logger
from handlers.punishment_system import mute_user, ban_user, log_punishment

router = Router()

# Bot instance
_bot_instance: Optional[Bot] = None

def set_bot_instance(bot_instance: Bot):
    """Bot instance'ını set et"""
    global _bot_instance
    _bot_instance = bot_instance

# ==============================================
# SPAM DETECTION CONFIGURATION
# ==============================================

# Spam tespiti için ayarlar
SPAM_CONFIG = {
    "max_messages_per_minute": 10,  # Dakikada maksimum mesaj sayısı
    "max_messages_per_5_minutes": 30,  # 5 dakikada maksimum mesaj sayısı
    "max_messages_per_10_minutes": 50,  # 10 dakikada maksimum mesaj sayısı
    "warning_threshold": 5,  # Uyarı için mesaj sayısı
    "mute_duration_minutes": 5,  # İlk spam için mute süresi (dakika)
    "ban_after_warnings": 3,  # Kaç uyarıdan sonra ban
    "cooldown_seconds": 2,  # Mesajlar arası minimum süre (saniye)
    "exclude_admins": True,  # Adminleri hariç tut
    "exclude_mods": True,  # Modları hariç tut
}

# Kullanıcı mesaj geçmişi (RAM'de tutulur)
# Format: {group_id: {user_id: [message_timestamps]}}
user_message_history: Dict[int, Dict[int, List[datetime]]] = defaultdict(lambda: defaultdict(list))

# Spam uyarı sayısı (RAM'de tutulur)
# Format: {group_id: {user_id: warning_count}}
spam_warnings: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

# ==============================================
# HELPER FUNCTIONS
# ==============================================

async def is_admin_or_mod(user_id: int, group_id: int) -> bool:
    """Kullanıcının admin veya mod olup olmadığını kontrol et"""
    try:
        from handlers.admin_permission_manager import get_user_admin_info_db
        from handlers.mod_handler import is_moderator
        from config import is_admin
        
        # Admin kontrolü (config'den)
        if is_admin(user_id):
            return True
        
        # Admin kontrolü (database'den - async)
        admin_info = await get_user_admin_info_db(user_id)
        if admin_info and admin_info.get('rank', 0) >= 1:
            return True
        
        # Mod kontrolü (async)
        if await is_moderator(user_id):
            return True
        
        return False
    except Exception as e:
        logger.debug(f"⚠️ is_admin_or_mod hatası: {e}")
        return False

def cleanup_old_messages(group_id: int, user_id: int, minutes: int = 10):
    """Eski mesaj kayıtlarını temizle"""
    if group_id not in user_message_history:
        return
    
    if user_id not in user_message_history[group_id]:
        return
    
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    user_message_history[group_id][user_id] = [
        msg_time for msg_time in user_message_history[group_id][user_id]
        if msg_time > cutoff_time
    ]

def count_messages_in_window(group_id: int, user_id: int, minutes: int) -> int:
    """Belirli bir zaman penceresindeki mesaj sayısını say"""
    cleanup_old_messages(group_id, user_id, minutes + 5)
    
    if group_id not in user_message_history:
        return 0
    
    if user_id not in user_message_history[group_id]:
        return 0
    
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    messages = [
        msg_time for msg_time in user_message_history[group_id][user_id]
        if msg_time > cutoff_time
    ]
    
    return len(messages)

def check_message_cooldown(group_id: int, user_id: int) -> bool:
    """Mesajlar arası cooldown kontrolü"""
    if group_id not in user_message_history:
        return True
    
    if user_id not in user_message_history[group_id]:
        return True
    
    messages = user_message_history[group_id][user_id]
    if not messages:
        return True
    
    last_message_time = messages[-1]
    time_diff = (datetime.now() - last_message_time).total_seconds()
    
    return time_diff >= SPAM_CONFIG["cooldown_seconds"]

# ==============================================
# SPAM DETECTION
# ==============================================

async def detect_spam(message: Message) -> tuple[bool, str, int]:
    """
    Spam tespiti yap
    
    Returns:
        (is_spam, reason, severity)
        severity: 1 = warning, 2 = mute, 3 = ban
    """
    try:
        user_id = message.from_user.id
        group_id = message.chat.id
        message_time = datetime.now()
        
        # Admin/Mod kontrolü (async)
        if SPAM_CONFIG["exclude_admins"] and await is_admin_or_mod(user_id, group_id):
            return (False, "", 0)
        
        # Mesaj geçmişine ekle
        user_message_history[group_id][user_id].append(message_time)
        
        # Eski mesajları temizle
        cleanup_old_messages(group_id, user_id, 10)
        
        # Cooldown kontrolü
        if not check_message_cooldown(group_id, user_id):
            return (True, "Mesajlar arası süre çok kısa (spam)", 2)
        
        # 1 dakika içindeki mesaj sayısı
        messages_1min = count_messages_in_window(group_id, user_id, 1)
        if messages_1min > SPAM_CONFIG["max_messages_per_minute"]:
            return (True, f"Dakikada {messages_1min} mesaj (limit: {SPAM_CONFIG['max_messages_per_minute']})", 2)
        
        # 5 dakika içindeki mesaj sayısı
        messages_5min = count_messages_in_window(group_id, user_id, 5)
        if messages_5min > SPAM_CONFIG["max_messages_per_5_minutes"]:
            return (True, f"5 dakikada {messages_5min} mesaj (limit: {SPAM_CONFIG['max_messages_per_5_minutes']})", 2)
        
        # 10 dakika içindeki mesaj sayısı
        messages_10min = count_messages_in_window(group_id, user_id, 10)
        if messages_10min > SPAM_CONFIG["max_messages_per_10_minutes"]:
            return (True, f"10 dakikada {messages_10min} mesaj (limit: {SPAM_CONFIG['max_messages_per_10_minutes']})", 2)
        
        # Uyarı eşiği kontrolü
        if messages_1min >= SPAM_CONFIG["warning_threshold"]:
            return (True, f"Dakikada {messages_1min} mesaj (uyarı eşiği)", 1)
        
        return (False, "", 0)
        
    except Exception as e:
        logger.error(f"❌ Spam detection hatası: {e}")
        return (False, "", 0)

# ==============================================
# SPAM PUNISHMENT
# ==============================================

async def handle_spam(message: Message, reason: str, severity: int):
    """Spam tespit edildiğinde ceza uygula"""
    try:
        user_id = message.from_user.id
        group_id = message.chat.id
        chat_id = message.chat.id
        
        # Sadece owner mute/ban yapabilir (güvenlik)
        config = get_config()
        owner_id = config.OWNER_ID  # OWNER_USER_ID değil, OWNER_ID
        
        # Owner kontrolü (spam punishment için owner gerekli)
        # Not: Bu kontrolü punishment_system.py'de yapıyoruz, burada sadece owner_id'yi geçiyoruz
        
        if severity == 1:
            # Uyarı
            warning_count = spam_warnings[group_id][user_id] + 1
            spam_warnings[group_id][user_id] = warning_count
            
            warning_msg = (
                f"⚠️ **SPAM UYARISI**\n\n"
                f"👤 **Kullanıcı:** {message.from_user.first_name}\n"
                f"📊 **Sebep:** {reason}\n"
                f"🔢 **Uyarı Sayısı:** {warning_count}/{SPAM_CONFIG['ban_after_warnings']}\n\n"
                f"💡 Lütfen mesaj gönderme hızınızı düşürün!"
            )
            
            await message.reply(warning_msg, parse_mode="Markdown")
            logger.info(f"⚠️ Spam uyarısı - User: {user_id}, Group: {group_id}, Count: {warning_count}")
            
        elif severity == 2:
            # Mute
            mute_duration = SPAM_CONFIG["mute_duration_minutes"]
            
            # Mute uygula (sadece owner)
            success = await mute_user(_bot_instance, chat_id, user_id, mute_duration, owner_id)
            
            if success:
                mute_msg = (
                    f"🔇 **SPAM MUTE**\n\n"
                    f"👤 **Kullanıcı:** {message.from_user.first_name}\n"
                    f"📊 **Sebep:** {reason}\n"
                    f"⏰ **Süre:** {mute_duration} dakika\n\n"
                    f"💡 Spam yapmayın! Mesaj gönderme hızınızı düşürün."
                )
                
                await message.reply(mute_msg, parse_mode="Markdown")
                
                # Log
                await log_punishment(user_id, group_id, "mute", mute_duration, owner_id, f"Spam: {reason}")
                
                logger.warning(f"🔇 Spam mute - User: {user_id}, Group: {group_id}, Duration: {mute_duration}min")
            else:
                logger.error(f"❌ Spam mute başarısız - User: {user_id}, Group: {group_id}")
            
        elif severity == 3:
            # Ban
            success = await ban_user(_bot_instance, chat_id, user_id, owner_id)
            
            if success:
                ban_msg = (
                    f"🚫 **SPAM BAN**\n\n"
                    f"👤 **Kullanıcı:** {message.from_user.first_name}\n"
                    f"📊 **Sebep:** {reason}\n"
                    f"🔢 **Uyarı Sayısı:** {spam_warnings[group_id][user_id]}/{SPAM_CONFIG['ban_after_warnings']}\n\n"
                    f"💡 Spam yapmak yasaktır!"
                )
                
                await message.reply(ban_msg, parse_mode="Markdown")
                
                # Log
                await log_punishment(user_id, group_id, "ban", None, owner_id, f"Spam: {reason}")
                
                logger.warning(f"🚫 Spam ban - User: {user_id}, Group: {group_id}")
            else:
                logger.error(f"❌ Spam ban başarısız - User: {user_id}, Group: {group_id}")
        
        # Uyarı sayısı ban eşiğine ulaştıysa ban uygula
        if spam_warnings[group_id][user_id] >= SPAM_CONFIG["ban_after_warnings"]:
            success = await ban_user(_bot_instance, chat_id, user_id, owner_id)
            if success:
                await log_punishment(user_id, group_id, "ban", None, owner_id, f"Spam: {spam_warnings[group_id][user_id]} uyarı")
                logger.warning(f"🚫 Spam ban (uyarı limiti) - User: {user_id}, Group: {group_id}")
        
    except Exception as e:
        logger.error(f"❌ Spam punishment hatası: {e}")

# ==============================================
# MESSAGE HANDLER
# ==============================================

@router.message()
async def spam_protection_handler(message: Message):
    """Tüm grup mesajlarını spam kontrolünden geçir"""
    try:
        # Sadece grup mesajlarında çalış
        if message.chat.type not in ["group", "supergroup"]:
            return
        
        # Bot mesajlarını atla
        if message.from_user.is_bot:
            return
        
        # Spam tespiti
        is_spam, reason, severity = await detect_spam(message)
        
        if is_spam:
            # Spam tespit edildi, ceza uygula
            await handle_spam(message, reason, severity)
            
            # Spam mesajını sil
            try:
                await message.delete()
            except:
                pass
        
    except Exception as e:
        logger.error(f"❌ Spam protection handler hatası: {e}")

# ==============================================
# ADMIN COMMANDS
# ==============================================

@router.message(Command("spamayarlar"))
async def spam_settings_command(message: Message):
    """Spam koruma ayarlarını göster"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        from config import is_admin
        if not is_admin(user_id):
            return
        
        # Grup kontrolü
        if message.chat.type not in ["group", "supergroup"]:
            await message.reply("❌ Bu komut sadece grup chatinde kullanılabilir!")
            return
        
        settings_msg = f"""
🛡️ **SPAM KORUMA AYARLARI**

📊 **Mevcut Ayarlar:**
• Dakikada maksimum mesaj: {SPAM_CONFIG['max_messages_per_minute']}
• 5 dakikada maksimum mesaj: {SPAM_CONFIG['max_messages_per_5_minutes']}
• 10 dakikada maksimum mesaj: {SPAM_CONFIG['max_messages_per_10_minutes']}
• Uyarı eşiği: {SPAM_CONFIG['warning_threshold']} mesaj/dakika
• Mute süresi: {SPAM_CONFIG['mute_duration_minutes']} dakika
• Ban eşiği: {SPAM_CONFIG['ban_after_warnings']} uyarı
• Mesajlar arası cooldown: {SPAM_CONFIG['cooldown_seconds']} saniye

🔒 **Koruma:**
• Adminler hariç: {'✅' if SPAM_CONFIG['exclude_admins'] else '❌'}
• Modlar hariç: {'✅' if SPAM_CONFIG['exclude_mods'] else '❌'}

💡 **Not:** Ayarları değiştirmek için kod düzenlemesi gerekir.
        """
        
        await message.reply(settings_msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Spam settings command hatası: {e}")

@router.message(Command("spamistatistik"))
async def spam_stats_command(message: Message):
    """Spam istatistiklerini göster"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        from config import is_admin
        if not is_admin(user_id):
            return
        
        # Grup kontrolü
        if message.chat.type not in ["group", "supergroup"]:
            await message.reply("❌ Bu komut sadece grup chatinde kullanılabilir!")
            return
        
        group_id = message.chat.id
        
        # İstatistikleri topla
        total_users = len(user_message_history.get(group_id, {}))
        total_warnings = sum(spam_warnings.get(group_id, {}).values())
        
        stats_msg = f"""
📊 **SPAM İSTATİSTİKLERİ**

👥 **Aktif Kullanıcılar:** {total_users}
⚠️ **Toplam Uyarı:** {total_warnings}

💡 **Not:** İstatistikler RAM'de tutulur, bot yeniden başlatıldığında sıfırlanır.
        """
        
        await message.reply(stats_msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Spam stats command hatası: {e}")

