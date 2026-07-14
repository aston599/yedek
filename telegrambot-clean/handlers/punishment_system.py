"""
⚖️ Cezalandırma Sistemi - KirveHub Bot
Moderator'lar için uyarı, mute ve ban sistemi
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from aiogram import Router, F, Bot
from aiogram.types import Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from database import get_db_pool, get_user_rank as db_get_user_rank, has_permission as db_has_permission
from utils.logger import logger
from handlers.admin_permission_manager import get_user_admin_info_db, has_min_rank_db
from config import is_admin, get_config, is_owner

router = Router()

# Bot instance
_bot_instance: Optional[Bot] = None

# Kötü niyetli kullanıcı tespiti için rate limiting
# Format: {user_id: [datetime1, datetime2, ...]}
_ban_actions: Dict[int, List[datetime]] = {}
_mute_actions: Dict[int, List[datetime]] = {}
_warn_actions: Dict[int, List[datetime]] = {}

# Kötü niyetli kullanıcılar (işaretlenmiş)
_malicious_users: set = set()

def set_bot_instance(bot_instance: Bot):
    """Bot instance'ını set et"""
    global _bot_instance
    _bot_instance = bot_instance

# =============================
# YETKİ KONTROLÜ
# =============================

async def is_moderator(user_id: int) -> bool:
    """Kullanıcı mod mu kontrol et (lazy import to avoid circular dependency)"""
    try:
        from handlers.mod_handler import get_moderators_from_db
        moderators = await get_moderators_from_db()
        return any(mod['user_id'] == user_id for mod in moderators)
    except Exception as e:
        logger.error(f"❌ Mod kontrolü hatası: {e}")
        return False

async def get_user_rank(user_id: int) -> int:
    """Kullanıcının rank'ını getir (mod kontrolü dahil)"""
    try:
        # Database'den rank al
        rank_info = await db_get_user_rank(user_id)
        base_rank = rank_info.get("rank_id", 1) if rank_info else 1
        
        # Mod kontrolü - Mod eklenen kişiler giriş seviyesinde yetkili (rank 2)
        if await is_moderator(user_id):
            # Eğer admin değilse ve rank 1 ise, mod olduğu için 2 döndür
            if not is_admin(user_id) and base_rank == 1:
                return 2
            # Hem mod hem admin ise, admin rank'ını döndür
            return base_rank
        
        # Mod değilse, normal rank döndür
        return base_rank
        
    except Exception as e:
        logger.error(f"❌ Get user rank hatası: {e}")
        return 1

async def has_permission(user_id: int, permission_type: str) -> bool:
    """Kullanıcının belirli bir yetkiye sahip olup olmadığını kontrol et (mod kontrolü dahil)"""
    try:
        # Admin kontrolü
        if is_admin(user_id):
            return True
        
        # Mod kontrolü - Mod eklenen kişiler giriş seviyesinde yetkili
        if await is_moderator(user_id):
            # Mod, "admin" yetkisi yok ama "mod" yetkisi var
            if permission_type == "admin":
                return False
            elif permission_type == "mod":
                return True
            # Diğer yetkiler için database kontrolü
            return await db_has_permission(user_id, permission_type)
        
        # Normal kullanıcı - database kontrolü
        return await db_has_permission(user_id, permission_type)
        
    except Exception as e:
        logger.error(f"❌ Has permission hatası: {e}")
        return False

async def can_punish_user(punisher_id: int, target_id: int = 0) -> bool:
    """Kullanıcı cezalandırma yetkisine sahip mi?"""
    try:
        # Admin kontrolü
        if await has_permission(punisher_id, "admin"):
            return True
        
        # Mod kontrolü
        if await is_moderator(punisher_id):
            # Eğer target_id 0 ise (henüz belirlenmedi), mod yetkisi yeterli
            if target_id == 0:
                return True
            
            # Mod, admin olmayan kullanıcıları cezalandırabilir
            target_rank = await get_user_rank(target_id)
            punisher_rank = await get_user_rank(punisher_id)
            
            # Mod, kendisinden düşük rank'taki kullanıcıları cezalandırabilir
            if target_rank < punisher_rank:
                return True
            
            # Mod, mod olmayan kullanıcıları cezalandırabilir
            if not await is_moderator(target_id):
                return True
            
            # Mod, admin olmayan modları cezalandırabilir
            if await is_moderator(target_id) and not await has_permission(target_id, "admin"):
                # Mod, diğer modları cezalandıramaz (sadece adminler yapabilir)
                return False
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Cezalandırma yetkisi kontrolü hatası: {e}")
        return False

# =============================
# DATABASE FONKSİYONLARI
# =============================

async def get_user_warnings(user_id: int, group_id: int) -> int:
    """Kullanıcının grup içindeki uyarı sayısını getir"""
    try:
        pool = await get_db_pool()
        if not pool:
            return 0
        
        async with pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM warnings 
                WHERE user_id = $1 AND group_id = $2 AND is_active = TRUE
            """, user_id, group_id)
            
            return result or 0
            
    except Exception as e:
        logger.error(f"❌ Uyarı sayısı getirme hatası: {e}")
        return 0

async def add_warning(user_id: int, group_id: int, warned_by: int, reason: str = None) -> Dict:
    """Kullanıcıya uyarı ekle"""
    try:
        pool = await get_db_pool()
        if not pool:
            return {"success": False, "error": "Database bağlantısı yok"}
        
        async with pool.acquire() as conn:
            # Uyarı ekle
            await conn.execute("""
                INSERT INTO warnings (user_id, group_id, warned_by, reason, warning_number, created_at)
                VALUES ($1, $2, $3, $4, 
                    (SELECT COALESCE(MAX(warning_number), 0) + 1 
                     FROM warnings 
                     WHERE user_id = $1 AND group_id = $2), 
                    NOW())
            """, user_id, group_id, warned_by, reason)
            
            # Toplam uyarı sayısını al
            warning_count = await get_user_warnings(user_id, group_id)
            
            logger.info(f"⚠️ Uyarı eklendi - User: {user_id}, Group: {group_id}, Count: {warning_count}")
            
            return {
                "success": True,
                "warning_count": warning_count,
                "user_id": user_id,
                "group_id": group_id
            }
            
    except Exception as e:
        logger.error(f"❌ Uyarı ekleme hatası: {e}")
        return {"success": False, "error": str(e)}

async def reset_warnings(user_id: int, group_id: int) -> bool:
    """Kullanıcının uyarılarını sıfırla"""
    try:
        pool = await get_db_pool()
        if not pool:
            return False
        
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE warnings 
                SET is_active = FALSE 
                WHERE user_id = $1 AND group_id = $2 AND is_active = TRUE
            """, user_id, group_id)
            
            logger.info(f"🔄 Uyarılar sıfırlandı - User: {user_id}, Group: {group_id}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Uyarı sıfırlama hatası: {e}")
        return False

async def handle_malicious_user(bot: Bot, user_id: int, chat_id: int, reason: str):
    """Kötü niyetli kullanıcıyı işaretle ve cezalandır"""
    try:
        # Zaten işaretlenmişse tekrar işlem yapma
        if user_id in _malicious_users:
            return
        
        _malicious_users.add(user_id)
        
        logger.warning(f"🚨 KÖTÜ NİYETLİ KULLANICI TESPİT EDİLDİ - User: {user_id}, Reason: {reason}")
        
        # 1. Mod yetkisini al (sadece mod ise)
        if await is_moderator(user_id):
            from handlers.mod_handler import remove_moderator_from_db
            await remove_moderator_from_db(user_id)
            logger.info(f"✅ Mod yetkisi alındı - User: {user_id}")
        
        # 2. Yazı yazmasını engelle (kalıcı mute)
        try:
            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
            
            # Kalıcı mute (until_date=None)
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=permissions
            )
            logger.info(f"🔇 Kötü niyetli kullanıcı susturuldu - User: {user_id}")
        except Exception as e:
            logger.error(f"❌ Mute hatası (kötü niyetli kullanıcı): {e}")
        
        # 3. Owner'a bildir
        try:
            config = get_config()
            admin_id = config.ADMIN_USER_ID if hasattr(config, 'ADMIN_USER_ID') else None
            
            if admin_id and bot:
                # Kullanıcı bilgilerini al
                pool = await get_db_pool()
                if pool:
                    async with pool.acquire() as conn:
                        user_info = await conn.fetchrow("""
                            SELECT first_name, username FROM users WHERE user_id = $1
                        """, user_id)
                        
                        user_name = user_info['first_name'] if user_info else 'Bilinmeyen'
                        user_username = user_info['username'] if user_info else 'Kullanıcı adı yok'
                        
                        admin_message = f"""
🚨 **KÖTÜ NİYETLİ KULLANICI TESPİT EDİLDİ!**

👤 **Kullanıcı:** {user_name} (@{user_username})
🆔 **ID:** `{user_id}`
📋 **Sebep:** {reason}
📅 **Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

🔧 **Yapılan İşlemler:**
✅ Mod yetkisi alındı
🔇 Yazı yazması engellendi (kalıcı mute)
📢 Owner'a bildirildi

⚠️ **Uyarı:** Bu kullanıcı arka arkaya çok hızlı ban/mute yapıyor!
                        """
                        
                        await bot.send_message(
                            admin_id,
                            admin_message,
                            parse_mode="Markdown"
                        )
                        logger.info(f"✅ Owner'a kötü niyetli kullanıcı bildirimi gönderildi - User: {user_id}")
        except Exception as e:
            logger.error(f"❌ Owner bildirimi hatası: {e}")
        
    except Exception as e:
        logger.error(f"❌ Kötü niyetli kullanıcı işleme hatası: {e}")

async def log_punishment(user_id: int, group_id: int, punishment_type: str, duration_minutes: int, punished_by: int, reason: str = None):
    """Cezalandırma kaydı oluştur"""
    try:
        pool = await get_db_pool()
        if not pool:
            return
        
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO punishment_logs (user_id, group_id, punishment_type, duration_minutes, punished_by, reason, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
            """, user_id, group_id, punishment_type, duration_minutes, punished_by, reason)
            
            logger.info(f"📝 Cezalandırma kaydedildi - User: {user_id}, Type: {punishment_type}, Duration: {duration_minutes}min")
            
    except Exception as e:
        logger.error(f"❌ Cezalandırma kaydı hatası: {e}")

# =============================
# CEZALANDIRMA FONKSİYONLARI
# =============================

async def mute_user(bot: Bot, chat_id: int, user_id: int, duration_minutes: int, punisher_id: int) -> bool:
    """Kullanıcıyı mute et - OWNER veya MOD (rate limiting ile)"""
    try:
        # Kötü niyetli kullanıcı kontrolü
        if punisher_id in _malicious_users:
            logger.warning(f"🚨 Kötü niyetli kullanıcı mute yapmaya çalıştı - User: {punisher_id}")
            return False
        
        # GÜVENLİK: Owner veya mod mute işlemini yapabilir
        config = get_config()
        is_owner_user = is_owner(punisher_id)
        is_mod_user = await is_moderator(punisher_id)
        
        if not is_owner_user and not is_mod_user:
            logger.warning(f"🔒 Güvenlik: Mute işlemi reddedildi - Punisher: {punisher_id} (Owner veya Mod değil)")
            return False
        
        # Modlar için rate limiting kontrolü
        if is_mod_user and not is_owner_user:
            current_time = datetime.now()
            
            # Eski kayıtları temizle (1 dakikadan eski)
            if punisher_id in _mute_actions:
                _mute_actions[punisher_id] = [
                    dt for dt in _mute_actions[punisher_id]
                    if (current_time - dt).total_seconds() < 60
                ]
            else:
                _mute_actions[punisher_id] = []
            
            # Yeni mute işlemini ekle
            _mute_actions[punisher_id].append(current_time)
            
            # 1 dakikada 5'ten fazla mute yapıldıysa kötü niyetli olarak işaretle
            if len(_mute_actions[punisher_id]) > 5:
                await handle_malicious_user(bot, punisher_id, chat_id, "Arka arkaya çok hızlı mute yapıyor")
                return False
        
        # Mute süresini hesapla
        until_date = datetime.now() + timedelta(minutes=duration_minutes)
        
        # ChatPermissions ile tüm izinleri kapat
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=permissions,
            until_date=until_date
        )
        
        logger.info(f"🔇 Kullanıcı mute edildi - User: {user_id}, Duration: {duration_minutes}min, Owner: {punisher_id}")
        return True
        
    except TelegramBadRequest as e:
        logger.error(f"❌ Mute hatası (TelegramBadRequest): {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Mute hatası: {e}")
        return False

async def unmute_user(bot: Bot, chat_id: int, user_id: int, punisher_id: int) -> bool:
    """Kullanıcının mute'unu kaldır - OWNER veya MOD"""
    try:
        # Yetki kontrolü
        is_owner_user = is_owner(punisher_id)
        is_mod_user = await is_moderator(punisher_id)
        
        if not is_owner_user and not is_mod_user:
            logger.warning(f"🔒 Güvenlik: Unmute işlemi reddedildi - Punisher: {punisher_id} (Owner veya Mod değil)")
            return False
        
        # Tüm izinleri geri ver
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=permissions
        )
        
        logger.info(f"🔓 Kullanıcının mute'u kaldırıldı - User: {user_id}, By: {punisher_id}")
        return True
        
    except TelegramBadRequest as e:
        logger.error(f"❌ Unmute hatası (TelegramBadRequest): {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unmute hatası: {e}")
        return False

async def unban_user(bot: Bot, chat_id: int, user_id: int, punisher_id: int) -> bool:
    """Kullanıcının ban'ını kaldır - OWNER veya MOD"""
    try:
        # GÜVENLİK: Owner veya mod unban işlemini yapabilir
        config = get_config()
        is_owner_user = is_owner(punisher_id)
        is_mod_user = await is_moderator(punisher_id)
        
        if not is_owner_user and not is_mod_user:
            logger.warning(f"🔒 Güvenlik: Unban işlemi reddedildi - Punisher: {punisher_id} (Owner veya Mod değil)")
            return False
        
        # Unban işlemi
        await bot.unban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            only_if_banned=True  # Sadece banlıysa kaldır
        )
        
        logger.info(f"✅ Kullanıcı ban'ı kaldırıldı - User: {user_id}, Unbanner: {punisher_id}")
        return True
        
    except TelegramBadRequest as e:
        logger.error(f"❌ Unban hatası (TelegramBadRequest): {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unban hatası: {e}")
        return False

async def ban_user(bot: Bot, chat_id: int, user_id: int, punisher_id: int) -> bool:
    """Kullanıcıyı banla - OWNER veya MOD (rate limiting ile)"""
    try:
        # Kötü niyetli kullanıcı kontrolü
        if punisher_id in _malicious_users:
            logger.warning(f"🚨 Kötü niyetli kullanıcı ban yapmaya çalıştı - User: {punisher_id}")
            return False
        
        # GÜVENLİK: Owner veya mod ban işlemini yapabilir
        config = get_config()
        is_owner_user = is_owner(punisher_id)
        is_mod_user = await is_moderator(punisher_id)
        
        if not is_owner_user and not is_mod_user:
            logger.warning(f"🔒 Güvenlik: Ban işlemi reddedildi - Punisher: {punisher_id} (Owner veya Mod değil)")
            return False
        
        # Modlar için rate limiting kontrolü
        if is_mod_user and not is_owner_user:
            current_time = datetime.now()
            
            # Eski kayıtları temizle (1 dakikadan eski)
            if punisher_id in _ban_actions:
                _ban_actions[punisher_id] = [
                    dt for dt in _ban_actions[punisher_id]
                    if (current_time - dt).total_seconds() < 60
                ]
            else:
                _ban_actions[punisher_id] = []
            
            # Yeni ban işlemini ekle
            _ban_actions[punisher_id].append(current_time)
            
            # 1 dakikada 3'ten fazla ban yapıldıysa kötü niyetli olarak işaretle
            if len(_ban_actions[punisher_id]) > 3:
                await handle_malicious_user(bot, punisher_id, chat_id, "Arka arkaya çok hızlı ban yapıyor")
                return False
        
        # Owner için de rate limiting kontrolü (güvenlik için)
        current_time = datetime.now()
        
        # Eski kayıtları temizle (1 dakikadan eski)
        if punisher_id in _ban_actions:
            _ban_actions[punisher_id] = [
                dt for dt in _ban_actions[punisher_id]
                if (current_time - dt).total_seconds() < 60
            ]
        else:
            _ban_actions[punisher_id] = []
        
        # Yeni ban işlemini ekle
        _ban_actions[punisher_id].append(current_time)
        
        # 1 dakikada 3'ten fazla ban yapıldıysa kötü niyetli olarak işaretle (owner için de geçerli)
        if len(_ban_actions[punisher_id]) > 3:
            await handle_malicious_user(bot, punisher_id, chat_id, "Arka arkaya çok hızlı ban yapıyor")
            return False
        
        # Ban işlemi - revoke_messages=True ile tüm mesajlar silinir
        await bot.ban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            revoke_messages=True  # Tüm mesajları sil
        )
        
        logger.info(f"🚫 Kullanıcı banlandı - User: {user_id}, Owner: {punisher_id}")
        return True
        
    except TelegramBadRequest as e:
        logger.error(f"❌ Ban hatası (TelegramBadRequest): {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Ban hatası: {e}")
        return False

async def delete_user_recent_messages(bot: Bot, chat_id: int, user_id: int, reply_message_id: int = None, count: int = 10) -> int:
    """Kullanıcının son N mesajını sil"""
    try:
        deleted_count = 0
        
        logger.info(f"🗑️ Kullanıcının son {count} mesajı silinmeye çalışılıyor - User: {user_id}, Chat: {chat_id}")
        
        # 1. Reply mesajını sil (eğer varsa)
        if reply_message_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=reply_message_id)
                deleted_count += 1
                logger.info(f"✅ Reply mesajı silindi - Message ID: {reply_message_id}")
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                if "message to delete not found" not in str(e).lower():
                    logger.debug(f"⚠️ Reply mesajı silinemedi - ID: {reply_message_id}, Error: {e}")
        
        # 2. Son mesajları silmeye çalış (Telegram API sınırlaması nedeniyle sınırlı)
        # Not: Telegram Bot API'de kullanıcının mesajlarını arama özelliği yok
        # Bu yüzden sadece reply mesajını ve yakın mesajları silmeye çalışıyoruz
        
        # Son 50 mesajı kontrol et (API limiti)
        # Not: Bu yaklaşım ideal değil ama Telegram API sınırlamaları nedeniyle en iyi çözüm
        # Gerçek uygulamada, mesajları gerçek zamanlı olarak takip edip bir veritabanında saklamak gerekir
        
        # Şimdilik: Sadece reply mesajını sildik, diğer mesajlar için mesaj takip sistemi gerekli
        # Bu özellik tam çalışması için mesajları gerçek zamanlı olarak takip etmek gerekir
        
        if deleted_count > 0:
            logger.info(f"✅ {deleted_count} mesaj silindi - User: {user_id}, Chat: {chat_id}")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"❌ Mesaj silme hatası: {e}")
        return 0

async def send_group_warning_notification(bot: Bot, chat_id: int, target_user, warned_by, warning_count: int, reason: str = None, duration_text: str = ""):
    """Grupta uyarı bildirimi gönder"""
    try:
        # Genel topluluk mesajı
        community_message = f"""
⚠️ <b>UYARI VERİLDİ</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
📊 <b>Uyarı Sayısı:</b> {warning_count}/3
👮 <b>Moderatör:</b> {warned_by.first_name} {f'(@{warned_by.username})' if warned_by.username else ''}
💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}

{duration_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Topluluğumuzu Korumak İçin:</b>
• Herkes mesajlaşmalarına dikkat etsin
• Kurallara uygun davranın
• Saygılı olun

💡 <b>Uyarı Sistemi:</b>
• 1. uyarı: 5 dakika susturma
• 2. uyarı: 30 dakika susturma  
• 3. uyarı: Kalıcı ban

Lütfen kurallara uyun! 🙏
        """
        
        await bot.send_message(
            chat_id=chat_id,
            text=community_message,
            parse_mode="HTML"
        )
        
        logger.info(f"📢 Grup uyarı bildirimi gönderildi - Chat: {chat_id}, User: {target_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Grup uyarı bildirimi hatası: {e}")

async def send_punishment_notification(bot: Bot, user_id: int, warning_count: int, punishment_type: str, duration_minutes: int = None, reason: str = None):
    """Cezalandırma bildirimi gönder"""
    try:
        if punishment_type == "warning":
            if warning_count == 1:
                message = f"""
⚠️ <b>İLK UYARI</b>

Merhaba! Bir moderatör tarafından uyarı aldınız.

📊 <b>Uyarı Sayısı:</b> 1/3

🔇 <b>Sonuç:</b> 5 dakika susturma

💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Önemli:</b>
• 2. uyarıda 30 dakika susturma
• 3. uyarıda kalıcı ban

Lütfen kurallara uyun! 🙏
                """
            elif warning_count == 2:
                message = f"""
⚠️ <b>İKİNCİ UYARI</b>

İkinci uyarı aldınız!

📊 <b>Uyarı Sayısı:</b> 2/3

🔇 <b>Sonuç:</b> 30 dakika susturma

💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>Son Uyarı:</b>
Bir uyarı daha alırsanız kalıcı olarak banlanacaksınız!

Lütfen kurallara uyun! 🙏
                """
            else:
                message = f"""
⚠️ <b>UYARI</b>

Uyarı aldınız!

📊 <b>Uyarı Sayısı:</b> {warning_count}/3

💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}

Lütfen kurallara uyun! 🙏
                """
        elif punishment_type == "mute":
            message = f"""
🔇 <b>SUSTURMA</b>

Bir moderatör tarafından susturulduğunuz için mesaj gönderemiyorsunuz.

⏰ <b>Süre:</b> {duration_minutes} dakika

💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Süre dolduğunda tekrar mesaj gönderebileceksiniz.
                """
        elif punishment_type == "ban":
            message = f"""
🚫 <b>BAN</b>

Bir moderatör tarafından kalıcı olarak banlandınız.

💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Bu karar hakkında itiraz etmek için adminlerle iletişime geçebilirsiniz.
                """
        else:
            return
        
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="HTML"
        )
        
        logger.info(f"📬 Cezalandırma bildirimi gönderildi - User: {user_id}, Type: {punishment_type}")
        
    except Exception as e:
        # Kullanıcı bot ile konuşmaya izin vermemiş olabilir
        logger.warning(f"⚠️ Cezalandırma bildirimi gönderilemedi - User: {user_id}, Error: {e}")

# =============================
# KOMUTLAR
# =============================

@router.message(Command("uyarı", "warn"))
@router.message(F.text.startswith("!uyarı"))
@router.message(F.text.startswith("!uyari"))
async def warn_command(message: Message):
    """Uyarı komutu - !uyarı @kullanıcı [sebep] veya !uyarı (reply) [sebep]"""
    try:
        if not _bot_instance:
            return
        
        user = message.from_user
        chat = message.chat
        
        # Özel mesajda çalışıyorsa, grup bilgisi gerekli
        # Grup komutları özelde çalıştırıldığında chat bilgisi korunur
        # Ama eğer gerçekten özel mesajdaysa, kullanıcıdan grup seçmesini iste
        if chat.type == "private":
            # Özel mesajda uyarı komutu kullanılamaz (grup gerekli)
            await message.reply("""
⚠️ **Uyarı Komutu Grup Gerekli**

Bu komut sadece grup içinde kullanılabilir.

💡 **Kullanım:**
1. Gruba gidin
2. Uyarı vermek istediğiniz kullanıcının mesajına yanıt verin
3. `!uyarı [sebep]` yazın

📋 **Örnek:**
```
!uyarı Spam yapıyor
```
            """, parse_mode="Markdown")
            return
        
        # Sadece grup/supergroup'da çalış
        if chat.type not in ["group", "supergroup"]:
            return
        
        # Yetki kontrolü
        if not await can_punish_user(user.id, 0):  # 0 = henüz hedef belirlenmedi
            await message.reply("❌ Bu komutu kullanmak için mod veya admin yetkisine sahip olmalısınız!")
            return
        
        # Hedef kullanıcıyı belirle
        target_user = None
        reason = None
        
        # Reply kontrolü - ÖNCE REPLY KONTROL ET
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user = message.reply_to_message.from_user
            # Sebep mesajdan al
            if message.text:
                parts = message.text.split(None, 1)
                if len(parts) > 1:
                    reason = parts[1]
        else:
            # Mention veya text mention kontrolü
            if message.entities:
                for entity in message.entities:
                    if entity.type == "mention":
                        username = message.text[entity.offset+1:entity.offset+entity.length]
                        # Username'den user_id bul (basit versiyon, gerçekte Telegram API'den alınmalı)
                        # Şimdilik reply kullanılmasını öner
                        await message.reply("⚠️ Lütfen uyarı vermek istediğiniz mesaja yanıt verin!")
                        return
                    elif entity.type == "text_mention":
                        target_user = entity.user
                        # Sebep mesajdan al
                        if message.text:
                            parts = message.text.split(None, 1)
                            if len(parts) > 1:
                                reason = parts[1]
                        break
        
        if not target_user:
            await message.reply("⚠️ Lütfen uyarı vermek istediğiniz mesaja yanıt verin veya kullanıcıyı etiketleyin!")
            return
        
        # Kendini uyaramaz
        if target_user.id == user.id:
            await message.reply("❌ Kendinize uyarı veremezsiniz!")
            return
        
        # Yetki kontrolü (hedef kullanıcı için)
        if not await can_punish_user(user.id, target_user.id):
            await message.reply("❌ Bu kullanıcıyı cezalandırma yetkiniz yok!")
            return
        
        # Kötü niyetli kullanıcı kontrolü
        if user.id in _malicious_users:
            await message.reply("🚨 Kötü niyetli kullanıcı olarak işaretlendiniz! Uyarı veremezsiniz.")
            return
        
        # Modlar için rate limiting kontrolü (uyarı için)
        if await is_moderator(user.id) and not is_owner(user.id):
            current_time = datetime.now()
            
            # Eski kayıtları temizle (1 dakikadan eski)
            if user.id in _warn_actions:
                _warn_actions[user.id] = [
                    dt for dt in _warn_actions[user.id]
                    if (current_time - dt).total_seconds() < 60
                ]
            else:
                _warn_actions[user.id] = []
            
            # Yeni uyarı işlemini ekle
            _warn_actions[user.id].append(current_time)
            
            # 1 dakikada 10'dan fazla uyarı yapıldıysa kötü niyetli olarak işaretle
            if len(_warn_actions[user.id]) > 10:
                await handle_malicious_user(_bot_instance, user.id, chat.id, "Arka arkaya çok hızlı uyarı veriyor")
                return
        
        # Uyarı ekle
        result = await add_warning(target_user.id, chat.id, user.id, reason)
        
        if not result.get("success"):
            await message.reply(f"❌ Uyarı eklenirken hata oluştu: {result.get('error', 'Bilinmeyen hata')}")
            return
        
        warning_count = result["warning_count"]
        
        # Uyarı sayısına göre işlem yap
        # YENİ: Modlar otomatik mute/ban yapabilir
        mute_success = False
        ban_success = False
        
        if warning_count == 1:
            # İlk uyarı: 5 dakika mute (modlar da yapabilir)
            if is_owner(user.id) or await is_moderator(user.id):
                mute_success = await mute_user(_bot_instance, chat.id, target_user.id, 5, user.id)
                if mute_success:
                    await log_punishment(target_user.id, chat.id, "mute", 5, user.id, reason)
                    await send_punishment_notification(_bot_instance, target_user.id, 1, "warning", 5, reason)
                
        elif warning_count == 2:
            # İkinci uyarı: 30 dakika mute (modlar da yapabilir)
            if is_owner(user.id) or await is_moderator(user.id):
                mute_success = await mute_user(_bot_instance, chat.id, target_user.id, 30, user.id)
                if mute_success:
                    await log_punishment(target_user.id, chat.id, "mute", 30, user.id, reason)
                    await send_punishment_notification(_bot_instance, target_user.id, 2, "warning", 30, reason)
                
        elif warning_count >= 3:
            # Üçüncü uyarı: Ban (modlar da yapabilir)
            if is_owner(user.id) or await is_moderator(user.id):
                ban_success = await ban_user(_bot_instance, chat.id, target_user.id, user.id)
                if ban_success:
                    await log_punishment(target_user.id, chat.id, "ban", 0, user.id, reason)
                    await send_punishment_notification(_bot_instance, target_user.id, 3, "ban", None, reason)
        
        # Duration text oluştur
        duration_text = ""
        
        if warning_count == 1:
            if mute_success:
                duration_text = "🔇 <b>Süre:</b> 5 dakika susturma ✅"
            else:
                duration_text = "🔇 <b>Süre:</b> 5 dakika susturma (uygulanamadı)"
        elif warning_count == 2:
            if mute_success:
                duration_text = "🔇 <b>Süre:</b> 30 dakika susturma ✅"
            else:
                duration_text = "🔇 <b>Süre:</b> 30 dakika susturma (uygulanamadı)"
        elif warning_count >= 3:
            if ban_success:
                duration_text = "🚫 <b>Sonuç:</b> Kalıcı ban ✅"
            else:
                duration_text = "🚫 <b>Sonuç:</b> Kalıcı ban (uygulanamadı)"
        
        # Grup bildirimi gönder (yeni format - topluluk mesajı)
        await send_group_warning_notification(
            _bot_instance,
            chat.id,
            target_user,
            user,
            warning_count,
            reason,
            duration_text
        )
        
        # Kullanıcının son 10 mesajını sil (reply mesajı dahil)
        reply_message_id = message.reply_to_message.message_id if message.reply_to_message else None
        deleted_count = await delete_user_recent_messages(_bot_instance, chat.id, target_user.id, reply_message_id, 10)
        if deleted_count > 0:
            logger.info(f"🗑️ {deleted_count} mesaj silindi - User: {target_user.id}, Chat: {chat.id}")
        
        # Komut mesajını sil
        try:
            await message.delete()
        except:
            pass
        
    except Exception as e:
        logger.error(f"❌ Uyarı komutu hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

@router.message(Command("uyarısıfırla", "resetwarn"))
async def reset_warnings_command(message: Message):
    """Uyarıları sıfırla komutu"""
    try:
        user = message.from_user
        chat = message.chat
        
        # Sadece grup/supergroup'da çalış
        if chat.type not in ["group", "supergroup"]:
            return
        
        # Yetki kontrolü
        if not await can_punish_user(user.id, 0):
            await message.reply("❌ Bu komutu kullanmak için mod veya admin yetkisine sahip olmalısınız!")
            return
        
        # Hedef kullanıcıyı belirle
        target_user = None
        
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
        else:
            await message.reply("⚠️ Lütfen uyarılarını sıfırlamak istediğiniz kullanıcının mesajına yanıt verin!")
            return
        
        # Uyarıları sıfırla
        success = await reset_warnings(target_user.id, chat.id)
        
        if success:
            await message.reply(f"""
✅ <b>Uyarılar Sıfırlandı</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
🔄 <b>Durum:</b> Tüm uyarılar sıfırlandı
👮 <b>Moderatör:</b> {user.first_name}
            """, parse_mode="HTML")
        else:
            await message.reply("❌ Uyarılar sıfırlanırken hata oluştu!")
        
    except Exception as e:
        logger.error(f"❌ Uyarı sıfırlama komutu hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

@router.message(Command("uyarılar", "warnings"))
async def warnings_command(message: Message):
    """Uyarıları görüntüle komutu"""
    try:
        chat = message.chat
        
        # Sadece grup/supergroup'da çalış
        if chat.type not in ["group", "supergroup"]:
            return
        
        # Hedef kullanıcıyı belirle
        target_user = None
        
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
        else:
            # Komutu kullanan kullanıcının uyarılarını göster
            target_user = message.from_user
        
        # Uyarı sayısını al
        warning_count = await get_user_warnings(target_user.id, chat.id)
        
        await message.reply(f"""
📊 <b>UYARI DURUMU</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
⚠️ <b>Uyarı Sayısı:</b> {warning_count}/3

{'🔇 1. uyarı: 5 dakika mute' if warning_count >= 1 else '✅ 1. uyarı henüz yok'}
{'🔇 2. uyarı: 30 dakika mute' if warning_count >= 2 else '✅ 2. uyarı henüz yok'}
{'🚫 3. uyarı: Kalıcı ban' if warning_count >= 3 else '✅ 3. uyarı henüz yok'}
        """, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"❌ Uyarı görüntüleme komutu hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

@router.message(Command("uyarıaşama", "warnstage"))
async def warn_stage_command(message: Message):
    """Manuel uyarı aşaması belirleme komutu - /uyarıaşama 2 [sebep] (reply ile)"""
    try:
        if not _bot_instance:
            return
        
        user = message.from_user
        chat = message.chat
        
        # Sadece grup/supergroup'da çalış
        if chat.type not in ["group", "supergroup"]:
            return
        
        # Yetki kontrolü - Sadece mod/admin
        if not await can_punish_user(user.id, 0):
            await message.reply("❌ Bu komutu kullanmak için mod veya admin yetkisine sahip olmalısınız!")
            return
        
        # Hedef kullanıcıyı belirle
        if not message.reply_to_message:
            await message.reply("⚠️ Lütfen uyarı aşaması belirlemek istediğiniz kullanıcının mesajına yanıt verin!")
            return
        
        target_user = message.reply_to_message.from_user
        
        # Komut parametrelerini al
        parts = message.text.split(None, 1)
        if len(parts) < 2:
            await message.reply("⚠️ Kullanım: `/uyarıaşama 2 [sebep]` (reply ile)\n• 1: İlk uyarı (5 dk mute)\n• 2: İkinci uyarı (30 dk mute)\n• 3: Üçüncü uyarı (ban)")
            return
        
        try:
            stage = int(parts[1].split()[0])
            reason = parts[1][len(parts[1].split()[0]):].strip() if len(parts[1].split()) > 1 else None
        except ValueError:
            await message.reply("⚠️ Kullanım: `/uyarıaşama 2 [sebep]` (reply ile)\n• 1: İlk uyarı (5 dk mute)\n• 2: İkinci uyarı (30 dk mute)\n• 3: Üçüncü uyarı (ban)")
            return
        
        if stage < 1 or stage > 3:
            await message.reply("⚠️ Aşama 1-3 arası olmalı!\n• 1: İlk uyarı (5 dk mute)\n• 2: İkinci uyarı (30 dk mute)\n• 3: Üçüncü uyarı (ban)")
            return
        
        # Mevcut uyarı sayısını al
        current_warnings = await get_user_warnings(target_user.id, chat.id)
        
        # Gerekli uyarı sayısına ulaşmak için uyarı ekle
        warnings_to_add = stage - current_warnings
        
        if warnings_to_add <= 0:
            await message.reply(f"⚠️ Kullanıcının zaten {current_warnings} uyarısı var. Aşama {stage} için yeterli.")
            return
        
        # Uyarıları ekle
        for _ in range(warnings_to_add):
            result = await add_warning(target_user.id, chat.id, user.id, reason)
            if not result.get("success"):
                await message.reply(f"❌ Uyarı eklenirken hata oluştu: {result.get('error', 'Bilinmeyen hata')}")
                return
        
        # Yeni uyarı sayısını al
        new_warning_count = await get_user_warnings(target_user.id, chat.id)
        
        # Uyarı sayısına göre işlem yap (sadece owner mute/ban yapabilir)
        if new_warning_count == 1:
            if is_owner(user.id):
                mute_success = await mute_user(_bot_instance, chat.id, target_user.id, 5, user.id)
                if mute_success:
                    await log_punishment(target_user.id, chat.id, "mute", 5, user.id, reason)
                    await send_punishment_notification(_bot_instance, target_user.id, 1, "warning", 5, reason)
        elif new_warning_count == 2:
            if is_owner(user.id):
                mute_success = await mute_user(_bot_instance, chat.id, target_user.id, 30, user.id)
                if mute_success:
                    await log_punishment(target_user.id, chat.id, "mute", 30, user.id, reason)
                    await send_punishment_notification(_bot_instance, target_user.id, 2, "warning", 30, reason)
        elif new_warning_count >= 3:
            if is_owner(user.id):
                ban_success = await ban_user(_bot_instance, chat.id, target_user.id, user.id)
                if ban_success:
                    await log_punishment(target_user.id, chat.id, "ban", 0, user.id, reason)
                    await send_punishment_notification(_bot_instance, target_user.id, 3, "ban", None, reason)
        
        await message.reply(f"""
✅ <b>UYARI AŞAMASI BELİRLENDİ</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
📊 <b>Yeni Uyarı Sayısı:</b> {new_warning_count}/3
👮 <b>Moderatör:</b> {user.first_name}
💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}
        """, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"❌ Uyarı aşama komutu hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

@router.message(Command("mute", "sustur"))
async def mute_command(message: Message):
    """Direkt mute komutu - /mute 30 [sebep] (reply ile) - SADECE OWNER"""
    try:
        if not _bot_instance:
            return
        
        user = message.from_user
        chat = message.chat
        
        # Sadece grup/supergroup'da çalış
        if chat.type not in ["group", "supergroup"]:
            return
        
        # GÜVENLİK: Owner veya mod mute yapabilir
        is_owner_user = is_owner(user.id)
        is_mod_user = await is_moderator(user.id)
        
        if not is_owner_user and not is_mod_user:
            await message.reply("❌ Bu komutu sadece bot sahibi veya mod kullanabilir!")
            return
        
        # Hedef kullanıcıyı belirle
        if not message.reply_to_message:
            await message.reply("⚠️ Lütfen susturmak istediğiniz kullanıcının mesajına yanıt verin!")
            return
        
        target_user = message.reply_to_message.from_user
        
        # Komut parametrelerini al
        parts = message.text.split(None, 1)
        duration_minutes = 5  # Varsayılan
        
        if len(parts) > 1:
            try:
                # İlk kelime süre olabilir
                first_word = parts[1].split()[0]
                duration_minutes = int(first_word)
                reason = parts[1][len(first_word):].strip() if len(parts[1]) > len(first_word) else None
            except ValueError:
                reason = parts[1]
        else:
            reason = None
        
        # Mute işlemi
        mute_success = await mute_user(_bot_instance, chat.id, target_user.id, duration_minutes, user.id)
        
        if mute_success:
            await log_punishment(target_user.id, chat.id, "mute", duration_minutes, user.id, reason)
            await send_punishment_notification(_bot_instance, target_user.id, 0, "mute", duration_minutes, reason)
            
            await message.reply(f"""
🔇 <b>KULLANICI SUSTURULDU</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
⏰ <b>Süre:</b> {duration_minutes} dakika
💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}
👮 <b>Moderatör:</b> {user.first_name}
            """, parse_mode="HTML")
        else:
            await message.reply("❌ Susturma uygulanamadı! (Bot yetkisi gerekli veya güvenlik kontrolü başarısız)")
        
    except Exception as e:
        logger.error(f"❌ Mute komutu hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

@router.message(Command("ban", "yasakla"))
async def ban_command(message: Message):
    """Direkt ban komutu - /ban [sebep] (reply ile) - SADECE OWNER"""
    try:
        if not _bot_instance:
            return
        
        user = message.from_user
        chat = message.chat
        
        # Sadece grup/supergroup'da çalış
        if chat.type not in ["group", "supergroup"]:
            return
        
        # GÜVENLİK: Sadece owner ban yapabilir
        if not is_owner(user.id):
            await message.reply("❌ Bu komutu sadece bot sahibi kullanabilir!")
            return
        
        # Hedef kullanıcıyı belirle
        if not message.reply_to_message:
            await message.reply("⚠️ Lütfen banlamak istediğiniz kullanıcının mesajına yanıt verin!")
            return
        
        target_user = message.reply_to_message.from_user
        
        # Sebep al
        parts = message.text.split(None, 1)
        reason = parts[1] if len(parts) > 1 else None
        
        # Ban işlemi
        ban_success = await ban_user(_bot_instance, chat.id, target_user.id, user.id)
        
        if ban_success:
            await log_punishment(target_user.id, chat.id, "ban", 0, user.id, reason)
            await send_punishment_notification(_bot_instance, target_user.id, 0, "ban", None, reason)
            
            await message.reply(f"""
🚫 <b>KULLANICI BANLANDI</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
🚫 <b>Sonuç:</b> Kalıcı ban
💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}
👮 <b>Moderatör:</b> {user.first_name}
            """, parse_mode="HTML")
        else:
            await message.reply("❌ Ban uygulanamadı! (Bot yetkisi gerekli veya güvenlik kontrolü başarısız)")
        
    except Exception as e:
        logger.error(f"❌ Ban komutu hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

