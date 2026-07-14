"""
👑 Admin Panel Sistemi - KirveHub Bot
Kapsamlı admin yönetim paneli ve komutları
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

# --- Recruitment yardımcıları (stub) ve db erişimi ---
try:
    from database import db_pool  # bazı bölümlerde referans veriliyor
except Exception:
    db_pool = None

_recruitment_active = True

def get_recruitment_status() -> bool:
    return _recruitment_active

def toggle_recruitment_system() -> bool:
    global _recruitment_active
    _recruitment_active = not _recruitment_active
    return _recruitment_active
from utils.logger import logger, log_system, log_error, log_warning, log_info
from utils.command_logger import log_command, log_admin

router = Router()

# Global variables
_bot_instance = None
admin_order_states = {}  # Admin sipariş durumları için
site_creation_data = {}  # Site ekleme süreci için state management
site_edit_data = {}  # Site düzenleme süreci için state management
site_delete_data = {}  # Site silme süreci için state management

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

async def _send_admin_panel_privately(user_id: int):
    """Admin paneli özel mesajla gönder - Görseldeki tasarım"""
    try:
        # Görseldeki admin panel buton düzeni
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Toplu Mesaj Gönder", callback_data="admin_broadcast"),
                InlineKeyboardButton(text="🔧 Komut Oluşturucu", callback_data="admin_command_creator")
            ],
            [
                InlineKeyboardButton(text="📊 Raporlar", callback_data="admin_reports"),
                InlineKeyboardButton(text="🛍️ Market Yönetimi", callback_data="admin_market_management")
            ],
            [
                InlineKeyboardButton(text="🌐 Site Yönetimi", callback_data="admin_site_management"),
                InlineKeyboardButton(text="🛡️ Admin Komutları", callback_data="admin_commands_list")
            ],
            [
                InlineKeyboardButton(text="🎲 Çekiliş Yap", callback_data="admin_lottery_create"),
                InlineKeyboardButton(text="⚙️ Sistem Yönetimi", callback_data="admin_system_management")
            ],
            [
                InlineKeyboardButton(text="⏰ Zamanlanmış Mesajlar", callback_data="admin_scheduled_messages"),
                InlineKeyboardButton(text="🛡️ Admin İzin Yöneticisi", callback_data="admin_permission_manager")
            ],
            [
                InlineKeyboardButton(text="🔄 Botu Yeniden Başlat", callback_data="admin_restart_bot")
            ]
        ])
        
        admin_message = f"""
KirveHub Media
/adminpanel
✅ Yönetici Paneli

Hoş geldiniz, KirveHub!

Hangi işlemi yapmak istiyorsun? {datetime.now().strftime('%H:%M')}
        """
        
        await _bot_instance.send_message(
            user_id,
            admin_message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logger.info(f"✅ Admin panel özel mesajla gönderildi: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Admin panel gönderilemedi: {e}")

# @router.message(Command("adminpanel"))  # MANUEL KAYITLI - ROUTER DEVRESİ DIŞI
async def admin_panel_command(message: types.Message) -> None:
    """Admin panel komutu - Görseldeki tasarım"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        config = get_config()
        
        # Detaylı log
        logger.info(f"🛡️ Admin panel komutu çağrıldı - User: {user_id} (@{username})")
        log_system(f"🛡️ Admin panel komutu çağrıldı - User: {user_id} (@{username})")
        
        # Admin kontrolü (DB tabanlı rank)
        try:
            from handlers.admin_permission_manager import get_user_admin_info_db
            admin_info = await get_user_admin_info_db(user_id)
            rank_id = admin_info.get("user", {}).get("rank_id", 1) if admin_info.get("success") else 1
        except Exception:
            rank_id = 1
        if rank_id <= 1:
            logger.warning(f"❌ Admin değil - User: {user_id} (@{username})")
            log_warning(f"❌ Admin değil - User: {user_id} (@{username})", None, None, None, None)
            return
        
        # Komut oluşturma sürecini iptal et (eğer varsa)
        try:
            from handlers.dynamic_command_creator import force_cancel_command_creation
            cancelled = await force_cancel_command_creation(user_id)
            if cancelled:
                logger.info(f"✅ Komut oluşturma süreci iptal edildi - User: {user_id}")
            else:
                logger.info(f"ℹ️ Komut oluşturma süreci yoktu - User: {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Komut oluşturma iptal hatası: {e}")
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                log_system(f"🔇 Admin panel komutu mesajı silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_admin_panel_privately(user_id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        log_system(f"🛡️ Admin panel komutu ÖZELİNDE - User: {message.from_user.first_name} ({user_id})")
        
        # Görseldeki admin panel buton düzeni
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Toplu Mesaj Gönder", callback_data="admin_broadcast"),
                InlineKeyboardButton(text="🔧 Komut Oluşturucu", callback_data="admin_command_creator")
            ],
            [
                InlineKeyboardButton(text="📊 Raporlar", callback_data="admin_reports"),
                InlineKeyboardButton(text="🛍️ Market Yönetimi", callback_data="admin_market_management")
            ],
            [
                InlineKeyboardButton(text="🎲 Çekiliş Yap", callback_data="admin_lottery_create"),
                InlineKeyboardButton(text="🛡️ Admin Komutları", callback_data="admin_commands_list")
            ],
            [
                InlineKeyboardButton(text="⚙️ Sistem Yönetimi", callback_data="admin_system_management"),
                InlineKeyboardButton(text="⏰ Zamanlanmış Mesajlar", callback_data="admin_scheduled_messages")
            ],
            [
                InlineKeyboardButton(text="🛡️ Admin İzin Yöneticisi", callback_data="admin_permission_manager")
            ],
            [
                InlineKeyboardButton(text="🔄 Botu Yeniden Başlat", callback_data="admin_restart_bot")
            ]
        ])
        
        admin_message = f"""
KirveHub Media
/adminpanel
✅ Yönetici Paneli

Hoş geldiniz, KirveHub!

Hangi işlemi yapmak istiyorsun? {datetime.now().strftime('%H:%M')}
        """
        
        await message.reply(
            admin_message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        logger.info(f"✅ Admin panel gösterildi - User: {user_id}")
        log_system(f"✅ Admin panel başarıyla gösterildi - User: {user_id} (@{username})")
        
    except Exception as e:
        logger.error(f"❌ Admin panel hatası: {e}")
        log_error(f"❌ Admin panel hatası: {e} - User: {user_id} (@{username})")
        await message.reply("❌ Admin panel yüklenemedi!")


# @router.callback_query(lambda c: c.data.startswith("admin_") or c.data.startswith("category_") or c.data.startswith("price_") or c.data in ["balance_commands", "event_commands", "system_commands", "admin_panel_main"] or c.data.startswith("event_") or c.data.startswith("admin_order_"))
async def admin_panel_callback(callback: types.CallbackQuery) -> None:
    """Admin panel callback handler"""
    try:
        user_id = callback.from_user.id
        username = callback.from_user.username or "Unknown"
        config = get_config()
        
        # Detaylı log
        logger.info(f"🔍 Admin panel callback alındı - User: {user_id} (@{username}) - Data: {callback.data}")
        
        # YENİ: EN BAŞTA DETAYLI LOGLAMA
        logger.info(f"🔍 CALLBACK RECEIVED - Raw data: {callback.data}")
        logger.info(f"🔍 CALLBACK RECEIVED - Type: {type(callback.data)}")
        logger.info(f"🔍 CALLBACK RECEIVED - Length: {len(callback.data) if callback.data else 0}")
        logger.info(f"🔍 CALLBACK RECEIVED - User: {user_id}")
        
        # Admin kontrolü (DB tabanlı rank)
        try:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(user_id, 3):
                await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
                return
        except Exception:
            await callback.answer("❌ Yetki doğrulanamadı!", show_alert=True)
            return
        
        action = callback.data
        logger.info(f"🔍 Callback data: {action} - User: {user_id}")
        
        # YENİ: DETAYLI LOGLAMA
        logger.info(f"🔍 CALLBACK DEBUG - Action: {action}, User: {user_id}")
        logger.info(f"🔍 CALLBACK DATA TYPE - Type: {type(action)}")
        logger.info(f"🔍 CALLBACK DATA LENGTH - Length: {len(action) if action else 0}")
        
        # Debug: Bilinmeyen callback'leri logla
        if action not in [
            "admin_settings", "admin_events_system", "admin_broadcast", "admin_market_management",
            "admin_market_orders", "admin_balance_management", "admin_recruitment_system",
            "admin_reports", "admin_statistics", "admin_restart_bot", "admin_command_creator",
            "admin_list_commands", "admin_create_command", "admin_back", "balance_commands",
            "event_commands", "system_commands", "admin_market", "admin_market_add",
            "admin_system_management", "admin_points_settings", "admin_daily_limit", "admin_weekly_limit",
            "set_points_custom", "set_daily_custom", "set_weekly_custom", "admin_permission_stats",
            "admin_permission_manager", "admin_permission_management", "admin_list_callback", "admin_permission_close",
            # Eksik olan ama desteklenen callback'ler
            "admin_commands_list", "admin_system_status"
        ]:
            logger.info(f"🔍 UNKNOWN CALLBACK - Action: {action}, User: {user_id}")
        
        # YENİ: ADMIN APPROVE/REJECT CALLBACK'LERİNİ KONTROL ET
        if action and action.startswith("admin_approve_"):
            logger.info(f"✅ ADMIN APPROVE CALLBACK DETECTED - Action: {action}, User: {user_id}")
            from handlers.admin_order_management import handle_admin_approve_order
            order_number = action.replace("admin_approve_", "")
            await handle_admin_approve_order(callback, order_number)
            return
        elif action and action.startswith("admin_reject_"):
            logger.info(f"❌ ADMIN REJECT CALLBACK DETECTED - Action: {action}, User: {user_id}")
            from handlers.admin_order_management import handle_admin_reject_order
            order_number = action.replace("admin_reject_", "")
            await handle_admin_reject_order(callback, order_number)
            return
        
        # YENİ: SET_POINTS_ CALLBACK'LERİNİ KONTROL ET
        if action and action.startswith("set_points_"):
            logger.info(f"💰 SET POINTS CALLBACK DETECTED - Action: {action}, User: {user_id}")
            await handle_points_setting(callback, action)
            return
        elif action and action.startswith("set_daily_"):
            logger.info(f"📅 SET DAILY CALLBACK DETECTED - Action: {action}, User: {user_id}")
            await handle_daily_limit_setting(callback, action)
            return
        elif action and action.startswith("set_weekly_"):
            logger.info(f"📊 SET WEEKLY CALLBACK DETECTED - Action: {action}, User: {user_id}")
            await handle_weekly_limit_setting(callback, action)
            return

        # YENİ BUTON SİSTEMİ - Görseldeki düzen
        if action == "admin_settings":
            logger.info(f"🔍 ADMIN SETTINGS CALLBACK - User: {user_id}")
            await show_settings_menu(callback)
        elif action == "admin_events_system":
            logger.info(f"🔍 ADMIN EVENTS SYSTEM CALLBACK - User: {user_id}")
        elif action == "admin_market_management":
            logger.info(f"🔍 ADMIN MARKET MANAGEMENT CALLBACK - User: {user_id}")
            await show_market_management_menu(callback)
        elif action == "admin_market_orders":
            logger.info(f"🔍 ADMIN MARKET ORDERS CALLBACK - User: {user_id}")
            # Sipariş yönetimi - yeni router sistemi
            await show_orders_list_callback(callback)
        # Market callback'lerini admin_market_management.py router'ına yönlendir
        # (admin_market_management ve admin_market_orders hariç - onlar yukarıda işleniyor)
        # admin_market ve admin_market_add da aşağıda özel handler'lara sahip
        elif action and action.startswith("admin_market_") and action not in ["admin_market_management", "admin_market_orders"]:
            logger.info(f"🔍 ADMIN MARKET CALLBACK YÖNLENDİRİLİYOR - Action: {action}, User: {user_id}")
            # admin_market_management.py'deki router'a yönlendir
            try:
                from handlers.admin_market_management import admin_market_callback_handler
                await admin_market_callback_handler(callback)
            except Exception as e:
                logger.error(f"❌ Market callback yönlendirme hatası: {e}", exc_info=True)
                await callback.answer("❌ Market işlemi yüklenirken hata oluştu!", show_alert=True)
        elif action == "admin_balance_management":
            logger.info(f"🔍 ADMIN BALANCE MANAGEMENT CALLBACK - User: {user_id}")
            await show_balance_management_menu(callback)
        elif action and action.startswith("admin_balance_"):
            logger.info(f"🔍 ADMIN BALANCE CALLBACK - User: {user_id}, Action: {action}")
            # Bakiye yönetimi callback'leri - balance_management.py'den çağır
            from handlers.balance_management import handle_balance_callback
            await handle_balance_callback(callback)
        elif action == "admin_recruitment_system":
            logger.info(f"🔍 ADMIN RECRUITMENT SYSTEM CALLBACK - User: {user_id}")
            await show_recruitment_system_menu(callback)
        elif action == "admin_reports":
            logger.info(f"📊 Admin reports callback tetiklendi - User: {user_id}")
            await show_reports_menu(callback)
        elif action == "admin_statistics":
            logger.info(f"🔍 ADMIN STATISTICS CALLBACK - User: {user_id}")
            await show_statistics_menu(callback)
        elif action == "admin_permission_manager":
            logger.info(f"🛡️ ADMIN PERMISSION MANAGER CALLBACK - User: {user_id}")
            from handlers.admin_permission_manager import admin_permission_manager_callback
            await admin_permission_manager_callback(callback)
        elif action == "bonus_stats":
            logger.info(f"🎁 BONUS STATS CALLBACK - User: {user_id}")
            from handlers.admin_bonus_stats import show_bonus_stats
            await show_bonus_stats(callback)
        elif action == "refresh_bonus_stats":
            logger.info(f"🔄 REFRESH BONUS STATS CALLBACK - User: {user_id}")
            from handlers.admin_bonus_stats import refresh_bonus_stats
            await refresh_bonus_stats(callback)
        elif action == "detailed_bonus_stats":
            logger.info(f"📊 DETAILED BONUS STATS CALLBACK - User: {user_id}")
            from handlers.admin_bonus_stats import show_detailed_bonus_stats
            await show_detailed_bonus_stats(callback)
        elif action and action.startswith("admin_stats_"):
            logger.info(f"🔍 ADMIN STATS CALLBACK - User: {user_id}, Action: {action}")
            # İstatistik callback'leri - statistics_system.py'den çağır
            from handlers.statistics_system import handle_stats_callback
            await handle_stats_callback(callback)
        elif action == "admin_restart_bot":
            logger.info(f"🔍 ADMIN RESTART BOT CALLBACK - User: {user_id}")
            """Bot restart onay menüsü"""
            try:
                user_id = callback.from_user.id
                config = get_config()
                
                # Admin kontrolü (Admin 3+)
                from handlers.admin_permission_manager import has_min_rank_db
                if not await has_min_rank_db(user_id, 3):
                    await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
                    return
                
                response = """
🔄 **BOT YENİDEN BAŞLATMA**

**⚠️ Dikkat:**
• Bot yeniden başlatılacak
• Tüm bağlantılar kesilecek
• ~10-15 saniye sürecek

**Onaylıyor musunuz?**
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Evet, Yeniden Başlat", callback_data="admin_restart_confirm"),
                        InlineKeyboardButton(text="❌ İptal", callback_data="admin_system_management")
                    ]
                ])
                
                await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
                
            except Exception as e:
                logger.error(f"❌ Bot restart callback hatası: {e}")
                await callback.answer("❌ Restart menüsü yüklenirken hata oluştu!", show_alert=True)
        elif action == "admin_broadcast":
            logger.info(f"🎯 BROADCAST CALLBACK YAKALANDI - User: {user_id}, Data: {action}")
            # Broadcast sistemi callback'i
            from handlers.broadcast_system import start_broadcast_callback
            await start_broadcast_callback(callback)
        elif action == "admin_broadcast_cancel":
            logger.info(f"🎯 BROADCAST CANCEL CALLBACK YAKALANDI - User: {user_id}, Data: {action}")
            # Broadcast iptal callback'i
            from handlers.broadcast_system import cancel_broadcast_callback
            await cancel_broadcast_callback(callback)
        elif action == "admin_command_creator":
            logger.info(f"🔍 ADMIN COMMAND CREATOR CALLBACK - User: {user_id}")
            await show_command_creator_menu(callback)
        elif action == "admin_list_commands":
            logger.info(f"🔍 ADMIN LIST COMMANDS CALLBACK - User: {user_id}")
            from handlers.dynamic_command_creator import list_custom_commands_handler
            await list_custom_commands_handler(callback)
        elif action == "admin_create_command":
            logger.info(f"🔍 ADMIN CREATE COMMAND CALLBACK - User: {user_id}")
            from handlers.dynamic_command_creator import start_command_creation
            await start_command_creation(callback)
        elif action == "admin_back":
            logger.info(f"🔍 ADMIN BACK CALLBACK - User: {user_id}")
            await show_back_menu(callback)
        elif action == "balance_commands":
            logger.info(f"🔍 BALANCE COMMANDS CALLBACK - User: {user_id}")
            await show_balance_commands_menu(callback)
        elif action == "event_commands":
            logger.info(f"🔍 EVENT COMMANDS CALLBACK - User: {user_id}")
            await show_event_commands_menu(callback)
        elif action == "system_commands":
            logger.info(f"🔍 SYSTEM COMMANDS CALLBACK - User: {user_id}")
            await show_system_commands_menu(callback)
        # Market callback'leri
        elif action == "admin_market":
            logger.info(f"🔍 ADMIN MARKET CALLBACK - User: {user_id}")
            await show_market_menu(callback)
        elif action == "admin_market_add":
            logger.info(f"🔍 ADMIN MARKET ADD CALLBACK - User: {user_id}")
            from handlers.admin_market_management import start_product_creation
            await start_product_creation(callback)
        # Diğer callback'ler
        elif action and action.startswith("category_"):
            logger.info(f"🔍 CATEGORY CALLBACK - User: {user_id}, Action: {action}")
            await handle_category_callback(callback, action)
        elif action and action.startswith("price_"):
            logger.info(f"🔍 PRICE CALLBACK - User: {user_id}, Action: {action}")
            await handle_price_callback(callback, action)
        elif action and action.startswith("admin_recruitment_"):
            logger.info(f"🔍 ADMIN RECRUITMENT CALLBACK - User: {user_id}, Action: {action}")
            # Kayıt teşvik sistemi işlemleri
            await handle_recruitment_callback(callback, action)
        elif action and action.startswith("recruitment_interval_"):
            logger.info(f"🔍 RECRUITMENT INTERVAL CALLBACK - User: {user_id}, Action: {action}")
            # Mesaj aralığı ayarlama
            await handle_recruitment_interval_callback(callback, action)
        elif action and action.startswith("admin_order_"):
            logger.info(f"🔍 ADMIN ORDER CALLBACK - User: {user_id}, Action: {action}")
            # Sipariş işlemleri
            parts = action.split("_")
            if len(parts) >= 4:
                order_id = int(parts[2])
                order_action = parts[3]
                await handle_order_action(callback, order_action, order_id)
        # Komut oluşturucu callback'leri
        elif action == "admin_create_command":
            logger.info(f"🔍 ADMIN CREATE COMMAND CALLBACK - User: {user_id}")
            # Dinamik komut oluşturucuyu başlat
            from handlers.dynamic_command_creator import start_command_creation
            await start_command_creation(callback)
        elif action == "admin_list_commands":
            logger.info(f"🔍 ADMIN LIST COMMANDS CALLBACK - User: {user_id}")
            from handlers.dynamic_command_creator import list_custom_commands_handler
            await list_custom_commands_handler(callback)
        elif action == "admin_delete_command":
            logger.info(f"🔍 ADMIN DELETE COMMAND CALLBACK - User: {user_id}")
            await callback.answer("🗑️ Komut silme özelliği yakında eklenecek!", show_alert=True)
        elif action == "admin_command_stats":
            logger.info(f"🔍 ADMIN COMMAND STATS CALLBACK - User: {user_id}")
            await callback.answer("📊 Komut istatistikleri yakında eklenecek!", show_alert=True)
        # SİSTEM YÖNETİMİ CALLBACK'LERİ
        elif action == "admin_system_management":
            logger.info(f"🔍 ADMIN SYSTEM MANAGEMENT CALLBACK - User: {user_id}")
            await show_system_management_menu(callback)
        elif action == "admin_link_commands":
            logger.info(f"🔍 ADMIN LINK COMMANDS CALLBACK - User: {user_id}")
            await show_link_commands_menu(callback)
        elif action == "admin_points_settings":
            logger.info(f"🔍 ADMIN POINTS SETTINGS CALLBACK - User: {user_id}")
            await show_points_settings_menu(callback)
        elif action == "admin_daily_limit":
            logger.info(f"🔍 ADMIN DAILY LIMIT CALLBACK - User: {user_id}")
            await show_daily_limit_menu(callback)
        elif action == "admin_weekly_limit":
            logger.info(f"🔍 ADMIN WEEKLY LIMIT CALLBACK - User: {user_id}")
            await show_weekly_limit_menu(callback)
        elif action == "admin_dynamic_settings":
            logger.info(f"🔍 ADMIN DYNAMIC SETTINGS CALLBACK - User: {user_id}")
            await show_dynamic_settings_menu(callback)
        elif action == "admin_system_status":
            logger.info(f"🔍 ADMIN SYSTEM STATUS CALLBACK - User: {user_id}")
            await show_system_status_menu(callback)
        elif action == "admin_permission_stats":
            logger.info(f"🔍 ADMIN PERMISSION STATS CALLBACK - User: {user_id}")
            from handlers.admin_permission_manager import admin_permission_stats_callback
            await admin_permission_stats_callback(callback)
        elif action == "admin_permission_manager":
            logger.info(f"🔍 ADMIN PERMISSION MANAGER CALLBACK - User: {user_id}")
            from handlers.admin_permission_manager import admin_permission_manager_callback
            await admin_permission_manager_callback(callback)
        elif action == "admin_permission_management":
            logger.info(f"🔍 ADMIN PERMISSION MANAGEMENT CALLBACK - User: {user_id}")
            from handlers.admin_permission_manager import admin_permission_management_callback
            await admin_permission_management_callback(callback)
        elif action == "admin_list_callback":
            logger.info(f"🔍 ADMIN LIST CALLBACK - User: {user_id}")
            from handlers.admin_permission_manager import admin_list_callback_handler
            await admin_list_callback_handler(callback)
        elif action == "admin_permission_close":
            logger.info(f"🔍 ADMIN PERMISSION CLOSE CALLBACK - User: {user_id}")
            from handlers.admin_permission_manager import admin_permission_close_callback
            await admin_permission_close_callback(callback)
        # SİSTEM YÖNETİMİ CALLBACK'LERİ - YENİ YAKLAŞIM
        elif action and action.startswith("set_points_"):
            logger.info(f"💰 SET POINTS CALLBACK - Action: {action}, User: {user_id}")
            await handle_points_setting(callback, action)
        elif action and action.startswith("set_daily_"):
            logger.info(f"📅 SET DAILY CALLBACK - Action: {action}, User: {user_id}")
            await handle_daily_limit_setting(callback, action)
        elif action and action.startswith("set_weekly_"):
            logger.info(f"📊 SET WEEKLY CALLBACK - Action: {action}, User: {user_id}")
            await handle_weekly_limit_setting(callback, action)
        elif action == "set_points_custom":
            logger.info(f"💰 SET POINTS CUSTOM CALLBACK - User: {user_id}")
            await start_custom_points_input(callback)
        elif action == "set_daily_custom":
            logger.info(f"📅 SET DAILY CUSTOM CALLBACK - User: {user_id}")
            await start_custom_daily_input(callback)
        elif action == "set_weekly_custom":
            logger.info(f"📊 SET WEEKLY CUSTOM CALLBACK - User: {user_id}")
            await start_custom_weekly_input(callback)
        # Rapor callback'leri - YENİ SİSTEM
        elif action == "admin_reports_users":
            await show_user_report(callback)
        elif action == "admin_reports_points":
            await show_point_report(callback)
        elif action == "admin_reports_events":
            await show_event_report(callback)
        elif action == "admin_reports_system":
            await show_system_report(callback)
        elif action == "admin_reports_users_refresh":
            await show_user_report(callback)
        elif action == "admin_reports_points_refresh":
            await show_point_report(callback)
        elif action == "admin_reports_events_refresh":
            await show_event_report(callback)
        elif action == "admin_reports_system_refresh":
            await show_system_report(callback)
        elif action == "admin_reports_users_detailed":
            await show_detailed_user_report(callback)
        elif action == "admin_reports_points_detailed":
            await show_detailed_point_report(callback)
        elif action == "admin_reports_events_detailed":
            await show_detailed_event_report(callback)
        elif action == "admin_reports_system_detailed":
            await show_detailed_system_report(callback)
        elif action == "admin_commands_list":
            await show_admin_commands_list(callback)

        elif action == "admin_site_management":
            await show_site_management_menu(callback)

        elif action and action.startswith("site_mgmt_"):
            # Site yönetim callback'leri
            if action == "site_mgmt_add":
                await start_site_creation(callback)
            elif action == "site_mgmt_list":
                await list_all_sites_admin(callback)
            elif action == "site_mgmt_edit":
                await show_site_edit_menu(callback)
            elif action == "site_mgmt_delete":
                await show_site_delete_menu(callback)
            elif action == "site_mgmt_cancel_creation":
                await cancel_site_creation(callback)
            elif action == "site_mgmt_confirm_creation":
                await confirm_site_creation(callback)
            elif action.startswith("site_mgmt_skip_"):
                # Opsiyonel adımları atla
                step = action.replace("site_mgmt_skip_", "")
                await skip_site_creation_step(callback, step)
            elif action == "site_mgmt_cancel_edit":
                await cancel_site_edit(callback)
            elif action == "site_mgmt_confirm_edit":
                await confirm_site_edit(callback)
            elif action == "site_mgmt_cancel_delete":
                await cancel_site_delete(callback)
            elif action == "site_mgmt_confirm_delete":
                await confirm_site_delete(callback)
            elif action.startswith("site_mgmt_edit_field_"):
                # Düzenlenecek alanı seç
                field = action.replace("site_mgmt_edit_field_", "")
                await start_site_field_edit(callback, field)

        elif action == "admin_lottery_create":
            # Direkt çekiliş oluşturma işlemini başlat
            try:
                user_id = callback.from_user.id
                config = get_config()
                
                logger.info(f"🎲 DIRECT LOTTERY CREATE - User: {user_id}")
                
                # Admin kontrolü (Admin 3+)
                from handlers.admin_permission_manager import has_min_rank_db
                if not await has_min_rank_db(user_id, 3):
                    await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
                    return
                
                # Memory manager kullanarak çekiliş oluşturma işlemini başlat
                from utils.memory_manager import memory_manager
                
                lottery_data = {
                    "type": "lottery",
                    "step": "cost",
                    "created_at": datetime.now()
                }
                
                memory_manager.set_lottery_data(user_id, lottery_data)
                memory_manager.set_input_state(user_id, "lottery_cost")
                
                logger.info(f"🎯 LOTTERY DATA SET FROM ADMIN - User: {user_id}, Step: cost, Data: {lottery_data}")
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
                ])
                
                await callback.message.edit_text(
                    "🎲 **Çekiliş Oluşturma**\n\n"
                    "Katılım ücreti kaç Kirve Point olsun?\n"
                    "Örnek: `10` veya `5.50`\n\n"
                    "**Lütfen ücreti yazın:**",
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                
                logger.info(f"✅ Çekiliş oluşturma başlatıldı - User: {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Çekiliş oluşturma hatası: {e}")
                await callback.answer("❌ Çekiliş oluşturma sırasında hata oluştu!", show_alert=True)
        elif action == "create_lottery_command":
            await execute_lottery_create_command(callback)
        elif action == "list_lotteries_command":
            await execute_list_lotteries_command(callback)
        elif action == "admin_scheduled_messages":
            logger.info(f"🔍 SCHEDULED MESSAGES CALLBACK YAKALANDI - User: {user_id}")
            try:
                from handlers.scheduled_messages import show_scheduled_messages_menu
                logger.info(f"✅ show_scheduled_messages_menu import edildi")
                await show_scheduled_messages_menu(callback)
                logger.info(f"✅ show_scheduled_messages_menu çalıştırıldı")
            except Exception as e:
                logger.error(f"❌ SCHEDULED MESSAGES HATA: {e}")
                import traceback
                logger.error(f"❌ TRACEBACK: {traceback.format_exc()}")
                await callback.answer("⚠️ Zamanlanmış mesajlar menüsü açılamadı!")
                return
        elif action == "scheduled_back":
            from handlers.scheduled_messages import show_scheduled_messages_menu
            await show_scheduled_messages_menu(callback)
        elif action == "admin_link_commands":
            await show_link_commands_menu(callback)
        elif action == "admin_scheduled_commands":
            await show_scheduled_commands_menu(callback)
        elif action == "create_link_command":
            from handlers.dynamic_command_creator import start_command_creation
            await start_command_creation(callback)
        elif action == "list_link_commands":
            await show_link_commands_list(callback)
        elif action == "manage_link_commands":
            await show_link_commands_management(callback)
        elif action == "link_stats":
            await show_link_commands_stats(callback)
        elif action == "admin_list_commands":
            from handlers.dynamic_command_creator import list_custom_commands_handler
            await list_custom_commands_handler(callback)
        elif action == "lottery_confirm_create":
            await handle_lottery_confirm_create(callback)
        elif action == "lottery_cancel":
            await handle_lottery_cancel(callback)
        elif action == "admin_restart_confirm":
            """Bot restart onayı"""
            try:
                user_id = callback.from_user.id
                config = get_config()
                
                # Admin kontrolü (Admin 3+)
                from handlers.admin_permission_manager import has_min_rank_db
                if not await has_min_rank_db(user_id, 3):
                    await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
                    return
                
                await callback.answer("🔄 Bot yeniden başlatılıyor...", show_alert=True)
                
                # Restart mesajı
                response = """
🔄 **BOT YENİDEN BAŞLATILIYOR**

**Durum:** Bot kapatılıyor ve yeniden başlatılıyor...
**Süre:** ~10-15 saniye

**Lütfen bekleyin...**
                """
                
                await callback.message.edit_text(response, parse_mode="Markdown")
                
                # Bot'u yeniden başlat
                import os
                import sys
                os.execv(sys.executable, ['python'] + sys.argv)
                
            except Exception as e:
                logger.error(f"❌ Bot restart hatası: {e}")
                await callback.answer("❌ Restart sırasında hata oluştu!", show_alert=True)
        elif action == "admin_maintenance_toggle":
            """Bakım modu toggle"""
            try:
                user_id = callback.from_user.id
                config = get_config()
                
                # Admin kontrolü (Admin 3+)
                from handlers.admin_permission_manager import has_min_rank_db
                if not await has_min_rank_db(user_id, 3):
                    await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
                    return
                
                # Bakım modunu toggle et
                import os
                from dotenv import load_dotenv
                
                # .env dosyasını oku
                load_dotenv()
                
                # Mevcut durumu al
                current_mode = os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true'
                new_mode = not current_mode
                
                # .env dosyasını güncelle
                env_path = '.env'
                if os.path.exists(env_path):
                    with open(env_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # MAINTENANCE_MODE satırını bul ve güncelle
                    updated = False
                    for i, line in enumerate(lines):
                        if line.startswith('MAINTENANCE_MODE='):
                            lines[i] = f'MAINTENANCE_MODE={str(new_mode).lower()}\n'
                            updated = True
                            break
                    
                    # Eğer satır yoksa ekle
                    if not updated:
                        lines.append(f'MAINTENANCE_MODE={str(new_mode).lower()}\n')
                    
                    # Dosyayı yaz
                    with open(env_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                
                status_text = "🔧 **BAKIM MODU AKTİF**" if new_mode else "✅ **BAKIM MODU KAPALI**"
                await callback.answer(f"{status_text}", show_alert=True)
                
                # Ana menüye geri dön
                await show_main_admin_menu(callback)
                
            except Exception as e:
                logger.error(f"❌ Bakım modu toggle hatası: {e}")
                await callback.answer("❌ Bakım modu değiştirilemedi!", show_alert=True)
        else:
            logger.info(f"🔍 UNHANDLED CALLBACK - Action: {action}, User: {user_id}")
            logger.info(f"🔍 CALLBACK DATA DEBUG - Raw data: {callback.data}")
            logger.info(f"🔍 CALLBACK DATA TYPE - Type: {type(callback.data)}")
            logger.info(f"🔍 CALLBACK DATA LENGTH - Length: {len(callback.data) if callback.data else 0}")
            await callback.answer("❌ Bilinmeyen admin işlemi!", show_alert=True)
            
    except Exception as e:
        logger.error(f"❌ Admin panel callback hatası: {e}")
        try:
            await callback.answer("❌ Bir hata oluştu!", show_alert=True)
        except Exception as answer_error:
            logger.error(f"❌ Callback answer da başarısız! {answer_error}")


async def show_balance_menu(callback: types.CallbackQuery) -> None:
    """Bakiye yönetimi menüsü"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Bakiye Ekle", callback_data="admin_balance_add"),
            InlineKeyboardButton(text="➖ Bakiye Çıkar", callback_data="admin_balance_remove")
        ],
        [
            InlineKeyboardButton(text="🎉 Bakiye Etkinliği", callback_data="admin_balance_event")
        ],
        [
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
💰 **Bakiye Yönetimi**

**Kullanılabilir İşlemler:**
• Bakiye ekleme/çıkarma
• Bakiye etkinlikleri

Hangi işlemi yapmak istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def show_settings_menu(callback: types.CallbackQuery) -> None:
    """Ayarlar menüsü"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚙️ Point Ayarları", callback_data="admin_settings_points"),
            InlineKeyboardButton(text="🕐 Zaman Ayarları", callback_data="admin_settings_time")
        ],
        [
            InlineKeyboardButton(text="🔔 Bildirim Ayarları", callback_data="admin_settings_notifications"),
            InlineKeyboardButton(text="🛡️ Güvenlik Ayarları", callback_data="admin_settings_security")
        ],
        [
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
⚙️ **Sistem Ayarları**

**Mevcut Ayarlar:**
• Point kazanım oranları
• Zaman limitleri
• Bildirim ayarları
• Güvenlik parametreleri

Hangi ayarı değiştirmek istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def show_events_system_menu(callback: types.CallbackQuery) -> None:
    """Etkinlik sistemi menüsü - Genel Çekiliş butonu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎲 Genel Çekiliş", callback_data="create_lottery_command")
        ],
        [
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
🎲 **ETKİNLİK SİSTEMİ**

🎯 **Genel çekiliş oluşturmak için aşağıdaki butona tıklayın:**

💡 **Bu buton direkt /cekilisyap komutunu çalıştırır.**
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def show_lottery_menu(callback: types.CallbackQuery) -> None:
    """Çekiliş botu menüsü"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎉 Yeni Çekiliş", callback_data="admin_lottery_new"),
            InlineKeyboardButton(text="📋 Aktif Çekilişler", callback_data="admin_lottery_active")
        ],
        [
            InlineKeyboardButton(text="🏆 Çekiliş Sonuçları", callback_data="admin_lottery_results"),
            InlineKeyboardButton(text="⚙️ Çekiliş Ayarları", callback_data="admin_lottery_settings")
        ],
        [
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
🎉 **Çekiliş Botu**

**Çekiliş Yönetimi:**
• Yeni çekiliş oluşturma
• Aktif çekilişleri görüntüleme
• Sonuçları kontrol etme
• Çekiliş ayarları

Hangi işlemi yapmak istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def show_broadcast_menu(callback: types.CallbackQuery) -> None:
    """Toplu mesaj menüsü (sade)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Toplu Mesaj", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
📢 **Toplu Mesaj Gönderimi**

Buraya yazacağınız mesaj, tüm kayıtlı kullanıcılara özelden gönderilecektir.

**Özellikler:**
• Tüm kayıtlı kullanıcılara gönderim
• Anlık sonuç raporu
• İptal seçeneği
• Güvenli admin kontrolü

Hangi işlemi yapmak istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def show_market_menu(callback: types.CallbackQuery) -> None:
    """Market yönetimi menüsü - /market komutu tetikler"""
    try:
        # /market komutunu tetikle
        from handlers.admin_market_management import market_management_command
        
        # Mesajı sil
        await callback.message.delete()
        
        # /market komutunu çalıştır
        await market_management_command(callback.message)
        
    except Exception as e:
        logger.error(f"❌ Market menu hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def show_recruitment_system_menu(callback: types.CallbackQuery) -> None:
    """Kayıt teşvik sistemi menüsü"""
    try:
        # Sistem durumunu al
        is_active = get_recruitment_status()
        status_text = "✅ **Aktif**" if is_active else "❌ **Pasif**"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Sistemi Kapat" if is_active else "✅ Sistemi Aç", 
                    callback_data="admin_recruitment_toggle"
                )
            ],
            [
                InlineKeyboardButton(text="⏰ Mesaj Aralığı", callback_data="admin_recruitment_interval"),
                InlineKeyboardButton(text="📝 Mesaj Şablonları", callback_data="admin_recruitment_templates")
            ],
            [
                InlineKeyboardButton(text="📊 İstatistikler", callback_data="admin_recruitment_stats"),
                InlineKeyboardButton(text="🎯 Test Mesajı", callback_data="admin_recruitment_test")
            ],
            [
                InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
            ]
        ])
        
        response = f"""
🎯 **Kayıt Teşvik Sistemi**

**Sistem Durumu:** {status_text}

**Yeni Özellikler:**
• 🆕 **Yeni kullanıcı tespiti** (ilk defa mesaj atanlar)
• ⏰ **5 dakika cooldown** (mesajlar arası)
• 📊 **Akıllı analiz** (3 mesajdan az atanlar)
• 🚫 **Spam koruması** (çok aktif kullanıcıları atla)

**Çalışma Mantığı:**
• Son 1 saatte aktif + En fazla 3 mesaj = Hedef
• 5 dakika aralıkla grup mesajı
• 24 saat kullanıcı cooldown
• Maksimum 3 kullanıcı hedefleme

**Kullanılabilir İşlemler:**
• Sistem açma/kapama
• Mesaj aralığı ayarlama
• Mesaj şablonları düzenleme
• İstatistik görüntüleme
• Test mesajı gönderme

Hangi işlemi yapmak istiyorsun?
        """
        
        await callback.message.edit_text(
            response,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Recruitment menu hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def show_balance_management_menu(callback: types.CallbackQuery) -> None:
    """Bakiye yönetimi menüsü"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Bakiye Ekle", callback_data="admin_balance_add"),
            InlineKeyboardButton(text="💸 Bakiye Çıkar", callback_data="admin_balance_remove")
        ],
        [
            InlineKeyboardButton(text="🎁 Sürpriz Bakiye", callback_data="admin_balance_surprise"),
            InlineKeyboardButton(text="📊 Bakiye Raporu", callback_data="admin_balance_report")
        ],
        [
            InlineKeyboardButton(text="🔄 Yenile", callback_data="admin_balance_management"),
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
💰 **Bakiye Yönetimi**

**Mevcut İşlemler:**
• Bakiye ekleme (reply veya etiket ile)
• Bakiye çıkarma (reply veya etiket ile)
• Sürpriz bakiye dağıtımı
• Bakiye raporları

**Komutlar:**
• `/bakiyee MIKTAR` (reply ile)
• `/bakiyec MIKTAR` (reply ile)
• `/bakiyeeid USER_ID MIKTAR`
• `/bakiyecid USER_ID MIKTAR`

**Özellikler:**
• Reply ile hızlı işlem
• Etiket ile kullanıcı seçimi
• Toplu bakiye dağıtımı
• Detaylı raporlar

Hangi işlemi yapmak istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def show_statistics_menu(callback: types.CallbackQuery) -> None:
    """İstatistikler menüsü"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Admin İstatistikleri", callback_data="admin_stats_admin"),
            InlineKeyboardButton(text="📈 Sistem İstatistikleri", callback_data="admin_stats_system")
        ],
        [
            InlineKeyboardButton(text="👥 Kullanıcı İstatistikleri", callback_data="admin_stats_users"),
            InlineKeyboardButton(text="🎯 Performans İstatistikleri", callback_data="admin_stats_performance")
        ],
        [
            InlineKeyboardButton(text="🎁 Bonus İstatistikleri", callback_data="bonus_stats")
        ],
        [
            InlineKeyboardButton(text="🔄 Yenile", callback_data="admin_statistics"),
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
📈 **İstatistikler Sistemi**

**Mevcut İstatistikler:**
• Admin istatistikleri (kullanıcı, point, mesaj)
• Sistem performans istatistikleri
• Kullanıcı aktivite istatistikleri
• Performans analizi
• 🎁 Bonus sistemi istatistikleri

**Özellikler:**
• Gerçek zamanlı veriler
• Detaylı analizler
• Grafik ve tablolar
• Export özellikleri
• Bonus dağıtım takibi

Hangi istatistiği görüntülemek istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def show_reports_menu(callback: types.CallbackQuery) -> None:
    """Raporlar menüsü"""
    logger.info(f"📊 Raporlar menüsü açıldı - User: {callback.from_user.id}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Kullanıcı", callback_data="admin_reports_users"),
            InlineKeyboardButton(text="💰 Point", callback_data="admin_reports_points")
        ],
        [
            InlineKeyboardButton(text="🎮 Etkinlik", callback_data="admin_reports_events"),
            InlineKeyboardButton(text="📈 Sistem", callback_data="admin_reports_system")
        ],
        [
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
📊 **Raporlar Sistemi**

Hangi raporu görüntülemek istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def show_games_menu(callback: types.CallbackQuery) -> None:
    """Topluluk oyunları menüsü"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎮 Yeni Oyun", callback_data="admin_games_new"),
            InlineKeyboardButton(text="📋 Aktif Oyunlar", callback_data="admin_games_active")
        ],
        [
            InlineKeyboardButton(text="🏆 Oyun Sonuçları", callback_data="admin_games_results"),
            InlineKeyboardButton(text="⚙️ Oyun Ayarları", callback_data="admin_games_settings")
        ],
        [
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
🎮 **Topluluk Oyunları**

**Oyun Yönetimi:**
• Yeni oyun oluşturma
• Aktif oyunları görüntüleme
• Oyun sonuçları
• Oyun ayarları

Hangi işlemi yapmak istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def show_command_creator_menu(callback: types.CallbackQuery) -> None:
    """Komut oluşturucu menüsü"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔧 Yeni Komut Oluştur", callback_data="admin_create_command"),
            InlineKeyboardButton(text="📝 Komutları Listele", callback_data="admin_list_commands")
        ],
        [
            InlineKeyboardButton(text="🗑️ Komut Sil", callback_data="admin_delete_command"),
            InlineKeyboardButton(text="📊 Komut İstatistikleri", callback_data="admin_command_stats")
        ],
        [
            InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
        ]
    ])
    
    response = """
🔧 **Komut Oluşturucu Sistemi**

**Kullanılabilir İşlemler:**
• Yeni custom komut oluştur (!site gibi)
• Mevcut komutları listele
• Komut silme
• Komut istatistikleri

**Örnek Kullanım:**
• `/komutolustur` - Yeni komut oluştur
• `/komutlar` - Tüm komutları listele
• `/komutsil !site` - Komut sil

Hangi işlemi yapmak istiyorsun?
    """
    
    await callback.message.edit_text(
        response,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def show_restart_menu(callback: types.CallbackQuery) -> None:
    """Bot restart menüsü"""
    try:
        user_id = callback.from_user.id
        config = get_config()
        
        # Admin kontrolü (Super Admin şart)
        try:
            from handlers.admin_permission_manager import has_min_rank_db
            has_perm = await has_min_rank_db(user_id, 4)
        except Exception:
            has_perm = (user_id == config.ADMIN_USER_ID)
        if not has_perm:
            await callback.answer("❌ Bu işlem için Super Admin yetkisi gerekli!", show_alert=True)
            return
        
        # Bakım modu durumunu al
        maintenance_status = "🔧 AKTİF" if config.MAINTENANCE_MODE else "✅ KAPALI"
        
        response = f"""
🔄 **BOT YÖNETİMİ**

**🔧 Bakım Modu:** {maintenance_status}

**⚠️ Dikkat:** Bot restart işlemi bot'u geçici olarak durduracak ve yeniden başlatacaktır.

**Hangi işlemi yapmak istiyorsun?**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Bot Restart", callback_data="admin_restart_bot"),
                InlineKeyboardButton(text=f"🔧 Bakım Modu", callback_data="admin_maintenance_toggle")
            ],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")]
        ])
        
        await callback.message.edit_text(
            response,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Restart menü hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def show_main_admin_menu(callback: types.CallbackQuery) -> None:
    """Ana admin menüsüne geri dön"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚙️ Ayarları Değiştir", callback_data="admin_settings"),
            InlineKeyboardButton(text="🎯 Etkinlik Sistemi", callback_data="admin_events_system")
        ],
        [
            InlineKeyboardButton(text="📢 Toplu Mesaj Gönder", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🛍️ Market Yönetimi", callback_data="admin_market_management")
        ],
        [
            InlineKeyboardButton(text="🔧 Komut Oluşturucu", callback_data="admin_command_creator"),
            InlineKeyboardButton(text="📊 Raporlar", callback_data="admin_reports")
        ],
        [
            InlineKeyboardButton(text="🔄 Botu Yeniden Başlat", callback_data="admin_restart_bot")
        ]
    ])
    
    response = f"""
KirveHub Media
/adminpanel
✅ Yönetici Paneli

Hoş geldiniz, KirveHub!

Hangi işlemi yapmak istiyorsun? {datetime.now().strftime('%H:%M')}
    """
    
    await callback.message.edit_text(
        response,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ==============================================
# SITE YÖNETİM SİSTEMİ
# ==============================================

async def show_site_management_menu(callback: types.CallbackQuery) -> None:
    """Site yönetimi menüsü"""
    try:
        user_id = callback.from_user.id
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Site Ekle", callback_data="site_mgmt_add"),
                InlineKeyboardButton(text="📋 Site Listesi", callback_data="site_mgmt_list")
            ],
            [
                InlineKeyboardButton(text="✏️ Site Düzenle", callback_data="site_mgmt_edit"),
                InlineKeyboardButton(text="🗑️ Site Sil", callback_data="site_mgmt_delete")
            ],
            [
                InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_back")
            ]
        ])
        
        response = """
🌐 **Site Yönetimi**

**Mevcut İşlemler:**
• Site ekleme
• Site listeleme
• Site düzenleme
• Site silme

**Özellikler:**
• Dinamik site yönetimi
• Öncelik sıralaması
• Aktif/Pasif durumu
• Detaylı site bilgileri

Hangi işlemi yapmak istiyorsun?
        """
        
        await callback.message.edit_text(
            response,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Site management menu hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def start_site_creation(callback: types.CallbackQuery) -> None:
    """Site ekleme sürecini başlat"""
    try:
        user_id = callback.from_user.id
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
            return
        
        # Site ekleme state'ini başlat
        site_creation_data[user_id] = {
            "step": "name",
            "data": {}
        }
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data="site_mgmt_cancel_creation")]
        ])
        
        await callback.message.edit_text(
            "🌐 **Site Ekleme - Adım 1/4**\n\n"
            "**Site Adını Yazın:**\n\n"
            "**Örnekler:**\n"
            "• `Mersobahis`\n"
            "• `Betboo`\n"
            "• `1xBet`\n\n"
            "**Lütfen site adını yazın:**",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Site creation başlatma hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def handle_site_creation_input(message: types.Message) -> None:
    """Site ekleme input handler'ı"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            return
        
        # Site ekleme sürecinde mi?
        if user_id not in site_creation_data:
            return
        
        site_info = site_creation_data[user_id]
        step = site_info.get("step")
        
        if step == "name":
            site_info["data"]["name"] = message.text.strip()
            site_info["step"] = "url"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ İptal", callback_data="site_mgmt_cancel_creation")]
            ])
            
            await message.reply(
                "🌐 **Site Ekleme - Adım 2/4**\n\n"
                "**Site URL'sini Yazın:**\n\n"
                "**Örnekler:**\n"
                "• `https://t2m.io/merso`\n"
                "• `https://example.com`\n\n"
                "**Lütfen site URL'sini yazın:**",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
        elif step == "url":
            url = message.text.strip()
            if not url.startswith(('http://', 'https://')):
                await message.reply("❌ Geçersiz URL! URL `http://` veya `https://` ile başlamalı.")
                return
            
            site_info["data"]["url"] = url
            site_info["step"] = "description"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Atla", callback_data="site_mgmt_skip_description")],
                [InlineKeyboardButton(text="❌ İptal", callback_data="site_mgmt_cancel_creation")]
            ])
            
            await message.reply(
                "🌐 **Site Ekleme - Adım 3/4**\n\n"
                "**Site Açıklamasını Yazın (Opsiyonel):**\n\n"
                "**Örnek:**\n"
                "`Güvenilir ve hızlı bahis sitesi`\n\n"
                "**Lütfen açıklamayı yazın veya atlayın:**",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
        elif step == "description":
            site_info["data"]["description"] = message.text.strip()
            site_info["step"] = "icon"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Atla (🌐)", callback_data="site_mgmt_skip_icon")],
                [InlineKeyboardButton(text="❌ İptal", callback_data="site_mgmt_cancel_creation")]
            ])
            
            await message.reply(
                "🌐 **Site Ekleme - Adım 4/4**\n\n"
                "**Site İkonunu Yazın (Emoji - Opsiyonel):**\n\n"
                "**Örnekler:**\n"
                "• `🎰`\n"
                "• `🏆`\n"
                "• `🎲`\n\n"
                "**Lütfen emoji yazın veya atlayın:**",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
        elif step == "icon":
            site_info["data"]["icon"] = message.text.strip()[:2] if message.text else "🌐"
            site_info["step"] = "confirm"
            
            # Onay mesajı göster
            data = site_info["data"]
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Onayla", callback_data="site_mgmt_confirm_creation")],
                [InlineKeyboardButton(text="❌ İptal", callback_data="site_mgmt_cancel_creation")]
            ])
            
            await message.reply(
                f"✅ **Site Bilgileri Onayı**\n\n"
                f"**📋 Site Detayları:**\n"
                f"• **Ad:** {data.get('name', 'Bilinmiyor')}\n"
                f"• **URL:** {data.get('url', 'Bilinmiyor')}\n"
                f"• **Açıklama:** {data.get('description', 'Yok')}\n"
                f"• **İkon:** {data.get('icon', '🌐')}\n\n"
                f"**💡 Siteyi oluşturmak için onaylayın.**",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        
    except Exception as e:
        logger.error(f"❌ Site creation input hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")


async def confirm_site_creation(callback: types.CallbackQuery) -> None:
    """Site ekleme işlemini onayla"""
    try:
        user_id = callback.from_user.id
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
            return
        
        if user_id not in site_creation_data:
            await callback.answer("❌ Site ekleme sürecinde bulunamadı!", show_alert=True)
            return
        
        data = site_creation_data[user_id]["data"]
        
        # Site ekle
        from handlers.site_manager import add_site
        success = await add_site(
            name=data.get("name"),
            url=data.get("url"),
            description=data.get("description", ""),
            icon=data.get("icon", "🌐"),
            priority=0
        )
        
        if success:
            await callback.message.edit_text(
                f"✅ **Site başarıyla eklendi!**\n\n"
                f"{data.get('icon', '🌐')} **{data.get('name')}**\n"
                f"🔗 {data.get('url')}\n"
                f"📝 {data.get('description', 'Açıklama yok')}",
                parse_mode="Markdown"
            )
            del site_creation_data[user_id]
        else:
            await callback.answer("❌ Site eklenemedi!", show_alert=True)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Site creation confirm hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def cancel_site_creation(callback: types.CallbackQuery) -> None:
    """Site ekleme işlemini iptal et"""
    try:
        user_id = callback.from_user.id
        
        if user_id in site_creation_data:
            del site_creation_data[user_id]
        
        await callback.message.edit_text("❌ Site ekleme işlemi iptal edildi.")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Site creation cancel hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def skip_site_creation_step(callback: types.CallbackQuery, step: str) -> None:
    """Site ekleme adımını atla"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in site_creation_data:
            await callback.answer("❌ Site ekleme sürecinde bulunamadı!", show_alert=True)
            return
        
        site_info = site_creation_data[user_id]
        
        if step == "description":
            site_info["data"]["description"] = ""
            site_info["step"] = "icon"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Atla (🌐)", callback_data="site_mgmt_skip_icon")],
                [InlineKeyboardButton(text="❌ İptal", callback_data="site_mgmt_cancel_creation")]
            ])
            
            await callback.message.edit_text(
                "🌐 **Site Ekleme - Adım 4/4**\n\n"
                "**Site İkonunu Yazın (Emoji - Opsiyonel):**\n\n"
                "**Örnekler:**\n"
                "• `🎰`\n"
                "• `🏆`\n"
                "• `🎲`\n\n"
                "**Lütfen emoji yazın veya atlayın:**",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
        elif step == "icon":
            site_info["data"]["icon"] = "🌐"
            site_info["step"] = "confirm"
            
            # Onay mesajı göster
            data = site_info["data"]
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Onayla", callback_data="site_mgmt_confirm_creation")],
                [InlineKeyboardButton(text="❌ İptal", callback_data="site_mgmt_cancel_creation")]
            ])
            
            await callback.message.edit_text(
                f"✅ **Site Bilgileri Onayı**\n\n"
                f"**📋 Site Detayları:**\n"
                f"• **Ad:** {data.get('name', 'Bilinmiyor')}\n"
                f"• **URL:** {data.get('url', 'Bilinmiyor')}\n"
                f"• **Açıklama:** {data.get('description', 'Yok')}\n"
                f"• **İkon:** {data.get('icon', '🌐')}\n\n"
                f"**💡 Siteyi oluşturmak için onaylayın.**",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Site creation skip hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def list_all_sites_admin(callback: types.CallbackQuery) -> None:
    """Tüm siteleri listele (admin)"""
    try:
        user_id = callback.from_user.id
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
            return
        
        from handlers.site_manager import get_all_sites
        sites = await get_all_sites()
        
        if not sites:
            await callback.message.edit_text("❌ Hiç site bulunamadı!")
            await callback.answer()
            return
        
        response = "🌐 **TÜM SİTELER (ADMIN)**\n"
        response += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        for site in sites:
            icon = site.get('icon', '🌐')
            name = site['name']
            url = site['url']
            description = site.get('description', '')
            priority = site.get('priority', 0)
            is_active = site.get('is_active', False)
            site_id = site['id']
            
            status = "✅ Aktif" if is_active else "❌ Pasif"
            
            response += f"{icon} **{name}** (ID: {site_id})\n"
            response += f"   └─ {status}\n"
            response += f"   └─ {url}\n"
            if description:
                response += f"   └─ {description}\n"
            response += f"   └─ Öncelik: {priority}\n\n"
        
        response += "━━━━━━━━━━━━━━━━━━━\n"
        response += f"📊 **Toplam:** {len(sites)} site"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_site_management")]
        ])
        
        await callback.message.edit_text(
            response,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Site list hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def show_site_edit_menu(callback: types.CallbackQuery) -> None:
    """Site düzenleme menüsü"""
    try:
        user_id = callback.from_user.id
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
            return
        
        from handlers.site_manager import get_all_sites
        sites = await get_all_sites()
        
        if not sites:
            await callback.message.edit_text("❌ Hiç site bulunamadı!")
            await callback.answer()
            return
        
        keyboard = []
        for site in sites[:10]:  # İlk 10 site
            site_id = site['id']
            icon = site.get('icon', '🌐')
            name = site['name']
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{icon} {name} (ID: {site_id})",
                    callback_data=f"site_mgmt_edit_field_{site_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_site_management")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "✏️ **Site Düzenleme**\n\n"
            "Düzenlemek istediğiniz siteyi seçin:",
            parse_mode="Markdown",
            reply_markup=markup
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Site edit menu hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def show_site_delete_menu(callback: types.CallbackQuery) -> None:
    """Site silme menüsü"""
    try:
        user_id = callback.from_user.id
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
            return
        
        from handlers.site_manager import get_all_sites
        sites = await get_all_sites()
        
        if not sites:
            await callback.message.edit_text("❌ Hiç site bulunamadı!")
            await callback.answer()
            return
        
        keyboard = []
        for site in sites[:10]:  # İlk 10 site
            site_id = site['id']
            icon = site.get('icon', '🌐')
            name = site['name']
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{icon} {name} (ID: {site_id})",
                    callback_data=f"site_mgmt_delete_{site_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="⬅️ Geri", callback_data="admin_site_management")])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            "🗑️ **Site Silme**\n\n"
            "⚠️ **Dikkat:** Site silme işlemi geri alınamaz!\n\n"
            "Silmek istediğiniz siteyi seçin:",
            parse_mode="Markdown",
            reply_markup=markup
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Site delete menu hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def handle_site_edit_input(message: types.Message) -> None:
    """Site düzenleme input handler'ı"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            return
        
        if user_id not in site_edit_data:
            return
        
        edit_info = site_edit_data[user_id]
        site_id = edit_info.get("site_id")
        field = edit_info.get("field")
        
        if not site_id or not field:
            return
        
        # Site güncelle
        from handlers.site_manager import update_site
        value = message.text.strip()
        
        # Değer tipi dönüşümü
        if field == "priority":
            value = int(value)
        elif field == "is_active":
            value = value.lower() in ['true', '1', 'yes', 'evet', 'aktif']
        
        success = await update_site(site_id, **{field: value})
        
        if success:
            await message.reply(f"✅ Site güncellendi! **{field}** = `{value}`", parse_mode="Markdown")
            del site_edit_data[user_id]
        else:
            await message.reply("❌ Site güncellenemedi!")
        
    except ValueError:
        await message.reply("❌ Geçersiz değer! Priority sayı olmalı.")
    except Exception as e:
        logger.error(f"❌ Site edit input hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")


async def handle_site_delete_input(message: types.Message) -> None:
    """Site silme input handler'ı (kullanılmıyor - callback ile çalışıyor)"""
    pass


async def start_site_field_edit(callback: types.CallbackQuery, field: str) -> None:
    """Site alanı düzenleme başlat"""
    try:
        user_id = callback.from_user.id
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
            return
        
        # Site ID'yi al
        site_id = int(field)
        
        # Düzenlenecek alanı seç
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Ad", callback_data=f"site_mgmt_edit_field_name_{site_id}"),
                InlineKeyboardButton(text="🔗 URL", callback_data=f"site_mgmt_edit_field_url_{site_id}")
            ],
            [
                InlineKeyboardButton(text="📄 Açıklama", callback_data=f"site_mgmt_edit_field_description_{site_id}"),
                InlineKeyboardButton(text="🎨 İkon", callback_data=f"site_mgmt_edit_field_icon_{site_id}")
            ],
            [
                InlineKeyboardButton(text="📊 Öncelik", callback_data=f"site_mgmt_edit_field_priority_{site_id}"),
                InlineKeyboardButton(text="✅ Aktiflik", callback_data=f"site_mgmt_edit_field_is_active_{site_id}")
            ],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="site_mgmt_edit")]
        ])
        
        from handlers.site_manager import get_site_by_id
        site = await get_site_by_id(site_id)
        
        if not site:
            await callback.answer("❌ Site bulunamadı!", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"✏️ **Site Düzenleme**\n\n"
            f"**Site:** {site.get('icon', '🌐')} {site['name']}\n\n"
            f"Düzenlemek istediğiniz alanı seçin:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Site field edit hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def cancel_site_edit(callback: types.CallbackQuery) -> None:
    """Site düzenleme işlemini iptal et"""
    try:
        user_id = callback.from_user.id
        
        if user_id in site_edit_data:
            del site_edit_data[user_id]
        
        await callback.message.edit_text("❌ Site düzenleme işlemi iptal edildi.")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Site edit cancel hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def confirm_site_edit(callback: types.CallbackQuery) -> None:
    """Site düzenleme işlemini onayla (kullanılmıyor - direkt güncelleme yapılıyor)"""
    pass


async def cancel_site_delete(callback: types.CallbackQuery) -> None:
    """Site silme işlemini iptal et"""
    try:
        user_id = callback.from_user.id
        
        if user_id in site_delete_data:
            del site_delete_data[user_id]
        
        await callback.message.edit_text("❌ Site silme işlemi iptal edildi.")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Site delete cancel hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


# ==============================================
# EKSİK KOMUTLAR - STUB FONKSİYONLAR
# ==============================================

async def clean_messages_command(message: types.Message) -> None:
    """Mesaj temizleme komutu - Stub"""
    try:
        user_id = message.from_user.id
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        await message.reply("⚠️ Mesaj temizleme özelliği henüz aktif değil.")
        logger.info(f"⚠️ clean_messages_command çağrıldı - User: {user_id}")
    except Exception as e:
        logger.error(f"❌ clean_messages_command hatası: {e}")

async def list_groups_command(message: types.Message) -> None:
    """Grup listesi komutu - Stub"""
    try:
        user_id = message.from_user.id
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        # Grup listesini göster
        from handlers.group_handler import group_info_command
        await group_info_command(message)
        logger.info(f"✅ list_groups_command çağrıldı - User: {user_id}")
    except Exception as e:
        logger.error(f"❌ list_groups_command hatası: {e}")

async def help_command(message: types.Message) -> None:
    """Yardım komutu - Stub"""
    try:
        from handlers.register_handler import yardim_command
        await yardim_command(message)
        logger.info(f"✅ help_command çağrıldı - User: {message.from_user.id}")
    except Exception as e:
        logger.error(f"❌ help_command hatası: {e}")

async def delete_group_command(message: types.Message) -> None:
    """Grup silme komutu - Stub"""
    try:
        user_id = message.from_user.id
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        await message.reply("⚠️ Grup silme özelliği henüz aktif değil.\n\nGrup ID'sini göndererek silme işlemi yapabilirsiniz.")
        logger.info(f"⚠️ delete_group_command çağrıldı - User: {user_id}")
    except Exception as e:
        logger.error(f"❌ delete_group_command hatası: {e}")

async def confirm_site_delete(callback: types.CallbackQuery) -> None:
    """Site silme işlemini onayla"""
    try:
        user_id = callback.from_user.id
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlem için admin yetkisi gerekli!", show_alert=True)
            return
        
        # Callback data'dan site ID'yi al
        if not callback.data or not callback.data.startswith("site_mgmt_delete_"):
            await callback.answer("❌ Geçersiz işlem!", show_alert=True)
            return
        
        site_id = int(callback.data.replace("site_mgmt_delete_", ""))
        
        # Site sil
        from handlers.site_manager import delete_site, get_site_by_id
        site = await get_site_by_id(site_id)
        
        if not site:
            await callback.answer("❌ Site bulunamadı!", show_alert=True)
            return
        
        success = await delete_site(site_id)
        
        if success:
            await callback.message.edit_text(
                f"✅ **Site silindi (deaktive edildi)!**\n\n"
                f"**ID:** {site_id}\n"
                f"{site.get('icon', '🌐')} **{site['name']}**\n\n"
                f"💡 Site veritabanında kaldı ama artık gözükmüyor.",
                parse_mode="Markdown"
            )
        else:
            await callback.answer("❌ Site silinemedi!", show_alert=True)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Site delete confirm hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


# ==============================================
# MARKET ÜRÜN EKLEME SİSTEMİ
# ==============================================

# ⚠️ DEPRECATED: Bu ürün ekleme sistemi artık kullanılmıyor!
# Admin panel artık handlers/admin_market_management.py sistemini kullanıyor
# main.py içindeki kontrol kaldırıldı, bu kod artık asla çağrılmıyor
# Bu kod güvenlik nedeniyle korunuyor ama aktif değil

# Global market product data storage (KULLANILMIYOR - sadece kod hatası önlemek için tutuldu)
product_data_storage = {}

async def start_product_creation(callback: types.CallbackQuery) -> None:
    """Market ürün ekleme sürecini başlat (DEPRECATED - KULLANILMIYOR)"""
    try:
        user_id = callback.from_user.id
        
        # Ürün verilerini temizle
        product_data_storage[user_id] = {
            "step": "website_name",
            "data": {}
        }
        
        logger.info(f"🛍️ Ürün ekleme Adım 1 başlatıldı - User: {user_id}")
        logger.info(f"📦 Product data storage: {product_data_storage}")
        
        response = """
🛍️ **Market Ürün Ekleme - Adım 1/7**

**🌐 Site Adını Yazın:**

**Örnekler:**
• `Betboo`
• `Betsafe`
• `1xBet`
• `Parimatch`

**Lütfen sitenin adını yazın:**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data="admin_market")]
        ])
        
        await callback.message.edit_text(
            response,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        logger.info(f"✅ Adım 1 mesajı gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Product creation başlatma hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def handle_product_step_input(message: types.Message) -> None:
    """Market ürün ekleme adım girişlerini handle et"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        from config import get_config
        config = get_config()
        if user_id != config.ADMIN_USER_ID:
            return
        
        # Ürün ekleme sürecinde mi?
        if user_id not in product_data_storage:
            logger.debug(f"❌ Ürün ekleme sürecinde değil - User: {user_id}")
            return
        
        process_data = product_data_storage[user_id]
        current_step = process_data["step"]
        
        logger.info(f"🔍 Ürün ekleme mesajı alındı - User: {user_id}, Text: {message.text}")
        logger.info(f"📝 Ürün ekleme sürecinde - Step: {current_step}")
        
        # Adım işleme
        if current_step == "website_name":
            await handle_website_name_input(message, process_data)
        elif current_step == "website_link":
            await handle_website_link_input(message, process_data)
        elif current_step == "product_name":
            await handle_product_name_input(message, process_data)
        elif current_step == "category":
            await handle_category_input(message, process_data)
        elif current_step == "stock":
            await handle_stock_input(message, process_data)
        elif current_step == "price":
            await handle_price_input(message, process_data)
        else:
            logger.warning(f"⚠️ Bilinmeyen adım: {current_step} - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Product step input hatası: {e}")
