"""
🛡️ Mod Sistemi - KirveHub Bot
Manuel mod yönetimi: ekleme, listeleme, silme
"""

import logging
import time
import asyncio
import re
import secrets
import string
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from database import get_db_pool
from utils.logger import logger
from config import is_admin
from aiogram import Bot
from aiogram.types import ChatPermissions
from aiogram.exceptions import TelegramBadRequest

router = Router()

# Bot instance
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance


# Spam engelleme için cooldown
_mod_command_cooldowns = {}  # {user_id: last_command_time}
_mod_group_cooldowns = {}  # {group_id: last_command_time} - Grup bazlı cooldown (flame koruması)
_MOD_COMMAND_COOLDOWN = 180  # 3 dakika cooldown (180 saniye) - Genel kullanım için
_MOD_GROUP_COOLDOWN = 180  # 3 dakika grup bazlı cooldown (180 saniye) - Flame koruması

# Mod aktivite takibi - Modların son mesaj zamanlarını takip et
# {group_id: {mod_user_id: last_message_time}}
mod_activity_by_group: Dict[int, Dict[int, datetime]] = {}

# Mod bildirim cooldown - Aynı grup için bildirim gönderme cooldown'u
# {group_id: last_notification_time}
mod_notification_cooldown: Dict[int, datetime] = {}

# Mod aktivite kontrolü ayarları
MOD_ACTIVITY_CHECK_INTERVAL = 600  # 10 dakikada bir kontrol et (spam önleme)
ACTIVE_CHAT_THRESHOLD_MINUTES = 15  # Son 15 dakikada mesaj varsa aktif sohbet sayılır
MOD_INACTIVE_THRESHOLD_MINUTES = 10  # Mod 10 dakikadır yazmamışsa bildirim gönder
MOD_NOTIFICATION_COOLDOWN_MINUTES = 30  # Aynı grup için 30 dakikada bir bildirim (spam önleme)
MIN_MESSAGES_FOR_NOTIFICATION = 3  # Bildirim için minimum mesaj sayısı (son 15 dakikada)


async def check_mod_command_cooldown(user_id: int) -> tuple[bool, int]:
    """Mod komutu cooldown kontrolü - Spam engelleme (kullanıcı bazlı)"""
    current_time = time.time()
    
    if user_id in _mod_command_cooldowns:
        last_time = _mod_command_cooldowns[user_id]
        time_passed = current_time - last_time
        
        if time_passed < _MOD_COMMAND_COOLDOWN:
            remaining = int(_MOD_COMMAND_COOLDOWN - time_passed)
            return False, remaining
    
    # Cooldown yok, kaydet
    _mod_command_cooldowns[user_id] = current_time
    return True, 0


async def check_mod_group_cooldown(group_id: int) -> tuple[bool, int]:
    """Mod komutu grup bazlı cooldown kontrolü - Flame koruması"""
    current_time = time.time()
    
    # Eski cooldown kayıtlarını temizle (bellek tasarrufu)
    if len(_mod_group_cooldowns) > 1000:  # 1000'den fazla grup varsa temizle
        await cleanup_old_cooldowns()
    
    if group_id in _mod_group_cooldowns:
        last_time = _mod_group_cooldowns[group_id]
        time_passed = current_time - last_time
        
        if time_passed < _MOD_GROUP_COOLDOWN:
            remaining = int(_MOD_GROUP_COOLDOWN - time_passed)
            return False, remaining
    
    # Cooldown yok, kaydet
    _mod_group_cooldowns[group_id] = current_time
    return True, 0


async def cleanup_old_cooldowns():
    """Eski cooldown kayıtlarını temizle (bellek tasarrufu)"""
    try:
        current_time = time.time()
        # 10 dakikadan eski cooldown kayıtlarını sil
        cutoff_time = current_time - 600  # 10 dakika
        
        # Kullanıcı bazlı cooldown temizleme
        old_users = [
            user_id for user_id, last_time in _mod_command_cooldowns.items()
            if last_time < cutoff_time
        ]
        for user_id in old_users:
            _mod_command_cooldowns.pop(user_id, None)
        
        # Grup bazlı cooldown temizleme
        old_groups = [
            group_id for group_id, last_time in _mod_group_cooldowns.items()
            if last_time < cutoff_time
        ]
        for group_id in old_groups:
            _mod_group_cooldowns.pop(group_id, None)
        
        if old_users or old_groups:
            logger.debug(f"🧹 Eski cooldown kayıtları temizlendi - Users: {len(old_users)}, Groups: {len(old_groups)}")
    except Exception as e:
        logger.debug(f"⏸️ Cooldown temizleme hatası (kritik değil): {e}")


async def is_moderator(user_id: int, include_inactive: bool = False) -> bool:
    """Kullanıcı mod mu kontrol et (varsayılan: sadece aktif modlar)"""
    try:
        moderators = await get_moderators_from_db(include_inactive=include_inactive)
        return any(mod['user_id'] == user_id for mod in moderators)
    except Exception as e:
        logger.error(f"❌ Mod kontrolü hatası: {e}")
        return False

async def get_moderators_from_db(include_inactive: bool = False) -> List[Dict]:
    """Database'den modları getir (varsayılan: sadece aktif modlar)"""
    try:
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool bulunamadı!")
            return []
        
        async with pool.acquire() as conn:
            if include_inactive:
                # Tüm modları getir (aktif + pasif)
                rows = await conn.fetch("""
                    SELECT m.id, m.user_id, m.username, m.first_name, m.last_name, 
                           m.added_by, m.added_at, m.is_active, m.notes,
                           u.kirve_points
                    FROM moderators m
                    LEFT JOIN users u ON u.user_id = m.user_id
                    ORDER BY m.is_active DESC, m.added_at ASC
                """)
            else:
                # Sadece aktif modları getir
                rows = await conn.fetch("""
                    SELECT m.id, m.user_id, m.username, m.first_name, m.last_name, 
                           m.added_by, m.added_at, m.is_active, m.notes,
                           u.kirve_points
                    FROM moderators m
                    LEFT JOIN users u ON u.user_id = m.user_id
                    WHERE m.is_active = TRUE
                    ORDER BY m.added_at ASC
                """)
            
            moderators = []
            for row in rows:
                moderators.append({
                    "id": row['id'],
                    "user_id": row['user_id'],
                    "username": row['username'],
                    "first_name": row['first_name'],
                    "last_name": row['last_name'],
                    "added_by": row['added_by'],
                    "added_at": row['added_at'],
                    "is_active": row['is_active'],
                    "notes": row['notes'],
                    "kirve_points": float(row['kirve_points']) if row['kirve_points'] else 0.0
                })
            
            logger.info(f"✅ Database'den {len(moderators)} aktif mod getirildi")
            return moderators
            
    except Exception as e:
        logger.error(f"❌ Mod listesi getirme hatası: {e}", exc_info=True)
        return []


async def add_moderator_to_db(user_id: int, username: str, first_name: str, last_name: str, added_by: int, notes: str = None) -> bool:
    """Database'e mod ekle"""
    try:
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool bulunamadı!")
            return False
        
        async with pool.acquire() as conn:
            # Önce kullanıcıyı users tablosuna ekle (yoksa) - is_registered değerini koru
            # Mod eklenirken kullanıcı database'de yoksa bile eklenir, is_registered FALSE kalır
            await conn.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, is_registered, last_activity)
                VALUES ($1, $2, $3, $4, FALSE, NOW())
                ON CONFLICT (user_id) DO UPDATE
                SET username = COALESCE(EXCLUDED.username, users.username),
                    first_name = COALESCE(EXCLUDED.first_name, users.first_name),
                    last_name = COALESCE(EXCLUDED.last_name, users.last_name),
                    last_activity = NOW()
                    -- is_registered değeri korunur (UPDATE SET'te yok, bu yüzden mevcut değer korunur)
            """, user_id, username or None, first_name or None, last_name or None)
            
            logger.debug(f"💾 Kullanıcı users tablosuna eklendi/korundu - User: {user_id}, Username: {username}")
            
            # Mod ekle (varsa güncelle)
            await conn.execute("""
                INSERT INTO moderators (user_id, username, first_name, last_name, added_by, notes, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, TRUE)
                ON CONFLICT (user_id) DO UPDATE
                SET username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    is_active = TRUE,
                    notes = COALESCE(EXCLUDED.notes, moderators.notes)
            """, user_id, username, first_name, last_name, added_by, notes)
            
            logger.info(f"✅ Mod eklendi - User ID: {user_id}, Added by: {added_by}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Mod ekleme hatası: {e}", exc_info=True)
        return False


async def remove_moderator_from_db(user_id: int) -> bool:
    """Database'den mod sil (is_active = FALSE yap)"""
    try:
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool bulunamadı!")
            return False
        
        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE moderators
                SET is_active = FALSE
                WHERE user_id = $1 AND is_active = TRUE
            """, user_id)
            
            if result == "UPDATE 1":
                logger.info(f"✅ Mod silindi - User ID: {user_id}")
                return True
            else:
                logger.warning(f"⚠️ Mod bulunamadı veya zaten silinmiş - User ID: {user_id}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Mod silme hatası: {e}", exc_info=True)
        return False


async def get_user_info_from_telegram(user_id: int) -> Optional[Dict]:
    """Telegram'dan kullanıcı bilgilerini getir"""
    try:
        if not _bot_instance:
            return None
        
        # Kullanıcı bilgilerini al (chat member olarak)
        try:
            # Önce kendi chat'imizden deneyelim
            chat_member = await _bot_instance.get_chat_member(user_id, user_id)
            user = chat_member.user
            
            return {
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_bot": user.is_bot
            }
        except:
            # Direkt user bilgisi al
            try:
                user = await _bot_instance.get_chat(user_id)
                return {
                    "user_id": user.id,
                    "username": getattr(user, 'username', None),
                    "first_name": getattr(user, 'first_name', None),
                    "last_name": getattr(user, 'last_name', None),
                    "is_bot": getattr(user, 'is_bot', False)
                }
            except:
                return None
                
    except Exception as e:
        logger.error(f"❌ Telegram kullanıcı bilgisi getirme hatası: {e}")
        return None


# Handler sırası önemli: !modekle ve !modsil önce kontrol edilmeli
@router.message(F.text.startswith("!modekle"))
async def add_moderator_command(message: Message) -> None:
    """!modekle <telegram_id> veya !modekle @username veya !modekle (etiketle) - Mod ekle"""
    try:
        user_id = message.from_user.id
        chat_type = message.chat.type
        chat_id = message.chat.id
        
        # KRİTİK LOG - Handler'ın çalıştığını görmek için
        logger.info(f"🛡️ !modekle komutu ROUTER HANDLER'da yakalandı! - User: {user_id}, Chat: {chat_id}, Type: {chat_type}, Text: {message.text}")
        logger.info(f"🔍 DEBUG - Message object: {message}, Reply: {message.reply_to_message}, Entities: {message.entities}")
        
        # Admin kontrolü
        if not is_admin(user_id):
            logger.warning(f"⚠️ !modekle komutu admin olmayan kullanıcı tarafından kullanıldı - User: {user_id}")
            if chat_type == "private":
                await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
            return
        
        # Grupta ise mesajı sil
        if chat_type in ["group", "supergroup"]:
            try:
                await message.delete()
            except:
                pass
        
        # Komut parametresini al
        text = message.text.strip()
        
        # Değişkenleri başlat
        target_user_id = None
        target_username = None
        target_first_name = None
        target_last_name = None
        
        # Debug: Reply kontrolü
        logger.info(f"🔍 DEBUG - Reply kontrolü: reply_to_message={message.reply_to_message is not None}, from_user={message.reply_to_message.from_user if message.reply_to_message else None}")
        
        # 1. Reply kontrolü (bir mesaja cevap vererek) - ÖNCE BUNU KONTROL ET
        if message.reply_to_message:
            logger.info(f"🔍 DEBUG - Reply mesajı var, from_user kontrolü yapılıyor...")
            if message.reply_to_message.from_user:
                target_user = message.reply_to_message.from_user
                target_user_id = target_user.id
                target_username = getattr(target_user, 'username', None)
                target_first_name = getattr(target_user, 'first_name', None)
                target_last_name = getattr(target_user, 'last_name', None)
                logger.info(f"✅ Reply'dan kullanıcı bulundu: {target_user_id} (@{target_username})")
            else:
                logger.warning(f"⚠️ Reply mesajı var ama from_user yok!")
        else:
            logger.info(f"🔍 DEBUG - Reply mesajı yok, diğer yöntemler deneniyor...")
        # 2. Mention kontrolü (entities) - ÖNCE text_mention kontrol et (etiketleme için)
        if not target_user_id and message.entities:
            for entity in message.entities:
                # Text mention (etiketleme) - ÖNCE BUNU KONTROL ET
                if entity.type == "text_mention":
                    # Text mention varsa user_id al (etiketleme)
                    target_user_id = entity.user.id
                    target_username = entity.user.username
                    target_first_name = entity.user.first_name
                    target_last_name = entity.user.last_name
                    logger.info(f"✅ Text mention'dan kullanıcı bulundu: {target_user_id} (@{target_username})")
                    break
                # Mention (@username yazma)
                elif entity.type == "mention":
                    mention_text = message.text[entity.offset:entity.offset + entity.length]
                    target_username = mention_text[1:]  # @ işaretini kaldır
                    logger.info(f"🔍 Username mention bulundu: @{target_username}")
                    
                    # Database'den username ile kullanıcı bul
                    if target_username:
                        try:
                            pool = await get_db_pool()
                            if pool:
                                async with pool.acquire() as conn:
                                    user_row = await conn.fetchrow("""
                                        SELECT user_id, first_name, last_name, username
                                        FROM users
                                        WHERE username = $1
                                        LIMIT 1
                                    """, target_username)
                                    
                                    if user_row:
                                        target_user_id = user_row['user_id']
                                        target_first_name = user_row['first_name']
                                        target_last_name = user_row['last_name']
                                        logger.info(f"✅ Username'den kullanıcı bulundu: @{target_username} -> {target_user_id}")
                                        break
                                    else:
                                        logger.warning(f"⚠️ Username database'de bulunamadı: @{target_username}")
                        except Exception as e:
                            logger.error(f"❌ Username ile kullanıcı arama hatası: {e}")
                    
                    # Database'de bulunamadıysa kullanıcıya bilgi ver
                    if not target_user_id:
                        usage_msg = "⚠️ <b>Kullanıcı Bulunamadı</b>\n\n"
                        usage_msg += f"@{target_username} kullanıcısı database'de bulunamadı.\n\n"
                        usage_msg += "<b>Alternatif Yöntemler:</b>\n"
                        usage_msg += "• Kullanıcının Telegram ID'sini alın: <code>!modekle 123456789</code>\n"
                        usage_msg += "• Kullanıcıya bir mesaj gönderin ve o mesaja cevap vererek <code>!modekle</code> yazın\n"
                        usage_msg += "• Kullanıcıyı etiketleyerek <code>!modekle</code> yazın"
                        
                        try:
                            if chat_type == "private":
                                await message.reply(usage_msg, parse_mode="HTML")
                            elif _bot_instance:
                                await _bot_instance.send_message(user_id, usage_msg, parse_mode="HTML")
                        except:
                            pass
                        return
        # 3. Username ile ekleme (text'te @username formatı)
        if not target_user_id and '@' in text:
            # @username formatını kontrol et
            match_username = re.search(r'@(\w+)', text)
            if match_username:
                target_username = match_username.group(1)
                logger.info(f"🔍 Username text'te bulundu: @{target_username}")
                
                # Database'den username ile kullanıcı bul
                try:
                    pool = await get_db_pool()
                    if pool:
                        async with pool.acquire() as conn:
                            user_row = await conn.fetchrow("""
                                SELECT user_id, first_name, last_name, username
                                FROM users
                                WHERE username = $1
                                LIMIT 1
                            """, target_username)
                            
                            if user_row:
                                target_user_id = user_row['user_id']
                                target_first_name = user_row['first_name']
                                target_last_name = user_row['last_name']
                                logger.info(f"✅ Username'den kullanıcı bulundu: @{target_username} -> {target_user_id}")
                            else:
                                logger.warning(f"⚠️ Username database'de bulunamadı: @{target_username}")
                                usage_msg = "⚠️ <b>Kullanıcı Bulunamadı</b>\n\n"
                                usage_msg += f"@{target_username} kullanıcısı database'de bulunamadı.\n\n"
                                usage_msg += "<b>Alternatif Yöntemler:</b>\n"
                                usage_msg += "• Kullanıcının Telegram ID'sini alın: <code>!modekle 123456789</code>\n"
                                usage_msg += "• Kullanıcıya bir mesaj gönderin ve o mesaja cevap vererek <code>!modekle</code> yazın"
                                
                                try:
                                    if chat_type == "private":
                                        await message.reply(usage_msg, parse_mode="HTML")
                                    elif _bot_instance:
                                        await _bot_instance.send_message(user_id, usage_msg, parse_mode="HTML")
                                except:
                                    pass
                                return
                except Exception as e:
                    logger.error(f"❌ Username ile kullanıcı arama hatası: {e}")
                    usage_msg = "❌ <b>Hata:</b> Kullanıcı aranırken bir sorun oluştu.\n\n"
                    usage_msg += "Lütfen Telegram ID kullanın: <code>!modekle 123456789</code>"
                    try:
                        if chat_type == "private":
                            await message.reply(usage_msg, parse_mode="HTML")
                        elif _bot_instance:
                            await _bot_instance.send_message(user_id, usage_msg, parse_mode="HTML")
                    except:
                        pass
                    return
        # 4. ID ile ekleme
        if not target_user_id:
            match_id = re.match(r'^!modekle\s+(\d+)$', text, re.IGNORECASE)
            if match_id:
                target_user_id = int(match_id.group(1))
            else:
                # Kullanım bilgisi göster
                usage_msg = "❌ <b>Kullanım:</b>\n\n"
                usage_msg += "• <code>!modekle 123456789</code> (Telegram ID ile)\n"
                usage_msg += "• <code>!modekle @username</code> (Username ile - database'de olmalı)\n"
                usage_msg += "• Bir mesaja cevap vererek <code>!modekle</code> yazın\n"
                usage_msg += "• Birini etiketleyerek <code>!modekle</code> yazın"
                
                try:
                    if chat_type == "private":
                        await message.reply(usage_msg, parse_mode="HTML")
                    elif _bot_instance:
                        await _bot_instance.send_message(user_id, usage_msg, parse_mode="HTML")
                except:
                    pass
                return
        
        # Kullanıcı bilgilerini al
        user_info = None
        if target_user_id:
            logger.info(f"🔍 DEBUG - target_user_id bulundu: {target_user_id}, target_first_name: {target_first_name}")
            # Eğer reply'dan, mention'dan veya username'den geldiyse direkt kullan
            if target_first_name is not None:
                # is_bot kontrolü
                is_bot_user = False
                if message.reply_to_message and message.reply_to_message.from_user:
                    is_bot_user = getattr(message.reply_to_message.from_user, 'is_bot', False)
                elif message.entities:
                    for entity in message.entities:
                        if entity.type == "text_mention" and hasattr(entity, 'user'):
                            is_bot_user = getattr(entity.user, 'is_bot', False)
                            break
                
                user_info = {
                    "user_id": target_user_id,
                    "username": target_username,
                    "first_name": target_first_name,
                    "last_name": target_last_name,
                    "is_bot": is_bot_user
                }
                logger.info(f"✅ Kullanıcı bilgileri reply/mention'dan alındı: {user_info}")
            else:
                # Telegram'dan bilgi çek
                logger.info(f"🔍 DEBUG - Telegram'dan kullanıcı bilgisi çekiliyor: {target_user_id}")
                user_info = await get_user_info_from_telegram(target_user_id)
                if user_info:
                    logger.info(f"✅ Telegram'dan kullanıcı bilgisi alındı: {user_info}")
                else:
                    logger.warning(f"⚠️ Telegram'dan kullanıcı bilgisi alınamadı: {target_user_id}")
        else:
            error_msg = "❌ Kullanıcı bilgileri alınamadı! Lütfen geçerli bir Telegram ID girin veya kullanıcıyı etiketleyin."
            logger.warning(f"⚠️ {error_msg}")
            try:
                if chat_type == "private":
                    await message.reply(error_msg)
                elif _bot_instance:
                    await _bot_instance.send_message(user_id, error_msg)
            except:
                pass
            return
        
        if not user_info:
            await message.reply("❌ Kullanıcı bilgileri alınamadı! Lütfen geçerli bir Telegram ID girin.")
            return
        
        if user_info.get('is_bot'):
            await message.reply("❌ Botlar mod olarak eklenemez!")
            return
        
        # Mod ekle
        success = await add_moderator_to_db(
            user_id=user_info['user_id'],
            username=user_info.get('username'),
            first_name=user_info.get('first_name', 'Bilinmeyen'),
            last_name=user_info.get('last_name'),
            added_by=user_id,
            notes=None
        )
        
        if success:
            username_display = f"@{user_info['username']}" if user_info.get('username') else "Kullanıcı adı yok"
            name_display = user_info.get('first_name', 'Bilinmeyen')
            last_name_display = user_info.get('last_name', '')
            full_name = f"{name_display} {last_name_display}".strip() if last_name_display else name_display
            
            # Admin'e özelden detaylı bilgi gönder
            admin_response = f"✅ <b>Mod Başarıyla Eklendi!</b>\n\n"
            admin_response += f"👤 <b>Kullanıcı Bilgileri:</b>\n"
            admin_response += f"   • <b>Ad:</b> {full_name}\n"
            admin_response += f"   • <b>Username:</b> {username_display}\n"
            admin_response += f"   • <b>Telegram ID:</b> <code>{user_info['user_id']}</code>\n\n"
            admin_response += f"➕ <b>Ekleyen Admin:</b> {message.from_user.first_name} (@{message.from_user.username if message.from_user.username else 'Kullanıcı adı yok'})\n"
            admin_response += f"🆔 <b>Admin ID:</b> <code>{user_id}</code>\n\n"
            admin_response += f"⏰ <b>Ekleme Zamanı:</b> {time.strftime('%d.%m.%Y %H:%M:%S')}"
            
            # Özelden admin'e gönder
            try:
                if chat_type == "private":
                    await message.reply(admin_response, parse_mode="HTML")
                elif _bot_instance:
                    await _bot_instance.send_message(user_id, admin_response, parse_mode="HTML")
                logger.info(f"✅ Mod eklendi bildirimi admin'e gönderildi - Admin: {user_id}, Mod: {user_info['user_id']}")
            except Exception as e:
                logger.error(f"❌ Mod ekleme bildirimi admin'e gönderilemedi: {e}")
        else:
            await message.reply("❌ Mod eklenirken hata oluştu! Lütfen tekrar deneyin.")
            
    except Exception as e:
        logger.error(f"❌ Mod ekleme komutu hatası: {e}", exc_info=True)
        try:
            if message.chat.type == "private":
                await message.reply("❌ Bir hata oluştu! Lütfen tekrar deneyin.")
        except:
            pass


# Handler sırası önemli: !modsil !modekle'den sonra ama !mod'dan önce
@router.message(F.text.startswith("!modsil"))
async def remove_moderator_command(message: Message) -> None:
    """!modsil <telegram_id> veya !modsil (etiketle) - Mod sil"""
    try:
        user_id = message.from_user.id
        chat_type = message.chat.type
        
        # Admin kontrolü
        if not is_admin(user_id):
            if chat_type == "private":
                await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
            return
        
        # Grupta ise mesajı sil
        if chat_type in ["group", "supergroup"]:
            try:
                await message.delete()
            except:
                pass
        
        # Komut parametresini al
        text = message.text.strip()
        
        # 1. Reply kontrolü (bir mesaja cevap vererek)
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user_id = message.reply_to_message.from_user.id
        # 2. Mention kontrolü (entities)
        elif message.entities:
            target_user_id = None
            for entity in message.entities:
                if entity.type == "text_mention":
                    # Text mention varsa user_id al
                    target_user_id = entity.user.id
                    break
        # 3. Numara veya ID ile silme
        else:
            match = re.match(r'^!modsil\s+(\d+)$', text, re.IGNORECASE)
            if match:
                input_number = int(match.group(1))
                
                # Önce modları getir (numara kontrolü için) - !modlar ile aynı sıralama
                # Sadece aktif modları getir, !modlar komutundaki sırayla aynı olmalı
                moderators = await get_moderators_from_db(include_inactive=False)
                
                # Eğer girilen sayı mod sayısından küçük veya eşitse (ve pozitifse), numara olarak kabul et
                # Örnek: 3 mod varsa, 1-3 arası numara olarak kabul edilir
                if 1 <= input_number <= len(moderators):
                    # Numara ile silme - Sıradaki modu al (1-based index)
                    target_mod = moderators[input_number - 1]  # 0-based index için -1
                    target_user_id = target_mod['user_id']
                    # Debug: Hangi modların sıralandığını logla
                    logger.info(f"✅ Numara ile mod silme - Sıra: {input_number}, User ID: {target_user_id}")
                    logger.info(f"📋 Mod listesi sıralaması: {[(idx+1, m['user_id'], m.get('username', 'N/A')) for idx, m in enumerate(moderators)]}")
                else:
                    # Numara değilse, Telegram ID olarak kabul et
                    target_user_id = input_number
                    logger.info(f"✅ Telegram ID ile mod silme - User ID: {target_user_id}")
            else:
                # Kullanım bilgisi göster
                usage_msg = "❌ <b>Kullanım:</b>\n\n"
                usage_msg += "• <code>!modsil 3</code> (Sıra numarası ile - <code>!modlar</code> komutundaki sıra)\n"
                usage_msg += "• <code>!modsil 123456789</code> (Telegram ID ile)\n"
                usage_msg += "• Bir mesaja cevap vererek <code>!modsil</code> yazın\n"
                usage_msg += "• Birini etiketleyerek <code>!modsil</code> yazın"
                
                try:
                    if chat_type == "private":
                        await message.reply(usage_msg, parse_mode="HTML")
                    elif _bot_instance:
                        await _bot_instance.send_message(user_id, usage_msg, parse_mode="HTML")
                except:
                    pass
                return
        
        if not target_user_id:
            await message.reply("❌ Kullanıcı bulunamadı! Lütfen geçerli bir Telegram ID girin veya kullanıcıyı etiketleyin.")
            return
        
        # Mod sil
        success = await remove_moderator_from_db(target_user_id)
        
        if success:
            response = f"✅ <b>Mod Silindi!</b>\n\n"
            response += f"🆔 <b>ID:</b> <code>{target_user_id}</code>\n"
            response += f"🗑️ <b>Silen:</b> {message.from_user.first_name}"
            
            # Özelden gönder
            try:
                if chat_type == "private":
                    await message.reply(response, parse_mode="HTML")
                elif _bot_instance:
                    await _bot_instance.send_message(user_id, response, parse_mode="HTML")
                logger.info(f"✅ Mod silindi bildirimi gönderildi - User: {user_id}")
            except Exception as e:
                logger.error(f"❌ Mod silme bildirimi gönderilemedi: {e}")
        else:
            error_msg = "❌ Mod bulunamadı veya zaten silinmiş!"
            try:
                if chat_type == "private":
                    await message.reply(error_msg)
                elif _bot_instance:
                    await _bot_instance.send_message(user_id, error_msg)
            except:
                pass
            
    except Exception as e:
        logger.error(f"❌ Mod silme komutu hatası: {e}", exc_info=True)
        try:
            if message.chat.type == "private":
                await message.reply("❌ Bir hata oluştu! Lütfen tekrar deneyin.")
        except:
            pass


@router.message(F.text.startswith("!mod"))
async def list_moderators_command(message: Message) -> None:
    """!mod veya !modlar komutu - Aktif modları listele"""
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        chat_type = message.chat.type
        
        # Komut kontrolü - !mod veya !modlar olmalı (ama !modekle ve !modsil değil)
        if not message.text:
            return
        
        text_lower = message.text.strip().lower()
        if text_lower not in ['!mod', '!mod ', '!modlar', '!modlar ']:
            # !mod ile başlayan ama farklı bir komut (örn: !modekle, !modsil)
            if not re.match(r'^!mod(lar)?\s*$', text_lower):
                return  # !modekle veya !modsil gibi komutlar, bu handler'ı atla
        
        logger.info(f"🛡️ !modlar komutu yakalandı - User: {user_id}, Chat: {chat_id}, Type: {chat_type}")
        
        # Database'den sadece aktif modları getir (liste için)
        moderators = await get_moderators_from_db(include_inactive=False)
        
        # Kullanıcının mod olup olmadığını kontrol et (aktif ve pasif modlar için)
        is_moderator_user = await is_moderator(user_id, include_inactive=True)
        
        # ÖNEMLİ: Özel mesajda mod kontrolü - Mod özelden !mod yazarsa sadece liste göster (bildirim yok)
        if chat_type == "private":
            # Özel mesajda sadece liste göster, bildirim gönderme
            # Devam et, liste gösterilecek (aşağıdaki kod)
            pass
        
        if is_moderator_user:
            logger.info(f"🛡️ Mod komutu mod tarafından kullanıldı - User: {user_id}, Cooldown atlandı")
        
        # Özelden: Her zaman listele (cooldown yok, bildirim yok)
        # Grupta: 3 dakikada bir (ama mod ise kullanıcı cooldown'u yok, grup cooldown'u var) + modlara bildirim gönder
        if chat_type in ["group", "supergroup"]:
            # Grup bazlı cooldown kontrolü (flame koruması) - Tüm kullanıcılar için geçerli
            can_use_group, remaining_group = await check_mod_group_cooldown(chat_id)
            if not can_use_group:
                logger.info(f"⏰ Mod komutu grup cooldown'da - Group: {chat_id}, Remaining: {remaining_group}s")
                # Cooldown mesajı göster (sessizce)
                return
            
            # Kullanıcı bazlı cooldown kontrolü (sadece mod değilse) - mesaj silmeden önce
            if not is_moderator_user:
                can_use, remaining = await check_mod_command_cooldown(user_id)
                if not can_use:
                    logger.info(f"⏰ Mod komutu cooldown'da - User: {user_id}, Remaining: {remaining}s")
                    # Cooldown mesajı göster (sessizce)
                    return
            else:
                logger.info(f"✅ Mod komutu mod tarafından kullanıldı, kullanıcı cooldown'u atlandı - User: {user_id}")
            
            # ÖNEMLİ: Sadece grupta !mod yazıldığında modlara özelden bildirim gönder
            # Özel mesajda bildirim gönderilmez, sadece liste gösterilir
            await notify_moderators_help_request(message, user_id)
            
            # Mesajı sil (mesaj silindikten sonra message.reply() kullanılamaz!)
            try:
                await message.delete()
                logger.info(f"🗑️ !modlar mesajı silindi - Chat: {chat_id}, User: {user_id}")
            except Exception as delete_error:
                logger.warning(f"⚠️ Mesaj silinemedi - Chat: {chat_id}, Error: {delete_error}")
                # Mesaj silinemediyse devam et, sorun değil
        
        if not moderators:
            # Özel mesajda mod ise sadece "mod bulunamadı" mesajı göster (yardım bilgisi yok)
            if chat_type == "private" and is_moderator_user:
                response = "❌ <b>Mod Bulunamadı</b>\n\nHenüz mod eklenmemiş."
            else:
                response = "❌ <b>Mod Bulunamadı</b>\n\nHenüz mod eklenmemiş.\n\n<b>Kullanım:</b>\n<code>!modekle 123456789</code> veya <code>!modekle @username</code>"
            try:
                if chat_type == "private":
                    await message.reply(response, parse_mode="HTML")
                elif _bot_instance:
                    await _bot_instance.send_message(user_id, response, parse_mode="HTML")
            except Exception as e:
                logger.error(f"❌ Mod listesi mesajı gönderilemedi - Error: {e}")
            return
        
        # HTML escape fonksiyonu
        def escape_html(text):
            if not text:
                return ""
            return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Mod listesini oluştur (HTML formatında)
        response = "🛡️ <b>AKTİF MODERATÖRLER</b>\n"
        response += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        for idx, mod in enumerate(moderators, 1):
            username = f"@{mod['username']}" if mod.get('username') else "Kullanıcı adı yok"
            name = escape_html(mod.get('first_name', 'Bilinmeyen'))
            username_escaped = escape_html(username) if not username.startswith('@') else f"@{escape_html(username[1:])}"
            user_id_display = f"<code>{mod['user_id']}</code>"
            
            response += f"{idx}. {name} ({username_escaped})\n"
            response += f"   🆔 ID: {user_id_display}\n"
            if mod.get('notes'):
                notes_escaped = escape_html(mod['notes'])
                response += f"   📝 Not: {notes_escaped}\n"
            response += "\n"
        
        response += "━━━━━━━━━━━━━━━━━━━\n"
        response += f"📊 <b>Toplam:</b> {len(moderators)} mod"
        
        # Hem chatte hem özelden gönder (grup ise)
        try:
            if chat_type == "private":
                # Özelden sadece chatte göster
                await message.reply(response, parse_mode="HTML")
            elif chat_type in ["group", "supergroup"]:
                # Grupta hem chatte hem özelden göster
                if _bot_instance:
                    # Önce chatte göster (mesaj silindiği için bot.send_message kullan)
                    try:
                        chat_title = escape_html(message.chat.title or "Grup")
                        chat_response = f"🛡️ <b>{chat_title} - Aktif Modlar</b>\n\n{response}"
                        
                        # Grupta !mod yazıldığında bildirim gönderildiğini belirten bilgi ekle
                        chat_response += "\n\n"
                        chat_response += "━━━━━━━━━━━━━━━━━━━\n"
                        chat_response += "💬 <b>Bilgi:</b> Aktif modlara bildirim gönderildi.\n"
                        chat_response += "❓ Sorularınız için sadece bu isimlere ulaşmalısınız."
                        
                        # Mesaj silindiği için message.reply() yerine bot.send_message() kullan
                        await _bot_instance.send_message(chat_id, chat_response, parse_mode="HTML")
                        logger.info(f"✅ Mod listesi chatte gösterildi - Chat: {chat_id}, Mod Count: {len(moderators)}")
                    except Exception as chat_error:
                        logger.error(f"❌ Mod listesi chatte gönderilemedi - Error: {chat_error}")
                        # HTML başarısız olursa plain text dene
                        try:
                            plain_chat_response = f"🛡️ {message.chat.title or 'Grup'} - Aktif Modlar\n\n"
                            for idx, mod in enumerate(moderators, 1):
                                username = f"@{mod['username']}" if mod.get('username') else "Kullanıcı adı yok"
                                name = mod.get('first_name', 'Bilinmeyen')
                                plain_chat_response += f"{idx}. {name} ({username})\n"
                            plain_chat_response += f"\n📊 Toplam: {len(moderators)} mod"
                            await _bot_instance.send_message(chat_id, plain_chat_response)
                        except Exception as plain_error:
                            logger.error(f"❌ Plain text mod listesi de gönderilemedi - Error: {plain_error}")
                    
                    # Sonra özelden gönder
                    try:
                        await _bot_instance.send_message(user_id, response, parse_mode="HTML")
                        logger.info(f"✅ Mod listesi özelden gönderildi - User: {user_id}")
                    except Exception as private_error:
                        logger.debug(f"⚠️ Özelden mod listesi gönderilemedi - User: {user_id}, Error: {private_error}")
            else:
                # Diğer chat tipleri için sadece reply
                await message.reply(response, parse_mode="HTML")
            
            logger.info(f"✅ Mod listesi gönderildi - User: {user_id}, Mod Count: {len(moderators)}")
        except Exception as e:
            logger.error(f"❌ Mod listesi gönderilemedi - Error: {e}", exc_info=True)
            # Plain text fallback
            try:
                plain_response = "🛡️ AKTİF MODERATÖRLER\n━━━━━━━━━━━━━━━━━━━\n\n"
                for idx, mod in enumerate(moderators, 1):
                    username = f"@{mod['username']}" if mod.get('username') else "Kullanıcı adı yok"
                    name = mod.get('first_name', 'Bilinmeyen')
                    plain_response += f"{idx}. {name} ({username})\n"
                    plain_response += f"   ID: {mod['user_id']}\n\n"
                plain_response += f"📊 Toplam: {len(moderators)} mod"
                
                if chat_type == "private":
                    await message.reply(plain_response)
                elif _bot_instance:
                    await _bot_instance.send_message(user_id, plain_response)
            except Exception as e2:
                logger.error(f"❌ Mod listesi plain text olarak da gönderilemedi: {e2}")
        
    except Exception as e:
        logger.error(f"❌ Mod listesi komutu hatası: {e}", exc_info=True)
        try:
            await message.reply("❌ Mod listesi yüklenirken hata oluştu!")
        except:
            pass


# =============================================
# MOD KOD SİSTEMİ - TEK KULLANIMLIK KODLAR
# =============================================

def generate_mod_code(length: int = 12) -> str:
    """Güvenli mod kodu üret (büyük harf + rakam)"""
    alphabet = string.ascii_uppercase + string.digits
    # 0, O, I, 1 gibi karıştırıcı karakterleri çıkar
    alphabet = alphabet.replace('0', '').replace('O', '').replace('I', '').replace('1', '')
    return ''.join(secrets.choice(alphabet) for _ in range(length))


async def create_mod_codes(count: int = 10, created_by: int = None) -> List[str]:
    """Mod kodları oluştur ve database'e kaydet"""
    try:
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool bulunamadı!")
            return []
        
        codes = []
        async with pool.acquire() as conn:
            for _ in range(count):
                # Benzersiz kod üret
                while True:
                    code = generate_mod_code()
                    # Kodun benzersiz olduğundan emin ol
                    existing = await conn.fetchrow(
                        "SELECT id FROM mod_codes WHERE code = $1",
                        code
                    )
                    if not existing:
                        break
                
                # Kodu database'e ekle
                await conn.execute("""
                    INSERT INTO mod_codes (code, is_used, created_by)
                    VALUES ($1, FALSE, $2)
                """, code, created_by)
                
                codes.append(code)
                logger.info(f"✅ Mod kodu oluşturuldu: {code}")
        
        logger.info(f"✅ {len(codes)} mod kodu başarıyla oluşturuldu")
        return codes
        
    except Exception as e:
        logger.error(f"❌ Mod kodu oluşturma hatası: {e}", exc_info=True)
        return []


async def use_mod_code(code: str, user_id: int) -> tuple[bool, str]:
    """Mod kodunu kullan (tek kullanımlık)"""
    try:
        pool = await get_db_pool()
        if not pool:
            return False, "❌ Database bağlantı hatası!"
        
        async with pool.acquire() as conn:
            # Kodu kontrol et
            code_row = await conn.fetchrow(
                "SELECT id, is_used, used_by FROM mod_codes WHERE code = $1",
                code.upper().strip()
            )
            
            if not code_row:
                return False, "❌ Geçersiz kod! Lütfen doğru kodu girin."
            
            if code_row['is_used']:
                used_by = code_row['used_by']
                return False, f"❌ Bu kod zaten kullanılmış! (Kullanan: {used_by})"
            
            # Kullanıcı zaten mod mu?
            is_already_mod = await is_moderator(user_id)
            if is_already_mod:
                return False, "❌ Zaten moderatörsünüz!"
            
            # Kodu kullanıldı olarak işaretle
            await conn.execute("""
                UPDATE mod_codes
                SET is_used = TRUE,
                    used_by = $1,
                    used_at = NOW()
                WHERE code = $2
            """, user_id, code.upper().strip())
            
            # Kullanıcı bilgilerini al
            user_info = await get_user_info_from_telegram(user_id)
            if not user_info:
                return False, "❌ Kullanıcı bilgileri alınamadı!"
            
            # Kullanıcıyı mod olarak ekle
            success = await add_moderator_to_db(
                user_id=user_info['user_id'],
                username=user_info.get('username'),
                first_name=user_info.get('first_name', 'Bilinmeyen'),
                last_name=user_info.get('last_name'),
                added_by=user_id,  # Kendisi ekliyor (kod ile)
                notes=f"Mod kodu ile eklendi: {code}"
            )
            
            if success:
                logger.info(f"✅ Mod kodu kullanıldı - Code: {code}, User: {user_id}")
                return True, "✅ Moderatör başarıyla eklendi! Artık mod yetkileriniz aktif."
            else:
                return False, "❌ Mod eklenirken hata oluştu! Lütfen admin ile iletişime geçin."
                
    except Exception as e:
        logger.error(f"❌ Mod kodu kullanma hatası: {e}", exc_info=True)
        return False, f"❌ Hata: {str(e)}"


async def list_mod_codes(show_used: bool = False) -> List[Dict]:
    """Mod kodlarını listele"""
    try:
        pool = await get_db_pool()
        if not pool:
            return []
        
        async with pool.acquire() as conn:
            if show_used:
                rows = await conn.fetch("""
                    SELECT code, is_used, used_by, used_at, created_at
                    FROM mod_codes
                    ORDER BY created_at DESC
                """)
            else:
                rows = await conn.fetch("""
                    SELECT code, is_used, used_by, used_at, created_at
                    FROM mod_codes
                    WHERE is_used = FALSE
                    ORDER BY created_at DESC
                """)
            
            codes = []
            for row in rows:
                codes.append({
                    "code": row['code'],
                    "is_used": row['is_used'],
                    "used_by": row['used_by'],
                    "used_at": row['used_at'],
                    "created_at": row['created_at']
                })
            
            return codes
            
    except Exception as e:
        logger.error(f"❌ Mod kodları listeleme hatası: {e}", exc_info=True)
        return []


@router.message(F.text.startswith("!modol"))
async def use_mod_code_command(message: Message) -> None:
    """!modol KOD komutu - Mod kodunu kullan"""
    try:
        user_id = message.from_user.id
        chat_type = message.chat.type
        
        # Komut parametresini al
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) < 2:
            usage_msg = "❌ <b>Kullanım:</b>\n\n"
            usage_msg += "<code>!modol KOD</code>\n\n"
            usage_msg += "Örnek: <code>!modol ABC123XYZ456</code>"
            
            try:
                if chat_type == "private":
                    await message.reply(usage_msg, parse_mode="HTML")
                elif chat_type in ["group", "supergroup"]:
                    try:
                        await message.delete()
                    except:
                        pass
                    if _bot_instance:
                        await _bot_instance.send_message(user_id, usage_msg, parse_mode="HTML")
            except:
                pass
            return
        
        code = parts[1].upper().strip()
        
        # Grupta ise mesajı sil
        if chat_type in ["group", "supergroup"]:
            try:
                await message.delete()
            except:
                pass
        
        # Kodu kullan
        success, result_msg = await use_mod_code(code, user_id)
        
        # Sonucu özelden gönder
        try:
            if chat_type == "private":
                await message.reply(result_msg, parse_mode="HTML")
            elif _bot_instance:
                await _bot_instance.send_message(user_id, result_msg, parse_mode="HTML")
            
            if success:
                logger.info(f"✅ Mod kodu başarıyla kullanıldı - User: {user_id}, Code: {code}")
        except Exception as e:
            logger.error(f"❌ Mod kodu sonuç mesajı gönderilemedi: {e}")
            
    except Exception as e:
        logger.error(f"❌ !modol komutu hatası: {e}", exc_info=True)
        try:
            if message.chat.type == "private":
                await message.reply("❌ Bir hata oluştu! Lütfen tekrar deneyin.")
        except:
            pass


@router.message(F.text.startswith("!modkodlar"))
async def list_mod_codes_command(message: Message) -> None:
    """!modkodlar komutu - Mod kodlarını listele (Admin only)"""
    try:
        user_id = message.from_user.id
        chat_type = message.chat.type
        
        # Admin kontrolü
        if not is_admin(user_id):
            if chat_type == "private":
                await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
            return
        
        # Grupta ise mesajı sil
        if chat_type in ["group", "supergroup"]:
            try:
                await message.delete()
            except:
                pass
        
        # Kodları listele
        codes = await list_mod_codes(show_used=False)
        
        if not codes:
            response = "❌ <b>Kullanılabilir Mod Kodu Yok</b>\n\nHenüz kod oluşturulmamış veya tüm kodlar kullanılmış."
        else:
            response = f"🔑 <b>KULLANILABİLİR MOD KODLARI</b>\n"
            response += "━━━━━━━━━━━━━━━━━━━\n\n"
            
            for idx, code_info in enumerate(codes, 1):
                response += f"{idx}. <code>{code_info['code']}</code>\n"
            
            response += f"\n━━━━━━━━━━━━━━━━━━━\n"
            response += f"📊 <b>Toplam:</b> {len(codes)} kullanılabilir kod"
        
        # Özelden gönder
        try:
            if chat_type == "private":
                await message.reply(response, parse_mode="HTML")
            elif _bot_instance:
                await _bot_instance.send_message(user_id, response, parse_mode="HTML")
        except Exception as e:
            logger.error(f"❌ Mod kodları listesi gönderilemedi: {e}")
            
    except Exception as e:
        logger.error(f"❌ !modkodlar komutu hatası: {e}", exc_info=True)


@router.message(F.text.startswith("!modkoduret"))
async def generate_mod_codes_command(message: Message) -> None:
    """!modkoduret [sayı] komutu - Mod kodları üret (Admin only)"""
    try:
        user_id = message.from_user.id
        chat_type = message.chat.type
        
        # Admin kontrolü
        if not is_admin(user_id):
            if chat_type == "private":
                await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
            return
        
        # Grupta ise mesajı sil
        if chat_type in ["group", "supergroup"]:
            try:
                await message.delete()
            except:
                pass
        
        # Komut parametresini al
        text = message.text.strip()
        parts = text.split()
        
        count = 10  # Varsayılan 10 kod
        if len(parts) >= 2:
            try:
                count = int(parts[1])
                if count < 1 or count > 50:
                    await message.reply("❌ Kod sayısı 1-50 arasında olmalı!")
                    return
            except ValueError:
                await message.reply("❌ Geçersiz sayı! Örnek: <code>!modkoduret 10</code>", parse_mode="HTML")
                return
        
        # Kodları üret
        codes = await create_mod_codes(count=count, created_by=user_id)
        
        if not codes:
            response = "❌ Mod kodları oluşturulurken hata oluştu!"
        else:
            response = f"✅ <b>{len(codes)} Mod Kodu Oluşturuldu!</b>\n\n"
            response += "🔑 <b>Kodlar:</b>\n"
            response += "━━━━━━━━━━━━━━━━━━━\n\n"
            
            for idx, code in enumerate(codes, 1):
                response += f"{idx}. <code>{code}</code>\n"
            
            response += f"\n━━━━━━━━━━━━━━━━━━━\n"
            response += f"📝 <b>Kullanım:</b> <code>!modol KOD</code>\n"
            response += f"📊 <b>Toplam:</b> {len(codes)} kod"
        
        # Özelden gönder
        try:
            if chat_type == "private":
                await message.reply(response, parse_mode="HTML")
            elif _bot_instance:
                await _bot_instance.send_message(user_id, response, parse_mode="HTML")
            
            logger.info(f"✅ {len(codes)} mod kodu oluşturuldu - Admin: {user_id}")
        except Exception as e:
            logger.error(f"❌ Mod kodları mesajı gönderilemedi: {e}")
            
    except Exception as e:
        logger.error(f"❌ !modkoduret komutu hatası: {e}", exc_info=True)
        try:
            if message.chat.type == "private":
                await message.reply("❌ Bir hata oluştu! Lütfen tekrar deneyin.")
        except:
            pass


# =============================================
# MOD AKTİF/PASİF SİSTEMİ
# =============================================

async def set_moderator_active_status(user_id: int, is_active: bool) -> bool:
    """Mod'un aktif/pasif durumunu ayarla"""
    try:
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool bulunamadı!")
            return False
        
        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE moderators
                SET is_active = $1
                WHERE user_id = $2
            """, is_active, user_id)
            
            if result == "UPDATE 1":
                status_text = "aktif" if is_active else "pasif"
                logger.info(f"✅ Mod durumu güncellendi - User: {user_id}, Durum: {status_text}")
                return True
            else:
                logger.warning(f"⚠️ Mod bulunamadı - User: {user_id}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Mod durumu güncelleme hatası: {e}", exc_info=True)
        return False


async def notify_moderators_help_request(message: Message, requester_id: int, is_admin_request: bool = False) -> None:
    """Grupta !mod yazıldığında veya admin özelden !mod yazdığında modlara özelden bildirim gönder"""
    try:
        if not _bot_instance:
            return
        
        # Aktif modları getir
        moderators = await get_moderators_from_db(include_inactive=False)
        
        if not moderators:
            return
        
        # Kullanıcı bilgilerini al
        requester_name = message.from_user.first_name or "Kullanıcı"
        requester_username = f"@{message.from_user.username}" if message.from_user.username else "Kullanıcı adı yok"
        
        # Chat tipi ve grup ID'sini al
        chat_type = message.chat.type
        group_id = message.chat.id if chat_type in ["group", "supergroup"] else None
        
        # İsteği yapan kişi mod mu?
        is_moderator_user = await is_moderator(requester_id, include_inactive=True)
        
        # SQL'e kayıt ekle
        try:
            from database import get_db_pool
            pool = await get_db_pool()
            if pool:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO mod_help_requests (user_id, group_id, chat_type, is_moderator, notification_sent)
                        VALUES ($1, $2, $3, $4, FALSE)
                    """, requester_id, group_id, chat_type, is_moderator_user)
                    logger.debug(f"📝 Mod yardım isteği kaydedildi - User: {requester_id}, Group: {group_id}, Type: {chat_type}")
        except Exception as log_error:
            logger.debug(f"⏸️ Mod yardım isteği kaydedilemedi (kritik değil): {log_error}")
        
        # Bildirim mesajı
        if is_admin_request:
            # Admin özelden yazdı
            notification = f"""
🆘 <b>YARDIM İSTEĞİ (ADMİN)</b>

👤 <b>Admin:</b> {requester_name} ({requester_username})
🆔 <b>ID:</b> <code>{requester_id}</code>

📝 <b>Mesaj:</b> Admin özelden <code>!mod</code> yazdı, yardım istiyor.

⏰ <b>Zaman:</b> {time.strftime('%d.%m.%Y %H:%M:%S')}
            """
        else:
            # Grupta yazıldı
            chat_title = message.chat.title or "Grup"
            chat_id = message.chat.id
            
            notification = f"""
🆘 <b>YARDIM İSTEĞİ</b>

👤 <b>Kullanıcı:</b> {requester_name} ({requester_username})
🆔 <b>ID:</b> <code>{requester_id}</code>
💬 <b>Grup:</b> {chat_title}
🆔 <b>Grup ID:</b> <code>{chat_id}</code>

📝 <b>Mesaj:</b> Grupta <code>!mod</code> yazdı, yardım istiyor.

⏰ <b>Zaman:</b> {time.strftime('%d.%m.%Y %H:%M:%S')}
            """
        
        # Tüm aktif modlara özelden bildirim gönder (istekte bulunan kişi de dahil)
        # NOT: Mod kendisi !mod yazdığında da bildirim almalı (diğer modlara yardım çağrısı yapıyor)
        sent_count = 0
        for mod in moderators:
            try:
                await _bot_instance.send_message(
                    mod['user_id'],
                    notification,
                    parse_mode="HTML"
                )
                sent_count += 1
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.debug(f"⏸️ Mod bildirimi gönderilemedi - Mod: {mod['user_id']}, Error: {e}")
        
        if sent_count > 0:
            logger.info(f"✅ {sent_count} mod'a yardım isteği bildirimi gönderildi - Requester: {requester_id}, Admin: {is_admin_request}")
            
            # SQL'deki kaydı güncelle - Bildirim gönderildi olarak işaretle
            try:
                from database import get_db_pool
                pool = await get_db_pool()
                if pool:
                    async with pool.acquire() as conn:
                        # En son kaydı bul ve güncelle
                        await conn.execute("""
                            UPDATE mod_help_requests
                            SET notification_sent = TRUE
                            WHERE id = (
                                SELECT id FROM mod_help_requests
                                WHERE user_id = $1 
                                  AND (group_id = $2 OR (group_id IS NULL AND $2 IS NULL))
                                  AND chat_type = $3
                                  AND requested_at >= NOW() - INTERVAL '1 minute'
                                ORDER BY requested_at DESC
                                LIMIT 1
                            )
                        """, requester_id, group_id, chat_type)
                        logger.debug(f"📝 Mod yardım isteği güncellendi - Notification sent: TRUE")
            except Exception as update_error:
                logger.debug(f"⏸️ Mod yardım isteği güncellenemedi (kritik değil): {update_error}")
        
    except Exception as e:
        logger.error(f"❌ Mod bildirimi hatası: {e}", exc_info=True)


@router.message(F.text.startswith("!modpasif"))
async def set_moderator_inactive_command(message: Message) -> None:
    """!modpasif komutu - Mod'u pasif yap (sadece kendisi)"""
    try:
        user_id = message.from_user.id
        chat_type = message.chat.type
        
        # Mod kontrolü (aktif veya pasif olabilir)
        is_mod = await is_moderator(user_id, include_inactive=True)
        if not is_mod:
            if chat_type == "private":
                await message.reply("❌ Bu komutu sadece moderatörler kullanabilir!")
            return
        
        # Grupta ise mesajı sil
        if chat_type in ["group", "supergroup"]:
            try:
                await message.delete()
            except:
                pass
        
        # Mod'u pasif yap
        success = await set_moderator_active_status(user_id, False)
        
        if success:
            response = "✅ <b>Mod Durumu Güncellendi</b>\n\n"
            response += "🔴 <b>Durum:</b> Pasif\n"
            response += "📝 <b>Açıklama:</b> Artık mod listesinde görünmeyeceksiniz.\n"
            response += "💡 <b>Not:</b> Mod yetkileriniz hala aktif, sadece listede görünmüyorsunuz.\n\n"
            response += "🔓 <b>Aktif Olmak İçin:</b> <code>!modaktif</code> yazın."
        else:
            response = "❌ Mod durumu güncellenirken hata oluştu!"
        
        # Özelden gönder
        try:
            if chat_type == "private":
                await message.reply(response, parse_mode="HTML")
            elif _bot_instance:
                await _bot_instance.send_message(user_id, response, parse_mode="HTML")
        except Exception as e:
            logger.error(f"❌ Mod pasif mesajı gönderilemedi: {e}")
            
    except Exception as e:
        logger.error(f"❌ !modpasif komutu hatası: {e}", exc_info=True)
        try:
            if message.chat.type == "private":
                await message.reply("❌ Bir hata oluştu! Lütfen tekrar deneyin.")
        except:
            pass


@router.message(F.text.startswith("!modrapor"))
async def mod_daily_report_command(message: Message) -> None:
    """!modrapor komutu - Mod günlük analiz raporunu talep et (bugünkü veriler dahil)"""
    try:
        user_id = message.from_user.id
        chat_type = message.chat.type
        
        # Mod kontrolü (aktif veya pasif olabilir)
        is_mod = await is_moderator(user_id, include_inactive=True)
        if not is_mod:
            if chat_type == "private":
                await message.reply("❌ Bu komutu sadece moderatörler kullanabilir!")
            return
        
        # Grupta ise mesajı sil
        if chat_type in ["group", "supergroup"]:
            try:
                await message.delete()
            except:
                pass
        
        # Rapor oluştur (bugünkü veriler dahil)
        report_data = await generate_mod_daily_report(user_id, include_today=True)
        
        if not report_data:
            response = "❌ Rapor oluşturulamadı! Lütfen daha sonra tekrar deneyin."
        else:
            # Rapor gönder
            success = await send_mod_daily_report(user_id, report_data)
            if success:
                response = "✅ Günlük analiz raporu özelden gönderildi!"
            else:
                response = "❌ Rapor gönderilemedi! Lütfen daha sonra tekrar deneyin."
        
        # Özelden gönder
        try:
            if chat_type == "private":
                await message.reply(response, parse_mode="HTML")
            elif _bot_instance:
                await _bot_instance.send_message(user_id, response, parse_mode="HTML")
        except Exception as e:
            logger.error(f"❌ Mod rapor komutu mesajı gönderilemedi: {e}")
            
    except Exception as e:
        logger.error(f"❌ !modrapor komutu hatası: {e}", exc_info=True)
        try:
            if message.chat.type == "private":
                await message.reply("❌ Bir hata oluştu! Lütfen tekrar deneyin.")
        except:
            pass


@router.message(F.text.startswith("!modkomut"))
async def mod_commands_help_command(message: Message) -> None:
    """!modkomut komutu - Mod komutlarını listele"""
    try:
        user_id = message.from_user.id
        chat_type = message.chat.type
        
        # Mod kontrolü (aktif veya pasif olabilir)
        is_mod = await is_moderator(user_id, include_inactive=True)
        if not is_mod and not is_admin(user_id):
            if chat_type == "private":
                await message.reply("❌ Bu komutu sadece moderatörler kullanabilir!")
            return
        
        # Grupta ise mesajı sil
        if chat_type in ["group", "supergroup"]:
            try:
                await message.delete()
            except:
                pass
        
        # Mod komutları listesi - DETAYLI AÇIKLAMA
        commands_text = """
🛡️ <b>MOD KOMUTLARI - DETAYLI KILAVUZ</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 <b>UYARI SİSTEMİ</b>

<b>Komutlar:</b>
• <code>!uyarı [sebep]</code> (reply ile)
• <code>!uyarı @username [sebep]</code>
• <code>!uyarı [user_id] [sebep]</code>
• <code>!uyariseviye</code> - Kullanıcının uyarı seviyesini görüntüle veya ayarla (0-3)
• <code>!uyarılar</code> - Kullanıcının uyarı sayısını görüntüle
• <code>!uyarısıfırla</code> (reply ile) - Kullanıcının tüm uyarılarını sıfırla

<b>📖 Nasıl Çalışır:</b>
Uyarı sistemi 3 aşamalıdır ve otomatik cezalandırma yapar:

<b>1️⃣ İlk Uyarı:</b>
• Kullanıcıya uyarı verilir
• <b>Otomatik olarak 5 dakika susturulur</b>
• Grupta bildirim mesajı gösterilir
• Kullanıcıya özelden bildirim gönderilir

<b>2️⃣ İkinci Uyarı:</b>
• Kullanıcıya ikinci uyarı verilir
• <b>Otomatik olarak 30 dakika susturulur</b>
• Grupta bildirim mesajı gösterilir
• Kullanıcıya özelden bildirim gönderilir

<b>3️⃣ Üçüncü Uyarı:</b>
• Kullanıcıya üçüncü uyarı verilir
• <b>Otomatik olarak kalıcı ban yapılır</b>
• Grupta bildirim mesajı gösterilir
• Kullanıcıya özelden bildirim gönderilir

<b>💡 Kullanım Örnekleri:</b>
• Bir mesaja reply yapıp: <code>!uyarı Spam yapıyor</code>
• Etiketleyerek: <code>!uyarı @username Küfür kullanıyor</code>
• ID ile: <code>!uyarı 123456789 Kurallara uymuyor</code>

<b>⚠️ Önemli Notlar:</b>
• Sebep belirtmek zorunlu değil ama önerilir
• Her uyarı otomatik olarak cezalandırma yapar
• Uyarılar grup bazında tutulur (her grup için ayrı)
• Uyarıları <code>!uyarısıfırla</code> ile sıfırlayabilirsiniz

<b>📊 Uyarı Seviyesi Ayarlama:</b>
<code>!uyariseviye</code> komutu ile kullanıcının uyarı seviyesini doğrudan ayarlayabilirsiniz:

<b>Göstermek için:</b>
• <code>!uyariseviye</code> (reply ile) - Mevcut seviyeyi gösterir
• <code>!uyariseviye @username</code> - Kullanıcının seviyesini gösterir

<b>Ayarlamak için:</b>
• <code>!uyariseviye [seviye]</code> (reply ile) - Seviyeyi ayarlar
• <code>!uyariseviye @username [seviye]</code> - Kullanıcının seviyesini ayarlar

<b>Seviyeler:</b>
• <code>0</code> - Tüm uyarıları sıfırla
• <code>1</code> - 1. seviyeye ayarla (5 dk mute)
• <code>2</code> - 2. seviyeye ayarla (30 dk mute)
• <code>3</code> - 3. seviyeye ayarla (Kalıcı ban)

<b>Örnek:</b>
• <code>!uyariseviye 2</code> (reply ile) - Kullanıcıyı 2. seviyeye ayarla
• <code>!uyariseviye @username 0</code> - Kullanıcının tüm uyarılarını sıfırla

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔇 <b>SUSTURMA (MUTE) SİSTEMİ</b>

<b>Komutlar:</b>
• <code>!sustur [süre] [sebep]</code> (reply ile)
• <code>!sustur [süre] @username [sebep]</code>
• <code>!sustur [süre] [user_id] [sebep]</code>
• <code>!mkaldir</code> / <code>!susturmakaldir</code> (reply ile) - Mute'u kaldır

<b>📖 Nasıl Çalışır:</b>
• Kullanıcıyı belirtilen süre boyunca susturur
• Süre dolduğunda otomatik olarak kalkar
• İstediğiniz zaman <code>!mkaldir</code> ile kaldırabilirsiniz
• Kullanıcıya özelden bildirim gönderilir

<b>💡 Kullanım Örnekleri:</b>
• <code>!sustur 10 Spam</code> (reply ile - 10 dakika)
• <code>!sustur 30 @username Küfür</code> (30 dakika)
• <code>!sustur 60 123456789 Kurallara uymuyor</code> (60 dakika)

<b>⚠️ Önemli Notlar:</b>
• Süre dakika cinsinden belirtilir (örn: 10 = 10 dakika)
• Minimum süre: 1 dakika
• Maksimum süre: Sınırsız (çok uzun süreler önerilmez)
• Mute sırasında kullanıcı hiçbir mesaj gönderemez

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚫 <b>BAN/UNBAN SİSTEMİ</b>

<b>Komutlar:</b>
• <code>!ban [sebep]</code> (reply ile)
• <code>!ban @username [sebep]</code>
• <code>!ban [user_id] [sebep]</code>
• <code>!yasakla</code> - Ban komutu (alias)
• <code>!unban</code> (reply ile) - Ban'ı kaldır
• <code>!unban @username</code>
• <code>!unban [user_id]</code>
• <code>!yasakkaldir</code> - Unban komutu (alias)

<b>📖 Nasıl Çalışır:</b>
• <code>!ban</code>: Kullanıcıyı kalıcı olarak banlar
• <code>!unban</code>: Kullanıcının ban'ını kaldırır, gruba tekrar katılabilir
• Reply, mention veya user ID ile çalışır
• Özel mesajda da kullanılabilir (grup ID gerekli)

<b>💡 Kullanım Örnekleri:</b>
• <code>!ban Spam yapıyor</code> (reply ile)
• <code>!ban @username Küfür</code>
• <code>!ban 123456789 Kurallara uymuyor</code>
• <code>!unban</code> (reply ile)
• <code>!unban @username</code>

<b>⚠️ Önemli Notlar:</b>
• Ban kalıcıdır, kullanıcı gruba tekrar katılamaz
• Unban ile ban kaldırılabilir
• Sebep belirtmek önerilir (loglarda görünür)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🗑️ <b>MESAJ SİLME</b>

<b>Komut:</b>
• <code>!sil</code> (reply ile)

<b>📖 Nasıl Çalışır:</b>
• Reply yaptığınız mesajı siler
• Komut mesajınız da otomatik silinir
• Sadece reply ile çalışır

<b>💡 Kullanım:</b>
Bir mesaja reply yapıp <code>!sil</code> yazın, mesaj silinir.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 <b>MOD YÖNETİMİ</b>

<b>Komutlar:</b>
• <code>!mod</code> / <code>!modlar</code> - Aktif modları listele
• <code>!modaktif</code> - Mod'u aktif yap (listede görünür)
• <code>!modpasif</code> - Mod'u pasif yap (listede görünmez)
• <code>!modrapor</code> - Günlük analiz raporu (bugünkü veriler dahil)
• <code>!modkomut</code> - Bu yardım mesajı

<b>📖 Nasıl Çalışır:</b>
• <code>!mod</code>: Grupta yazıldığında aktif modları listeler ve modlara bildirim gönderir
• <code>!modaktif</code>: Pasif modları aktif yapar, listede görünür hale gelir
• <code>!modpasif</code>: Aktif modları pasif yapar, listede görünmez (ama yetkileri aktif kalır)
• <code>!modrapor</code>: Günlük analiz raporunu talep eder (bugünkü veriler dahil). Otomatik rapor her gün 00:00'da gönderilir, bu komut ile istediğiniz zaman rapor alabilirsiniz

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 <b>ÖZEL MESAJDA KULLANIM</b>

Tüm komutlar özel mesajda da kullanılabilir!

<b>Uyarı Komutu:</b>
• <code>!uyarı [grup_id] [user_id/@username] [sebep]</code>
• <code>!uyarı [user_id/@username] [sebep]</code> (aktif gruplardan ilkini kullan)

<b>Susturma Komutu:</b>
• <code>!sustur [grup_id] [süre] [user_id/@username] [sebep]</code>
• <code>!sustur [süre] [user_id/@username] [sebep]</code> (aktif gruplardan ilkini kullan)

<b>💡 Örnek:</b>
• <code>!uyarı -1001234567890 123456789 Spam</code>
• <code>!sustur -1001234567890 30 @username Küfür</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>KULLANIM İPUÇLARI</b>

<b>1. Reply ile Kullanım:</b>
• Bir mesaja reply yapın
• Komutu yazın (örn: <code>!uyarı Spam</code>)
• En kolay ve güvenli yöntem

<b>2. Etiket ile Kullanım:</b>
• <code>@username</code> ile kullanıcıyı etiketleyin
• Komutu yazın (örn: <code>!uyarı @username Spam</code>)

<b>3. ID ile Kullanım:</b>
• Kullanıcının Telegram ID'sini yazın
• Komutu yazın (örn: <code>!uyarı 123456789 Spam</code>)

<b>4. Sebep Belirtme:</b>
• Sebep belirtmek zorunlu değil ama önerilir
• Sebep, loglarda ve bildirimlerde görünür
• Örnek: <code>!uyarı Spam yapıyor</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>ÖNEMLİ KURALLAR VE SINIRLAMALAR</b>

<b>1. Yetki Sınırlamaları:</b>
• Modlar diğer modları cezalandıramaz
• Modlar adminleri cezalandıramaz
• Sadece normal kullanıcıları cezalandırabilirsiniz

<b>2. Otomatik Cezalandırma:</b>
• Uyarı sistemi otomatik çalışır
• 1. uyarı → 5 dakika mute (otomatik)
• 2. uyarı → 30 dakika mute (otomatik)
• 3. uyarı → Kalıcı ban (otomatik)
• Ban işlemi sadece 3. uyarıda yapılır

<b>3. Rate Limiting (Güvenlik):</b>
• 1 dakikada 5'ten fazla mute → Kötü niyetli kullanıcı
• 1 dakikada 10'dan fazla uyarı → Kötü niyetli kullanıcı
• 1 dakikada 3'ten fazla ban → Kötü niyetli kullanıcı
• Kötü niyetli kullanıcılar otomatik olarak işaretlenir

<b>4. Loglama:</b>
• Tüm işlemler loglanır
• Her işlem database'e kaydedilir
• İşlem geçmişi tutulur

<b>5. Bildirimler:</b>
• Tüm cezalandırmalar grupta bildirilir
• Kullanıcıya özelden bildirim gönderilir
• Modlar yardım isteklerinde bildirim alır

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆘 <b>YARDIM İSTEĞİ SİSTEMİ</b>

<b>Nasıl Çalışır:</b>
• Grupta birisi <code>!mod</code> yazdığında
• Tüm aktif modlara özelden bildirim gönderilir
• Bildirimde kullanıcı bilgileri ve grup bilgileri yer alır

<b>Aktif Sohbet Bildirimi:</b>
• Grupta aktif sohbet varsa (son 10 dakikada mesaj)
• Ve modlar bir süredir yazmamışsa (5 dakika)
• Modlara özelden bildirim gönderilir
• "Yardıma ihtiyaç olabilir, kontrol et" mesajı

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 <b>KOMUT ÖZETİ</b>

<b>Uyarı:</b> <code>!uyarı</code> → Otomatik cezalandırma
<b>Uyarı Seviyesi:</b> <code>!uyariseviye</code> → Uyarı seviyesini gör veya ayarla
<b>Sustur:</b> <code>!sustur [süre]</code> → Manuel susturma
<b>Mute Kaldır:</b> <code>!mkaldir</code> / <code>!susturmakaldir</code> → Susturmayı kaldır
<b>Ban:</b> <code>!ban</code> / <code>!yasakla</code> → Kullanıcıyı banla
<b>Unban:</b> <code>!unban</code> / <code>!yasakkaldir</code> → Ban'ı kaldır
<b>Mesaj Sil:</b> <code>!sil</code> → Mesaj sil
<b>Uyarılar:</b> <code>!uyarılar</code> → Uyarı sayısını gör
<b>Uyarı Sıfırla:</b> <code>!uyarısıfırla</code> → Uyarıları sıfırla
<b>Mod Listesi:</b> <code>!mod</code> → Modları listele
<b>Mod Aktif:</b> <code>!modaktif</code> → Mod'u aktif yap
<b>Mod Pasif:</b> <code>!modpasif</code> → Mod'u pasif yap
<b>Mod Rapor:</b> <code>!modrapor</code> → Günlük analiz raporu (bugünkü veriler dahil)
<b>Mod Komutları:</b> <code>!modkomut</code> → Bu yardım mesajı

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ <b>BAŞARILI KULLANIM İÇİN:</b>
• Her zaman sebep belirtin
• Reply ile kullanmayı tercih edin
• Rate limiting'e dikkat edin
• Logları kontrol edin
• Yardım isteklerine hızlı yanıt verin

🚀 <b>İyi moderasyonlar!</b>
        """
        
        # Özelden gönder
        try:
            if chat_type == "private":
                await message.reply(commands_text, parse_mode="HTML")
            elif _bot_instance:
                await _bot_instance.send_message(user_id, commands_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"❌ Mod komutları mesajı gönderilemedi: {e}")
            
    except Exception as e:
        logger.error(f"❌ !modkomut komutu hatası: {e}", exc_info=True)
        try:
            if message.chat.type == "private":
                await message.reply("❌ Bir hata oluştu! Lütfen tekrar deneyin.")
        except:
            pass


@router.message(F.text.startswith("!modaktif"))
async def set_moderator_active_command(message: Message) -> None:
    """!modaktif komutu - Mod'u aktif yap (sadece kendisi)"""
    try:
        user_id = message.from_user.id
        chat_type = message.chat.type
        
        # Mod kontrolü (aktif veya pasif olabilir)
        is_mod = await is_moderator(user_id, include_inactive=True)
        if not is_mod:
            if chat_type == "private":
                await message.reply("❌ Bu komutu sadece moderatörler kullanabilir!")
            return
        
        # Grupta ise mesajı sil
        if chat_type in ["group", "supergroup"]:
            try:
                await message.delete()
            except:
                pass
        
        # Mod'u aktif yap
        success = await set_moderator_active_status(user_id, True)
        
        if success:
            response = "✅ <b>Mod Durumu Güncellendi</b>\n\n"
            response += "🟢 <b>Durum:</b> Aktif\n"
            response += "📝 <b>Açıklama:</b> Artık mod listesinde görüneceksiniz.\n"
            response += "💡 <b>Not:</b> Mod yetkileriniz aktif ve listede görünüyorsunuz.\n\n"
            response += "🔒 <b>Pasif Olmak İçin:</b> <code>!modpasif</code> yazın."
        else:
            response = "❌ Mod durumu güncellenirken hata oluştu!"
        
        # Özelden gönder
        try:
            if chat_type == "private":
                await message.reply(response, parse_mode="HTML")
            elif _bot_instance:
                await _bot_instance.send_message(user_id, response, parse_mode="HTML")
        except Exception as e:
            logger.error(f"❌ Mod aktif mesajı gönderilemedi: {e}")
            
    except Exception as e:
        logger.error(f"❌ !modaktif komutu hatası: {e}", exc_info=True)
        try:
            if message.chat.type == "private":
                await message.reply("❌ Bir hata oluştu! Lütfen tekrar deneyin.")
        except:
            pass


# =============================================
# MOD KOMUTLARI - MESAJ SİLME, MUTE, SUSTUR
# =============================================

@router.message(F.text.startswith("!sil"))
async def delete_message_command(message: Message) -> None:
    """!sil komutu - Reply ile mesaj silme (Mod yetkisi gerekli)"""
    try:
        user_id = message.from_user.id
        chat = message.chat
        
        # Sadece grup/supergroup'da çalış
        if chat.type not in ["group", "supergroup"]:
            return
        
        # Mod kontrolü
        if not await is_moderator(user_id) and not is_admin(user_id):
            await message.reply("❌ Bu komutu kullanmak için mod yetkisine sahip olmalısınız!")
            return
        
        # Reply kontrolü
        if not message.reply_to_message:
            await message.reply("⚠️ Lütfen silmek istediğiniz mesaja yanıt verin!")
            return
        
        # Mesajı sil
        try:
            await message.reply_to_message.delete()
            logger.info(f"🗑️ Mesaj silindi - Chat: {chat.id}, Message ID: {message.reply_to_message.message_id}, By: {user_id}")
            
            # Komut mesajını da sil
            try:
                await message.delete()
            except:
                pass
        except TelegramBadRequest as e:
            if "message to delete not found" in str(e).lower():
                await message.reply("⚠️ Mesaj zaten silinmiş veya bulunamadı!")
            else:
                await message.reply(f"❌ Mesaj silinirken hata oluştu: {e}")
        except Exception as e:
            logger.error(f"❌ Mesaj silme hatası: {e}")
            await message.reply("❌ Mesaj silinirken hata oluştu!")
            
    except Exception as e:
        logger.error(f"❌ !sil komutu hatası: {e}", exc_info=True)
        try:
            await message.reply("❌ Bir hata oluştu!")
        except:
            pass


@router.message(F.text.startswith("!susturmakaldir"))
@router.message(F.text.startswith("!susturma kaldır"))
async def unmute_command_alias(message: Message) -> None:
    """!susturmakaldir komutu - Mute kaldırma (alias)"""
    # Aynı işlevi yapan !mkaldir komutunu çağır
    await unmute_command(message)


@router.message(F.text.startswith("!mkaldir"))
@router.message(F.text.startswith("!mkaldır"))
async def unmute_command(message: Message) -> None:
    """!mkaldir komutu - Mute kaldırma (Mod yetkisi gerekli)"""
    try:
        if not _bot_instance:
            return
        
        user_id = message.from_user.id
        chat = message.chat
        
        # Sadece grup/supergroup'da çalış
        if chat.type not in ["group", "supergroup"]:
            return
        
        # Mod kontrolü
        if not await is_moderator(user_id) and not is_admin(user_id):
            await message.reply("❌ Bu komutu kullanmak için mod yetkisine sahip olmalısınız!")
            return
        
        # Hedef kullanıcıyı belirle
        target_user = None
        
        # 1. Reply kontrolü
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user = message.reply_to_message.from_user
        # 2. Mention kontrolü
        elif message.entities:
            for entity in message.entities:
                if entity.type == "text_mention":
                    target_user = entity.user
                    break
        
        if not target_user:
            await message.reply("⚠️ Lütfen mute'unu kaldırmak istediğiniz kullanıcının mesajına yanıt verin veya etiketleyin!")
            return
        
        # Mute kaldır (lazy import to avoid circular dependency)
        from handlers.punishment_system import unmute_user
        success = await unmute_user(_bot_instance, chat.id, target_user.id, user_id)
        
        if success:
            await message.reply(f"""
✅ <b>Mute Kaldırıldı</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
🔓 <b>Durum:</b> Artık mesaj gönderebilir
👮 <b>Moderatör:</b> {message.from_user.first_name}
            """, parse_mode="HTML")
            
            # Komut mesajını sil
            try:
                await message.delete()
            except:
                pass
        else:
            await message.reply("❌ Mute kaldırılırken hata oluştu!")
            
    except Exception as e:
        logger.error(f"❌ !mkaldir komutu hatası: {e}", exc_info=True)
        try:
            await message.reply("❌ Bir hata oluştu!")
        except:
            pass


@router.message(F.text.startswith("!sustur"))
async def mute_command(message: Message) -> None:
    """Genişletilmiş !sustur komutu - Reply, mention, ID, özel mesaj, grup, sebep"""
    try:
        if not _bot_instance:
            return
        
        user_id = message.from_user.id
        chat = message.chat
        
        # Mod kontrolü
        if not await is_moderator(user_id) and not is_admin(user_id):
            if chat.type == "private":
                await message.reply("❌ Bu komutu kullanmak için mod yetkisine sahip olmalısınız!")
            return
        
        # Komut parametrelerini parse et
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) < 2:
            await message.reply("""
⚠️ <b>Kullanım:</b>

<b>Özel Mesajda:</b>
• <code>!sustur [grup_id] [süre] [user_id/@username] [sebep]</code>
• <code>!sustur [süre] [user_id/@username] [sebep]</code> (aktif gruplardan ilkini kullan)

<b>Grupta:</b>
• <code>!sustur [süre] [sebep]</code> (reply ile)
• <code>!sustur [süre] @username [sebep]</code>
• <code>!sustur [süre] [user_id] [sebep]</code>

<b>Örnek:</b>
• <code>!sustur 10 Spam</code> (reply ile - 10 dakika)
• <code>!sustur 30 @username Spam</code>
• <code>!sustur 15 123456789 Spam</code>
            """, parse_mode="HTML")
            return
        
        target_user = None
        duration = None
        reason = None
        group_id = None
        
        # Özel mesajda mı?
        if chat.type == "private":
            # Özel mesajda: !sustur [grup_id] [süre] [user_id/@username] [sebep]
            # Veya: !sustur [süre] [user_id/@username] [sebep]
            
            # İlk parametre grup ID mi?
            if len(parts) >= 2 and parts[1].startswith("-") and parts[1][1:].isdigit():
                group_id = int(parts[1])
                # İkinci parametre süre
                if len(parts) >= 3:
                    try:
                        duration = int(parts[2])
                        if duration <= 0:
                            await message.reply("❌ Süre pozitif bir sayı olmalı!")
                            return
                    except ValueError:
                        await message.reply("❌ Geçersiz süre!")
                        return
                    # Üçüncü parametre user_id/@username
                    if len(parts) >= 4:
                        user_param = parts[3]
                        # Sebep varsa al
                        if len(parts) >= 5:
                            reason = " ".join(parts[4:])
                    else:
                        await message.reply("❌ Kullanıcı belirtilmedi!")
                        return
                else:
                    await message.reply("❌ Süre belirtilmedi!")
                    return
            else:
                # İlk parametre süre, aktif gruplardan ilkini kullan
                from handlers.mod_warning_system import get_active_groups_for_user
                active_groups = await get_active_groups_for_user(user_id)
                if not active_groups:
                    await message.reply("❌ Aktif grup bulunamadı! Lütfen grup ID'si belirtin.")
                    return
                group_id = active_groups[0]
                
                # İlk parametre süre
                try:
                    duration = int(parts[1])
                    if duration <= 0:
                        await message.reply("❌ Süre pozitif bir sayı olmalı!")
                        return
                except ValueError:
                    await message.reply("❌ Geçersiz süre!")
                    return
                
                # İkinci parametre user_id/@username
                if len(parts) >= 3:
                    user_param = parts[2]
                    # Sebep varsa al
                    if len(parts) >= 4:
                        reason = " ".join(parts[3:])
                else:
                    await message.reply("❌ Kullanıcı belirtilmedi!")
                    return
            
            # Kullanıcıyı bul
            from handlers.mod_warning_system import find_user_by_username_or_id
            target_user_dict = await find_user_by_username_or_id(user_param, group_id)
            if not target_user_dict:
                await message.reply(f"❌ Kullanıcı bulunamadı: {user_param}")
                return
            
            # Telegram User objesi oluştur
            from aiogram.types import User
            target_user = User(
                id=target_user_dict["user_id"],
                is_bot=False,
                first_name=target_user_dict.get("first_name", "Kullanıcı"),
                username=target_user_dict.get("username"),
                last_name=target_user_dict.get("last_name")
            )
            
        else:
            # Grupta
            group_id = chat.id
            
            # Süreyi al (ilk parametre)
            try:
                duration = int(parts[1])
                if duration <= 0:
                    await message.reply("❌ Süre pozitif bir sayı olmalı!")
                    return
            except ValueError:
                await message.reply("❌ Geçersiz süre! Örnek: <code>!sustur 10</code>", parse_mode="HTML")
                return
            
            # 1. Reply kontrolü
            if message.reply_to_message and message.reply_to_message.from_user:
                target_user = message.reply_to_message.from_user
                # Sebep varsa al
                if len(parts) >= 3:
                    reason = " ".join(parts[2:])
            # 2. Mention kontrolü
            elif message.entities and len(parts) >= 3:
                for entity in message.entities:
                    if entity.type == "text_mention":
                        target_user = entity.user
                        # Sebep varsa al
                        if len(parts) >= 3:
                            reason = " ".join(parts[2:])
                        break
                    elif entity.type == "mention":
                        username = message.text[entity.offset+1:entity.offset+entity.length]
                        from handlers.mod_warning_system import find_user_by_username_or_id
                        target_user_dict = await find_user_by_username_or_id(username, group_id)
                        if target_user_dict:
                            from aiogram.types import User
                            target_user = User(
                                id=target_user_dict["user_id"],
                                is_bot=False,
                                first_name=target_user_dict.get("first_name", "Kullanıcı"),
                                username=target_user_dict.get("username"),
                                last_name=target_user_dict.get("last_name")
                            )
                            # Sebep varsa al
                            if len(parts) >= 3:
                                reason = " ".join(parts[2:])
                        break
            # 3. ID kontrolü (ikinci parametre sayı ise)
            elif len(parts) >= 3 and parts[2].isdigit():
                user_id_param = int(parts[2])
                from handlers.mod_warning_system import find_user_by_username_or_id
                target_user_dict = await find_user_by_username_or_id(str(user_id_param), group_id)
                if target_user_dict:
                    from aiogram.types import User
                    target_user = User(
                        id=target_user_dict["user_id"],
                        is_bot=False,
                        first_name=target_user_dict.get("first_name", "Kullanıcı"),
                        username=target_user_dict.get("username"),
                        last_name=target_user_dict.get("last_name")
                    )
                    # Sebep varsa al
                    if len(parts) >= 4:
                        reason = " ".join(parts[3:])
            
            if not target_user:
                await message.reply("""
⚠️ <b>Kullanım:</b>

• <code>!sustur [süre] [sebep]</code> (reply ile)
• <code>!sustur [süre] @username [sebep]</code>
• <code>!sustur [süre] [user_id] [sebep]</code>

<b>Örnek:</b>
• <code>!sustur 10 Spam</code> (reply ile)
• <code>!sustur 30 @username Spam</code>
• <code>!sustur 15 123456789 Spam</code>
                """, parse_mode="HTML")
                return
        
        # Kendini susturamaz
        if target_user.id == user_id:
            await message.reply("❌ Kendinizi susturamazsınız!")
            return
        
        # Yetki kontrolü
        from handlers.punishment_system import can_punish_user
        if not await can_punish_user(user_id, target_user.id):
            await message.reply("❌ Bu kullanıcıyı cezalandırma yetkiniz yok!")
            return
        
        # Mute işlemi
        from handlers.punishment_system import mute_user, log_punishment, send_punishment_notification
        success = await mute_user(_bot_instance, group_id, target_user.id, duration, user_id)
        
        if success:
            await log_punishment(target_user.id, group_id, "mute", duration, user_id, reason)
            await send_punishment_notification(_bot_instance, target_user.id, 0, "mute", duration, reason)
            
            response = f"""
🔇 <b>KULLANICI SUSTURULDU</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
⏱️ <b>Süre:</b> {duration} dakika
💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}
👮 <b>Moderatör:</b> {message.from_user.first_name}
            """
            
            # Özel mesajda mı?
            if chat.type == "private":
                await message.reply(response, parse_mode="HTML")
            else:
                await message.reply(response, parse_mode="HTML")
                
                # Komut mesajını sil
                try:
                    await message.delete()
                except:
                    pass
        else:
            await message.reply("❌ Kullanıcı susturulurken hata oluştu!")
            
    except Exception as e:
        logger.error(f"❌ !sustur komutu hatası: {e}", exc_info=True)
        try:
            await message.reply("❌ Bir hata oluştu!")
        except:
            pass


# =============================================
# MOD AKTİVİTE TAKİBİ VE BİLDİRİM SİSTEMİ
# =============================================

async def record_mod_activity(group_id: int, user_id: int):
    """Mod aktivitesini kaydet - Mod'un son mesaj zamanını güncelle"""
    try:
        current_time = datetime.now()
        
        # Grup için mod aktivite dict'i oluştur
        if group_id not in mod_activity_by_group:
            mod_activity_by_group[group_id] = {}
        
        # Mod'un son mesaj zamanını güncelle
        mod_activity_by_group[group_id][user_id] = current_time
        
        logger.debug(f"📝 Mod aktivitesi kaydedildi - Group: {group_id}, Mod: {user_id}")
        
    except Exception as e:
        logger.debug(f"⏸️ Mod aktivite kayıt hatası (kritik değil): {e}")


async def check_active_chat_and_notify_mods():
    """Aktif sohbet kontrolü ve mod bildirimi - Arka plan görevi"""
    try:
        if not _bot_instance:
            return
        
        # Database'den aktif modları al
        active_mods = await get_moderators_from_db(include_inactive=False)
        if not active_mods:
            return
        
        # Tüm grupları kontrol et
        from handlers.group_activity_monitor import group_activity_status
        
        current_time = datetime.now()
        
        for group_id, group_status in group_activity_status.items():
            try:
                # Son mesaj zamanını kontrol et
                last_message_time = group_status.get('last_message_time')
                if not last_message_time:
                    continue
                
                # Son mesajın bot tarafından gönderilip gönderilmediğini kontrol et
                is_bot_message = group_status.get('is_bot_message', False)
                if is_bot_message:
                    # Son mesaj bot tarafından gönderildiyse, bildirim gönderme (spam önleme)
                    continue
                
                # Son mesaj zamanı kontrolü (aktif sohbet eşiği)
                time_diff = current_time - last_message_time
                minutes_since_last_message = time_diff.total_seconds() / 60
                
                # Eğer son 15 dakikada mesaj yoksa aktif sohbet sayılmaz
                if minutes_since_last_message > ACTIVE_CHAT_THRESHOLD_MINUTES:
                    continue  # Aktif sohbet değil, atla
                
                # Bu grup için bildirim cooldown kontrolü
                if group_id in mod_notification_cooldown:
                    last_notification = mod_notification_cooldown[group_id]
                    time_since_notification = current_time - last_notification
                    if time_since_notification.total_seconds() / 60 < MOD_NOTIFICATION_COOLDOWN_MINUTES:
                        continue  # Cooldown aktif, atla
                
                # Bu gruptaki mod aktivitelerini kontrol et
                group_mod_activity = mod_activity_by_group.get(group_id, {})
                
                # Aktif modları kontrol et - En az bir mod son 5 dakikada yazmış mı?
                active_mods_in_group = []
                for mod in active_mods:
                    mod_id = mod['user_id']
                    mod_last_activity = group_mod_activity.get(mod_id)
                    
                    if mod_last_activity:
                        mod_time_diff = current_time - mod_last_activity
                        mod_minutes_inactive = mod_time_diff.total_seconds() / 60
                        
                        # Mod son 10 dakikada yazmışsa aktif sayılır
                        if mod_minutes_inactive <= MOD_INACTIVE_THRESHOLD_MINUTES:
                            active_mods_in_group.append(mod)
                
                # Eğer hiç aktif mod yoksa, tüm aktif modlara bildirim gönder
                if not active_mods_in_group:
                    # Grup adını al
                    try:
                        chat = await _bot_instance.get_chat(group_id)
                        group_name = chat.title or f"Grup {group_id}"
                    except:
                        group_name = f"Grup {group_id}"
                    
                    # Bildirim mesajı (daha kısa ve öz)
                    notification = f"""
🔔 <b>AKTİF SOHBET BİLDİRİMİ</b>

💬 <b>Grup:</b> {group_name}
🆔 <b>Grup ID:</b> <code>{group_id}</code>

📝 <b>Durum:</b> Grupta aktif sohbet var (son {int(minutes_since_last_message)} dakika)
⏰ <b>Son Mesaj:</b> {last_message_time.strftime('%H:%M:%S')}

⚠️ <b>Not:</b> Mod yok, kontrol edin.

🕐 <b>Zaman:</b> {current_time.strftime('%d.%m.%Y %H:%M:%S')}
                    """
                    
                    # Tüm aktif modlara özelden bildirim gönder
                    sent_count = 0
                    for mod in active_mods:
                        try:
                            await _bot_instance.send_message(
                                mod['user_id'],
                                notification,
                                parse_mode="HTML"
                            )
                            sent_count += 1
                            await asyncio.sleep(0.1)  # Rate limiting
                        except Exception as e:
                            logger.debug(f"⏸️ Mod bildirimi gönderilemedi - Mod: {mod['user_id']}, Error: {e}")
                    
                    # Bildirim cooldown'unu güncelle
                    mod_notification_cooldown[group_id] = current_time
                    
                    if sent_count > 0:
                        logger.info(f"✅ {sent_count} mod'a aktif sohbet bildirimi gönderildi - Group: {group_id}")
                
            except Exception as e:
                logger.debug(f"⏸️ Grup kontrolü hatası (kritik değil) - Group: {group_id}, Error: {e}")
        
    except Exception as e:
        logger.error(f"❌ Aktif sohbet kontrolü hatası: {e}", exc_info=True)


async def mod_activity_monitor_task():
    """Mod aktivite takibi arka plan görevi - Periyodik olarak çalışır"""
    try:
        logger.info("🛡️ Mod aktivite takibi başlatıldı")
        
        while True:
            try:
                # Aktif sohbet kontrolü ve mod bildirimi
                await check_active_chat_and_notify_mods()
                
                # Belirtilen aralıkta tekrar kontrol et
                await asyncio.sleep(MOD_ACTIVITY_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"❌ Mod aktivite takibi görevi hatası: {e}", exc_info=True)
                # Hata durumunda kısa bir bekleme sonrası devam et
                await asyncio.sleep(60)  # 1 dakika bekle
                
    except Exception as e:
        logger.error(f"❌ Mod aktivite takibi görevi kritik hatası: {e}", exc_info=True)


# =============================================
# MOD GÜNLÜK ANALİZ SİSTEMİ
# =============================================

async def generate_mod_daily_report(mod_user_id: int, include_today: bool = False) -> Dict[str, Any]:
    """Mod için günlük analiz raporu oluştur
    
    Args:
        mod_user_id: Mod kullanıcı ID'si
        include_today: True ise bugünkü verileri de dahil et (komut ile talep edildiğinde)
    """
    try:
        pool = await get_db_pool()
        if not pool:
            return {}
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Hangi tarih aralığını kullanacağız?
        if include_today:
            # Bugünkü verileri de dahil et (komut ile talep edildiğinde)
            report_date = today
            date_filter = today
            report_date_text = f"{today.strftime('%d.%m.%Y')} (Bugün dahil)"
        else:
            # Sadece dünkü veriler (otomatik rapor için)
            report_date = yesterday
            date_filter = yesterday
            report_date_text = yesterday.strftime('%d.%m.%Y')
        
        async with pool.acquire() as conn:
            # Mod bilgilerini al
            mod_info = await conn.fetchrow("""
                SELECT user_id, username, first_name, last_name, is_active
                FROM moderators
                WHERE user_id = $1
            """, mod_user_id)
            
            if not mod_info:
                return {}
            
            # Mesaj sayısı (dün veya bugün dahil)
            period_messages = await conn.fetchval("""
                SELECT COALESCE(SUM(message_count), 0)
                FROM daily_stats
                WHERE user_id = $1 AND message_date = $2
            """, mod_user_id, date_filter)
            
            # Toplam mesaj sayısı (tüm zamanlar)
            total_messages = await conn.fetchval("""
                SELECT COALESCE(total_messages, 0)
                FROM users
                WHERE user_id = $1
            """, mod_user_id)
            
            # En aktif olduğu grup (dünkü veya bugünkü mesaj sayısına göre)
            most_active_group = await conn.fetchrow("""
                SELECT ds.group_id, rg.group_name, ds.message_count
                FROM daily_stats ds
                LEFT JOIN registered_groups rg ON ds.group_id = rg.group_id
                WHERE ds.user_id = $1 AND ds.message_date = $2
                ORDER BY ds.message_count DESC
                LIMIT 1
            """, mod_user_id, date_filter)
            
            # Mod aktivite takibi - Mod olarak mesaj yazmadığı süre
            mod_inactive_time = None
            # mod_activity_by_group yapısı: {group_id: {mod_user_id: datetime}}
            all_last_activity = []
            for group_id, mod_activities in mod_activity_by_group.items():
                if mod_user_id in mod_activities:
                    all_last_activity.append(mod_activities[mod_user_id])
            
            if all_last_activity:
                last_activity = max(all_last_activity)
                inactive_duration = datetime.now() - last_activity
                mod_inactive_time = {
                    "hours": int(inactive_duration.total_seconds() / 3600),
                    "minutes": int((inactive_duration.total_seconds() % 3600) / 60)
                }
            
            # Mod performans skoru (basit hesaplama)
            # Mesaj sayısı + aktiflik durumu
            performance_score = 0
            if period_messages:
                performance_score += min(period_messages * 10, 100)  # Max 100 puan
            
            if mod_inactive_time:
                inactive_hours = mod_inactive_time["hours"]
                if inactive_hours < 2:
                    performance_score += 50  # Çok aktif
                elif inactive_hours < 6:
                    performance_score += 30  # Aktif
                elif inactive_hours < 12:
                    performance_score += 10  # Orta
                # 12+ saat = 0 puan
            
            # Mod cezalandırma işlemleri (dünkü veya bugünkü)
            period_punishments = await conn.fetchval("""
                SELECT COUNT(*)
                FROM punishment_logs
                WHERE punished_by = $1 
                AND DATE(created_at) = $2
            """, mod_user_id, date_filter)
            
            # Mod yardım isteklerine yanıt (dünkü)
            # Bu veri şu an yok, ileride eklenebilir
            
            return {
                "mod_info": {
                    "user_id": mod_info["user_id"],
                    "username": mod_info["username"],
                    "first_name": mod_info["first_name"],
                    "is_active": mod_info["is_active"]
                },
                "period_messages": period_messages or 0,
                "total_messages": total_messages or 0,
                "most_active_group": {
                    "group_id": most_active_group["group_id"] if most_active_group else None,
                    "group_name": most_active_group["group_name"] if most_active_group else None,
                    "message_count": most_active_group["message_count"] if most_active_group else 0
                },
                "mod_inactive_time": mod_inactive_time,
                "performance_score": min(performance_score, 100),
                "period_punishments": period_punishments or 0,
                "report_date": report_date_text,
                "include_today": include_today
            }
            
    except Exception as e:
        logger.error(f"❌ Mod günlük rapor hatası - Mod: {mod_user_id}, Error: {e}", exc_info=True)
        return {}


async def send_mod_daily_report(mod_user_id: int, report_data: Dict[str, Any]) -> bool:
    """Mod'a günlük analiz raporunu özelden gönder"""
    try:
        if not _bot_instance or not report_data:
            return False
        
        mod_info = report_data.get("mod_info", {})
        mod_name = mod_info.get("first_name", "Mod")
        
        # Rapor mesajı oluştur
        include_today = report_data.get('include_today', False)
        period_label = "Bugünkü" if include_today else "Dünkü"
        
        report_message = f"""
📊 <b>MOD GÜNLÜK ANALİZ RAPORU</b>

📅 <b>Tarih:</b> {report_data.get('report_date', 'Bilinmiyor')}
👤 <b>Mod:</b> {mod_name} {f"(@{mod_info.get('username')})" if mod_info.get('username') else ""}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 <b>MESAJ İSTATİSTİKLERİ:</b>
• {period_label} Mesaj: <code>{report_data.get('period_messages', 0)}</code>
• Toplam Mesaj: <code>{report_data.get('total_messages', 0)}</code>

💬 <b>EN AKTİF GRUP:</b>
"""
        
        most_active = report_data.get("most_active_group", {})
        if most_active.get("group_name"):
            report_message += f"• Grup: {most_active['group_name']}\n"
            report_message += f"• Mesaj: <code>{most_active.get('message_count', 0)}</code>\n"
        else:
            period_text = "bugün" if include_today else "dün"
            report_message += f"• {period_text.capitalize()} hiç mesaj yazılmamış\n"
        
        report_message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Modsuz geçen süre
        inactive_time = report_data.get("mod_inactive_time")
        if inactive_time:
            hours = inactive_time.get("hours", 0)
            minutes = inactive_time.get("minutes", 0)
            if hours > 0 or minutes > 0:
                report_message += f"⏰ <b>MODSUZ GEÇEN SÜRE:</b>\n"
                report_message += f"• <code>{hours} saat {minutes} dakika</code>\n\n"
            else:
                report_message += f"✅ <b>DURUM:</b> Aktif (son mesajdan bu yana çok kısa süre geçti)\n\n"
        else:
            report_message += f"⚠️ <b>DURUM:</b> Mod aktivite verisi bulunamadı\n\n"
        
        report_message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Performans skoru
        performance_score = report_data.get("performance_score", 0)
        if performance_score >= 80:
            score_emoji = "🟢"
            score_text = "Mükemmel"
        elif performance_score >= 60:
            score_emoji = "🟡"
            score_text = "İyi"
        elif performance_score >= 40:
            score_emoji = "🟠"
            score_text = "Orta"
        else:
            score_emoji = "🔴"
            score_text = "Düşük"
        
        report_message += f"{score_emoji} <b>PERFORMANS SKORU:</b> <code>{performance_score}/100</code> ({score_text})\n\n"
        
        # Cezalandırma işlemleri
        punishments = report_data.get("period_punishments", 0)
        if punishments > 0:
            period_text = "bugünkü" if include_today else "dünkü"
            report_message += f"🛡️ <b>CEZALANDIRMA İŞLEMLERİ ({period_text.capitalize()}):</b> <code>{punishments}</code> işlem\n\n"
        
        report_message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        if include_today:
            report_message += "💡 <b>Not:</b> Bu rapor komut ile talep edilmiştir (bugünkü veriler dahil).\n"
        else:
            report_message += "💡 <b>Not:</b> Bu rapor her 24 saatte bir otomatik olarak gönderilir.\n"
        report_message += "📊 Tekrar rapor almak için <code>!modrapor</code> komutunu kullanabilirsiniz."
        
        # Mod'a özelden gönder
        await _bot_instance.send_message(
            mod_user_id,
            report_message,
            parse_mode="HTML"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Mod günlük rapor gönderme hatası - Mod: {mod_user_id}, Error: {e}", exc_info=True)
        return False


async def send_daily_reports_to_all_mods():
    """Tüm aktif modlara günlük rapor gönder"""
    try:
        if not _bot_instance:
            return
        
        # Aktif modları al
        active_mods = await get_moderators_from_db(include_inactive=False)
        
        if not active_mods:
            logger.info("ℹ️ Aktif mod bulunamadı, rapor gönderilemedi")
            return
        
        logger.info(f"📊 {len(active_mods)} mod'a günlük rapor gönderiliyor...")
        
        sent_count = 0
        failed_count = 0
        
        for mod in active_mods:
            try:
                mod_user_id = mod['user_id']
                
                # Rapor oluştur (otomatik rapor - sadece dünkü veriler)
                report_data = await generate_mod_daily_report(mod_user_id, include_today=False)
                
                if report_data:
                    # Rapor gönder
                    success = await send_mod_daily_report(mod_user_id, report_data)
                    
                    if success:
                        sent_count += 1
                        logger.info(f"✅ Mod günlük rapor gönderildi - Mod: {mod_user_id}")
                    else:
                        failed_count += 1
                        logger.warning(f"⚠️ Mod günlük rapor gönderilemedi - Mod: {mod_user_id}")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ Mod günlük rapor oluşturulamadı - Mod: {mod_user_id}")
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Mod rapor hatası - Mod: {mod.get('user_id')}, Error: {e}", exc_info=True)
        
        logger.info(f"📊 Günlük rapor gönderimi tamamlandı - Başarılı: {sent_count}, Başarısız: {failed_count}")
        
    except Exception as e:
        logger.error(f"❌ Günlük rapor gönderme hatası: {e}", exc_info=True)


async def cleanup_old_mod_help_requests():
    """Eski mod yardım isteklerini temizle - 30 günden eski kayıtları sil"""
    try:
        from database import get_db_pool
        pool = await get_db_pool()
        if not pool:
            return
        
        async with pool.acquire() as conn:
            # 30 günden eski kayıtları sil
            result = await conn.execute("""
                DELETE FROM mod_help_requests
                WHERE requested_at < NOW() - INTERVAL '30 days'
            """)
            
            # Silinen kayıt sayısını al
            deleted_count = int(result.split()[-1]) if result.startswith("DELETE") else 0
            
            if deleted_count > 0:
                logger.info(f"🧹 {deleted_count} eski mod yardım isteği kaydı temizlendi (30 günden eski)")
            else:
                logger.debug(f"🧹 Eski mod yardım isteği kaydı bulunamadı (30 günden eski)")
                
    except Exception as e:
        logger.debug(f"⏸️ Mod yardım istekleri temizleme hatası (kritik değil): {e}")


async def mod_daily_report_task():
    """Mod günlük rapor arka plan görevi - Her 24 saatte bir çalışır"""
    try:
        logger.info("📊 Mod günlük rapor sistemi başlatıldı")
        
        # İlk çalıştırmayı hesapla - Her gün saat 00:00'da çalışsın
        now = datetime.now()
        next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Eğer bugün 00:00 geçtiyse, yarın 00:00'ı hesapla
        if now >= next_run:
            next_run += timedelta(days=1)
        
        # İlk çalıştırmaya kadar bekle
        wait_seconds = (next_run - now).total_seconds()
        logger.info(f"⏰ İlk rapor {next_run.strftime('%d.%m.%Y %H:%M:%S')} tarihinde gönderilecek ({int(wait_seconds/3600)} saat sonra)")
        
        await asyncio.sleep(wait_seconds)
        
        # İlk raporu gönder
        await send_daily_reports_to_all_mods()
        
        # Eski kayıtları temizle (ilk çalıştırmada)
        await cleanup_old_mod_help_requests()
        
        # Her 24 saatte bir tekrarla
        while True:
            await asyncio.sleep(86400)  # 24 saat = 86400 saniye
            await send_daily_reports_to_all_mods()
            # Her gün eski kayıtları temizle
            await cleanup_old_mod_help_requests()
            
    except Exception as e:
        logger.error(f"❌ Mod günlük rapor görevi kritik hatası: {e}", exc_info=True)
