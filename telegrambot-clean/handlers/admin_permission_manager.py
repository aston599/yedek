"""
👑 Admin İzin Yöneticisi - KirveHub Bot
Admin seviyeleri ve yetki yönetimi sistemi
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config import get_config
from database import get_db_pool
from utils.logger import logger

router = Router()

# Bot instance setter
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

async def delete_message_after_delay(message, delay=5):
    """Mesajı belirtilen süre sonra sil"""
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except:
        pass

# =============================
# DATABASE FONKSİYONLARI
# =============================

async def update_user_rank_db(user_id: int, new_rank: int) -> dict:
    """Kullanıcının admin seviyesini güncelle (Database)"""
    try:
        pool = await get_db_pool()
        if not pool:
            return {"success": False, "error": "Database bağlantısı yok"}
            
        async with pool.acquire() as conn:
            # Kullanıcıyı bul
            user = await conn.fetchrow("""
                SELECT user_id, first_name, username, COALESCE(rank_id, 1) as current_rank
                FROM users WHERE user_id = $1
            """, user_id)
            
            if not user:
                return {"success": False, "error": f"Kullanıcı bulunamadı: {user_id}"}
            
            old_rank = user["current_rank"]
            
            # Rank'ı güncelle
            await conn.execute("""
                UPDATE users 
                SET rank_id = $1, last_activity = NOW()
                WHERE user_id = $2
            """, new_rank, user_id)
            
            logger.info(f"🛡️ Admin rank güncellendi - User: {user_id}, Old: {old_rank}, New: {new_rank}")
            
            return {
                "success": True,
                "user_id": user_id,
                "old_rank": old_rank,
                "new_rank": new_rank,
                "user_name": user["first_name"],
                "username": user["username"]
            }
            
    except Exception as e:
        logger.error(f"❌ Update user rank hatası: {e}")
        return {"success": False, "error": str(e)}

async def get_user_admin_info_db(user_id: int) -> dict:
    """Kullanıcının admin bilgilerini getir (Database)"""
    try:
        pool = await get_db_pool()
        if not pool:
            return {"success": False, "error": "Database bağlantısı yok"}
            
        async with pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT user_id, first_name, username, COALESCE(rank_id, 1) as rank_id,
                       last_activity, is_registered
                FROM users WHERE user_id = $1
            """, user_id)
            
            if not user:
                return {"success": False, "error": f"Kullanıcı bulunamadı: {user_id}"}
            
            user_dict = dict(user)
            # Super Admin override: DB ne olursa olsun 4 kabul et
            try:
                config = get_config()
                if user_id == config.ADMIN_USER_ID:
                    user_dict["rank_id"] = 4
            except Exception:
                pass
            
            return {
                "success": True,
                "user": user_dict
            }
            
    except Exception as e:
        logger.error(f"❌ Get user admin info hatası: {e}")
        return {"success": False, "error": str(e)}

async def has_min_rank_db(user_id: int, min_rank: int) -> bool:
    """Kullanıcının min_rank ve üzeri yetkisi var mı? Super Admin her zaman geçer.

    min_rank: 2 (Admin 1), 3 (Admin 2), 4 (Super Admin)
    """
    try:
        config = get_config()
        if user_id == config.ADMIN_USER_ID:
            return True
        info = await get_user_admin_info_db(user_id)
        if not info.get("success"):
            return False
        rank_id = int(info["user"].get("rank_id") or 1)
        return rank_id >= int(min_rank)
    except Exception as e:
        logger.error(f"❌ has_min_rank_db hatası: {e}")
        return False

async def get_all_admins_db() -> dict:
    """Tüm adminleri getir (Database)"""
    try:
        pool = await get_db_pool()
        if not pool:
            return {"success": False, "error": "Database bağlantısı yok"}
            
        async with pool.acquire() as conn:
            admins = await conn.fetch("""
                SELECT user_id, first_name, username, rank_id, last_activity, is_registered
                FROM users 
                WHERE rank_id > 1 AND is_registered = TRUE
                ORDER BY rank_id DESC, last_activity DESC
            """)
            
            return {
                "success": True,
                "admins": [dict(admin) for admin in admins]
            }
            
    except Exception as e:
        logger.error(f"❌ Get all admins hatası: {e}")
        return {"success": False, "error": str(e)}

async def find_user_by_username_db(username: str) -> dict:
    """Username'den kullanıcı bilgilerini getir (Database)"""
    try:
        pool = await get_db_pool()
        if not pool:
            return {"success": False, "error": "Database bağlantısı yok"}
            
        async with pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT user_id, first_name, username, COALESCE(rank_id, 1) as rank_id
                FROM users WHERE username = $1
            """, username)
            
            if not user:
                return {"success": False, "error": f"Kullanıcı bulunamadı: @{username}"}
            
            return {
                "success": True,
                "user": dict(user)
            }
            
    except Exception as e:
        logger.error(f"❌ Find user by username hatası: {e}")
        return {"success": False, "error": str(e)}

# =============================
# YARDIMCI FONKSİYONLAR
# =============================

def get_rank_name(rank_id: int) -> str:
    """Rank ID'den rank adını döndür"""
    rank_names = {
        1: "Üye",
        2: "Admin 1", 
        3: "Admin 2",
        4: "Super Admin"
    }
    return rank_names.get(rank_id, f"Seviye {rank_id}")

def get_rank_permissions(rank_id: int) -> str:
    """Rank ID'den yetkileri döndür"""
    permissions = {
        1: "Temel komutlar",
        2: "Chat moderasyon + Bakiye yönetimi",
        3: "Grup kayıt + Etkinlik yönetimi", 
        4: "Tam yetki + Sistem ayarları"
    }
    return permissions.get(rank_id, "Bilinmeyen yetki")

def is_super_admin(user_id: int) -> bool:
    """Kullanıcının Super Admin olup olmadığını kontrol et"""
    config = get_config()
    return user_id == config.ADMIN_USER_ID

# =============================
# MESAJ GÖNDERME FONKSİYONLARI
# =============================

async def send_error_message(message: types.Message, text: str) -> None:
    """Hata mesajı gönder"""
    if message.chat.type == "private":
        await message.reply(text)
    else:
        sent_message = await message.answer("❌ Hata oluştu! Detaylar özel mesajda.")
        if _bot_instance:
            try:
                await _bot_instance.send_message(message.from_user.id, text)
            except Exception as e:
                logger.error(f"❌ Bot instance mesaj gönderme hatası: {e}")
        asyncio.create_task(delete_message_after_delay(sent_message))

async def send_response_message(message: types.Message, text: str) -> None:
    """Yanıt mesajı gönder"""
    if message.chat.type == "private":
        await message.reply(text, parse_mode="Markdown")
    else:
        sent_message = await message.answer("✅ İşlem tamamlandı! Detaylar özel mesajda.")
        if _bot_instance:
            try:
                await _bot_instance.send_message(message.from_user.id, text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"❌ Bot instance mesaj gönderme hatası: {e}")
        asyncio.create_task(delete_message_after_delay(sent_message))

# =============================
# KOMUT HANDLER'LARI
# =============================

@router.message(Command("adminyap"))
async def make_admin_command(message: types.Message) -> None:
    """Admin yetkisi verme: /adminyap @username SEVİYE veya reply ile /adminyap SEVİYE"""
    try:
        # Super Admin kontrolü
        if not is_super_admin(message.from_user.id):
            return
        
        # Grup chatindeyse komut mesajını sil (ama çalışmaya devam et)
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
        
        # Komut metnini parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        user_id = None
        admin_level = None
        
        # 1. Reply ile kullanım: /adminyap SEVİYE
        if message.reply_to_message and len(parts) == 2:
            try:
                user_id = message.reply_to_message.from_user.id
                admin_level = int(parts[1])
            except ValueError:
                await send_error_message(message, "❌ Geçersiz seviye! Örnek: `/adminyap 2`")
                return
        
        # 2. Etiket ile kullanım: /adminyap @username SEVİYE
        elif len(parts) == 3 and parts[1] and parts[1].startswith('@'):
            try:
                username = parts[1][1:]  # @ işaretini kaldır
                admin_level = int(parts[2])
                
                # Username'den user_id bul
                result = await find_user_by_username_db(username)
                if not result["success"]:
                    await send_error_message(message, result["error"])
                    return
                    
                user_id = result["user"]["user_id"]
                    
            except ValueError:
                await send_error_message(message, "❌ Geçersiz seviye! Örnek: `/adminyap @username 2`")
                return
        
        else:
            await send_error_message(message, "❌ Kullanım:\n• `/adminyap SEVİYE` (reply ile)\n• `/adminyap @username SEVİYE` (etiket ile)")
            return
        
        if admin_level < 1 or admin_level > 4:
            await send_error_message(message, "❌ Seviye 1-4 arası olmalı!\n• 1: Üye\n• 2: Admin 1\n• 3: Admin 2\n• 4: Super Admin")
            return
        
        # Admin yetkisi ver
        result = await update_user_rank_db(user_id, admin_level)
        
        if result["success"]:
            response = f"""
✅ **Admin Yetkisi Verildi!**

**👤 User ID:** {user_id}
**👤 İsim:** {result["user_name"]}
**🛡️ Eski Seviye:** {get_rank_name(result["old_rank"])}
**🛡️ Yeni Seviye:** {get_rank_name(admin_level)}
**👑 Yetki:** {get_rank_permissions(admin_level)}
            """
        else:
            response = f"❌ Hata: {result['error']}"
        
        await send_response_message(message, response)
        
    except Exception as e:
        logger.error(f"❌ Make admin hatası: {e}")
        await send_error_message(message, "❌ Bir hata oluştu!")

@router.message(Command("adminçıkar"))
async def remove_admin_command(message: types.Message) -> None:
    """Admin yetkisi alma: /adminçıkar @username veya reply ile /adminçıkar"""
    try:
        # Super Admin kontrolü
        if not is_super_admin(message.from_user.id):
            return
        
        # Grup chatindeyse komut mesajını sil (ama çalışmaya devam et)
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
        
        # Komut metnini parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        user_id = None
        
        # 1. Reply ile kullanım: /adminçıkar
        if message.reply_to_message and len(parts) == 1:
            user_id = message.reply_to_message.from_user.id
        
        # 2. Etiket ile kullanım: /adminçıkar @username
        elif len(parts) == 2 and parts[1] and parts[1].startswith('@'):
            username = parts[1][1:]  # @ işaretini kaldır
            
            # Username'den user_id bul
            result = await find_user_by_username_db(username)
            if not result["success"]:
                await send_error_message(message, result["error"])
                return
                
            user_id = result["user"]["user_id"]
        
        else:
            await send_error_message(message, "❌ Kullanım:\n• `/adminçıkar` (reply ile)\n• `/adminçıkar @username` (etiket ile)")
            return
        
        # Kendini admin çıkarma kontrolü
        if user_id == message.from_user.id:
            await send_error_message(message, "❌ Kendinizi admin çıkaramazsınız!")
            return
        
        # Admin yetkisini al (rank 1'e düşür)
        result = await update_user_rank_db(user_id, 1)
        
        if result["success"]:
            response = f"""
❌ **Admin Yetkisi Alındı!**

**👤 User ID:** {user_id}
**👤 İsim:** {result["user_name"]}
**🛡️ Eski Seviye:** {get_rank_name(result["old_rank"])}
**🛡️ Yeni Seviye:** Üye
**👑 Yetki:** Temel komutlar
            """
        else:
            response = f"❌ Hata: {result['error']}"
        
        await send_response_message(message, response)
        
    except Exception as e:
        logger.error(f"❌ Remove admin hatası: {e}")
        await send_error_message(message, "❌ Bir hata oluştu!")

@router.message(Command("adminlist"))
async def list_admins_command(message: types.Message) -> None:
    """Admin listesi: /adminlist"""
    try:
        # Super Admin kontrolü
        if not is_super_admin(message.from_user.id):
            return
        
        # Grup chatindeyse komut mesajını sil (ama çalışmaya devam et)
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
        
        # Admin listesini al
        result = await get_all_admins_db()
        
        if result["success"]:
            admin_list = "🛡️ **ADMİN LİSTESİ**\n\n"
            
            for admin in result["admins"]:
                level_name = get_rank_name(admin["rank_id"])
                username = admin['username'] or 'Kullanıcı adı yok'
                last_activity = admin['last_activity'].strftime('%d.%m.%Y %H:%M') if admin['last_activity'] else 'Bilinmiyor'
                
                admin_list += f"👤 **{admin['first_name']}** (@{username})\n"
                admin_list += f"🛡️ **Seviye:** {level_name}\n"
                admin_list += f"📅 **Son Aktivite:** {last_activity}\n\n"
            
            admin_list += f"📊 **Toplam Admin:** {len(result['admins'])} kişi"
            
            await send_response_message(message, admin_list)
        else:
            await send_error_message(message, f"❌ Hata: {result['error']}")
        
    except Exception as e:
        logger.error(f"❌ List admins hatası: {e}")
        await send_error_message(message, "❌ Bir hata oluştu!")

@router.message(Command("admininfo"))
async def admin_info_command(message: types.Message) -> None:
    """Kullanıcı admin bilgisi: /admininfo @username veya reply ile /admininfo"""
    try:
        # Super Admin kontrolü
        if not is_super_admin(message.from_user.id):
            return
        
        # Grup chatindeyse komut mesajını sil (ama çalışmaya devam et)
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
        
        # Komut metnini parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        user_id = None
        
        # 1. Reply ile kullanım: /admininfo
        if message.reply_to_message and len(parts) == 1:
            user_id = message.reply_to_message.from_user.id
        
        # 2. Etiket ile kullanım: /admininfo @username
        elif len(parts) == 2 and parts[1].startswith('@'):
            username = parts[1][1:]  # @ işaretini kaldır
            
            # Username'den user_id bul
            result = await find_user_by_username_db(username)
            if not result["success"]:
                await send_error_message(message, result["error"])
                return
                
            user_id = result["user"]["user_id"]
        
        else:
            await send_error_message(message, "❌ Kullanım:\n• `/admininfo` (reply ile)\n• `/admininfo @username` (etiket ile)")
            return
        
        # Kullanıcı bilgilerini al
        result = await get_user_admin_info_db(user_id)
        
        if result["success"]:
            user = result["user"]
            level_name = get_rank_name(user["rank_id"])
            permissions = get_rank_permissions(user["rank_id"])
            last_activity = user['last_activity'].strftime('%d.%m.%Y %H:%M') if user['last_activity'] else 'Bilinmiyor'
            username = user['username'] or 'Kullanıcı adı yok'
            
            response = f"""
👤 **KULLANICI BİLGİLERİ**

**🆔 User ID:** {user_id}
**👤 İsim:** {user['first_name']}
**🏷️ Username:** @{username}
**🛡️ Seviye:** {level_name}
**👑 Yetki:** {permissions}
**📅 Son Aktivite:** {last_activity}
**✅ Kayıtlı:** {'Evet' if user['is_registered'] else 'Hayır'}
            """
        else:
            response = f"❌ Hata: {result['error']}"
        
        await send_response_message(message, response)
        
    except Exception as e:
        logger.error(f"❌ Admin info hatası: {e}")
        await send_error_message(message, "❌ Bir hata oluştu!")

@router.message(Command("yetkiver"))
async def give_permission_command(message: types.Message) -> None:
    """Yetki verme: /yetkiver @username SEVİYE veya reply ile /yetkiver SEVİYE"""
    # /adminyap komutunun aynısı, sadece farklı isim
    await make_admin_command(message)

@router.message(Command("yetkial"))
async def take_permission_command(message: types.Message) -> None:
    """Yetki alma: /yetkial @username veya reply ile /yetkial"""
    # /adminçıkar komutunun aynısı, sadece farklı isim
    await remove_admin_command(message)

# =============================
# CALLBACK HANDLER'LARI
# =============================

@router.callback_query(F.data == "admin_permission_manager")
async def admin_permission_manager_callback(callback: types.CallbackQuery) -> None:
    """Admin izin yöneticisi callback handler"""
    try:
        user_id = callback.from_user.id
        config = get_config()
        
        # Super Admin kontrolü
        from config import is_admin
        if not is_admin(user_id):
            await callback.answer("❌ Bu işlemi sadece Super Admin yapabilir!", show_alert=True)
            return
        
        # Admin izin yöneticisi menüsünü göster
        menu_message = f"""
🛡️ **ADMİN İZİN YÖNETİCİSİ**

🎯 **Mevcut Durum:** ✅ Aktif
📊 **Router Durumu:** ✅ Entegre edildi

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **KOMUTLAR:**
• `/adminyap` - Admin yetkisi ver
• `/adminçıkar` - Admin yetkisi al
• `/adminlist` - Admin listesi
• `/admininfo` - Kullanıcı bilgisi
• `/yetkiver` - Yetki verme (alias)
• `/yetkial` - Yetki alma (alias)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **Bilgi:** Sistem Super Admin tarafından yönetilir.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Admin Listesi", callback_data="admin_list_callback")],
            [InlineKeyboardButton(text="🛡️ Yetki Yönetimi", callback_data="admin_permission_management")],
            [InlineKeyboardButton(text="📊 İstatistikler", callback_data="admin_permission_stats")],
            [InlineKeyboardButton(text="❌ Kapat", callback_data="admin_permission_close")]
        ])
        
        # Mesaj aynıysa gereksiz güncellemeyi atla
        try:
            current_text = callback.message.text or ""
            if current_text.strip() == menu_message.strip():
                await callback.answer("✅ Güncel", show_alert=False)
            else:
                await callback.message.edit_text(
                    menu_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
        except Exception as edit_err:
            logger.warning(f"⚠️ edit_text atlandı: {edit_err}")
        
    except Exception as e:
        logger.error(f"❌ Admin permission manager callback hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.callback_query(F.data == "admin_list_callback")
async def admin_list_callback_handler(callback: types.CallbackQuery) -> None:
    """Admin listesi callback handler"""
    try:
        user_id = callback.from_user.id
        config = get_config()
        
        # Super Admin kontrolü
        from config import is_admin
        if not is_admin(user_id):
            await callback.answer("❌ Bu işlemi sadece Super Admin yapabilir!", show_alert=True)
            return
        
        # Admin listesini al
        result = await get_all_admins_db()
        
        if result["success"]:
            admin_list = "🛡️ **ADMİN LİSTESİ**\n\n"
            
            for admin in result["admins"]:
                level_name = get_rank_name(admin["rank_id"])
                username = admin['username'] or 'Kullanıcı adı yok'
                last_activity = admin['last_activity'].strftime('%d.%m.%Y %H:%M') if admin['last_activity'] else 'Bilinmiyor'
                
                admin_list += f"👤 **{admin['first_name']}** (@{username})\n"
                admin_list += f"🛡️ **Seviye:** {level_name}\n"
                admin_list += f"📅 **Son Aktivite:** {last_activity}\n\n"
            
            admin_list += f"📊 **Toplam Admin:** {len(result['admins'])} kişi"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Yenile", callback_data="admin_list_callback")],
                [InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_permission_manager")],
                [InlineKeyboardButton(text="❌ Kapat", callback_data="admin_permission_close")]
            ])
            
            # Mesaj aynıysa gereksiz güncellemeyi atla
            try:
                current_text = callback.message.text or ""
                if current_text.strip() == admin_list.strip():
                    await callback.answer("✅ Güncel", show_alert=False)
                else:
                    await callback.message.edit_text(
                        admin_list,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
            except Exception as edit_err:
                logger.warning(f"⚠️ edit_text atlandı: {edit_err}")
        else:
            await callback.answer(f"❌ Hata: {result['error']}", show_alert=True)
        
    except Exception as e:
        logger.error(f"❌ Admin list callback hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.callback_query(F.data == "admin_permission_management")
async def admin_permission_management_callback(callback: types.CallbackQuery) -> None:
    """Admin yetki yönetimi callback handler"""
    try:
        user_id = callback.from_user.id
        config = get_config()
        
        # Super Admin kontrolü
        if user_id != config.ADMIN_USER_ID:
            await callback.answer("❌ Bu işlemi sadece Super Admin yapabilir!", show_alert=True)
            return
        
        # Yetki yönetimi menüsünü göster
        management_message = f"""
🛡️ **ADMİN YETKİ YÖNETİMİ**

📋 **Kullanım Komutları:**

**👑 Admin Yetkisi Verme:**
• `/adminyap SEVİYE` (reply ile)
• `/adminyap @username SEVİYE` (etiket ile)

**❌ Admin Yetkisi Alma:**
• `/adminçıkar` (reply ile)
• `/adminçıkar @username` (etiket ile)

**📊 Bilgi Alma:**
• `/admininfo` (reply ile)
• `/admininfo @username` (etiket ile)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**🛡️ Seviye Sistemi:**
• **1:** Üye (Temel komutlar)
• **2:** Admin 1 (Chat moderasyon + Bakiye yönetimi)
• **3:** Admin 2 (Grup kayıt + Etkinlik yönetimi)
• **4:** Super Admin (Tam yetki + Sistem ayarları)

💡 **Not:** Sadece Super Admin yetki verebilir/alabilir.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Admin Listesi", callback_data="admin_list_callback")],
            [InlineKeyboardButton(text="📊 İstatistikler", callback_data="admin_permission_stats")],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_permission_manager")],
            [InlineKeyboardButton(text="❌ Kapat", callback_data="admin_permission_close")]
        ])
        
        # Mesaj aynıysa gereksiz güncellemeyi atla
        try:
            current_text = callback.message.text or ""
            if current_text.strip() == management_message.strip():
                await callback.answer("✅ Güncel", show_alert=False)
            else:
                await callback.message.edit_text(
                    management_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
        except Exception as edit_err:
            logger.warning(f"⚠️ edit_text atlandı: {edit_err}")
        
    except Exception as e:
        logger.error(f"❌ Admin permission management callback hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.callback_query(F.data == "admin_permission_stats")
async def admin_permission_stats_callback(callback: types.CallbackQuery) -> None:
    """Admin izin istatistikleri callback handler"""
    try:
        user_id = callback.from_user.id
        config = get_config()
        
        # Super Admin kontrolü
        if user_id != config.ADMIN_USER_ID:
            await callback.answer("❌ Bu işlemi sadece Super Admin yapabilir!", show_alert=True)
            return
        
        # Admin listesini al
        result = await get_all_admins_db()
        
        if result["success"]:
            # Seviye bazlı istatistikler
            level_stats = {}
            for admin in result["admins"]:
                level = admin["rank_id"]
                level_stats[level] = level_stats.get(level, 0) + 1
            
            stats_message = f"""
📊 **ADMİN İZİN İSTATİSTİKLERİ**

👥 **Genel İstatistikler:**
• **Toplam Admin:** {len(result['admins'])} kişi
• **Aktif Sistem:** ✅ Çalışıyor
• **Router Durumu:** ✅ Entegre edildi

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛡️ **Seviye Dağılımı:**
"""
            
            for level in sorted(level_stats.keys()):
                level_name = get_rank_name(level)
                count = level_stats[level]
                stats_message += f"• **{level_name}:** {count} kişi\n"
            
            stats_message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **Sistem Durumu:** ✅ Aktif ve çalışıyor
        """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Yenile", callback_data="admin_permission_stats")],
                [InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_permission_manager")],
                [InlineKeyboardButton(text="❌ Kapat", callback_data="admin_permission_close")]
            ])
            
            await callback.message.edit_text(
                stats_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            await callback.answer(f"❌ Hata: {result['error']}", show_alert=True)
        
    except Exception as e:
        logger.error(f"❌ Admin permission stats callback hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.callback_query(F.data == "admin_permission_close")
async def admin_permission_close_callback(callback: types.CallbackQuery) -> None:
    """Admin izin yöneticisi kapatma callback handler"""
    try:
        await callback.message.delete()
        await callback.answer("❌ Mesaj kapatıldı")
        
    except Exception as e:
        logger.error(f"❌ Admin permission close callback hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

# =============================
# DIŞA AÇIK FONKSİYONLAR
# =============================

async def make_user_admin(user_id: int, admin_level: int) -> dict:
    """Dış modüller için admin yetkisi verme fonksiyonu"""
    return await update_user_rank_db(user_id, admin_level)

async def remove_user_admin(user_id: int) -> dict:
    """Dış modüller için admin yetkisini alma fonksiyonu"""
    return await update_user_rank_db(user_id, 1)

async def get_user_admin_info(user_id: int) -> dict:
    """Dış modüller için kullanıcı admin bilgisi alma fonksiyonu"""
    return await get_user_admin_info_db(user_id)

async def get_admin_list() -> dict:
    """Dış modüller için admin listesi alma fonksiyonu"""
    return await get_all_admins_db() 