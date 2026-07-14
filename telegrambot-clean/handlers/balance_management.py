"""
💰 Çok Basit Bakiye Sistemi - KirveHub Bot
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from aiogram import Router, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config import get_config
from utils.logger import logger

# Database bağlantısını kontrol et
def check_db_pool():
    try:
        from database import db_pool
        if not db_pool:
            logger.error("❌ Database pool yok!")
            return False
        return True
    except Exception as e:
        logger.error(f"❌ Database pool kontrol hatası: {e}")
        return False

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

# @router.message(Command("bakiyee"))
async def add_balance_command(message: Message) -> None:
    """Bakiye ekleme: reply veya etiket ile /bakiyee MIKTAR"""
    try:
        # Admin kontrolü (Admin2+)
        try:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(message.from_user.id, 3):
                return
        except Exception:
            config = get_config()
            if message.from_user.id != config.ADMIN_USER_ID:
                return
        
        # Grup chatindeyse komut mesajını sil ve özel mesajla işlem yap
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
        
        # Komut metnini parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        user_id = None
        amount = None
        
        # 1. Reply ile kullanım: /bakiyee MIKTAR
        if message.reply_to_message and len(parts) == 2:
            try:
                user_id = message.reply_to_message.from_user.id
                amount = float(parts[1])
            except ValueError:
                await send_error_message(message, "❌ Geçersiz miktar! Örnek: `/bakiyee 10`")
                return
        
        # 2. Etiket ile kullanım: /bakiyee @username MIKTAR
        elif len(parts) == 3 and parts[1] and parts[1].startswith('@'):
            try:
                username = parts[1][1:]  # @ işaretini kaldır
                amount = float(parts[2])
                
                # Username'den user_id bul
                user_id = await find_user_by_username(username)
                if not user_id:
                    await send_error_message(message, f"❌ Kullanıcı bulunamadı: @{username}")
                    return
                    
            except ValueError:
                await send_error_message(message, "❌ Geçersiz miktar! Örnek: `/bakiyee @username 10`")
                return
        
        else:
            await send_error_message(message, "❌ Kullanım:\n• `/bakiyee MIKTAR` (reply ile)\n• `/bakiyee @username MIKTAR` (etiket ile)")
            return
        
        if amount <= 0:
            await send_error_message(message, "❌ Miktar pozitif olmalı!")
            return
        
        # Bakiye ekleme işlemi
        result = await add_balance_simple(user_id, amount)
        
        if result["success"]:
            response = f"""
✅ **Bakiye Eklendi!**

**👤 User ID:** {user_id}
**💰 Eski Bakiye:** {result["old_balance"]:.2f} KP
**💰 Yeni Bakiye:** {result["new_balance"]:.2f} KP
**➕ Eklenen:** {amount:.2f} KP
            """
            
            # Kullanıcıya bildirim gönder
            await notify_user_balance_change(user_id, message.from_user.id, amount, "add", result["old_balance"], result["new_balance"])
        else:
            response = f"❌ Hata: {result['error']}"
        
        await send_response_message(message, response)
        
    except Exception as e:
        logger.error(f"❌ Add balance hatası: {e}")
        await send_error_message(message, "❌ Bir hata oluştu!")

# @router.message(Command("bakiyeeid"))
async def add_balance_id_command(message: Message) -> None:
    """ID ile bakiye ekleme: /bakiyeeid USER_ID MIKTAR"""
    try:
        # Admin kontrolü (Admin2+)
        try:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(message.from_user.id, 3):
                return
        except Exception:
            config = get_config()
            if message.from_user.id != config.ADMIN_USER_ID:
                return
        
        # Grup chatindeyse komut mesajını sil ve özel mesajla işlem yap
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
        
        # Komut metnini parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        if len(parts) != 3:
            await send_error_message(message, "❌ Kullanım: `/bakiyeeid USER_ID MIKTAR`\nÖrnek: `/bakiyeeid 6513506166 10`")
            return
        
        try:
            user_id = int(parts[1])
            amount = float(parts[2])
        except ValueError:
            await send_error_message(message, "❌ Geçersiz ID veya miktar! Örnek: `/bakiyeeid 6513506166 10`")
            return
        
        if amount <= 0:
            await send_error_message(message, "❌ Miktar pozitif olmalı!")
            return
        
        # Bakiye ekleme işlemi
        result = await add_balance_simple(user_id, amount)
        
        if result["success"]:
            response = f"""
✅ **Bakiye Eklendi!**

**👤 User ID:** {user_id}
**💰 Eski Bakiye:** {result["old_balance"]:.2f} KP
**💰 Yeni Bakiye:** {result["new_balance"]:.2f} KP
**➕ Eklenen:** {amount:.2f} KP
            """
            
            # Kullanıcıya bildirim gönder
            await notify_user_balance_change(user_id, message.from_user.id, amount, "add", result["old_balance"], result["new_balance"])
        else:
            response = f"❌ Hata: {result['error']}"
        
        await send_response_message(message, response)
        
    except Exception as e:
        logger.error(f"❌ Add balance ID hatası: {e}")
        await send_error_message(message, "❌ Bir hata oluştu!")

# @router.message(Command("bakiyec"))
async def remove_balance_command(message: Message) -> None:
    """Bakiye çıkarma: reply veya etiket ile /bakiyec MIKTAR"""
    try:
        # Admin kontrolü
        config = get_config()
        if message.from_user.id != config.ADMIN_USER_ID:
            return
        
        # Grup chatindeyse komut mesajını sil ve özel mesajla işlem yap
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
        
        # Komut metnini parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        user_id = None
        amount = None
        
        # 1. Reply ile kullanım: /bakiyec MIKTAR
        if message.reply_to_message and len(parts) == 2:
            try:
                user_id = message.reply_to_message.from_user.id
                amount = float(parts[1])
            except ValueError:
                await send_error_message(message, "❌ Geçersiz miktar! Örnek: `/bakiyec 10`")
                return
        
        # 2. Etiket ile kullanım: /bakiyec @username MIKTAR
        elif len(parts) == 3 and parts[1] and parts[1].startswith('@'):
            try:
                username = parts[1][1:]  # @ işaretini kaldır
                amount = float(parts[2])
                
                # Username'den user_id bul
                user_id = await find_user_by_username(username)
                if not user_id:
                    await send_error_message(message, f"❌ Kullanıcı bulunamadı: @{username}")
                    return
                    
            except ValueError:
                await send_error_message(message, "❌ Geçersiz miktar! Örnek: `/bakiyec @username 10`")
                return
        
        else:
            await send_error_message(message, "❌ Kullanım:\n• `/bakiyec MIKTAR` (reply ile)\n• `/bakiyec @username MIKTAR` (etiket ile)")
            return
        
        if amount <= 0:
            await send_error_message(message, "❌ Miktar pozitif olmalı!")
            return
        
        # Bakiye çıkarma işlemi
        result = await remove_balance_simple(user_id, amount)
        
        if result["success"]:
            response = f"""
✅ **Bakiye Çıkarıldı!**

**👤 User ID:** {user_id}
**💰 Eski Bakiye:** {result["old_balance"]:.2f} KP
**💰 Yeni Bakiye:** {result["new_balance"]:.2f} KP
**➖ Çıkarılan:** {amount:.2f} KP
            """
            
            # Kullanıcıya bildirim gönder
            await notify_user_balance_change(user_id, message.from_user.id, amount, "remove", result["old_balance"], result["new_balance"])
        else:
            response = f"❌ Hata: {result['error']}"
        
        await send_response_message(message, response)
        
    except Exception as e:
        logger.error(f"❌ Remove balance hatası: {e}")
        await send_error_message(message, "❌ Bir hata oluştu!")

# @router.message(Command("bakiyecid"))
async def remove_balance_id_command(message: Message) -> None:
    """ID ile bakiye çıkarma: /bakiyecid USER_ID MIKTAR"""
    try:
        # Admin kontrolü
        config = get_config()
        if message.from_user.id != config.ADMIN_USER_ID:
            return
        
        # Grup chatindeyse komut mesajını sil ve özel mesajla işlem yap
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
        
        # Komut metnini parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        if len(parts) != 3:
            await send_error_message(message, "❌ Kullanım: `/bakiyecid USER_ID MIKTAR`\nÖrnek: `/bakiyecid 6513506166 10`")
            return
        
        try:
            user_id = int(parts[1])
            amount = float(parts[2])
        except ValueError:
            await send_error_message(message, "❌ Geçersiz ID veya miktar! Örnek: `/bakiyecid 6513506166 10`")
            return
        
        if amount <= 0:
            await send_error_message(message, "❌ Miktar pozitif olmalı!")
            return
        
        # Bakiye çıkarma işlemi
        result = await remove_balance_simple(user_id, amount)
        
        if result["success"]:
            response = f"""
✅ **Bakiye Çıkarıldı!**

**👤 User ID:** {user_id}
**💰 Eski Bakiye:** {result["old_balance"]:.2f} KP
**💰 Yeni Bakiye:** {result["new_balance"]:.2f} KP
**➖ Çıkarılan:** {amount:.2f} KP
            """
            
            # Kullanıcıya bildirim gönder
            await notify_user_balance_change(user_id, message.from_user.id, amount, "remove", result["old_balance"], result["new_balance"])
        else:
            response = f"❌ Hata: {result['error']}"
        
        await send_response_message(message, response)
        
    except Exception as e:
        logger.error(f"❌ Remove balance ID hatası: {e}")
        await send_error_message(message, "❌ Bir hata oluştu!")

async def add_balance_simple(user_id: int, amount: float) -> dict:
    """Çok basit bakiye ekleme"""
    try:
        if not check_db_pool():
            return {"success": False, "error": "Database bağlantısı yok"}
        
        from database import db_pool
        async with db_pool.acquire() as conn:
            # Kullanıcıyı bul
            user = await conn.fetchrow("""
                SELECT user_id, first_name, COALESCE(kirve_points, 0) as current_balance
                FROM users WHERE user_id = $1
            """, user_id)
            
            if not user:
                return {"success": False, "error": f"Kullanıcı bulunamadı: {user_id}"}
            
            current_balance = float(user["current_balance"])
            new_balance = current_balance + amount
            
            # Bakiyeyi güncelle
            await conn.execute("""
                UPDATE users 
                SET kirve_points = $1, last_activity = NOW()
                WHERE user_id = $2
            """, new_balance, user_id)
            
            logger.info(f"💰 Bakiye eklendi - User: {user_id}, Amount: {amount}, Old: {current_balance}, New: {new_balance}")
            
            return {
                "success": True,
                "old_balance": current_balance,
                "new_balance": new_balance,
                "amount": amount
            }
            
    except Exception as e:
        logger.error(f"❌ Add balance simple hatası: {e}")
        return {"success": False, "error": str(e)}

async def remove_balance_simple(user_id: int, amount: float) -> dict:
    """Çok basit bakiye çıkarma"""
    try:
        if not check_db_pool():
            return {"success": False, "error": "Database bağlantısı yok"}
        
        from database import db_pool
        async with db_pool.acquire() as conn:
            # Kullanıcıyı bul
            user = await conn.fetchrow("""
                SELECT user_id, first_name, COALESCE(kirve_points, 0) as current_balance
                FROM users WHERE user_id = $1
            """, user_id)
            
            if not user:
                return {"success": False, "error": f"Kullanıcı bulunamadı: {user_id}"}
            
            current_balance = float(user["current_balance"])
            new_balance = max(0, current_balance - amount)  # Negatif olmasın
            
            # Bakiyeyi güncelle
            await conn.execute("""
                UPDATE users 
                SET kirve_points = $1, last_activity = NOW()
                WHERE user_id = $2
            """, new_balance, user_id)
            
            logger.info(f"💰 Bakiye çıkarıldı - User: {user_id}, Amount: {amount}, Old: {current_balance}, New: {new_balance}")
            
            return {
                "success": True,
                "old_balance": current_balance,
                "new_balance": new_balance,
                "amount": amount
            }
            
    except Exception as e:
        logger.error(f"❌ Remove balance simple hatası: {e}")
        return {"success": False, "error": str(e)}

async def send_error_message(message: Message, text: str) -> None:
    """Hata mesajı gönder"""
    if message.chat.type == "private":
        await message.reply(text)
    else:
        sent_message = await message.answer("❌ Hata oluştu! Detaylar özel mesajda.")
        await _bot_instance.send_message(message.from_user.id, text)
        asyncio.create_task(delete_message_after_delay(sent_message))

async def send_response_message(message: Message, text: str) -> None:
    """Yanıt mesajı gönder"""
    if message.chat.type == "private":
        await message.reply(text, parse_mode="Markdown")
    else:
        sent_message = await message.answer("✅ İşlem tamamlandı! Detaylar özel mesajda.")
        await _bot_instance.send_message(message.from_user.id, text, parse_mode="Markdown")
        asyncio.create_task(delete_message_after_delay(sent_message))

async def notify_user_balance_change(user_id: int, admin_id: int, amount: float, operation: str, old_balance: float, new_balance: float) -> None:
    """Kullanıcıya bakiye değişikliği bildirimi gönder"""
    try:
        from database import db_pool
        if not db_pool:
            return
        
        # Admin bilgilerini al
        async with db_pool.acquire() as conn:
            admin_info = await conn.fetchrow("""
                SELECT first_name, username FROM users WHERE user_id = $1
            """, admin_id)
        
        admin_name = admin_info["first_name"] if admin_info else "Admin"
        admin_username = admin_info["username"] if admin_info else ""
        
        # Kullanıcı bilgilerini al
        user_info = await conn.fetchrow("""
            SELECT first_name, username FROM users WHERE user_id = $1
        """, user_id)
        
        user_name = user_info["first_name"] if user_info else "Kullanıcı"
        
        # İşlem türü
        if operation == "add":
            operation_text = "💰 **Bakiye Eklendi!**"
            amount_text = f"➕ **Eklenen:** {amount:.2f} KP"
            admin_action = f"👤 **Admin:** {admin_name}"
        else:
            operation_text = "💰 **Bakiye Çıkarıldı!**"
            amount_text = f"➖ **Çıkarılan:** {amount:.2f} KP"
            admin_action = f"👤 **Admin:** {admin_name}"
        
        # Bildirim mesajı
        notification = f"""
{operation_text}

{admin_action}
{amount_text}

**💰 Eski Bakiye:** {old_balance:.2f} KP
**💰 Yeni Bakiye:** {new_balance:.2f} KP

**⏰ Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}
        """
        
        # Kullanıcıya bildirim gönder
        await _bot_instance.send_message(user_id, notification, parse_mode="Markdown")
        logger.info(f"📬 Bakiye bildirimi gönderildi - User: {user_id}, Admin: {admin_id}, Amount: {amount}")
        
    except Exception as e:
        logger.error(f"❌ Bakiye bildirimi hatası: {e}")

async def find_user_by_username(username: str) -> Optional[int]:
    """Username'den user_id bul"""
    try:
        if not check_db_pool():
            return None
        
        from database import db_pool
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT user_id FROM users WHERE username = $1
            """, username)
            
            if user:
                return user["user_id"]
            else:
                return None
                
    except Exception as e:
        logger.error(f"❌ Find user by username hatası: {e}")
        return None 

async def show_add_balance_menu(callback, user_data):
    """Bakiye ekleme menüsü"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Kullanıcıya Bakiye Ekle", callback_data="balance_add_user"),
            InlineKeyboardButton(text="📝 ID ile Bakiye Ekle", callback_data="balance_add_id")
        ],
        [
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
➕ **Bakiye Ekleme**

**Mevcut Komutlar:**
• `/bakiyee [miktar]` - Reply ile bakiye ekle
• `/bakiyeeid [user_id] [miktar]` - ID ile bakiye ekle

**Buton İşlemleri:**
• Kullanıcı seçerek bakiye ekleme
• ID girerek bakiye ekleme

Hangi yöntemi kullanmak istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def show_remove_balance_menu(callback, user_data):
    """Bakiye çıkarma menüsü"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Kullanıcıdan Bakiye Çıkar", callback_data="balance_remove_user"),
            InlineKeyboardButton(text="📝 ID ile Bakiye Çıkar", callback_data="balance_remove_id")
        ],
        [
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
➖ **Bakiye Çıkarma**

**Mevcut Komutlar:**
• `/bakiyec [miktar]` - Reply ile bakiye çıkar
• `/bakiyecid [user_id] [miktar]` - ID ile bakiye çıkar

**Buton İşlemleri:**
• Kullanıcı seçerek bakiye çıkarma
• ID girerek bakiye çıkarma

Hangi yöntemi kullanmak istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def show_bulk_balance_menu(callback, user_data):
    """Toplu bakiye menüsü - Artık Bakiye Etkinliği"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎉 Yeni Bakiye Etkinliği", callback_data="balance_event_new"),
            InlineKeyboardButton(text="📋 Aktif Etkinlikler", callback_data="balance_event_list")
        ],
        [
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
🎉 **Bakiye Etkinliği**

**Mevcut Komutlar:**
• `/sürpriz [miktar]` - Bakiye etkinliği başlat

**Buton İşlemleri:**
• Yeni bakiye etkinliği oluşturma
• Aktif etkinlikleri görüntüleme

Hangi işlemi yapmak istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    ) 

async def handle_balance_callback(callback):
    """Bakiye yönetimi callback handler"""
    try:
        user_id = callback.from_user.id
        action = callback.data
        
        # Admin kontrolü
        from config import get_config
        config = get_config()
        if user_id != config.ADMIN_USER_ID:
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        if action == "admin_balance_add":
            await show_add_balance_menu(callback, {})
        elif action == "admin_balance_remove":
            await show_remove_balance_menu(callback, {})
        elif action == "admin_balance_surprise":
            await show_bulk_balance_menu(callback, {})
        elif action == "admin_balance_report":
            await show_balance_report(callback)
        else:
            await callback.answer("❌ Bilinmeyen bakiye işlemi!", show_alert=True)
            
    except Exception as e:
        logger.error(f"❌ Bakiye callback hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def show_balance_report(callback):
    """Bakiye raporu göster"""
    try:
        # Basit bakiye raporu
        response = """
💰 **Bakiye Raporu**

**Komutlar:**
• `/bakiyee MIKTAR` - Bakiye ekle (reply ile)
• `/bakiyec MIKTAR` - Bakiye çıkar (reply ile)
• `/bakiyeeid USER_ID MIKTAR` - ID ile bakiye ekle
• `/bakiyecid USER_ID MIKTAR` - ID ile bakiye çıkar

**Örnek Kullanım:**
• `/bakiyee 10` (reply ile)
• `/bakiyec 5` (reply ile)
• `/bakiyeeid 123456789 20`
• `/bakiyecid 123456789 10`

**Not:** Reply ile kullanım daha hızlıdır.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_balance_management")
            ]
        ])
        
        await callback.message.edit_text(
            response,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Bakiye raporu hatası: {e}")
        await callback.answer("❌ Rapor yüklenemedi!", show_alert=True) 