"""
🛡️ Mod Uyarı Sistemi - Genişletilmiş Versiyon
Reply, mention, ID ile çalışır, özel mesajda ve grupta çalışır
"""

import logging
from typing import Optional
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command

from utils.logger import logger
from config import is_admin
from handlers.mod_handler import is_moderator
from handlers.punishment_system import (
    add_warning, mute_user, ban_user, unban_user, log_punishment, 
    send_punishment_notification, send_group_warning_notification,
    delete_user_recent_messages, can_punish_user, get_user_warnings
)
from database import get_db_pool

router = Router()

_bot_instance: Optional[Bot] = None

def set_bot_instance(bot_instance: Bot):
    """Bot instance'ını set et"""
    global _bot_instance
    _bot_instance = bot_instance


async def find_user_by_username_or_id(username_or_id: str, group_id: int = None) -> Optional[dict]:
    """Username veya ID'den kullanıcı bul"""
    try:
        if not _bot_instance:
            return None
        
        # ID kontrolü
        if username_or_id.isdigit():
            user_id = int(username_or_id)
            try:
                # Grup içinde kullanıcıyı bul
                if group_id:
                    member = await _bot_instance.get_chat_member(group_id, user_id)
                    return {
                        "user_id": member.user.id,
                        "username": member.user.username,
                        "first_name": member.user.first_name,
                        "last_name": member.user.last_name
                    }
                else:
                    # Özel mesajda direkt kullanıcı bilgisi al
                    chat = await _bot_instance.get_chat(user_id)
                    return {
                        "user_id": chat.id,
                        "username": getattr(chat, 'username', None),
                        "first_name": getattr(chat, 'first_name', None),
                        "last_name": getattr(chat, 'last_name', None)
                    }
            except Exception as e:
                logger.debug(f"⏸️ Kullanıcı bulunamadı (ID): {e}")
                return None
        
        # Username kontrolü (@ işareti varsa kaldır)
        if username_or_id.startswith("@"):
            username = username_or_id[1:]
        else:
            username = username_or_id
        
        # Database'den username ile kullanıcı bul
        pool = await get_db_pool()
        if pool:
            async with pool.acquire() as conn:
                user = await conn.fetchrow("""
                    SELECT user_id, username, first_name, last_name
                    FROM users WHERE username = $1
                """, username)
                
                if user:
                    return {
                        "user_id": user['user_id'],
                        "username": user['username'],
                        "first_name": user['first_name'],
                        "last_name": user['last_name']
                    }
        
        # Grup içinde username ile kullanıcı bul
        if group_id:
            try:
                # Telegram API'de username ile direkt arama yok, database'den bulduk
                # Ama grup içinde kontrol edelim
                pass
            except:
                pass
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Kullanıcı bulma hatası: {e}")
        return None


async def get_active_groups_for_user(user_id: int) -> list:
    """Kullanıcının aktif olduğu grupları getir"""
    try:
        pool = await get_db_pool()
        if not pool:
            return []
        
        async with pool.acquire() as conn:
            groups = await conn.fetch("""
                SELECT DISTINCT group_id 
                FROM daily_stats 
                WHERE user_id = $1
                ORDER BY message_date DESC
                LIMIT 10
            """, user_id)
            
            return [row['group_id'] for row in groups]
            
    except Exception as e:
        logger.error(f"❌ Aktif gruplar getirme hatası: {e}")
        return []


@router.message(Command("uyarı", "warn"))
@router.message(F.text.startswith("!uyarı"))
@router.message(F.text.startswith("!uyari"))
async def warn_command_extended(message: Message):
    """Genişletilmiş uyarı komutu - Reply, mention, ID, özel mesaj, grup"""
    try:
        if not _bot_instance:
            return
        
        user = message.from_user
        chat = message.chat
        
        # Yetki kontrolü
        if not await can_punish_user(user.id, 0):
            if chat.type == "private":
                await message.reply("❌ Bu komutu kullanmak için mod veya admin yetkisine sahip olmalısınız!")
            return
        
        # Komut parametrelerini parse et
        text = message.text.strip()
        parts = text.split()
        
        target_user = None
        reason = None
        group_id = None
        
        # Özel mesajda mı?
        if chat.type == "private":
            # Özel mesajda: !uyarı [grup_id] [user_id/@username] [sebep]
            # Veya: !uyarı [user_id/@username] [sebep] (aktif gruplardan ilkini kullan)
            
            if len(parts) < 2:
                # Aktif grupları listele
                active_groups = await get_active_groups_for_user(user.id)
                if not active_groups:
                    await message.reply("""
⚠️ <b>Kullanım:</b>

<b>Özel Mesajda:</b>
• <code>!uyarı [grup_id] [user_id/@username] [sebep]</code>
• <code>!uyarı [user_id/@username] [sebep]</code> (aktif gruplardan ilkini kullan)

<b>Grupta:</b>
• <code>!uyarı [sebep]</code> (reply ile)
• <code>!uyarı @username [sebep]</code>
• <code>!uyarı [user_id] [sebep]</code>

<b>Örnek:</b>
• <code>!uyarı -1001234567890 123456789 Spam</code>
• <code>!uyarı @username Spam</code>
• <code>!uyarı 123456789 Spam</code>
                    """, parse_mode="HTML")
                    return
                
                # Aktif grupları göster
                groups_text = "\n".join([f"• <code>{gid}</code>" for gid in active_groups[:5]])
                await message.reply(f"""
⚠️ <b>Lütfen grup ID'si belirtin:</b>

<b>Aktif Gruplarınız:</b>
{groups_text}

<b>Kullanım:</b>
<code>!uyarı [grup_id] [user_id/@username] [sebep]</code>
                """, parse_mode="HTML")
                return
            
            # Grup ID kontrolü (ilk parametre sayı ise grup ID olabilir)
            if len(parts) >= 2:
                # İlk parametre grup ID mi?
                if parts[1].startswith("-") and parts[1][1:].isdigit():
                    group_id = int(parts[1])
                    # İkinci parametre user_id/@username
                    if len(parts) >= 3:
                        user_param = parts[2]
                        # Sebep varsa al
                        if len(parts) >= 4:
                            reason = " ".join(parts[3:])
                    else:
                        await message.reply("❌ Kullanıcı belirtilmedi!")
                        return
                else:
                    # İlk parametre user_id/@username, aktif gruplardan ilkini kullan
                    active_groups = await get_active_groups_for_user(user.id)
                    if not active_groups:
                        await message.reply("❌ Aktif grup bulunamadı! Lütfen grup ID'si belirtin.")
                        return
                    group_id = active_groups[0]
                    user_param = parts[1]
                    # Sebep varsa al
                    if len(parts) >= 3:
                        reason = " ".join(parts[2:])
            
            # Kullanıcıyı bul
            target_user_dict = await find_user_by_username_or_id(user_param, group_id)
            if not target_user_dict:
                await message.reply(f"❌ Kullanıcı bulunamadı: {user_param}")
                return
            
            # Telegram User objesi oluştur (basit versiyon)
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
            
            # 1. Reply kontrolü
            if message.reply_to_message and message.reply_to_message.from_user:
                target_user = message.reply_to_message.from_user
                # Sebep mesajdan al
                if len(parts) > 1:
                    reason = " ".join(parts[1:])
            # 2. Mention kontrolü
            elif message.entities:
                for entity in message.entities:
                    if entity.type == "text_mention":
                        target_user = entity.user
                        # Sebep mesajdan al
                        if len(parts) > 1:
                            reason = " ".join(parts[1:])
                        break
                    elif entity.type == "mention":
                        username = message.text[entity.offset+1:entity.offset+entity.length]
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
                            # Sebep mesajdan al
                            if len(parts) > 1:
                                reason = " ".join(parts[1:])
                        break
            # 3. ID kontrolü (ilk parametre sayı ise)
            elif len(parts) >= 2 and parts[1].isdigit():
                user_id_param = int(parts[1])
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
                    if len(parts) >= 3:
                        reason = " ".join(parts[2:])
            
            if not target_user:
                await message.reply("""
⚠️ <b>Kullanım:</b>

• <code>!uyarı [sebep]</code> (reply ile)
• <code>!uyarı @username [sebep]</code>
• <code>!uyarı [user_id] [sebep]</code>

<b>Örnek:</b>
• <code>!uyarı Spam yapıyor</code> (reply ile)
• <code>!uyarı @username Spam</code>
• <code>!uyarı 123456789 Spam</code>
                """, parse_mode="HTML")
                return
        
        # Kendini uyaramaz
        if target_user.id == user.id:
            await message.reply("❌ Kendinize uyarı veremezsiniz!")
            return
        
        # Yetki kontrolü (hedef kullanıcı için)
        if not await can_punish_user(user.id, target_user.id):
            await message.reply("❌ Bu kullanıcıyı cezalandırma yetkiniz yok!")
            return
        
        # Uyarı ekle
        result = await add_warning(target_user.id, group_id, user.id, reason)
        
        if not result.get("success"):
            await message.reply(f"❌ Uyarı eklenirken hata oluştu: {result.get('error', 'Bilinmeyen hata')}")
            return
        
        warning_count = result["warning_count"]
        
        # Uyarı sayısına göre işlem yap
        mute_success = False
        ban_success = False
        
        if warning_count == 1:
            # İlk uyarı: 5 dakika mute
            mute_success = await mute_user(_bot_instance, group_id, target_user.id, 5, user.id)
            if mute_success:
                await log_punishment(target_user.id, group_id, "mute", 5, user.id, reason)
                await send_punishment_notification(_bot_instance, target_user.id, 1, "warning", 5, reason)
                
        elif warning_count == 2:
            # İkinci uyarı: 30 dakika mute
            mute_success = await mute_user(_bot_instance, group_id, target_user.id, 30, user.id)
            if mute_success:
                await log_punishment(target_user.id, group_id, "mute", 30, user.id, reason)
                await send_punishment_notification(_bot_instance, target_user.id, 2, "warning", 30, reason)
                
        elif warning_count >= 3:
            # Üçüncü uyarı: Ban
            ban_success = await ban_user(_bot_instance, group_id, target_user.id, user.id)
            if ban_success:
                await log_punishment(target_user.id, group_id, "ban", 0, user.id, reason)
                await send_punishment_notification(_bot_instance, target_user.id, 3, "ban", None, reason)
        
        # Duration text oluştur
        duration_text = ""
        if warning_count == 1:
            duration_text = "🔇 <b>Süre:</b> 5 dakika susturma ✅" if mute_success else "🔇 <b>Süre:</b> 5 dakika susturma (uygulanamadı)"
        elif warning_count == 2:
            duration_text = "🔇 <b>Süre:</b> 30 dakika susturma ✅" if mute_success else "🔇 <b>Süre:</b> 30 dakika susturma (uygulanamadı)"
        elif warning_count >= 3:
            duration_text = "🚫 <b>Sonuç:</b> Kalıcı ban ✅" if ban_success else "🚫 <b>Sonuç:</b> Kalıcı ban (uygulanamadı)"
        
        # Özel mesajda mı?
        if chat.type == "private":
            # Özel mesajda özel bildirim
            response = f"""
⚠️ <b>UYARI VERİLDİ</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
🆔 <b>ID:</b> <code>{target_user.id}</code>
📊 <b>Uyarı Sayısı:</b> {warning_count}/3
💬 <b>Grup ID:</b> <code>{group_id}</code>
💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}

{duration_text}
            """
            await message.reply(response, parse_mode="HTML")
        else:
            # Grupta grup bildirimi gönder
            await send_group_warning_notification(
                _bot_instance,
                group_id,
                target_user,
                user,
                warning_count,
                reason,
                duration_text
            )
            
            # Kullanıcının son 10 mesajını sil
            reply_message_id = message.reply_to_message.message_id if message.reply_to_message else None
            deleted_count = await delete_user_recent_messages(_bot_instance, group_id, target_user.id, reply_message_id, 10)
            if deleted_count > 0:
                logger.info(f"🗑️ {deleted_count} mesaj silindi - User: {target_user.id}, Chat: {group_id}")
            
            # Komut mesajını sil
            try:
                await message.delete()
            except:
                pass
        
    except Exception as e:
        logger.error(f"❌ Uyarı komutu hatası: {e}", exc_info=True)
        try:
            await message.reply("❌ Bir hata oluştu!")
        except:
            pass


@router.message(F.text.startswith("!ban"))
@router.message(F.text.startswith("!yasakla"))
async def ban_command_extended(message: Message):
    """!ban / !yasakla komutu - Reply, mention, ID, özel mesaj, grup, sebep"""
    try:
        if not _bot_instance:
            return
        
        user = message.from_user
        chat = message.chat
        
        # Mod kontrolü
        if not await is_moderator(user.id) and not is_admin(user.id):
            if chat.type == "private":
                await message.reply("❌ Bu komutu kullanmak için mod yetkisine sahip olmalısınız!")
            return
        
        # Komut parametrelerini parse et
        text = message.text.strip()
        parts = text.split()
        
        target_user = None
        group_id = None
        reason = None
        
        # Özel mesajda mı?
        if chat.type == "private":
            # Özel mesajda grup ID ve kullanıcı belirtilmeli
            if len(parts) < 3:
                await message.reply("""
⚠️ <b>Kullanım (Özel Mesaj):</b>

• <code>!ban [group_id] [user_id/@username] [sebep]</code>
• <code>!ban [group_id] @username [sebep]</code>

<b>Örnek:</b>
• <code>!ban -1001234567890 123456789 Spam</code>
• <code>!ban -1001234567890 @username Spam</code>
                """, parse_mode="HTML")
                return
            
            # İlk parametre group_id
            try:
                group_id = int(parts[1])
            except ValueError:
                await message.reply("❌ Geçersiz grup ID!")
                return
            
            # İkinci parametre user_id/@username
            user_param = parts[2]
            # Sebep varsa al
            if len(parts) >= 4:
                reason = " ".join(parts[3:])
            
            # Kullanıcıyı bul
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
            
            # 1. Reply kontrolü
            if message.reply_to_message and message.reply_to_message.from_user:
                target_user = message.reply_to_message.from_user
                # Sebep mesajdan al
                if len(parts) > 1:
                    reason = " ".join(parts[1:])
            # 2. Mention kontrolü
            elif message.entities:
                for entity in message.entities:
                    if entity.type == "text_mention":
                        target_user = entity.user
                        # Sebep mesajdan al
                        if len(parts) > 1:
                            reason = " ".join(parts[1:])
                        break
                    elif entity.type == "mention":
                        username = message.text[entity.offset+1:entity.offset+entity.length]
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
                            # Sebep mesajdan al
                            if len(parts) > 1:
                                reason = " ".join(parts[1:])
                        break
            # 3. ID kontrolü (ilk parametre sayı ise)
            elif len(parts) >= 2 and parts[1].isdigit():
                user_id_param = int(parts[1])
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
                    if len(parts) >= 3:
                        reason = " ".join(parts[2:])
        
        if not target_user:
            await message.reply("""
⚠️ <b>Kullanım:</b>

• <code>!ban [sebep]</code> (reply ile)
• <code>!ban @username [sebep]</code>
• <code>!ban [user_id] [sebep]</code>

<b>Örnek:</b>
• <code>!ban Spam yapıyor</code> (reply ile)
• <code>!ban @username Spam</code>
• <code>!ban 123456789 Spam</code>
            """, parse_mode="HTML")
            return
        
        # Cezalandırma yetkisi kontrolü
        if not await can_punish_user(user.id, target_user.id):
            await message.reply("❌ Bu kullanıcıyı cezalandıramazsınız! (Mod veya admin)")
            return
        
        # Ban işlemi
        ban_success = await ban_user(_bot_instance, group_id, target_user.id, user.id)
        
        if ban_success:
            # Log kaydı
            await log_punishment(target_user.id, group_id, "ban", 0, user.id, reason)
            
            # Özel mesajda mı?
            if chat.type == "private":
                response = f"""
🚫 <b>KULLANICI BANLANDI</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
🆔 <b>ID:</b> <code>{target_user.id}</code>
💬 <b>Grup ID:</b> <code>{group_id}</code>
🚫 <b>Sonuç:</b> Kalıcı ban ✅
💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}
👮 <b>Moderatör:</b> {user.first_name}
                """
                await message.reply(response, parse_mode="HTML")
            else:
                # Grupta grup bildirimi
                await message.reply(f"""
🚫 <b>KULLANICI BANLANDI</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
🚫 <b>Sonuç:</b> Kalıcı ban ✅
💬 <b>Sebep:</b> {reason or 'Belirtilmedi'}
👮 <b>Moderatör:</b> {user.first_name}
                """, parse_mode="HTML")
                
                # Komut mesajını sil
                try:
                    await message.delete()
                except:
                    pass
        else:
            await message.reply("❌ Ban uygulanamadı! (Bot yetkisi gerekli veya güvenlik kontrolü başarısız)")
        
    except Exception as e:
        logger.error(f"❌ Ban komutu hatası: {e}", exc_info=True)
        try:
            await message.reply("❌ Bir hata oluştu!")
        except:
            pass


@router.message(F.text.startswith("!unban"))
@router.message(F.text.startswith("!yasakkaldir"))
async def unban_command_extended(message: Message):
    """!unban / !yasakkaldir komutu - Reply, mention, ID, özel mesaj, grup"""
    try:
        if not _bot_instance:
            return
        
        user = message.from_user
        chat = message.chat
        
        # Mod kontrolü
        if not await is_moderator(user.id) and not is_admin(user.id):
            if chat.type == "private":
                await message.reply("❌ Bu komutu kullanmak için mod yetkisine sahip olmalısınız!")
            return
        
        # Komut parametrelerini parse et
        text = message.text.strip()
        parts = text.split()
        
        target_user = None
        group_id = None
        
        # Özel mesajda mı?
        if chat.type == "private":
            # Özel mesajda grup ID ve kullanıcı belirtilmeli
            if len(parts) < 3:
                await message.reply("""
⚠️ <b>Kullanım (Özel Mesaj):</b>

• <code>!unban [group_id] [user_id/@username]</code>
• <code>!unban [group_id] @username</code>

<b>Örnek:</b>
• <code>!unban -1001234567890 123456789</code>
• <code>!unban -1001234567890 @username</code>
                """, parse_mode="HTML")
                return
            
            # İlk parametre group_id
            try:
                group_id = int(parts[1])
            except ValueError:
                await message.reply("❌ Geçersiz grup ID!")
                return
            
            # İkinci parametre user_id/@username
            user_param = parts[2]
            
            # Kullanıcıyı bul
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
            
            # 1. Reply kontrolü
            if message.reply_to_message and message.reply_to_message.from_user:
                target_user = message.reply_to_message.from_user
            # 2. Mention kontrolü
            elif message.entities:
                for entity in message.entities:
                    if entity.type == "text_mention":
                        target_user = entity.user
                        break
                    elif entity.type == "mention":
                        username = message.text[entity.offset+1:entity.offset+entity.length]
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
                        break
            # 3. ID kontrolü (ilk parametre sayı ise)
            elif len(parts) >= 2 and parts[1].isdigit():
                user_id_param = int(parts[1])
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
        
        if not target_user:
            await message.reply("""
⚠️ <b>Kullanım:</b>

• <code>!unban</code> (reply ile)
• <code>!unban @username</code>
• <code>!unban [user_id]</code>

<b>Örnek:</b>
• <code>!unban</code> (reply ile)
• <code>!unban @username</code>
• <code>!unban 123456789</code>
            """, parse_mode="HTML")
            return
        
        # Unban işlemi
        unban_success = await unban_user(_bot_instance, group_id, target_user.id, user.id)
        
        if unban_success:
            # Özel mesajda mı?
            if chat.type == "private":
                response = f"""
✅ <b>BAN KALDIRILDI</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
🆔 <b>ID:</b> <code>{target_user.id}</code>
💬 <b>Grup ID:</b> <code>{group_id}</code>
🔓 <b>Durum:</b> Artık gruba katılabilir
👮 <b>Moderatör:</b> {user.first_name}
                """
                await message.reply(response, parse_mode="HTML")
            else:
                # Grupta grup bildirimi
                await message.reply(f"""
✅ <b>BAN KALDIRILDI</b>

👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
🔓 <b>Durum:</b> Artık gruba katılabilir
👮 <b>Moderatör:</b> {user.first_name}
                """, parse_mode="HTML")
                
                # Komut mesajını sil
                try:
                    await message.delete()
                except:
                    pass
        else:
            await message.reply("❌ Ban kaldırılamadı! (Kullanıcı banlı değil veya bot yetkisi gerekli)")
        
    except Exception as e:
        logger.error(f"❌ Unban komutu hatası: {e}", exc_info=True)
        try:
            await message.reply("❌ Bir hata oluştu!")
        except:
            pass


@router.message(F.text.startswith("!uyariseviye"))
@router.message(F.text.startswith("!uyariseviyesi"))
async def warning_level_command(message: Message):
    """!uyariseviye komutu - Kullanıcının uyarı seviyesini göster veya ayarla"""
    try:
        if not _bot_instance:
            return
        
        user = message.from_user
        chat = message.chat
        
        # Mod kontrolü
        if not await is_moderator(user.id) and not is_admin(user.id):
            if chat.type == "private":
                await message.reply("❌ Bu komutu kullanmak için mod yetkisine sahip olmalısınız!")
            return
        
        # Komut parametrelerini parse et
        text = message.text.strip()
        parts = text.split()
        
        target_user = None
        group_id = None
        target_level = None  # Ayarlanacak seviye (None ise sadece göster)
        
        # Özel mesajda mı?
        if chat.type == "private":
            # Özel mesajda grup ID ve kullanıcı belirtilmeli
            if len(parts) < 3:
                await message.reply("""
⚠️ <b>Kullanım (Özel Mesaj):</b>

<b>Göstermek için:</b>
• <code>!uyariseviye [group_id] [user_id/@username]</code>

<b>Ayarlamak için:</b>
• <code>!uyariseviye [group_id] [user_id/@username] [seviye]</code>

<b>Seviye:</b> 0, 1, 2, veya 3

<b>Örnek:</b>
• <code>!uyariseviye -1001234567890 123456789</code> (göster)
• <code>!uyariseviye -1001234567890 123456789 2</code> (2. seviyeye ayarla)
                """, parse_mode="HTML")
                return
            
            # İlk parametre group_id
            try:
                group_id = int(parts[1])
            except ValueError:
                await message.reply("❌ Geçersiz grup ID!")
                return
            
            # İkinci parametre user_id/@username
            user_param = parts[2]
            
            # Üçüncü parametre seviye (varsa)
            if len(parts) >= 4:
                try:
                    target_level = int(parts[3])
                    if target_level < 0 or target_level > 3:
                        await message.reply("❌ Seviye 0-3 arasında olmalı!")
                        return
                except ValueError:
                    await message.reply("❌ Geçersiz seviye! (0, 1, 2, veya 3)")
                    return
            
            # Kullanıcıyı bul
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
            
            # 1. Reply kontrolü
            if message.reply_to_message and message.reply_to_message.from_user:
                target_user = message.reply_to_message.from_user
                # Seviye varsa al (ilk parametre)
                if len(parts) >= 2 and parts[1].isdigit():
                    target_level = int(parts[1])
                    if target_level < 0 or target_level > 3:
                        await message.reply("❌ Seviye 0-3 arasında olmalı!")
                        return
            # 2. Mention kontrolü
            elif message.entities:
                for entity in message.entities:
                    if entity.type == "text_mention":
                        target_user = entity.user
                        # Seviye varsa al (mention'dan sonra)
                        if len(parts) >= 2:
                            try:
                                target_level = int(parts[1])
                                if target_level < 0 or target_level > 3:
                                    await message.reply("❌ Seviye 0-3 arasında olmalı!")
                                    return
                            except ValueError:
                                pass
                        break
                    elif entity.type == "mention":
                        username = message.text[entity.offset+1:entity.offset+entity.length]
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
                            # Seviye varsa al (mention'dan sonra)
                            if len(parts) >= 2:
                                try:
                                    target_level = int(parts[1])
                                    if target_level < 0 or target_level > 3:
                                        await message.reply("❌ Seviye 0-3 arasında olmalı!")
                                        return
                                except ValueError:
                                    pass
                        break
            # 3. ID kontrolü (ilk parametre sayı ise)
            elif len(parts) >= 2 and parts[1].isdigit():
                user_id_param = int(parts[1])
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
                    # Seviye varsa al (ikinci parametre)
                    if len(parts) >= 3:
                        try:
                            target_level = int(parts[2])
                            if target_level < 0 or target_level > 3:
                                await message.reply("❌ Seviye 0-3 arasında olmalı!")
                                return
                        except ValueError:
                            pass
            else:
                # Kullanıcı belirtilmemişse, komutu kullananın uyarı seviyesini göster
                target_user = user
        
        if not target_user:
            await message.reply("""
⚠️ <b>Kullanım:</b>

<b>Göstermek için:</b>
• <code>!uyariseviye</code> (kendi uyarı seviyenizi gösterir)
• <code>!uyariseviye</code> (reply ile)
• <code>!uyariseviye @username</code>
• <code>!uyariseviye [user_id]</code>

<b>Ayarlamak için:</b>
• <code>!uyariseviye [seviye]</code> (reply ile)
• <code>!uyariseviye @username [seviye]</code>
• <code>!uyariseviye [user_id] [seviye]</code>

<b>Seviye:</b> 0, 1, 2, veya 3

<b>Örnek:</b>
• <code>!uyariseviye</code> (göster)
• <code>!uyariseviye 2</code> (reply ile - 2. seviyeye ayarla)
• <code>!uyariseviye @username 1</code> (1. seviyeye ayarla)
            """, parse_mode="HTML")
            return
        
        # Cezalandırma yetkisi kontrolü (ayarlama yapılacaksa)
        if target_level is not None:
            if not await can_punish_user(user.id, target_user.id):
                await message.reply("❌ Bu kullanıcıyı cezalandıramazsınız! (Mod veya admin)")
                return
        
        # Mevcut uyarı sayısını al
        current_warning_count = await get_user_warnings(target_user.id, group_id)
        
        # Seviye ayarlanacak mı?
        if target_level is not None:
            # Seviye ayarla
            from handlers.punishment_system import reset_warnings
            
            # Önce tüm uyarıları sıfırla
            await reset_warnings(target_user.id, group_id)
            
            # Hedef seviyeye kadar uyarı ekle
            if target_level > 0:
                reason = f"Uyarı seviyesi {target_level}'e ayarlandı (Mod: {user.first_name})"
                for i in range(target_level):
                    result = await add_warning(target_user.id, group_id, user.id, reason)
                    if not result.get("success"):
                        await message.reply(f"❌ Uyarı eklenirken hata oluştu: {result.get('error', 'Bilinmeyen hata')}")
                        return
                
                # Otomatik cezalandırma uygula
                new_warning_count = await get_user_warnings(target_user.id, group_id)
                
                # 1. uyarı: 5 dakika mute
                if new_warning_count == 1:
                    mute_success = await mute_user(_bot_instance, group_id, target_user.id, user.id, 5, reason)
                    if mute_success:
                        await log_punishment(target_user.id, group_id, "mute", 5, user.id, reason)
                # 2. uyarı: 30 dakika mute
                elif new_warning_count == 2:
                    mute_success = await mute_user(_bot_instance, group_id, target_user.id, user.id, 30, reason)
                    if mute_success:
                        await log_punishment(target_user.id, group_id, "mute", 30, user.id, reason)
                # 3. uyarı: Kalıcı ban
                elif new_warning_count >= 3:
                    ban_success = await ban_user(_bot_instance, group_id, target_user.id, user.id)
                    if ban_success:
                        await log_punishment(target_user.id, group_id, "ban", 0, user.id, reason)
            
            # Güncellenmiş uyarı sayısını al
            warning_count = await get_user_warnings(target_user.id, group_id)
            action_text = f"✅ <b>Uyarı seviyesi {target_level}'e ayarlandı!</b>\n\n"
        else:
            # Sadece göster
            warning_count = current_warning_count
            action_text = ""
        
        # Uyarı seviyesi mesajı
        level_text = ""
        next_action = ""
        
        if warning_count == 0:
            level_text = "✅ <b>Seviye 0:</b> Uyarı yok"
            next_action = "1. uyarı: 5 dakika mute"
        elif warning_count == 1:
            level_text = "⚠️ <b>Seviye 1:</b> 1. uyarı verildi"
            next_action = "2. uyarı: 30 dakika mute"
        elif warning_count == 2:
            level_text = "🔇 <b>Seviye 2:</b> 2. uyarı verildi"
            next_action = "3. uyarı: Kalıcı ban"
        elif warning_count >= 3:
            level_text = "🚫 <b>Seviye 3:</b> 3. uyarı verildi (Banlandı)"
            next_action = "Ban durumu aktif"
        
        response = f"""
📊 <b>UYARI SEVİYESİ</b>

{action_text}👤 <b>Kullanıcı:</b> {target_user.first_name} {f'(@{target_user.username})' if target_user.username else ''}
🆔 <b>ID:</b> <code>{target_user.id}</code>
💬 <b>Grup ID:</b> <code>{group_id}</code>

{level_text}
⚠️ <b>Uyarı Sayısı:</b> {warning_count}/3

📋 <b>Sıradaki İşlem:</b> {next_action}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Uyarı Sistemi:</b>
• 1. uyarı → 5 dakika mute
• 2. uyarı → 30 dakika mute
• 3. uyarı → Kalıcı ban
        """
        
        # Özel mesajda mı?
        if chat.type == "private":
            await message.reply(response, parse_mode="HTML")
        else:
            # Grupta özelden gönder
            try:
                await _bot_instance.send_message(user.id, response, parse_mode="HTML")
                # Komut mesajını sil
                try:
                    await message.delete()
                except:
                    pass
            except:
                await message.reply(response, parse_mode="HTML")
                try:
                    await message.delete()
                except:
                    pass
        
    except Exception as e:
        logger.error(f"❌ Uyarı seviyesi komutu hatası: {e}", exc_info=True)
        try:
            await message.reply("❌ Bir hata oluştu!")
        except:
            pass

