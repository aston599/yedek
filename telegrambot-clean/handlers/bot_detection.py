"""
🤖 Bot Tespit Sistemi - KirveHub Bot
Gruptaki botları tespit eder ve listeler
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict
from aiogram import Router, Bot, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatMember
from aiogram.filters import Command

from database import get_db_pool
from config import get_config, is_admin
from utils.logger import logger

router = Router()

# Bot instance
_bot_instance: Optional[Bot] = None

def set_bot_instance(bot_instance: Bot):
    """Bot instance'ını set et"""
    global _bot_instance
    _bot_instance = bot_instance

# ==============================================
# BOT BLOCKING SYSTEM
# ==============================================

# Engellenmiş botlar (RAM'de tutulur)
# Format: {group_id: {bot_id: {"blocked_by": int, "blocked_at": datetime}}}
blocked_bots: Dict[int, Dict[int, Dict]] = defaultdict(dict)

async def load_blocked_bots_from_db():
    """SQL'den engellenmiş botları yükle"""
    try:
        pool = await get_db_pool()
        if not pool:
            return
        
        async with pool.acquire() as conn:
            # blocked_bots tablosu var mı kontrol et
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'blocked_bots'
                )
            """)
            
            if not table_exists:
                # Tablo yoksa oluştur
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS blocked_bots (
                        id SERIAL PRIMARY KEY,
                        group_id BIGINT NOT NULL,
                        bot_id BIGINT NOT NULL,
                        blocked_by BIGINT NOT NULL,
                        blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(group_id, bot_id)
                    )
                """)
                logger.info("✅ blocked_bots tablosu oluşturuldu")
                return
            
            # Engellenmiş botları yükle
            rows = await conn.fetch("""
                SELECT group_id, bot_id, blocked_by, blocked_at
                FROM blocked_bots
            """)
            
            for row in rows:
                group_id = row['group_id']
                bot_id = row['bot_id']
                blocked_bots[group_id][bot_id] = {
                    "blocked_by": row['blocked_by'],
                    "blocked_at": row['blocked_at']
                }
            
            logger.info(f"✅ {len(rows)} engellenmiş bot yüklendi")
            
    except Exception as e:
        logger.error(f"❌ Blocked bots yükleme hatası: {e}")

async def block_bot_in_db(group_id: int, bot_id: int, blocked_by: int) -> bool:
    """Botu SQL'de engelle"""
    try:
        pool = await get_db_pool()
        if not pool:
            return False
        
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO blocked_bots (group_id, bot_id, blocked_by)
                VALUES ($1, $2, $3)
                ON CONFLICT (group_id, bot_id) DO UPDATE SET
                    blocked_by = EXCLUDED.blocked_by,
                    blocked_at = CURRENT_TIMESTAMP
            """, group_id, bot_id, blocked_by)
            
            return True
    except Exception as e:
        logger.error(f"❌ Bot engelleme hatası (SQL): {e}")
        return False

async def unblock_bot_in_db(group_id: int, bot_id: int) -> bool:
    """Botu SQL'de engellemeyi kaldır"""
    try:
        pool = await get_db_pool()
        if not pool:
            return False
        
        async with pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM blocked_bots
                WHERE group_id = $1 AND bot_id = $2
            """, group_id, bot_id)
            
            return True
    except Exception as e:
        logger.error(f"❌ Bot engelleme kaldırma hatası (SQL): {e}")
        return False

def is_bot_blocked(group_id: int, bot_id: int) -> bool:
    """Botun engellenip engellenmediğini kontrol et"""
    return bot_id in blocked_bots.get(group_id, {})

async def block_bot(group_id: int, bot_id: int, blocked_by: int) -> bool:
    """Botu engelle"""
    try:
        # RAM'e ekle
        blocked_bots[group_id][bot_id] = {
            "blocked_by": blocked_by,
            "blocked_at": datetime.now()
        }
        
        # SQL'e kaydet
        await block_bot_in_db(group_id, bot_id, blocked_by)
        
        logger.info(f"🚫 Bot engellendi - Group: {group_id}, Bot: {bot_id}, By: {blocked_by}")
        return True
    except Exception as e:
        logger.error(f"❌ Bot engelleme hatası: {e}")
        return False

async def unblock_bot(group_id: int, bot_id: int) -> bool:
    """Bot engellemeyi kaldır"""
    try:
        # RAM'den sil
        if group_id in blocked_bots and bot_id in blocked_bots[group_id]:
            del blocked_bots[group_id][bot_id]
        
        # SQL'den sil
        await unblock_bot_in_db(group_id, bot_id)
        
        logger.info(f"✅ Bot engelleme kaldırıldı - Group: {group_id}, Bot: {bot_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Bot engelleme kaldırma hatası: {e}")
        return False

# ==============================================
# BOT DETECTION
# ==============================================

async def get_group_bots(bot: Bot, chat_id: int) -> List[Dict]:
    """
    Gruptaki tüm botları listele
    
    Returns:
        List of bot info dicts: [{"user_id": int, "username": str, "first_name": str, "is_bot": bool, "status": str}]
    """
    try:
        bots = []
        
        # Chat member sayısını al (yaklaşık)
        try:
            chat = await bot.get_chat(chat_id)
            member_count = chat.members_count if hasattr(chat, 'members_count') else None
        except:
            member_count = None
        
        # Botları tespit etmek için admin listesini al
        # (Telegram API'de direkt bot listesi yok, bu yüzden admin listesinden başlayalım)
        try:
            administrators = await bot.get_chat_administrators(chat_id)
            
            for admin in administrators:
                user = admin.user
                if user.is_bot:
                    bots.append({
                        "user_id": user.id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "is_bot": True,
                        "status": admin.status,  # "administrator", "creator", etc.
                        "can_manage_chat": admin.can_manage_chat if hasattr(admin, 'can_manage_chat') else False,
                        "can_delete_messages": admin.can_delete_messages if hasattr(admin, 'can_delete_messages') else False,
                        "can_restrict_members": admin.can_restrict_members if hasattr(admin, 'can_restrict_members') else False,
                    })
        except Exception as e:
            logger.warning(f"⚠️ Admin listesi alınamadı: {e}")
        
        # Normal üyeleri kontrol et (sınırlı - sadece son aktif olanlar)
        # Not: Telegram API'de tüm üyeleri listeleme özelliği yok
        # Bu yüzden sadece adminlerdeki botları gösteriyoruz
        
        return bots
        
    except Exception as e:
        logger.error(f"❌ Bot detection hatası: {e}")
        return []

async def check_user_is_bot(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Belirli bir kullanıcının bot olup olmadığını kontrol et"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.user.is_bot
    except:
        return False

# ==============================================
# COMMANDS
# ==============================================

@router.message(Command("botlar"))
@router.message(Command("bots"))
async def list_bots_command(message: Message):
    """Gruptaki botları listele"""
    try:
        user_id = message.from_user.id
        
        # Sadece grup chatinde çalış
        if message.chat.type not in ["group", "supergroup"]:
            await message.reply("❌ Bu komut sadece grup chatinde kullanılabilir!")
            return
        
        chat_id = message.chat.id
        
        # Botları al
        bots = await get_group_bots(_bot_instance, chat_id)
        
        if not bots:
            await message.reply("🤖 Grupta bot bulunamadı veya bot listesi alınamadı.")
            return
        
        # Mesaj oluştur
        response = f"🤖 **GRUPTAKİ BOTLAR** ({len(bots)})\n\n"
        response += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        for idx, bot_info in enumerate(bots, 1):
            username = bot_info.get('username', 'Yok')
            first_name = bot_info.get('first_name', 'Bilinmiyor')
            status = bot_info.get('status', 'unknown')
            
            # Status Türkçe çevirisi
            status_tr = {
                "creator": "👑 Grup Sahibi",
                "administrator": "🛡️ Admin",
                "member": "👤 Üye"
            }.get(status, f"❓ {status}")
            
            response += f"**{idx}. {first_name}**\n"
            if username:
                response += f"   └─ @{username}\n"
            response += f"   └─ {status_tr}\n"
            
            # Yetkiler
            if bot_info.get('can_delete_messages'):
                response += f"   └─ ✅ Mesaj silebilir\n"
            if bot_info.get('can_restrict_members'):
                response += f"   └─ ✅ Üyeleri kısıtlayabilir\n"
            
            response += "\n"
        
        response += "━━━━━━━━━━━━━━━━━━━\n"
        response += f"💡 **Not:** Telegram API sınırlamaları nedeniyle sadece admin botlar gösterilir."
        
        # Butonlar
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Yenile", callback_data="bots_refresh"),
                InlineKeyboardButton(text="❌ Kapat", callback_data="bots_close")
            ]
        ])
        
        # Grup chatindeyse özelden gönder
        if message.chat.type in ["group", "supergroup"]:
            try:
                await message.delete()
            except:
                pass
            
            if _bot_instance:
                await _bot_instance.send_message(
                    user_id,
                    response,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
        else:
            await message.reply(response, parse_mode="Markdown", reply_markup=keyboard)
        
        logger.info(f"🤖 Bot listesi gösterildi - User: {user_id}, Group: {chat_id}, Bot count: {len(bots)}")
        
    except Exception as e:
        logger.error(f"❌ List bots command hatası: {e}")
        await message.reply("❌ Bot listesi alınırken hata oluştu!")

@router.message(Command("botkontrol"))
async def check_bot_command(message: Message):
    """Belirli bir kullanıcının bot olup olmadığını kontrol et"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not is_admin(user_id):
            return
        
        # Sadece grup chatinde çalış
        if message.chat.type not in ["group", "supergroup"]:
            await message.reply("❌ Bu komut sadece grup chatinde kullanılabilir!")
            return
        
        # Mesajı parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        if len(parts) < 2:
            await message.reply("❌ Kullanım: `/botkontrol @kullanıcı` veya `/botkontrol [user_id]`")
            return
        
        target = parts[1]
        target_user_id = None
        
        # @username veya user_id parse et
        if target.startswith("@"):
            # Username'den user_id bul (bu özellik Telegram API'de yok, reply kullan)
            if message.reply_to_message:
                target_user_id = message.reply_to_message.from_user.id
            else:
                await message.reply("❌ Username ile kontrol için mesaja yanıt verin!")
                return
        else:
            try:
                target_user_id = int(target)
            except:
                await message.reply("❌ Geçersiz user_id!")
                return
        
        chat_id = message.chat.id
        
        # Bot kontrolü
        is_bot = await check_user_is_bot(_bot_instance, chat_id, target_user_id)
        
        # Kullanıcı bilgilerini al
        try:
            member = await _bot_instance.get_chat_member(chat_id, target_user_id)
            user = member.user
            username = user.username or "Yok"
            first_name = user.first_name or "Bilinmiyor"
        except:
            username = "Bilinmiyor"
            first_name = "Bilinmiyor"
        
        result_msg = f"""
🤖 **BOT KONTROL SONUCU**

👤 **Kullanıcı:** {first_name}
🆔 **ID:** {target_user_id}
📝 **Username:** @{username}

{'🤖 **BOT**' if is_bot else '👤 **İNSAN KULLANICI**'}
        """
        
        await message.reply(result_msg, parse_mode="Markdown")
        
        logger.info(f"🤖 Bot kontrolü - User: {user_id}, Target: {target_user_id}, Is bot: {is_bot}")
        
    except Exception as e:
        logger.error(f"❌ Check bot command hatası: {e}")
        await message.reply("❌ Bot kontrolü yapılırken hata oluştu!")

# ==============================================
# NEW MEMBER HANDLER
# ==============================================

@router.message(lambda m: m.new_chat_members is not None)
async def new_member_bot_check(message: Message):
    """Yeni üye geldiğinde bot kontrolü yap"""
    try:
        # Sadece grup chatinde çalış
        if message.chat.type not in ["group", "supergroup"]:
            return
        
        chat_id = message.chat.id
        new_members = message.new_chat_members
        
        bots_detected = []
        
        for member in new_members:
            if member.is_bot:
                bots_detected.append({
                    "user_id": member.id,
                    "username": member.username,
                    "first_name": member.first_name
                })
        
        if bots_detected:
            # Admin'e bildir
            config = get_config()
            admin_id = config.ADMIN_USER_ID
            
            bot_list = "\n".join([
                f"• {bot['first_name']} (@{bot['username'] or 'yok'})"
                for bot in bots_detected
            ])
            
            notification = f"""
🤖 **YENİ BOT TESPİT EDİLDİ**

📊 **Grup:** {message.chat.title}
👥 **Bot Sayısı:** {len(bots_detected)}

**Botlar:**
{bot_list}

💡 **Not:** Botlar otomatik olarak tespit edildi.
            """
            
            if _bot_instance:
                await _bot_instance.send_message(admin_id, notification, parse_mode="Markdown")
            
            logger.info(f"🤖 Yeni bot tespit edildi - Group: {chat_id}, Bots: {len(bots_detected)}")
        
    except Exception as e:
        logger.error(f"❌ New member bot check hatası: {e}")

# ==============================================
# CALLBACK HANDLERS
# ==============================================

@router.callback_query(lambda c: c.data == "bots_refresh")
async def refresh_bots_callback(callback: types.CallbackQuery):
    """Bot listesini yenile"""
    try:
        chat_id = callback.message.chat.id
        
        # Botları al
        bots = await get_group_bots(_bot_instance, chat_id)
        
        if not bots:
            await callback.answer("🤖 Grupta bot bulunamadı!", show_alert=True)
            return
        
        # Mesajı güncelle
        response = f"🤖 **GRUPTAKİ BOTLAR** ({len(bots)})\n\n"
        response += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        for idx, bot_info in enumerate(bots, 1):
            username = bot_info.get('username', 'Yok')
            first_name = bot_info.get('first_name', 'Bilinmiyor')
            status = bot_info.get('status', 'unknown')
            
            status_tr = {
                "creator": "👑 Grup Sahibi",
                "administrator": "🛡️ Admin",
                "member": "👤 Üye"
            }.get(status, f"❓ {status}")
            
            response += f"**{idx}. {first_name}**\n"
            if username:
                response += f"   └─ @{username}\n"
            response += f"   └─ {status_tr}\n\n"
        
        response += "━━━━━━━━━━━━━━━━━━━\n"
        response += f"💡 **Not:** Telegram API sınırlamaları nedeniyle sadece admin botlar gösterilir."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Yenile", callback_data="bots_refresh"),
                InlineKeyboardButton(text="❌ Kapat", callback_data="bots_close")
            ]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        await callback.answer("✅ Bot listesi yenilendi!")
        
    except Exception as e:
        logger.error(f"❌ Refresh bots callback hatası: {e}")
        await callback.answer("❌ Hata oluştu!", show_alert=True)

@router.callback_query(lambda c: c.data == "bots_close")
async def close_bots_callback(callback: types.CallbackQuery):
    """Bot listesini kapat"""
    try:
        await callback.message.delete()
        await callback.answer("✅ Kapatıldı!")
    except:
        await callback.answer("❌ Mesaj silinemedi!")

# ==============================================
# BOT BLOCKING COMMANDS
# ==============================================

@router.message(Command("botengelle"))
async def block_bot_command(message: Message):
    """Botu engelle: /botengelle @bot, /botengelle [bot_id], /botengelle hepsi, /botengelle ac"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not is_admin(user_id):
            return
        
        # Sadece grup chatinde çalış
        if message.chat.type not in ["group", "supergroup"]:
            await message.reply("❌ Bu komut sadece grup chatinde kullanılabilir!")
            return
        
        chat_id = message.chat.id
        
        # Mesajı parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        # Özel komutlar: "hepsi" ve "ac"
        if len(parts) >= 2:
            special_command = parts[1].lower()
            
            if special_command == "hepsi":
                # Tüm botları engelle
                await block_all_bots(message, chat_id, user_id)
                return
            elif special_command == "ac":
                # Tüm botları aç
                await unblock_all_bots(message, chat_id, user_id)
                return
        
        # Normal bot engelleme
        target_bot_id = None
        target_bot_name = None
        
        if len(parts) < 2:
            # Reply ile kullanım
            if message.reply_to_message:
                target_user = message.reply_to_message.from_user
                if not target_user.is_bot:
                    await message.reply("❌ Bu komut sadece botlar için kullanılabilir!")
                    return
                target_bot_id = target_user.id
                target_bot_name = target_user.first_name or target_user.username or "Bilinmiyor"
            else:
                await message.reply("❌ Kullanım: `/botengelle @bot`, `/botengelle [bot_id]`, `/botengelle hepsi` veya `/botengelle ac`")
                return
        else:
            target = parts[1]
            
            # @username veya user_id parse et
            if target.startswith("@"):
                # Username'den bot bul (reply gerekli)
                if message.reply_to_message:
                    target_user = message.reply_to_message.from_user
                    if not target_user.is_bot:
                        await message.reply("❌ Bu komut sadece botlar için kullanılabilir!")
                        return
                    target_bot_id = target_user.id
                    target_bot_name = target_user.first_name or target_user.username or "Bilinmiyor"
                else:
                    await message.reply("❌ Username ile engelleme için bot mesajına yanıt verin!")
                    return
            else:
                try:
                    target_bot_id = int(target)
                    # Bot bilgilerini al
                    try:
                        member = await _bot_instance.get_chat_member(chat_id, target_bot_id)
                        if not member.user.is_bot:
                            await message.reply("❌ Bu komut sadece botlar için kullanılabilir!")
                            return
                        target_bot_name = member.user.first_name or member.user.username or "Bilinmiyor"
                    except:
                        target_bot_name = f"Bot {target_bot_id}"
                except:
                    await message.reply("❌ Geçersiz bot ID!")
                    return
        
        # Botu engelle
        success = await block_bot(chat_id, target_bot_id, user_id)
        
        if success:
            result_msg = f"""
🚫 **BOT ENGELLENDİ**

🤖 **Bot:** {target_bot_name}
🆔 **ID:** {target_bot_id}
👤 **Engelleyen:** {message.from_user.first_name}

💡 Bu botun mesajları artık otomatik olarak silinecek.
            """
            
            await message.reply(result_msg, parse_mode="Markdown")
            
            # Grup mesajını sil
            try:
                await message.delete()
            except:
                pass
            
            logger.warning(f"🚫 Bot engellendi - Group: {chat_id}, Bot: {target_bot_id}, By: {user_id}")
        else:
            await message.reply("❌ Bot engellenirken hata oluştu!")
        
    except Exception as e:
        logger.error(f"❌ Block bot command hatası: {e}")
        await message.reply("❌ Bot engelleme sırasında hata oluştu!")

async def block_all_bots(message: Message, chat_id: int, user_id: int):
    """Gruptaki tüm botları engelle"""
    try:
        # Gruptaki tüm botları al
        bots = await get_group_bots(_bot_instance, chat_id)
        
        if not bots:
            await message.reply("ℹ️ Grupta bot bulunamadı!")
            return
        
        blocked_count = 0
        already_blocked = 0
        failed = 0
        
        for bot_info in bots:
            bot_id = bot_info['user_id']
            
            # Zaten engellenmiş mi kontrol et
            if is_bot_blocked(chat_id, bot_id):
                already_blocked += 1
                continue
            
            # Botu engelle
            success = await block_bot(chat_id, bot_id, user_id)
            if success:
                blocked_count += 1
            else:
                failed += 1
        
        result_msg = f"""
🚫 **TÜM BOTLAR ENGELLENDİ**

📊 **Sonuçlar:**
• ✅ Yeni engellenen: {blocked_count}
• ℹ️ Zaten engellenmiş: {already_blocked}
• ❌ Başarısız: {failed}
• 📊 Toplam bot: {len(bots)}

💡 Tüm botların mesajları artık otomatik olarak silinecek.
        """
        
        await message.reply(result_msg, parse_mode="Markdown")
        
        # Grup mesajını sil
        try:
            await message.delete()
        except:
            pass
        
        logger.warning(f"🚫 Tüm botlar engellendi - Group: {chat_id}, Blocked: {blocked_count}, By: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Block all bots hatası: {e}")
        await message.reply("❌ Tüm botlar engellenirken hata oluştu!")

async def unblock_all_bots(message: Message, chat_id: int, user_id: int):
    """Gruptaki tüm engellenmiş botları aç"""
    try:
        # Engellenmiş botları al
        blocked = blocked_bots.get(chat_id, {})
        
        if not blocked:
            await message.reply("ℹ️ Bu grupta engellenmiş bot yok!")
            return
        
        unblocked_count = 0
        failed = 0
        
        for bot_id in list(blocked.keys()):
            success = await unblock_bot(chat_id, bot_id)
            if success:
                unblocked_count += 1
            else:
                failed += 1
        
        result_msg = f"""
✅ **TÜM BOTLAR AÇILDI**

📊 **Sonuçlar:**
• ✅ Açılan bot: {unblocked_count}
• ❌ Başarısız: {failed}
• 📊 Toplam engellenmiş: {len(blocked)}

💡 Tüm botlar artık mesaj gönderebilir.
        """
        
        await message.reply(result_msg, parse_mode="Markdown")
        
        # Grup mesajını sil
        try:
            await message.delete()
        except:
            pass
        
        logger.info(f"✅ Tüm botlar açıldı - Group: {chat_id}, Unblocked: {unblocked_count}, By: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Unblock all bots hatası: {e}")
        await message.reply("❌ Tüm botlar açılırken hata oluştu!")

@router.message(Command("botkabul"))
async def unblock_bot_command(message: Message):
    """Bot engellemeyi kaldır: /botkabul @bot veya /botkabul [bot_id]"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not is_admin(user_id):
            return
        
        # Sadece grup chatinde çalış
        if message.chat.type not in ["group", "supergroup"]:
            await message.reply("❌ Bu komut sadece grup chatinde kullanılabilir!")
            return
        
        chat_id = message.chat.id
        
        # Mesajı parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        target_bot_id = None
        target_bot_name = None
        
        if len(parts) < 2:
            # Reply ile kullanım
            if message.reply_to_message:
                target_user = message.reply_to_message.from_user
                if not target_user.is_bot:
                    await message.reply("❌ Bu komut sadece botlar için kullanılabilir!")
                    return
                target_bot_id = target_user.id
                target_bot_name = target_user.first_name or target_user.username or "Bilinmiyor"
            else:
                await message.reply("❌ Kullanım: `/botkabul @bot` veya bir bot mesajına yanıt verin!")
                return
        else:
            target = parts[1]
            
            # @username veya user_id parse et
            if target.startswith("@"):
                # Username'den bot bul (reply gerekli)
                if message.reply_to_message:
                    target_user = message.reply_to_message.from_user
                    if not target_user.is_bot:
                        await message.reply("❌ Bu komut sadece botlar için kullanılabilir!")
                        return
                    target_bot_id = target_user.id
                    target_bot_name = target_user.first_name or target_user.username or "Bilinmiyor"
                else:
                    await message.reply("❌ Username ile kabul için bot mesajına yanıt verin!")
                    return
            else:
                try:
                    target_bot_id = int(target)
                    # Bot bilgilerini al
                    try:
                        member = await _bot_instance.get_chat_member(chat_id, target_bot_id)
                        if not member.user.is_bot:
                            await message.reply("❌ Bu komut sadece botlar için kullanılabilir!")
                            return
                        target_bot_name = member.user.first_name or member.user.username or "Bilinmiyor"
                    except:
                        target_bot_name = f"Bot {target_bot_id}"
                except:
                    await message.reply("❌ Geçersiz bot ID!")
                    return
        
        # Bot engellenmiş mi kontrol et
        if not is_bot_blocked(chat_id, target_bot_id):
            await message.reply("ℹ️ Bu bot zaten engellenmemiş!")
            return
        
        # Bot engellemeyi kaldır
        success = await unblock_bot(chat_id, target_bot_id)
        
        if success:
            result_msg = f"""
✅ **BOT ENGELLEME KALDIRILDI**

🤖 **Bot:** {target_bot_name}
🆔 **ID:** {target_bot_id}
👤 **Kaldıran:** {message.from_user.first_name}

💡 Bu bot artık mesaj gönderebilir.
            """
            
            await message.reply(result_msg, parse_mode="Markdown")
            
            # Grup mesajını sil
            try:
                await message.delete()
            except:
                pass
            
            logger.info(f"✅ Bot engelleme kaldırıldı - Group: {chat_id}, Bot: {target_bot_id}, By: {user_id}")
        else:
            await message.reply("❌ Bot engelleme kaldırılırken hata oluştu!")
        
    except Exception as e:
        logger.error(f"❌ Unblock bot command hatası: {e}")
        await message.reply("❌ Bot engelleme kaldırma sırasında hata oluştu!")

@router.message(Command("botengelliste"))
async def list_blocked_bots_command(message: Message):
    """Engellenmiş botları listele"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not is_admin(user_id):
            return
        
        # Sadece grup chatinde çalış
        if message.chat.type not in ["group", "supergroup"]:
            await message.reply("❌ Bu komut sadece grup chatinde kullanılabilir!")
            return
        
        chat_id = message.chat.id
        
        # Engellenmiş botları al
        blocked = blocked_bots.get(chat_id, {})
        
        if not blocked:
            await message.reply("ℹ️ Bu grupta engellenmiş bot yok.")
            return
        
        # Liste oluştur
        response = f"🚫 **ENGELLENMİŞ BOTLAR** ({len(blocked)})\n\n"
        response += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        for bot_id, info in blocked.items():
            try:
                # Bot bilgilerini al
                member = await _bot_instance.get_chat_member(chat_id, bot_id)
                bot_name = member.user.first_name or member.user.username or f"Bot {bot_id}"
                bot_username = member.user.username or "Yok"
            except:
                bot_name = f"Bot {bot_id}"
                bot_username = "Bilinmiyor"
            
            blocked_at = info.get('blocked_at', 'Bilinmiyor')
            if isinstance(blocked_at, datetime):
                blocked_at = blocked_at.strftime("%Y-%m-%d %H:%M")
            
            response += f"🤖 **{bot_name}**\n"
            response += f"   └─ ID: {bot_id}\n"
            if bot_username != "Yok":
                response += f"   └─ @{bot_username}\n"
            response += f"   └─ Engellenme: {blocked_at}\n\n"
        
        response += "━━━━━━━━━━━━━━━━━━━\n"
        response += "💡 **Not:** `/botkabul [bot_id]` ile engellemeyi kaldırabilirsiniz."
        
        # Grup mesajını sil ve özelden gönder
        try:
            await message.delete()
        except:
            pass
        
        if _bot_instance:
            await _bot_instance.send_message(user_id, response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ List blocked bots command hatası: {e}")
        await message.reply("❌ Engellenmiş botlar listelenirken hata oluştu!")

# ==============================================
# BOT MESSAGE HANDLER (Engellenmiş bot mesajlarını sil)
# ==============================================

@router.message()
async def block_bot_messages_handler(message: Message):
    """Engellenmiş botların mesajlarını sil"""
    try:
        # Sadece grup mesajlarında çalış
        if message.chat.type not in ["group", "supergroup"]:
            return
        
        # Bot mesajı mı kontrol et
        if not message.from_user or not message.from_user.is_bot:
            return
        
        chat_id = message.chat.id
        bot_id = message.from_user.id
        
        # Bot engellenmiş mi kontrol et
        if is_bot_blocked(chat_id, bot_id):
            # Mesajı sil
            try:
                await message.delete()
                logger.info(f"🚫 Engellenmiş bot mesajı silindi - Group: {chat_id}, Bot: {bot_id}")
            except Exception as e:
                logger.warning(f"⚠️ Engellenmiş bot mesajı silinemedi: {e}")
        
    except Exception as e:
        logger.error(f"❌ Block bot messages handler hatası: {e}")

