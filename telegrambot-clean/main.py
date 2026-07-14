"""
Modern Telegram Bot - aiogram + Database
Moduler yapida, Python 3.13 uyumlu
"""

# TEST SATIRI - Ubuntu'da bu satiri ara: TEST_UBUNTU_2024
import asyncio
import logging
import os
import psutil
import time
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram import types

# Local imports
from config import get_config, validate_config
from database import init_database, close_database
from handlers import (
    start_command, kirvekayit_command,
    register_callback_handler, kayitsil_command, kirvegrup_command, 
    group_info_command, botlog_command, monitor_group_message, start_cleanup_task,
    menu_command, profile_callback_handler, yardim_command, komutlar_command,
    siparislerim_command, siralama_command, profil_command
)
# private_message_handler kullanılmıyor - simple_message_handler kullanılıyor (satır 1454)
# Recruitment system - start_recruitment_background kullanılıyor (satır 1514)
from handlers.recruitment_system import (
    start_recruitment_background, handle_recruitment_response
)
# Chat system - message_monitor.py içinde kullanılıyor (lazy import)
# handle_chat_message, send_chat_response - message_monitor içinde lazy import
# bot_write_command, chat_callback_handler - main.py'de lazy import (satır 539, 540, 1208)
# handle_chat_message_new (chat_message_handler) - message_monitor içinde lazy import
from handlers.chat_message_handler import set_bot_instance as set_chat_message_bot_instance
from handlers.admin_panel import router as admin_panel_router
# clean_messages_command, list_groups_command, help_command, delete_group_command
# lazy import kullanılıyor (satır 723, 728, 733, 738, 1830)
from handlers.simple_events import router as simple_events_router, set_bot_instance as set_events_bot_instance
from handlers.unknown_commands import router as unknown_commands_router, set_bot_instance as set_unknown_bot_instance
from handlers.event_participation import router as event_participation_router, set_bot_instance as set_participation_bot_instance
from handlers.events_list import router as events_list_router, set_bot_instance as set_events_list_bot_instance
from handlers.system_notifications import send_maintenance_notification, send_startup_notification
from handlers.scheduled_messages import (
    set_bot_instance as set_scheduled_bot, 
    start_scheduled_messages,
    router as scheduled_messages_router
)
from handlers.punishment_system import router as punishment_router, set_bot_instance as set_punishment_bot
from handlers.maintenance_system import router as maintenance_router, set_bot_instance as set_maintenance_bot
from handlers.mod_handler import router as mod_handler_router, set_bot_instance as set_mod_bot, mod_activity_monitor_task
from handlers.mod_warning_system import router as mod_warning_router, set_bot_instance as set_mod_warning_bot
from handlers.detailed_logging_system import (
    log_system_startup, log_system_shutdown, log_error, 
    log_system_health_check, log_missing_data, log_deprecated_feature,
    log_conflict_resolution, log_invalid_input, log_overflow_protection,
    log_deadlock_detection, log_data_corruption, set_bot_instance as set_logging_bot_instance,
    router as detailed_logging_router
)
from handlers.admin_top10 import router as admin_top10_router, set_bot_instance as set_top10_bot_instance
from handlers.admin_kplog import router as admin_kplog_router
from handlers.activity_reward_system import router as activity_reward_router
from handlers.boss_greeting_system import router as boss_greeting_router
from handlers.market_callbacks import router as market_callbacks_router
from handlers.admin_market_fix import router as admin_market_fix_router
from handlers.admin_category_manager import router as admin_category_manager_router
from handlers.admin_category_fixer import router as admin_category_fixer_router
from handlers.site_manager import router as site_manager_router, set_bot_instance as set_site_manager_bot_instance
from handlers.statistics_system import router as statistics_router
from handlers.broadcast_system import router as broadcast_router
from handlers.admin_permission_manager import router as admin_permission_router
from handlers.admin_commands import router as admin_commands_router
from handlers.event_management import router as event_management_router
from handlers.dynamic_command_creator import router as dynamic_command_router
from handlers.special_events_notifier import router as special_events_router
from handlers.special_events_manager import router as special_events_manager_router, set_bot_instance as set_special_events_manager_bot
from handlers.new_user_handler import router as new_user_handler_router, set_bot_instance as set_new_user_handler_bot
from handlers.log_station_manager import router as log_station_manager_router
from handlers.secret_commands import router as secret_commands_router
from handlers.get_id import router as get_id_router
# Balance management - Komutlar kullanılıyor (satır 580-583)
from handlers.balance_management import (
    add_balance_command, remove_balance_command,
    add_balance_id_command, remove_balance_id_command
)
from handlers.admin_order_management import (
    router as admin_order_router,
    show_orders_list_modern,
    handle_admin_order_message,
    admin_order_states
)
from handlers.admin_market_management import (
    router as admin_market_router,
    market_management_command,
    handle_product_creation_input,
    start_product_creation,
    confirm_product_creation,
    cancel_product_creation
)
from handlers.admin_commands import delete_command_command
from handlers.simple_events import create_lottery_command as create_event_command
from handlers.dynamic_command_creator import handle_custom_command
from handlers.event_management import (
    set_forced_winners_command,
    list_forced_winners_command,
    remove_forced_winner_command,
    end_lottery_command as end_event_command
)
from handlers.events_list import (
    list_active_lotteries as list_active_events,
    refresh_lotteries_list_callback
)
# Admin panel imports - lazy import kullanılacak (büyük dosya nedeniyle)
# Fonksiyonlar kullanıldığı yerde import edilecek - FINAL
admin_panel_command = None
clean_messages_command = None
list_groups_command = None
help_command = None
approve_order_command = None
test_market_system_command = None
test_sql_queries_command = None
test_user_orders_command = None
update_bot_command = None
delete_group_command = None
fix_scheduled_messages_command = None
from handlers.broadcast_system import (
    start_broadcast_callback, cancel_broadcast_callback,
    broadcast_stats_callback, broadcast_back_callback,
    broadcast_close_callback
)
# Bot instance setters (grouped)
from handlers.start_handler import set_bot_instance as set_start_bot_instance
from handlers.admin_panel import set_bot_instance as set_admin_panel_bot_instance
from handlers.statistics_system import set_bot_instance as set_statistics_bot_instance
from handlers.event_management import set_bot_instance as set_event_management_bot_instance
from handlers.dynamic_command_creator import set_bot_instance as set_dynamic_command_bot_instance
from handlers.broadcast_system import set_bot_instance as set_broadcast_bot_instance
from handlers.balance_management import set_bot_instance as set_balance_bot_instance
from handlers.admin_permission_manager import set_bot_instance as set_admin_permission_bot_instance
from handlers.admin_market_management import set_bot_instance as set_admin_market_bot_instance
from handlers.admin_commands import set_bot_instance as set_admin_commands_bot_instance
from handlers.market_callbacks import set_bot_instance as set_market_callbacks_bot_instance
from handlers.market_system import set_bot_instance as set_market_system_bot_instance
from handlers.group_handler import set_bot_instance as set_group_handler_bot_instance
from handlers.profile_handler import set_bot_instance as set_profile_bot_instance
from handlers.interactive_features import set_bot_instance as set_interactive_features_bot_instance

from utils import setup_logger
from utils.logger import log_system, log_bot, log_error, log_info, log_warning
from utils.universal_logger import get_universal_logger, log_everything, log_command_attempt
from utils.rate_limiter import rate_limiter, rate_limit
from utils.memory_manager import memory_manager, start_memory_cleanup, cleanup_all_resources

# TOP10 için gerekli import'lar
from datetime import datetime

# Logger'ı kur
logger = setup_logger()

# Bot instance çakışmasını önlemek için global değişken
_bot_instance = None
_bot_lock_file = "bot_running.lock"

def check_bot_running():
    """Bot'un çalışıp çalışmadığını kontrol et"""
    try:
        # Lock file kontrolü
        if os.path.exists(_bot_lock_file):
            # Lock file'ın yaşını kontrol et (5 dakikadan eskiyse sil)
            file_age = time.time() - os.path.getmtime(_bot_lock_file)
            if file_age > 300:  # 5 dakika
                os.remove(_bot_lock_file)
                return False
            return True
        
        # Process kontrolü
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'main.py' in ' '.join(proc.info['cmdline'] or []):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except Exception as e:
        logger.error(f"❌ Bot running check hatası: {e}")
        return False

def create_bot_lock():
    """Bot lock file oluştur"""
    try:
        with open(_bot_lock_file, 'w') as f:
            f.write(str(time.time()))
        logger.info("✅ Bot lock oluşturuldu")
    except Exception as e:
        logger.error(f"❌ Bot lock oluşturma hatası: {e}")

def remove_bot_lock():
    """Bot lock file'ı sil"""
    try:
        if os.path.exists(_bot_lock_file):
            os.remove(_bot_lock_file)
            logger.info("✅ Bot lock silindi")
    except Exception as e:
        logger.error(f"❌ Bot lock silme hatası: {e}")

async def cleanup_resources():
    """Bot kapatılırken kaynakları temizle"""
    try:
        # Database bağlantısını kapat
        try:
            await close_database()
            logger.info("✅ Database bağlantısı kapatıldı")
        except Exception as e:
            logger.error(f"❌ Database kapatma hatası: {e}")
        
        remove_bot_lock()
        
        # Bot session'ını kapat
        global _bot_instance
        if _bot_instance:
            try:
                await _bot_instance.session.close()
            except Exception as cleanup_error:
                logger.debug(f"Bot session cleanup hatası (kritik değil): {cleanup_error}")
            _bot_instance = None
            
        logger.info("🧹 Bot kaynakları temizlendi")
    except Exception as e:
        logger.error(f"❌ Bot cleanup hatası: {e}")

# ==============================================
# TOP10 KOMUTU - DİREKT FONKSİYON
# ==============================================

async def handle_top10_command_direct(message) -> None:
    """Top 10 KP ve mesaj listesi komutu - Direkt handler"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        
        # Config ve admin kontrolü
        config = get_config()
        from config import is_admin
        if not is_admin(user_id):
            logger.warning(f"❌ Top10 komutu - Admin değil: {user_id} (@{username})")
            await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
            return
        
        logger.info(f"🏆 Top10 komutu çağrıldı - Admin: {user_id} (@{username})")
        
        # Grup seçim menüsü göster
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Kayıtlı grupları al
        from database import get_db_pool
        pool = await get_db_pool()
        if not pool:
            await message.reply("❌ Database bağlantısı hatası!")
            return
            
        async with pool.acquire() as conn:
            groups = await conn.fetch("""
                WITH recent_groups AS (
                    SELECT ds.group_id,
                           COALESCE(rg.group_name, 'Grup ' || ds.group_id::text) AS group_name,
                           SUM(ds.message_count) AS msg
                    FROM daily_stats ds
                    JOIN registered_groups rg ON rg.group_id = ds.group_id
                    WHERE rg.is_active = TRUE
                      AND ds.message_date >= (CURRENT_DATE - INTERVAL '7 days')
                    GROUP BY ds.group_id, rg.group_name
                )
                SELECT group_id, group_name
                FROM recent_groups
                ORDER BY (group_id = -1002231486317) DESC, msg DESC, group_name ASC
                LIMIT 20
            """)
        
        if not groups:
            await message.reply("❌ Kayıtlı grup bulunamadı!")
            return
            
        # Grup seçim keyboard'u oluştur
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        for group in groups:
            group_id = group['group_id']
            group_name = group['group_name'] or f"Grup {str(group_id)[-4:]}"
            # Telegram'dan canlı başlık almayı dene
            display_name = group_name
            try:
                chat = await message.bot.get_chat(group_id)
                if getattr(chat, 'title', None):
                    display_name = chat.title
            except Exception:
                pass
            
            button = InlineKeyboardButton(
                text=f"📊 {display_name}",
                callback_data=f"top10_send_{group_id}"
            )
            keyboard.inline_keyboard.append([button])
        
        # İptal butonu ekle
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="❌ İptal", callback_data="top10_cancel")
        ])
        
        await message.reply(
            "🏆 <b>TOP 10 LİSTESİNİ HANGİ GRUBA GÖNDEREYİM?</b>\n\n"
            "📊 Aşağıdan grup seçin:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"❌ Top10 komutu hatası: {e}")
        await message.reply("❌ Top10 listesi yüklenirken hata oluştu!")


async def handle_top10_send_to_group(callback, target_chat_id) -> None:
    """Top 10 listesini seçilen gruba gönder"""
    try:
        user_id = callback.from_user.id
        username = callback.from_user.username or "Unknown"
        
        logger.info(f"🏆 Top10 grup gönderimi - Admin: {user_id}, Target: {target_chat_id}")

        # Hedef chat gerçekten kayıtlı ve aktif mi?
        from database import is_group_registered
        if not await is_group_registered(target_chat_id):
            await callback.answer("❌ Geçersiz/aktif olmayan grup!", show_alert=True)
            return
        
        # Database'den verileri al
        from database import get_db_pool
        pool = await get_db_pool()
        if not pool:
            await callback.answer("❌ Database bağlantısı hatası!")
            return
            
        async with pool.acquire() as conn:
            # Top 10 KP kullanıcıları
            top_kp = await conn.fetch("""
                SELECT u.username, u.first_name, u.kirve_points, u.user_id
                FROM users u
                WHERE u.kirve_points > 0
                ORDER BY u.kirve_points DESC
                LIMIT 10
            """)
            
            # Top 10 mesaj kullanıcıları (users tablosundan)
            top_messages = await conn.fetch("""
                SELECT u.username, u.first_name, u.total_messages, u.user_id
                FROM users u
                WHERE u.total_messages > 0
                ORDER BY u.total_messages DESC
                LIMIT 10
            """)
        
        # Mesajı formatla
        current_time = datetime.now().strftime('%d.%m.%Y %H:%M')
        
        response = f"""
🏆 <b>TOP 10 LİDERLİK TABLOSU</b>

💎 <b>TOP 10 KIRVE POINT:</b>
"""
        
        if top_kp:
            medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            for i, user in enumerate(top_kp):
                username = user['username'] or user['first_name'] or f"User{user['user_id']}"
                kp = user['kirve_points']
                medal = medals[i] if i < len(medals) else "🏅"
                
                response += f"{medal} <b>{i+1}.</b> @{username} - <b>{kp:.1f} KP</b>\n"
        else:
            response += "❌ KP verisi bulunamadı\n"
        
        response += "\n💬 <b>TOP 10 MESAJ:</b>\n"
        
        if top_messages:
            medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            for i, user in enumerate(top_messages):
                username = user['username'] or user['first_name'] or f"User{user['user_id']}"
                messages = user['total_messages']
                medal = medals[i] if i < len(medals) else "🏅"
                
                response += f"{medal} <b>{i+1}.</b> @{username} - <b>{messages} mesaj</b>\n"
        else:
            response += "❌ Mesaj verisi bulunamadı\n"
        
        response += f"""

📅 <b>Güncellenme:</b> {current_time}
🤖 <b>KirveHub Bot</b> - Top 10 Sistemi
"""
        
        # Gruba mesajı gönder (callback üzerinden mevcut bot'u kullan)
        try:
            await callback.message.bot.send_message(
                chat_id=target_chat_id,
                text=response,
                parse_mode="HTML"
            )
            
            # Callback'i güncelle
            await callback.message.edit_text(
                "✅ <b>TOP 10 LİSTESİ BAŞARIYLA GÖNDERİLDİ!</b>\n\n"
                f"📊 Grup ID: <code>{target_chat_id}</code>\n"
                f"⏰ Gönderim: {current_time}",
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Top10 listesi gruba gönderildi - Target: {target_chat_id}")
            
        except Exception as send_error:
            logger.error(f"❌ Top10 grup gönderim hatası: {send_error}")
            await callback.message.edit_text(
                "❌ <b>GRUP GÖNDERİM HATASI!</b>\n\n"
                f"🔍 Hata: {str(send_error)}\n"
                "❓ Bot bu grupta admin mi?",
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"❌ Top10 grup gönderim hatası: {e}")
        await callback.answer("❌ Top10 listesi gönderilirken hata oluştu!")

async def main():
    """Ana bot fonksiyonu"""
    try:
        logger.info("🔍 Bot başlatma süreci başlatılıyor...")
        
        # Bot lock kontrolü
        logger.info("🔒 Bot lock kontrolü yapılıyor...")
        if check_bot_running():
            logger.warning("❌ Bot zaten çalışıyor! Mevcut instance durduruluyor...")
            log_system("Bot zaten çalışıyor! Mevcut instance durduruluyor...")
            # Eski instance'ı temizle
            await cleanup_resources()
            # Kısa bekleme
            await asyncio.sleep(3)
        
        logger.info("✅ Bot lock kontrolü geçildi")
        
        # Lock file oluştur
        logger.info("📝 Lock file oluşturuluyor...")
        create_bot_lock()
        logger.info("✅ Lock file oluşturuldu")
        
        logger.info("🚀 Bot başlatılıyor...")
        log_system("Bot başlatılıyor...")
        
        # Konfigürasyon kontrolü
        logger.info("⚙️ Konfigürasyon kontrol ediliyor...")
        config = get_config()
        logger.info("✅ Konfigürasyon yüklendi")
        log_system("Konfigürasyon doğrulandı")
        
        # Database bağlantısı
        logger.info("🗄️ Database bağlantısı kuruluyor...")
        log_system("Database bağlantısı kuruluyor...")
        logger.info("⏳ Database başlatılıyor (bu işlem birkaç dakika sürebilir)...")
        db_success = await init_database()
        if not db_success:
            logger.warning("⚠️ Database bağlantısı başarısız!")
            log_warning("⚠️ Database olmadan devam ediliyor!", None, None, None, None)
        else:
            logger.info("✅ Database bağlantısı başarılı!")
            log_system("✅ Database bağlantısı başarılı!")
        
        # Bot instance oluştur
        logger.info("🤖 Bot instance oluşturuluyor...")
        log_system("Bot instance oluşturuluyor...")
        
        # Eski bot session'ını temizle
        try:
            if '_bot_instance' in globals() and _bot_instance:
                await _bot_instance.session.close()
        except Exception as cleanup_error:
            logger.debug(f"Eski bot session cleanup hatası (kritik değil): {cleanup_error}")
            
        bot = Bot(token=config.BOT_TOKEN)
        logger.info("✅ Bot instance oluşturuldu")
        _bot_instance = bot  # Global instance'ı set et
        
        # Bot instance'ını TÜM handler'lara aktar (gruplu)
        logger.info("🔗 Bot instance handler'lara aktarılıyor...")
        log_system("Bot instance handler'lara aktarılıyor...")
        
        # Core handlers
        set_start_bot_instance(bot)  # Start handler bot instance
        set_events_bot_instance(bot)
        set_unknown_bot_instance(bot)
        set_participation_bot_instance(bot)
        set_events_list_bot_instance(bot)
        set_scheduled_bot(bot)
        set_punishment_bot(bot)
        set_maintenance_bot(bot)
        set_logging_bot_instance(bot)
        
        # Admin handlers
        set_admin_panel_bot_instance(bot)
        set_statistics_bot_instance(bot)
        set_event_management_bot_instance(bot)
        set_dynamic_command_bot_instance(bot)
        set_broadcast_bot_instance(bot)
        set_balance_bot_instance(bot)
        set_admin_permission_bot_instance(bot)
        set_admin_market_bot_instance(bot)
        set_admin_commands_bot_instance(bot)
        set_top10_bot_instance(bot)
        set_market_callbacks_bot_instance(bot)
        set_market_system_bot_instance(bot)
        set_group_handler_bot_instance(bot)
        set_profile_bot_instance(bot)
        set_interactive_features_bot_instance(bot)
        set_special_events_manager_bot(bot)  # Special events manager bot instance
        set_new_user_handler_bot(bot)  # New user handler bot instance
        set_chat_message_bot_instance(bot)
        set_site_manager_bot_instance(bot)
        set_mod_bot(bot)  # Mod sistemi bot instance (duplicate import kaldırıldı)
        set_mod_warning_bot(bot)  # Mod uyarı sistemi bot instance
        
        # Register handler bot instance (!kayitol komutu için) - Lazy import
        try:
            from handlers.register_handler import set_bot_instance as set_register_bot
            set_register_bot(bot)
        except Exception as e:
            logger.warning(f"⚠️ Register handler bot instance ayarlanamadı: {e}")
        
        log_system("✅ Bot instance tüm handler'lara aktarıldı!")
        logger.info("🔧 SYSTEM: ✅ Bot instance tüm handler'lara aktarıldı!")
        
        dp = Dispatcher()
        
        # Handler'ları kaydet
        log_system("Handler'lar kaydediliyor...")
        
        # 1. CALLBACK HANDLER'LARI (inline button'lar) - ÖNCE callback'leri kaydet
        dp.callback_query(F.data == "register_user")(register_callback_handler)
        dp.callback_query(F.data == "get_info")(register_callback_handler)
        
        # Chat callback'leri - lazy import
        async def handle_show_commands(callback: types.CallbackQuery):
            from handlers.chat_system import chat_callback_handler
            await chat_callback_handler(callback)
        async def handle_close_message(callback: types.CallbackQuery):
            from handlers.chat_system import chat_callback_handler
            await chat_callback_handler(callback)
        dp.callback_query(F.data == "show_commands")(handle_show_commands)
        dp.callback_query(F.data == "close_message")(handle_close_message)
        
        # Etkinlik listesi callback'i
        dp.callback_query(F.data == "refresh_lotteries_list")(refresh_lotteries_list_callback)
        
        log_system("Callback handler'lar kaydedildi")
        
        # Profil callback'leri - Basit filter
        dp.callback_query(lambda c: c.data and c.data.startswith("profile_"))(profile_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("buy_product_"))(profile_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("confirm_buy_"))(profile_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("view_product_"))(profile_callback_handler)
        dp.callback_query(F.data == "product_sold_out")(profile_callback_handler)
        dp.callback_query(F.data == "my_orders")(profile_callback_handler)
        dp.callback_query(F.data == "profile_orders")(profile_callback_handler)
        dp.callback_query(F.data == "insufficient_balance")(profile_callback_handler)
        dp.callback_query(F.data == "out_of_stock")(profile_callback_handler)
        dp.callback_query(F.data == "profile_back")(profile_callback_handler)
        dp.callback_query(F.data == "profile_refresh")(profile_callback_handler)
        
        # Ranking callback'leri - Ayrı kayıt
        dp.callback_query(F.data == "ranking_top_kp")(profile_callback_handler)
        dp.callback_query(F.data == "ranking_top_messages")(profile_callback_handler)
        
        # Admin sipariş yönetimi router'ı (import başta yapıldı)
        dp.include_router(admin_order_router)
        
        # Broadcast system callback'leri admin_panel_callback'te yönetiliyor
        # Bu callback'ler router üzerinden otomatik olarak işleniyor
        
        # Admin sipariş callback'leri - admin_panel.py içinde handle ediliyor
        
        # Admin commands list callback'leri kaldırıldı
        # admin_commands_back router tarafından yönetiliyor
        
        # Çekiliş callback'leri - Router'da tanımlı olduğu için kaldırıldı
        
        # Debug handler'ı kaldırıldı - callback çakışmasına neden oluyordu
        
        # Bakiye komutları - MANUEL KAYIT (import başta yapıldı)
        dp.message(Command("bakiyee"))(add_balance_command)
        dp.message(Command("bakiyec"))(remove_balance_command)
        dp.message(Command("bakiyeeid"))(add_balance_id_command)
        dp.message(Command("bakiyecid"))(remove_balance_id_command)
        
        # 1. GRUP SESSİZLİK SİSTEMİ - EN ÖNCE KAYIT ET!
        # Grup chatindeki tüm komutları yakala ve özelde çalıştır (cezalandırma komutları hariç)
        # Cezalandırma komutları: /uyarı, /warn, /uyarısıfırla, /resetwarn, /uyarılar, /warnings, /uyarıaşama, /warnstage, /mute, /sustur, /ban, /yasakla, /unmute, /unban
        dp.message(
            F.chat.type.in_(["group", "supergroup"]), 
            F.text.startswith("/"),
            ~F.text.startswith("/uyarı"),
            ~F.text.startswith("/warn"),
            ~F.text.startswith("/uyarısıfırla"),
            ~F.text.startswith("/resetwarn"),
            ~F.text.startswith("/uyarılar"),
            ~F.text.startswith("/warnings"),
            ~F.text.startswith("/uyarıaşama"),
            ~F.text.startswith("/warnstage"),
            ~F.text.startswith("/mute"),
            ~F.text.startswith("/sustur"),
            ~F.text.startswith("/unmute"),
            ~F.text.startswith("/susturma"),
            ~F.text.startswith("/ban"),
            ~F.text.startswith("/yasakla"),
            ~F.text.startswith("/unban"),
            ~F.text.startswith("/yasakkaldır"),
            ~F.text.startswith("/yasakla")
        )(handle_group_command_silently)
        
        # 2. KOMUT HANDLER'LARI
        dp.message(CommandStart())(start_command)
        
        # 💎 MESAJ MONITOR - Point sistemi ve mesaj kayıt (ÖNCE) - TAM YETKİ: AKTİF
        # Sadece point sistemi için, dinamik komutları engellemeyecek
        dp.message(F.chat.type.in_(["group", "supergroup"]), ~F.text.startswith("/"), ~F.text.startswith("!"))(monitor_group_message)
        
        # 💬 CHAT SİSTEMİ - message_monitor.py içinde entegre edilmiş
        # handle_chat_message ve handle_chat_message_new message_monitor içinde lazy import ile çağrılıyor
        # Doğrudan handler kaydı yok - çakışma önlendi
        dp.message(Command("kirvekayit"))(kirvekayit_command)
        dp.message(Command("kayitsil"))(kayitsil_command)
        
        # !kayitol komutu - Grupta otomatik kayıt
        from handlers.register_handler import kayitol_command, set_bot_instance as set_register_bot
        dp.message(F.text.startswith("!kayitol"))(kayitol_command)
        dp.message(F.text.startswith("!kayıtol"))(kayitol_command)  # Türkçe karakter desteği
        # Grup komutları handle_group_command_silently'de işleniyor
        dp.message(Command("kirvegrup"))(kirvegrup_command)
        dp.message(Command("botlog"))(botlog_command)
        dp.message(Command("grupbilgi"))(group_info_command)
        dp.message(Command("menu"))(menu_command)
        dp.message(Command("menü"))(menu_command)  # Türkçe karakter desteği
        dp.message(Command("komutlar"))(komutlar_command)
        dp.message(Command("siparislerim"))(siparislerim_command)
        dp.message(Command("siralama"))(siralama_command)
        dp.message(Command("profil"))(profil_command)
        
        # Admin komutları artık router'larda
        
        # Etkinlik komutları kaldırıldı
        
        # Admin komutları - Router'da tanımlı olduğu için kaldırıldı
        
        # Market komutuna log ekle
        async def market_command_with_log(message: types.Message):
            # Detaylı log
            from handlers.detailed_logging_system import log_command_execution
            await log_command_execution(
                user_id=message.from_user.id,
                username=message.from_user.username or message.from_user.first_name,
                command="market",
                chat_id=message.chat.id,
                chat_type=message.chat.type
            )
            await market_management_command(message)
        
        dp.message(Command("market"))(market_command_with_log)
        
        # Market callback handler (import başta yapıldı)
        dp.include_router(admin_market_router)
        
        # Admin commands list ve reports router'ları kaldırıldı
        
        # 🔥 CRİTİK: MANUEL HANDLER KAYIT - GRUP SESSİZLİĞİ İÇİN (ROUTER'LAR YOK!)

        # 🌐 !siteler KOMUTU - EN ÜSTE MANUEL HANDLER (TÜM HANDLER'LARDAN ÖNCE!)
        # Bu handler TÜM handler'lardan ÖNCE çalışır, !siteler komutunu kesinlikle yakalar
        # ÖNEMLİ: handle_custom_command'dan ÖNCE kaydedilmeli!
        from handlers.site_manager import site_command
        async def handle_site_command_manual(message: types.Message):
            """!siteler komutu için manuel handler - EN ÜSTE"""
            logger.info(f"🔍 !siteler handler çağrıldı - User: {message.from_user.id}, Text: '{message.text}'")
            
            if not message.text:
                logger.debug("⚠️ Mesaj metni yok, handler'dan çıkılıyor")
                return
            
            text_lower = message.text.strip().lower()
            logger.info(f"🔍 !siteler handler - Text lower: '{text_lower}'")
            
            # Tam olarak !siteler veya !siteler ile başlayan komutlar
            if text_lower == '!siteler' or text_lower.startswith('!siteler '):
                logger.info(f"✅ !siteler komutu MANUEL HANDLER'da yakalandı! - User: {message.from_user.id}, Text: '{message.text}'")
                try:
                    await site_command(message)
                    logger.info(f"✅ !siteler komutu başarıyla çalıştırıldı - User: {message.from_user.id}")
                except Exception as e:
                    logger.error(f"❌ !siteler komutu hatası: {e}", exc_info=True)
            else:
                logger.debug(f"⚠️ !siteler handler - Komut eşleşmedi: '{text_lower}'")
        
        # Handler'ı kaydet - text filter ile (TÜM HANDLER'LARDAN ÖNCE!)
        # ÖNEMLİ: handle_custom_command'dan ÖNCE kaydedilmeli!
        dp.message(F.text.startswith("!siteler"))(handle_site_command_manual)
        logger.info("✅ !siteler komutu manuel handler olarak kaydedildi (TÜM HANDLER'LARDAN ÖNCE!)")
        
        # 📢 !tanitim KOMUTU - Bot tanıtım mesajı (v2)
        async def handle_tanitim_command_manual(message: types.Message):
            """!tanitim komutu için manuel handler"""
            try:
                if not message.text:
                    return
                
                text_lower = message.text.strip().lower()
                if text_lower != '!tanitim' and not text_lower.startswith('!tanitim '):
                    return
                
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                
                # Bot username'ini al (deep link için)
                bot_info = await bot.get_me()
                bot_username = bot_info.username
                bot_deep_link = f"https://t.me/{bot_username}?start=register" if bot_username else None
                
                # Bot tanıtım mesajı
                tanitim_text = """
👋 **Merhaba Kirvelerim!**

Ben **Kirve Rebekka Bot**! KirveHub topluluğunun bir parçasıyım.

📝 **Nasıl Kayıt Olunur?**
Özelden `/start` yazarak kayıt olabilirsiniz!

💎 **Kirve Point Sistemi**
• Her mesajınız **Kirve Point (KP)** kazandırır
• Kazandığınız KP'lerle **Market**'ten ürün alabilirsiniz
• Freespinler, bakiyeler ve daha fazlası!

🎮 **Hemen Başlayın:**
Aşağıdaki butona tıklayarak kayıt olun ve KP kazanmaya başlayın!
                """
                
                # Butonlar: Kayıt Ol ve Market
                keyboard_buttons = []
                
                # Kayıt Ol butonu (bot deep link)
                if bot_deep_link:
                    keyboard_buttons.append([
                        InlineKeyboardButton(
                            text="🎯 Kayıt Ol",
                            url=bot_deep_link
                        )
                    ])
                else:
                    # Eğer bot username yoksa, alternatif olarak start komutu göster
                    keyboard_buttons.append([
                        InlineKeyboardButton(
                            text="🎯 Kayıt Ol - /start yazın",
                            url=f"https://t.me/{bot_username}" if bot_username else None
                        )
                    ])
                
                # Market linki butonu
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text="🛍️ Market'e Git - kirve1.com/market",
                        url="https://kirve1.com/market"
                    )
                ])
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                
                # Grupta göster
                await message.answer(
                    tanitim_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                logger.info(f"✅ !tanitim komutu başarıyla çalıştırıldı - User: {message.from_user.id}")
                
            except Exception as e:
                logger.error(f"❌ !tanitim komutu hatası: {e}", exc_info=True)
        
        dp.message(F.text.startswith("!tanitim"))(handle_tanitim_command_manual)
        logger.info("✅ !tanitim komutu manuel handler olarak kaydedildi")

        # Dinamik "!" komutları için mesaj handler kaydı
        # NOT: !site, !siteler ve !market özel komutlar, bunlar filtre dışında!
        try:
            # !site, !siteler, !market, !tanitim'i filtre dışında bırak - Lambda ile kontrol
            async def should_handle_dynamic_command(message: types.Message) -> bool:
                """!site, !siteler, !market, !tanitim ve mod komutlarını filtre dışında bırak"""
                if not message.text or not message.text.startswith('!'):
                    return False
                command = message.text.strip().split()[0].lower()
                # !site, !siteler, !market, !tanitim, !mod, !modlar, !modekle, !modsil özel komutlar, bunları atla
                if command in ['!site', '!siteler', '!market', '!tanitim', '!mod', '!modlar', '!modekle', '!modsil']:
                    return False
                return True
            
            dp.message(should_handle_dynamic_command)(handle_custom_command)
        except Exception as e:
            logger.error(f"❌ Dinamik komut handler kaydı başarısız: {e}")
        
        # MANUEL HANDLER KAYITLARI - TEK ADMİN PANELİ
        # Lazy import ile admin panel komutları
        async def handle_admin_panel(message: Message):
            from handlers.admin_panel import admin_panel_command as cmd
            await cmd(message)
        dp.message(Command("adminpanel"))(handle_admin_panel)
        
        async def handle_update_bot(message: Message):
            from handlers.admin_panel import update_bot_command as cmd
            await cmd(message)
        dp.message(Command("updatebot"))(handle_update_bot)
        
        async def handle_admin_komutlar(message: Message):
            from handlers.admin_panel import admin_panel_command as cmd
            await cmd(message)
        dp.message(Command("adminkomutlar"))(handle_admin_komutlar)
        
        # Mesaj silme komutu - lazy import
        async def handle_clean_messages(message: Message):
            from handlers.admin_panel import clean_messages_command as cmd
            await cmd(message)
        dp.message(Command("temizle"))(handle_clean_messages)
        
        async def handle_list_groups(message: Message):
            from handlers.admin_panel import list_groups_command as cmd
            await cmd(message)
        dp.message(Command("gruplar"))(handle_list_groups)
        
        async def handle_delete_group(message: Message):
            from handlers.admin_panel import delete_group_command as cmd
            await cmd(message)
        dp.message(Command("grupsil"))(handle_delete_group)
        
        async def handle_help(message: Message):
            from handlers.admin_panel import help_command as cmd
            await cmd(message)
        dp.message(Command("yardim"))(handle_help)
        
        dp.message(Command("siparisliste"))(show_orders_list_modern) # Sipariş listesi
        
        async def handle_approve_order(message: Message):
            from handlers.admin_panel import approve_order_command as cmd
            await cmd(message)
        dp.message(Command("siparisonayla"))(handle_approve_order)
        
        # Test komutları - lazy import
        async def handle_test_market(message: Message):
            from handlers.admin_panel import test_market_system_command as cmd
            await cmd(message)
        dp.message(Command("testmarket"))(handle_test_market)
        
        async def handle_test_sql(message: Message):
            from handlers.admin_panel import test_sql_queries_command as cmd
            await cmd(message)
        dp.message(Command("testsql"))(handle_test_sql)
        
        async def handle_test_siparis(message: Message):
            from handlers.admin_panel import test_user_orders_command as cmd
            await cmd(message)
        dp.message(Command("testsiparis"))(handle_test_siparis)
        
        async def handle_fix_scheduled(message: Message):
            from handlers.admin_panel import fix_scheduled_messages_command as cmd
            await cmd(message)
        dp.message(Command("fixscheduled"))(handle_fix_scheduled)
        
        # Görsel ve seviye sistemi test komutları (manuel handler)
        from handlers.test_commands import (
            test_avatar_command,
            test_level_command,
            test_icon_command,
            test_notification_command,
            test_level_up_command,
            test_all_command,
            test_help_command
        )
        dp.message(Command("testavatar"))(test_avatar_command)
        dp.message(Command("testseviye"))(test_level_command)
        dp.message(Command("testikon"))(test_icon_command)
        dp.message(Command("testbildirim"))(test_notification_command)
        dp.message(Command("testseviyeatlama"))(test_level_up_command)
        dp.message(Command("testtum"))(test_all_command)
        dp.message(Command("testyardim"))(test_help_command)
        
        dp.message(Command("etkinlikler"))(list_active_events)
        dp.message(Command("etkinlikbitir"))(end_event_command)
        
        # Admin komutları - Manuel handler kayıtları (import başta yapıldı)
        dp.message(Command("komutsil"))(delete_command_command)
        
        # Etkinlik oluşturma komutu (import başta yapıldı)
        dp.message(Command("etkinlik"))(create_event_command)
        
        # 🔐 GİZLİ KOMUTLAR (import başta yapıldı)
        dp.include_router(secret_commands_router)
        dp.include_router(get_id_router)
        
        # 💬 Zamanlanmış mesajlar (import başta yapıldı)
        dp.include_router(scheduled_messages_router)
        
        # ⚖️ Cezalandırma Sistemi (uyarı, mute, ban)
        dp.include_router(punishment_router)
        
        # 🔧 Bakım Modu Sistemi (/bakim, /bakimbitis)
        dp.include_router(maintenance_router)
        
        # 🧪 Test komutları router'ı (erken kayıt - diğer router'lardan önce)
        try:
            from handlers.test_commands import router as test_commands_router
            dp.include_router(test_commands_router)
            logger.info("✅ test_commands_router eklendi - Test komutları aktif!")
        except Exception as e:
            logger.warning(f"⚠️ test_commands_router zaten ekli veya hata: {e}")
        
        # 🤖 AI Sohbet Sistemi (Intent recognition ve action execution)
        from handlers.ai_chat_system import router as ai_chat_router, set_bot_instance as set_ai_chat_bot
        set_ai_chat_bot(bot)
        dp.include_router(ai_chat_router)
        
        # 🛡️ Spam Koruması Sistemi (Otomatik mute/ban)
        from handlers.spam_protection import router as spam_protection_router, set_bot_instance as set_spam_bot
        set_spam_bot(bot)
        dp.include_router(spam_protection_router)
        
        # 🤖 Bot Tespit Sistemi (Gruptaki botları listele ve engelle)
        from handlers.bot_detection import router as bot_detection_router, set_bot_instance as set_bot_detection_bot, load_blocked_bots_from_db
        set_bot_detection_bot(bot)
        # Engellenmiş botları yükle
        await load_blocked_bots_from_db()
        dp.include_router(bot_detection_router)
        
        # 📢 BROADCAST ROUTER - EN ÖNCE (Mesaj handler'ı için)
        dp.include_router(broadcast_router) # Yayın sistemi router'ı
        dp.include_router(special_events_router)  # Özel etkinlik kanal bildirimi
        
        # SADECE GEREKLİ ROUTER'LAR - ÇAKIŞMA ÖNLENMİŞ
        dp.include_router(statistics_router)  # İstatistikler sistemi router'ı
        # Recruitment router kaldırıldı - new_user_handler kullanılıyor
        dp.include_router(admin_permission_router) # Admin izin yöneticisi router'ı
        dp.include_router(admin_commands_router) # Admin komutları router'ı
        
        log_system("Router'lar kayıtlandı!")
        
        # SADECE GEREKLİ ROUTER'LAR - ÇAKIŞMA ÖNLENMİŞ
        # Router'ları try-except ile ekle (yeniden başlatma durumunda çakışma olmasın)
        # Her router için ayrı try-except (bir router hata verse bile diğerleri eklenir)
        
        # 🌐 SİTE MANAGER EN ÜSTE - !site komutu için KRİTİK!
        # NOT: Router'daki !siteler handler'ı manuel handler tarafından override edilir
        try:
            dp.include_router(site_manager_router)
            logger.info("✅ site_manager_router eklendi - !site komutu aktif!")
        except Exception as e:
            logger.warning(f"⚠️ site_manager_router zaten ekli veya hata: {e}")
        
        # 🛡️ MOD HANDLER - !mod komutu için
        try:
            dp.include_router(mod_handler_router)
            logger.info("✅ mod_handler_router eklendi - !mod komutu aktif!")
        except Exception as e:
            logger.warning(f"⚠️ mod_handler_router zaten ekli veya hata: {e}")
        
        try:
            dp.include_router(event_participation_router)
        except Exception as e:
            logger.warning(f"⚠️ event_participation_router zaten ekli: {e}")
        
        # Event Management Router - Etkinlik yönetimi komutları için
        try:
            dp.include_router(event_management_router)
            logger.info("✅ event_management_router eklendi - Etkinlik yönetimi aktif!")
        except Exception as e:
            logger.warning(f"⚠️ event_management_router zaten ekli veya hata: {e}")
        
        try:
            dp.include_router(dynamic_command_router)
        except Exception as e:
            logger.warning(f"⚠️ dynamic_command_router zaten ekli: {e}")
        
        try:
            dp.include_router(admin_top10_router)
        except Exception as e:
            logger.warning(f"⚠️ admin_top10_router zaten ekli: {e}")
        
        try:
            dp.include_router(admin_kplog_router)
        except Exception as e:
            logger.warning(f"⚠️ admin_kplog_router zaten ekli: {e}")
        
        try:
            dp.include_router(activity_reward_router)
        except Exception as e:
            logger.warning(f"⚠️ activity_reward_router zaten ekli: {e}")
        
        try:
            dp.include_router(boss_greeting_router)
        except Exception as e:
            logger.warning(f"⚠️ boss_greeting_router zaten ekli: {e}")
        
        try:
            dp.include_router(market_callbacks_router)
        except Exception as e:
            logger.warning(f"⚠️ market_callbacks_router zaten ekli: {e}")
        
        try:
            dp.include_router(admin_market_fix_router)
        except Exception as e:
            logger.warning(f"⚠️ admin_market_fix_router zaten ekli: {e}")
        
        try:
            dp.include_router(admin_category_manager_router)
        except Exception as e:
            logger.warning(f"⚠️ admin_category_manager_router zaten ekli: {e}")
        
        try:
            dp.include_router(admin_category_fixer_router)
        except Exception as e:
            logger.warning(f"⚠️ admin_category_fixer_router zaten ekli: {e}")
        
        try:
            dp.include_router(simple_events_router)
        except Exception as e:
            logger.warning(f"⚠️ simple_events_router zaten ekli: {e}")
        
        try:
            dp.include_router(unknown_commands_router)
        except Exception as e:
            logger.warning(f"⚠️ unknown_commands_router zaten ekli: {e}")
        
        try:
            dp.include_router(events_list_router)
        except Exception as e:
            logger.warning(f"⚠️ events_list_router zaten ekli: {e}")
        
        try:
            dp.include_router(detailed_logging_router)
        except Exception as e:
            logger.warning(f"⚠️ detailed_logging_router zaten ekli: {e}")
        
        try:
            dp.include_router(admin_panel_router)
        except Exception as e:
            logger.warning(f"⚠️ admin_panel_router zaten ekli: {e}")
        
        # Special Events Manager Router - Özel etkinlikler yönetimi
        try:
            dp.include_router(special_events_manager_router)
            logger.info("✅ special_events_manager_router eklendi - Özel etkinlikler aktif!")
        except Exception as e:
            logger.warning(f"⚠️ special_events_manager_router zaten ekli veya hata: {e}")
        
        # New User Handler Router - Yeni kullanıcı katılımı
        try:
            dp.include_router(new_user_handler_router)
            logger.info("✅ new_user_handler_router eklendi - Yeni kullanıcı handler aktif!")
        except Exception as e:
            logger.warning(f"⚠️ new_user_handler_router zaten ekli veya hata: {e}")
        
        # Log Station Manager Router - Log yönetimi
        try:
            dp.include_router(log_station_manager_router)
            logger.info("✅ log_station_manager_router eklendi - Log istasyonu aktif!")
        except Exception as e:
            logger.warning(f"⚠️ log_station_manager_router zaten ekli veya hata: {e}")
        
        # NOT: !siteler komutu yukarıda (router'dan önce) kaydedildi - TEKRAR KAYIT YOK
        
        # 🛍️ !market KOMUTU - EN ÜSTE MANUEL HANDLER (router'dan önce!)
        # Bu handler router'lardan ÖNCE çalışır, !market komutunu kesinlikle yakalar
        async def handle_market_command_manual(message: types.Message):
            """!market komutu için manuel handler - Site yönlendirmesi"""
            if message.text and message.text.strip().lower() in ['!market', '!market ']:
                logger.info(f"🛍️ !market komutu MANUEL HANDLER'da yakalandı! - User: {message.from_user.id}")
                
                user_id = message.from_user.id
                
                # Grupta ise mesajı sil (Rate limiter ile)
                if message.chat.type in ["group", "supergroup"]:
                    from utils.safe_message_delete import safe_delete_message
                    await safe_delete_message(message, reason="!market command")
                
                # Site yönlendirmesi mesajı gönder
                try:
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    
                    market_text = "🛍️ **KIRVE MARKET**\n\n"
                    market_text += "Market sistemimiz web sitesinde!\n\n"
                    market_text += "🌐 **Web Market:**\n"
                    market_text += "https://kirve1.com/market\n\n"
                    market_text += "💡 Hesabınız otomatik olarak senkronize edilecektir."
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="🌐 Web Market'e Git",
                            url="https://kirve1.com/market"
                        )]
                    ])
                    
                    if message.chat.type == "private":
                        await message.reply(market_text, reply_markup=keyboard, parse_mode="Markdown")
                    else:
                        # Grupta ise özelden gönder
                        from aiogram import Bot
                        from config import get_config
                        config = get_config()
                        temp_bot = Bot(token=config.BOT_TOKEN)
                        try:
                            await temp_bot.send_message(
                                chat_id=user_id,
                                text=market_text,
                                reply_markup=keyboard,
                                parse_mode="Markdown"
                            )
                        finally:
                            await temp_bot.session.close()
                    
                    logger.info(f"✅ Market yönlendirmesi gönderildi - User: {user_id}")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    logger.error(f"❌ Market yönlendirmesi gönderme hatası: {e}", exc_info=True)
                    
                    # Kullanıcı botu başlatmamış
                    if "bot was blocked" in error_msg or "user is deactivated" in error_msg or "chat not found" in error_msg:
                        try:
                            await message.reply(
                                "⚠️ **Market'e ulaşmak için beni özel mesajdan başlatmalısın!**\n\n"
                                "👉 [@KirveLastBot](https://t.me/KirveLastBot) - /start\n\n"
                                "🌐 Veya direkt: https://kirve1.com/market",
                                parse_mode="Markdown"
                            )
                        except Exception as send_error:
                            logger.debug(f"Market mesajı gönderme hatası (kritik değil): {send_error}")
                    else:
                        try:
                            await message.reply(
                                "🌐 **Market:** https://kirve1.com/market",
                                parse_mode="Markdown"
                            )
                        except Exception as send_error:
                            logger.error(f"❌ Hata mesajı gönderilemedi: {send_error}")
        
        dp.message(F.text.startswith("!market"))(handle_market_command_manual)
        logger.info("✅ !market komutu manuel handler olarak kaydedildi (EN ÜSTE)")
        
        # 🛡️ !mod KOMUTU - EN ÜSTE MANUEL HANDLER (router'dan önce!)
        # Bu handler router'lardan ÖNCE çalışır, !mod ve !modlar komutlarını kesinlikle yakalar
        # NOT: !modekle ve !modsil router'da işlenir, bu handler sadece !mod ve !modlar için
        from handlers.mod_handler import list_moderators_command
        import re
        async def handle_mod_command_manual(message: types.Message):
            """!mod veya !modlar komutu için manuel handler - EN ÜSTE"""
            if message.text:
                text_lower = message.text.strip().lower()
                # Sadece !mod veya !modlar (listeleme komutu) - !modekle ve !modsil'i atla
                if text_lower in ['!mod', '!mod ', '!modlar', '!modlar '] or re.match(r'^!mod(lar)?\s*$', text_lower):
                    # !modekle veya !modsil değilse işle
                    if not text_lower.startswith('!modekle') and not text_lower.startswith('!modsil'):
                        logger.info(f"🛡️ !modlar komutu MANUEL HANDLER'da yakalandı! - User: {message.from_user.id}")
                        await list_moderators_command(message)
        
        # Sadece !mod ve !modlar için handler (ama !modekle ve !modsil'i atla)
        async def should_handle_mod_list(message: types.Message) -> bool:
            """Sadece !mod ve !modlar için True döner"""
            if not message.text or not message.text.startswith('!mod'):
                return False
            text_lower = message.text.strip().lower()
            # !modekle veya !modsil değilse True
            if text_lower.startswith('!modekle') or text_lower.startswith('!modsil'):
                return False
            # Sadece !mod veya !modlar
            return text_lower in ['!mod', '!mod ', '!modlar', '!modlar '] or re.match(r'^!mod(lar)?\s*$', text_lower)
        
        dp.message(should_handle_mod_list)(handle_mod_command_manual)
        logger.info("✅ !mod ve !modlar komutları manuel handler olarak kaydedildi (EN ÜSTE)")
        
        # 🛡️ !modekle KOMUTU - EN ÜSTE MANUEL HANDLER (router'dan önce!)
        # Bu handler router'lardan ÖNCE çalışır, !modekle komutunu kesinlikle yakalar
        from handlers.mod_handler import add_moderator_command
        async def handle_modekle_command_manual(message: types.Message):
            """!modekle komutu için manuel handler - EN ÜSTE"""
            if message.text and message.text.strip().lower().startswith('!modekle'):
                logger.info(f"🛡️ !modekle komutu MANUEL HANDLER'da yakalandı! - User: {message.from_user.id}, Text: {message.text}")
                await add_moderator_command(message)
        
        dp.message(F.text.startswith("!modekle"))(handle_modekle_command_manual)
        logger.info("✅ !modekle komutu manuel handler olarak kaydedildi (EN ÜSTE)")
        
        # 🛡️ !modsil KOMUTU - EN ÜSTE MANUEL HANDLER (router'dan önce!)
        # Bu handler router'lardan ÖNCE çalışır, !modsil komutunu kesinlikle yakalar
        from handlers.mod_handler import remove_moderator_command
        async def handle_modsil_command_manual(message: types.Message):
            """!modsil komutu için manuel handler - EN ÜSTE"""
            if message.text and message.text.strip().lower().startswith('!modsil'):
                logger.info(f"🛡️ !modsil komutu MANUEL HANDLER'da yakalandı! - User: {message.from_user.id}, Text: {message.text}")
                await remove_moderator_command(message)
        
        dp.message(F.text.startswith("!modsil"))(handle_modsil_command_manual)
        logger.info("✅ !modsil komutu manuel handler olarak kaydedildi (EN ÜSTE)")
        
        # Bot yazma komutu
        # Bot write command - lazy import
        async def handle_bot_write(message: Message):
            from handlers.chat_system import bot_write_command
            await bot_write_command(message)
        dp.message(Command("botyaz"))(handle_bot_write)
        
        # HİLELİ KAZANAN ATAMA KOMUTLARI - DİREKT EKLENDİ
        from handlers.event_management import (
            set_forced_winners_command, 
            list_forced_winners_command,
            remove_forced_winner_command
        )
        dp.message(Command("kazananayarla"))(set_forced_winners_command)
        dp.message(Command("kazananliste"))(list_forced_winners_command)
        dp.message(Command("kazanansil"))(remove_forced_winner_command)
        
        # 4. PRIVATE MESSAGE HANDLER - Market ürün ekleme + admin sipariş mesajları (EN SON!)
        # handle_product_step_input artık admin_market_management.py'de
        # handle_site_creation_input, handle_site_edit_input, handle_site_delete_input 
        # admin_panel.py'de lazy import ile kullanılıyor
        from handlers.admin_order_management import handle_admin_order_message
        from handlers.admin_market_management import handle_product_creation_input
        
        # Broadcast message handler handle_all_chat_inputs içinde işleniyor
        
        # BROADCAST CALLBACK HANDLER'LARI - MANUEL KAYIT
        from handlers.broadcast_system import start_broadcast_callback, cancel_broadcast_callback, broadcast_stats_callback, broadcast_back_callback, broadcast_close_callback
        dp.callback_query(lambda c: c.data == "admin_broadcast")(start_broadcast_callback)
        dp.callback_query(lambda c: c.data == "admin_broadcast_cancel")(cancel_broadcast_callback)
        dp.callback_query(lambda c: c.data == "broadcast_stats")(broadcast_stats_callback)
        dp.callback_query(lambda c: c.data == "broadcast_back")(broadcast_back_callback)
        dp.callback_query(lambda c: c.data == "broadcast_close")(broadcast_close_callback)
        
        # 🔧 CHAT-BASED SİSTEMLER - TEK HANDLER İLE YÖNETİM
        async def handle_all_chat_inputs(message: Message):
            """Tüm chat-based input sistemlerini tek handler'da yönet"""
            try:
                user_id = message.from_user.id
                
                # DEBUG: Input handler başlatıldı
                # logger.info(f"🔧 INPUT HANDLER BAŞLATILDI - User: {user_id}, Text: '{message.text}'")
                
                # Komut mesajlarını atla
                if message.text.startswith("/"):
                    log_system(f"⏭️ Komut mesajı atlandı - User: {user_id}")
                    return
                
                # 0. BROADCAST SİSTEMİ KONTROLÜ - GERİ EKLENDİ
                from handlers.broadcast_system import broadcast_states
                if user_id in broadcast_states and broadcast_states[user_id] == "waiting_for_message":
                    log_system(f"📢 BROADCAST STATE BULUNDU - User: {user_id}")
                    # Broadcast mesajını işle
                    from handlers.broadcast_system import process_broadcast_message_router
                    await process_broadcast_message_router(message)
                    return
                
                # 1. Komut oluşturma sistemi kontrolü
                from handlers.dynamic_command_creator import command_creation_states
                if user_id in command_creation_states:
                    from handlers.dynamic_command_creator import handle_command_creation_input
                    await handle_command_creation_input(message)
                    return
                
                # 2. Market ürün ekleme sistemi kontrolü
                from handlers.admin_market_management import product_creation_data
                if user_id in product_creation_data:
                    from handlers.admin_market_management import handle_product_creation_input
                    await handle_product_creation_input(message)
                    return
                
                # 2.5. Site bakiyeleri kullanıcı adı input kontrolü
                from handlers.market_callbacks import site_username_states
                if user_id in site_username_states:
                    # Kullanıcı adı input'unu işle
                    username_text = message.text.strip()
                    
                    # "-" veya boş ise atla
                    if username_text == "-" or not username_text:
                        site_username = None
                    else:
                        # Kullanıcı adını temizle (maksimum 255 karakter)
                        site_username = username_text[:255] if len(username_text) > 255 else username_text
                    
                    state_data = site_username_states[user_id]
                    product_id = state_data['product_id']
                    
                    # Sipariş oluştur
                    from handlers.market_system import confirm_buy_product_with_username
                    await confirm_buy_product_with_username(message, product_id, site_username=site_username)
                    
                    # State'i temizle
                    del site_username_states[user_id]
                    return
                
                # Site ekleme süreci kontrolü
                from handlers.admin_panel import site_creation_data
                if user_id in site_creation_data:
                    from handlers.admin_panel import handle_site_creation_input
                    await handle_site_creation_input(message)
                    return
                
                # Site düzenleme süreci kontrolü
                from handlers.admin_panel import site_edit_data
                if user_id in site_edit_data:
                    from handlers.admin_panel import handle_site_edit_input
                    await handle_site_edit_input(message)
                    return
                
                # Site silme süreci kontrolü
                from handlers.admin_panel import site_delete_data
                if user_id in site_delete_data:
                    from handlers.admin_panel import handle_site_delete_input
                    await handle_site_delete_input(message)
                    return
                
                # 2.1. Market ürün düzenleme sistemi kontrolü
                from handlers.admin_market_management import product_edit_data
                if user_id in product_edit_data:
                    log_system(f"🔍 MARKET EDIT HANDLER ÇAĞRILDI - User: {user_id}, Data: {product_edit_data[user_id]}")
                    from handlers.admin_market_management import handle_product_edit_input
                    await handle_product_edit_input(message)
                    return
                else:
                    log_system(f"🔍 MARKET EDIT DATA YOK - User: {user_id}, Keys: {list(product_edit_data.keys())}")
                
                # 2.2. Market ürün silme sistemi kontrolü
                from handlers.admin_market_management import product_delete_data
                if user_id in product_delete_data:
                    from handlers.admin_market_management import handle_product_delete_input
                    await handle_product_delete_input(message)
                    return
                
                # 3. Admin sipariş mesajları kontrolü
                from handlers.admin_order_management import admin_order_states
                if user_id in admin_order_states:
                    from handlers.admin_order_management import handle_admin_order_message
                    await handle_admin_order_message(message)
                    return
                
                # 4. Custom input kontrolü - Sistem ayarları için
                from utils.memory_manager import memory_manager
                cache_manager = memory_manager.get_cache_manager()
                input_state = cache_manager.get_cache(f"input_state_{user_id}")
                if input_state and input_state in ["custom_points", "custom_daily", "custom_weekly"]:
                    log_system(f"💰 CUSTOM INPUT BULUNDU - User: {user_id}, State: {input_state}")
                    from handlers.admin_panel import handle_custom_input
                    await handle_custom_input(message)
                    return
                
                # 6. Recruitment response kontrolü - sadece recruitment callback'lerinde çalışır
                # Burada çağrılmaz, sadece callback'lerde çalışır
                
                # 7. Çekiliş input kontrolü - çekiliş oluşturma sürecinde
                lottery_data = memory_manager.get_lottery_data(user_id)
                # logger.info(f"🎯 ÇEKİLİŞ KONTROL - User: {user_id}, lottery_data: {lottery_data}")
                if lottery_data:
                    log_system(f"🎯 ÇEKİLİŞ INPUT BULUNDU - User: {user_id}, Data: {lottery_data}")
                    from handlers.simple_events import handle_lottery_input
                    await handle_lottery_input(message)
                    return
                else:
                    # logger.info(f"🎯 ÇEKİLİŞ DATA YOK - User: {user_id}")
                    pass
                
                # 8. Scheduled Messages input kontrolü
                input_state = memory_manager.get_input_state(user_id)
                if input_state and (input_state.startswith("create_bot_") or input_state.startswith("recreate_bot_") or input_state.startswith("add_link_")):
                    log_system(f"🔍 SCHEDULED INPUT BULUNDU - User: {user_id}, State: {input_state}")
                    from handlers.scheduled_messages import handle_scheduled_input
                    await handle_scheduled_input(message)
                    return
                
                # 9. Dinamik komut çalıştırma kontrolü - en son
                # NOT: !site, !siteler, !market, !tanitim, !mod, !modlar, !modekle, !modsil özel komutlar, bunları atla!
                if message.text and message.text.startswith('!'):
                    command_name = message.text.strip().split()[0].lower()
                    if command_name not in ['!site', '!siteler', '!market', '!tanitim', '!mod', '!modlar', '!modekle', '!modsil']:
                        from handlers.dynamic_command_creator import handle_custom_command
                        await handle_custom_command(message)
                
                # 10. Özelden menü gösterme sistemi - Kayıtlı kullanıcılar için
                if message.chat.type == "private":
                    from database import is_user_registered, add_message_to_user, get_user_points_cached
                    is_registered = await is_user_registered(user_id)
                    
                    if is_registered:
                        # Özelden yeni point sistemi - Her 10 mesajda 0.02 point
                        current_balance = await get_user_points_cached(user_id)
                        total_messages = current_balance.get('total_messages', 0) if current_balance else 0
                        
                        # Yeni mesaj sayısı
                        new_total_messages = total_messages + 1
                        
                        # Her 10 mesajda bir point kazanılır
                        if new_total_messages % 10 == 0:
                            old_balance = current_balance.get('kirve_points', 0.0) if current_balance else 0.0
                            
                            # Point ekle (özel chat için group_id = 0)
                            await add_message_to_user(user_id, 0)
                            
                            # Yeni bakiyeyi hesapla
                            new_balance = old_balance + 0.02
                            
                            log_system(f"💎 Özelden point eklendi - User: {user_id}, Points: +0.02, New Balance: {new_balance:.2f}, Mesaj: {new_total_messages}")
                        else:
                            log_system(f"📝 Özelden mesaj sayısı artırıldı - User: {user_id}, Mesaj: {new_total_messages}/10")
                        
                        # Özelden menü cooldown kontrolü
                        import time
                        current_time = time.time()
                        # ÖNEMLİ: Özel mesajlarda cooldown yok - Her zaman menü göster
                        # Kullanıcı özelden yazdığında hemen menü gösterilmeli
                        
                        # Kayıtlı kullanıcı - Menü göster
                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🎮 Ana Menü", callback_data="menu_command")]
                        ])
                        
                        response_text = f"""
**Merhaba {message.from_user.first_name}!** 👋

**KirveHub**'ta aktifsin! Hemen menu'ye git ve özellikleri keşfet:

**Ne yapabilirsin:**
• 💎 **Point kazan** - Her mesajın point kazandırır
• 🛍️ **Market alışverişi** - Point'lerini freespinler, bakiyeler için kullan
• 🎯 **Etkinliklere katıl** - Point'lerinle çekilişlere, bonus hunt'lara katıl
• 📊 **Profilini gör** - İstatistiklerin ve sıralaman
• 🏆 **Yarış** - En aktif üyeler arasında yer al

**Hemen başla:**
💎 **Point kazanmaya devam et!**
🛍️ **Market'ten alışveriş yap!**
🎯 **Etkinliklere katıl!**


_🎯 Market'te point'lerini freespinler için kullanabilirsin!_
_🏆 Etkinliklerde point'lerinle özel ödüller kazanabilirsin!_
                        """
                        
                        await message.reply(
                            response_text,
                            parse_mode="Markdown",
                            reply_markup=keyboard
                        )
                        
                        log_system(f"💬 Özelden menü gösterildi - User: {user_id}")
                
            except Exception as e:
                log_error(f"❌ Chat input handler hatası: {e}")

        # BASİT HANDLER - TÜM ÖZEL MESAJLAR İÇİN - TAM YETKİ: EN ÜSTTE
        @dp.message(F.chat.type == "private")
        async def simple_message_handler(message: Message):
            """Basit mesaj handler - Sadece özel mesajlar için"""
            try:
                user_id = message.from_user.id
                username = message.from_user.username or "Unknown"
                
                # TAM YETKİ: KESİN LOG - Bu satır görünüyorsa handler çalışıyor
                logger.debug(f"🔍 HANDLER ÇALIŞIYOR - User: {user_id}, Text: {message.text}")
                log_system(f"📨 Özel mesaj alındı - User: {user_id} (@{username})")
                
                # TAM YETKİ: Debug: Mesaj detayları
                log_system(f"🔍 MESAJ DETAYLARI - Text: '{message.text}', Chat Type: {message.chat.type}, User ID: {user_id}")
                
                # TAM YETKİ: Özel mesaj yakalandı
                log_system(f"✅ TAM YETKİ: ÖZEL MESAJ YAKALANDI - User: {user_id}, Text: '{message.text}'")
                
                # Debug: Komut oluşturma sürecinde mi kontrol et
                from handlers.dynamic_command_creator import command_creation_states
                if user_id in command_creation_states:
                    log_system(f"🔧 KOMUT OLUŞTURMA SÜRECİNDE - User: {user_id}, Step: {command_creation_states[user_id].get('step', 'unknown')}")
                else:
                    log_system(f"🔧 KOMUT OLUŞTURMA SÜRECİNDE DEĞİL - User: {user_id}")
                
                # Komut değilse handle_all_chat_inputs'u çağır
                if not message.text.startswith("/"):
                    # TAM YETKİ: Komut oluşturma sürecinde olan kullanıcılar için dinamik komut kontrolünü atla
                    if user_id in command_creation_states:
                        log_system(f"🔧 KOMUT OLUŞTURMA SÜRECİNDE - Dinamik komut kontrolü atlanıyor - User: {user_id}")
                        # Komut oluşturma sürecinde olan kullanıcılar için direkt handle_all_chat_inputs'a git
                        await handle_all_chat_inputs(message)
                        return
                    
                    # Dinamik komut kontrolü - ! ile başlayan komutlar için (sadece komut oluşturma sürecinde olmayan kullanıcılar)
                    # NOT: !site, !siteler, !market, !tanitim, !mod, !modlar, !modekle, !modsil özel komutlar, bunları atla!
                    if message.text and message.text.startswith('!'):
                        command_name = message.text.strip().split()[0].lower()
                        if command_name not in ['!site', '!siteler', '!market', '!tanitim', '!mod', '!modlar', '!modekle', '!modsil']:
                            log_system(f"🔍 Özelde dinamik komut tespit edildi - Text: {message.text}")
                            from handlers.dynamic_command_creator import handle_custom_command
                            await handle_custom_command(message)
                            return
                    
                    # Tüm özel mesaj kontrolleri handle_all_chat_inputs'da yapılıyor
                    await handle_all_chat_inputs(message)
                    log_system(f"✅ Özel mesaj işlendi - User: {user_id}")
                else:
                    # Komut logu
                    command = message.text.split()[0] if message.text else "Unknown"
                    log_system(f"⚡ Komut alındı: {command} - User: {user_id} (@{username})")
                    
                    # Komutları doğrudan işle
                    if command == "/testsql":
                        from handlers.admin_panel import test_sql_queries_command
                        await test_sql_queries_command(message)
                    elif command == "/start":
                        from handlers.start_handler import start_command
                        await start_command(message)
                    elif command == "/menu":
                        from handlers.profile_handler import menu_command
                        await menu_command(message)
                    elif command == "/cekilisler":
                        from handlers.event_participation import list_active_events
                        await list_active_events(message)
                    elif command == "/cekilisyap":
                        from handlers.simple_events import create_lottery_command
                        await create_lottery_command(message)
                    elif command == "/top10":
                        # TOP10 KOMUTU - DİREKT BURADA İŞLE!
                        logger.info(f"🔥 TOP10 KOMUTU YAKALANDI! User: {user_id}")
                        log_system(f"🔥 TOP10 KOMUTU YAKALANDI! User: {user_id}")
                        await handle_top10_command_direct(message)
                    else:
                        # Diğer komutlar için normal handler'lara bırak
                        log_system(f"🔄 Komut router'lara yönlendiriliyor: {command} - User: {user_id}")
                        return
                    
            except Exception as e:
                log_error(f"❌ Private message handler hatası: {e}")
                logger.error(f"HANDLER HATASI: {e}")
        
        # Eski karmaşık kayıt - iptal
        # dp.message(F.chat.type == "private", ~F.text.startswith("/"))(handle_all_chat_inputs)
        
        # Grup mesajları monitor_group_message içinde işleniyor
        # Recruitment callback handler router'da tanımlı
        
        # Admin panel callback'leri - SADECE admin panel prefix'leri (event_ prefix'i YOK!)
        from handlers.admin_panel import admin_panel_callback
        dp.callback_query(
            F.data.startswith("admin_") |
            F.data.startswith("category_") |
            F.data.startswith("price_") |
            F.data.startswith("admin_order_") |
            F.data.startswith("set_points_") |
            F.data.startswith("set_daily_") |
            F.data.startswith("set_weekly_") |
            F.data.startswith("balance_") |
            F.data.startswith("system_")
        )(admin_panel_callback)
        
        # Start menü callback handler'ları
        async def start_menu_callback(callback: types.CallbackQuery):
            """Start menü callback'lerini işle"""
            try:
                user_id = callback.from_user.id
                data = callback.data
                
                if data == "menu_command":
                    # Ana menü callback'i - doğrudan show_menu_from_callback kullan
                    from handlers.profile_handler import show_menu_from_callback
                    await show_menu_from_callback(callback)
                elif data.startswith("top10_send_"):
                    # Top10 grup gönderim callback'i
                    target_chat_id = int(data.replace("top10_send_", ""))
                    await handle_top10_send_to_group(callback, target_chat_id)
                elif data == "top10_cancel":
                    # Top10 iptal callback'i
                    await callback.edit_message_text(
                        "❌ <b>TOP 10 GÖNDERİMİ İPTAL EDİLDİ</b>\n\n"
                        "🔄 Yeniden denemek için /top10 yazın.",
                        parse_mode="HTML"
                    )
                elif data == "market_command":
                    # Market komutu için doğrudan market callback'i çağır
                    from handlers.profile_handler import profile_callback_handler
                    # Callback data'sını geçici olarak değiştir
                    original_data = callback.data
                    callback.data = "profile_market"
                    try:
                        await profile_callback_handler(callback)
                    finally:
                        callback.data = original_data
                elif data == "events_command":
                    # Etkinlikler komutu için doğrudan events callback'i çağır
                    from handlers.profile_handler import profile_callback_handler
                    original_data = callback.data
                    callback.data = "profile_events"
                    try:
                        await profile_callback_handler(callback)
                    finally:
                        callback.data = original_data
                elif data == "profile_command":
                    # Profil komutu için doğrudan profile callback'i çağır
                    from handlers.profile_handler import profile_callback_handler
                    original_data = callback.data
                    callback.data = "profile_main"
                    try:
                        await profile_callback_handler(callback)
                    finally:
                        callback.data = original_data
                elif data == "ranking_command":
                    # Sıralama komutu için doğrudan ranking callback'i çağır
                    from handlers.profile_handler import profile_callback_handler
                    original_data = callback.data
                    callback.data = "profile_ranking"
                    try:
                        await profile_callback_handler(callback)
                    finally:
                        callback.data = original_data
                elif data == "help_command":
                    from handlers.register_handler import yardim_command
                    await yardim_command(callback.message)
                elif data == "start_command":
                    # Start komutunu çağır
                    from handlers.start_handler import start_command
                    await start_command(callback.message)

                
                try:
                    await callback.answer("✅ Komut çalıştırıldı!")
                except Exception as answer_error:
                    # Query timeout hatası - sessizce geç
                    if "query is too old" in str(answer_error).lower() or "timeout" in str(answer_error).lower():
                        logger.debug(f"⏸️ Start menu callback answer timeout - User: {callback.from_user.id}")
                    else:
                        logger.warning(f"⚠️ Start menu callback answer hatası: {answer_error}")
                
            except Exception as e:
                log_error(f"❌ Start menü callback hatası: {e}")
                try:
                    await callback.answer("❌ Hata oluştu!")
                except Exception as answer_error:
                    logger.debug(f"Callback answer hatası (kritik değil): {answer_error}")  # Query timeout - sessizce geç
        
        # Start menü callback'lerini kaydet
        dp.callback_query(F.data.in_(["menu_command", "market_command", "events_command", "profile_command", "ranking_command", "help_command", "start_command"]))(start_menu_callback)
        
        # Top10 callback'lerini kaydet
        dp.callback_query(lambda c: c.data and (c.data.startswith("top10_send_") or c.data == "top10_cancel"))(start_menu_callback)
        
        # Dinamik komut oluşturucu callback'leri - MANUEL KAYIT
        from handlers.dynamic_command_creator import (
            start_command_creation, cancel_command_creation, 
            handle_skip_button_text, handle_skip_button_url,
            list_custom_commands_handler, delete_custom_command_handler
        )
        dp.callback_query(F.data == "admin_command_creator")(start_command_creation)
        dp.callback_query(F.data == "cancel_command_creation")(cancel_command_creation)
        dp.callback_query(F.data == "skip_button_text")(handle_skip_button_text)
        dp.callback_query(F.data == "skip_button_url")(handle_skip_button_url)
        dp.callback_query(F.data == "list_custom_commands")(list_custom_commands_handler)
        dp.callback_query(F.data == "delete_custom_command")(delete_custom_command_handler)
        
        # 🔥 YENİ EKSİK SİSTEMLER - CALLBACK HANDLER'LAR
        # Zamanlanmış mesajlar sistemi callback'leri - EKSİK FONKSIYONLAR, KALDIRILDI
        # from handlers.scheduled_messages import (
        #     scheduled_bot_callback, start_scheduled_bot_creation, 
        #     cancel_scheduled_bot_creation, edit_scheduled_bot_callback,
        #     delete_scheduled_bot_callback, confirm_scheduled_bot_delete
        # )
        # dp.callback_query(F.data == "admin_scheduled_messages")(scheduled_bot_callback)
        # dp.callback_query(F.data == "create_scheduled_bot")(start_scheduled_bot_creation)
        # dp.callback_query(F.data == "cancel_scheduled_bot")(cancel_scheduled_bot_creation)
        # dp.callback_query(F.data.startswith("edit_scheduled_"))(edit_scheduled_bot_callback)
        # dp.callback_query(F.data.startswith("delete_scheduled_"))(delete_scheduled_bot_callback)
        # dp.callback_query(F.data.startswith("confirm_delete_scheduled_"))(confirm_scheduled_bot_delete)
        
        # Bakiye etkinlikleri sistemi callback'leri - Router'da tanımlı olduğu için kaldırıldı
        
        # Scheduled Messages callback'leri
        from handlers.scheduled_messages import scheduled_callback_handler
        dp.callback_query(lambda c: c.data and c.data.startswith("scheduled_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("toggle_bot_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("edit_bot_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("bot_toggle_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("edit_messages_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("edit_interval_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("edit_link_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("edit_image_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("edit_name_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("set_interval_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("remove_link_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("add_link_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("remove_image_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("add_image_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("create_bot_profile"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("edit_message_text_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("send_message_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("recreate_bot_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("delete_bot_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("create_bot_link_yes_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("create_bot_link_no_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("select_bot_group_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("recreate_bot_link_yes_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("recreate_bot_link_no_"))(scheduled_callback_handler)
        dp.callback_query(lambda c: c.data and c.data.startswith("select_recreate_group_"))(scheduled_callback_handler)

        
        # 🔥 MANUEL HANDLER KAYIT - ÇEKİLİŞ MESAJ HANDLER'ı (AKTİF)
        # Not: handle_all_chat_inputs içinde zaten kontrol ediliyor
        
        log_system("Tüm handler'lar kaydedildi!")
        
        # Background task'ları başlat
        asyncio.create_task(start_cleanup_task())
        asyncio.create_task(start_memory_cleanup())  # Memory cleanup
        asyncio.create_task(start_recruitment_background())  # Kayıt teşvik sistemi
        asyncio.create_task(mod_activity_monitor_task())  # Mod aktivite takibi - Aktif sohbet algılama
        
        # Mod günlük rapor sistemi - Her 24 saatte bir modlara rapor gönder
        from handlers.mod_handler import mod_daily_report_task
        asyncio.create_task(mod_daily_report_task())  # Mod günlük analiz raporları
        
        # Zamanlanmış mesajlar - Asenkron başlat
        try:
            asyncio.create_task(start_scheduled_messages(bot))  # Zamanlanmış mesajlar
            log_system("✅ Zamanlanmış mesajlar başlatıldı")
        except Exception as e:
            log_system(f"❌ Zamanlanmış mesajlar başlatma hatası: {e}")
            
        log_system("Background cleanup task başlatıldı!")
        log_system("🎯 Kayıt teşvik sistemi başlatıldı!")
        
        # Memory cache güncelleme task'ı kaldırıldı
        
        # Bot bilgilerini al
        log_system("🔍 Bot bilgileri alınıyor...")
        bot_info = await bot.get_me()
        log_system(f"🤖 Bot: @{bot_info.username} - {bot_info.first_name}")
        log_system(f"👤 Admin ID: {config.ADMIN_USER_ID}")
        
        log_system("🚀 Bot başarıyla çalışmaya başladı!")
        log_system("⏹️ Durdurmak için Ctrl+C")
        
        # Detaylı log sistemi başlatma
        from utils.logging_utils import set_logging_system
        from handlers.detailed_logging_system import logging_system
        set_logging_system(logging_system)
        
        # Telegram logger'ı kur (rate limit korumalı)
        try:
            from utils.telegram_logger import setup_telegram_logger
            setup_telegram_logger(bot, config.LOG_GROUP_ID)
            log_system("📱 Telegram logger başarıyla kuruldu")
        except Exception as _tl_err:
            log_warning(f"Telegram logger kurulamadı: {_tl_err}")
            log_system("📱 Console logger aktif (Telegram logger kapalı)")
        
        await log_system_startup()
        
        # STARTUP BİLDİRİMİ: DEVRE DIŞI BIRAKILDI
        # STARTUP BİLDİRİMİ: Admin'lere bot başlatma bildirimi
        log_system("📢 Startup bildirimi hazırlanıyor...")
        
        # Background'da çalıştır - database pool kontrolü ile
        async def delayed_startup_notification():
            from database import db_pool
            
            # Database pool'u bekle (maksimum 30 saniye)
            for attempt in range(30):
                if db_pool is not None:
                    log_system(f"Database pool hazır, startup bildirimi gönderiliyor (attempt {attempt + 1})")
                    break
                await asyncio.sleep(1)
            else:
                log_warning("Database pool 30 saniye sonra hala hazır değil, startup bildirimini atlıyoruz", None, None, None, None)
                return
            
            try:
                await send_startup_notification()
            except Exception as e:
                log_error(f"Startup bildirimi hatası: {e}")
        
        # Background'da çalıştır
        asyncio.create_task(delayed_startup_notification())
        
        # Bot'u başlat
        logger.info("🚀 Bot polling başlatılıyor...")
        log_system("🚀 Bot polling başlatılıyor...")
        logger.info("✅ Bot başarıyla çalışıyor! Komutlar hazır.")
        log_system("✅ Bot başarıyla çalışıyor! Komutlar hazır.")
        
        # Periyodik log gönderimi için background task - DEVRE DIŞI BIRAKILDI
        # async def periodic_logging():
        #     while True:
        #         try:
        #             await asyncio.sleep(60)  # Her 60 saniyede bir
        #             log_system("🔄 Bot aktif çalışıyor - Periyodik log")
        #             
        #             # Database durumunu kontrol et
        #             from database import db_pool
        #             if db_pool:
        #                 log_system("✅ Database bağlantısı aktif")
        #             else:
        #                 log_warning("⚠️ Database bağlantısı yok")
        #                 
        #         except Exception as e:
        #             log_error(f"Periyodik log hatası: {e}")
        # 
        # # Background task'i başlat
        # logger.info("🔄 Periyodik log task'i başlatılıyor...")
        # asyncio.create_task(periodic_logging())
        # logger.info("✅ Periyodik log task'i başlatıldı")
        
        logger.info("🎯 Bot polling başlatılıyor...")
        
        # Eski mesajları atla - Webhook ve pending update'leri temizle
        logger.info("🧹 Eski mesajlar temizleniyor...")
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Eski mesajlar temizlendi!")
        
        # Sadece belirli update tiplerini kabul et
        allowed_updates = ["message", "callback_query", "my_chat_member"]
        
        await dp.start_polling(
            bot, 
            timeout=60, 
            request_timeout=60, 
            drop_pending_updates=True,
            allowed_updates=allowed_updates
        )
        
    except KeyboardInterrupt:
        log_system("Bot kullanıcı tarafından durduruldu!")
        
        # Detaylı log sistemi kapatma
        await log_system_shutdown()
        
        # SHUTDOWN BİLDİRİMİ: DEVRE DIŞI BIRAKILDI
        # log_system("Shutdown bildirimi gönderiliyor...")
        # try:
        #     # Önce bildirim gönder
        #     await send_maintenance_notification()
        #     log_system("Shutdown bildirimi başarıyla gönderildi!")
        #     
        #     # Bildirim gönderildikten sonra 2 saniye bekle
        #     await asyncio.sleep(2)
        #     
        #     # Sonra temiz kapanış
        #     await cleanup_resources()
        #     
        # except Exception as e:
        #     log_error(f"Shutdown bildirimi hatası: {e}")
        #     await cleanup_resources()
        
        # Temiz kapanış
        await cleanup_resources()
            
    except Exception as e:
        # log_error kullan (import edilmiş olmalı)
        try:
            log_error(f"Bot başlatma hatası: {e}")
        except NameError:
            # Eğer log_error import edilmemişse logger kullan
            logger.error(f"Bot başlatma hatası: {e}", exc_info=True)
        
        # Detaylı log
        try:
            from handlers.detailed_logging_system import log_error as detailed_log_error
            await detailed_log_error(e, "Bot başlatma hatası")
        except Exception as detailed_log_err:
            logger.debug(f"Detaylı log sistemi hatası (kritik değil): {detailed_log_err}")
        
    finally:
        await cleanup_resources()

# handle_group_chat fonksiyonu kaldırıldı - Chat sistemi message_monitor.py içinde entegre edilmiş

async def handle_group_command_silently(message: Message):
    """Grup chatindeki komutları yakala ve özelde çalıştır"""
    try:
        user_id = message.from_user.id
        command = message.text.split()[0]  # İlk kelimeyi al (komut)
        
        log_system(f"🔇 Grup komutu yakalandı - User: {user_id}, Command: {command}, Group: {message.chat.id}")
        
        # Mesajı sil
        try:
            await message.delete()
            log_system(f"✅ Grup komut mesajı silindi - Command: {command}")
        except Exception as e:
            log_error(f"❌ Grup komut mesajı silinemedi: {e}")
            
            # Detaylı log
            try:
                from handlers.detailed_logging_system import log_error as detailed_log_error
                await detailed_log_error(e, "Grup komut mesajı silme hatası")
            except Exception as log_error:
                logger.debug(f"Detaylı log sistemi hatası (kritik değil): {log_error}")
        
        # Komutu özelde çalıştır
        try:
            # Bot instance'ını al
            from config import get_config
            config = get_config()
            from aiogram import Bot
            temp_bot = Bot(token=config.BOT_TOKEN)
            
            # Import'ları burada yap
            from handlers.start_handler import start_command
            from handlers.register_handler import kirvekayit_command
            from handlers.profile_handler import menu_command
            from handlers.events_list import list_active_lotteries, send_lotteries_list_privately, send_group_lotteries_list
            from handlers.simple_events import create_lottery_command
            from handlers.admin_panel import admin_panel_command
            # from handlers.admin_commands_list import admin_commands_list
            # Lazy import for admin panel commands - direkt import
            from handlers.admin_panel import clean_messages_command, list_groups_command, help_command, delete_group_command
            from handlers.group_handler import kirvegrup_command, botlog_command, group_info_command
            from handlers.admin_order_management import show_orders_list_modern
            from handlers.events_list import list_active_lotteries as list_active_events
            from handlers.event_management import end_lottery_command
            
            # Komut türüne göre işle
            if command == "/start":
                await start_command(message)
            elif command == "/kirvekayit":
                await kirvekayit_command(message)
            elif command == "/menu":
                await menu_command(message)
            elif command == "/cekilisler":
                # Admin kontrolü
                from config import is_admin
                is_admin_user = is_admin(user_id)
                
                if is_admin_user:
                    # Admin için özel çekiliş listesi (bitirme butonu ile)
                    await send_lotteries_list_privately(user_id, is_admin=True)
                else:
                    # Normal kullanıcı için grup çekiliş listesi (sadece katılım)
                    await send_group_lotteries_list(user_id)
            elif command == "/cekilisyap":
                await create_lottery_command(message)
            elif command == "/adminpanel":
                await admin_panel_command(message)
            elif command == "/adminkomutlar":
                await admin_panel_command(message)  # admin_commands_list yerine admin_panel_command
            elif command == "/temizle":
                await clean_messages_command(message)
            elif command == "/gruplar":
                await list_groups_command(message)
            elif command == "/grupsil":
                await delete_group_command(message)
            elif command == "/kirvegrup":
                from handlers.group_handler import kirvegrup_command
                await kirvegrup_command(message)
            elif command == "/botlog":
                await botlog_command(message)
            elif command == "/grupbilgi":
                await group_info_command(message)
            elif command == "/yardim":
                await yardim_command(message)
            elif command == "/siparisliste":
                await show_orders_list_modern(message)
            elif command == "/etkinlikler":
                await list_active_events(message)
            elif command == "/cekilisbitir":
                await end_lottery_command(message)
            elif command == "/adminyap":
                from handlers.admin_permission_manager import make_admin_command
                await make_admin_command(message)
            elif command == "/adminçıkar":
                from handlers.admin_permission_manager import remove_admin_command
                await remove_admin_command(message)
            elif command == "/adminlist":
                from handlers.admin_permission_manager import list_admins_command
                await list_admins_command(message)
            elif command == "/admininfo":
                from handlers.admin_permission_manager import admin_info_command
                await admin_info_command(message)
            elif command == "/yetkiver":
                from handlers.admin_permission_manager import give_permission_command
                await give_permission_command(message)
            elif command == "/yetkial":
                from handlers.admin_permission_manager import take_permission_command
                await take_permission_command(message)
            elif command == "/bakiyeetkinlik":
                # from handlers.balance_event import create_balance_event_command
                # await create_balance_event_command(message)
                pass # Eski komutu kaldır
            elif command == "/bakiyeetkinlikler":
                # from handlers.balance_event import list_balance_events_command
                pass # Eski komutu kaldır
            elif command == "/adminstats":
                from handlers.statistics_system import admin_stats_command
                await admin_stats_command(message)
            elif command == "/sistemistatistik":
                from handlers.statistics_system import system_stats_command
                await system_stats_command(message)
            elif command == "/testsql":
                from handlers.admin_panel import test_sql_queries_command
                await test_sql_queries_command(message)
            elif command in ["/uyarı", "/warn"]:
                # Uyarı komutu grup içinde çalışmalı
                # Özel mesajda uyarı komutu kullanılamaz
                error_message = """
⚠️ **Uyarı Komutu Grup Gerekli**

Bu komut sadece grup içinde kullanılabilir.

💡 **Kullanım:**
1. Gruba gidin
2. Uyarı vermek istediğiniz kullanıcının mesajına yanıt verin
3. `/uyarı [sebep]` yazın

📋 **Örnek:**
```
/uyarı Spam yapıyor
```

🔔 **Not:** Grup komutları otomatik olarak silinir ve özel mesajda yanıtlanır.
                """
                await temp_bot.send_message(user_id, error_message, parse_mode="Markdown")
            elif command in ["/uyarısıfırla", "/resetwarn"]:
                from handlers.punishment_system import reset_warnings_command
                await reset_warnings_command(message)
            elif command in ["/uyarılar", "/warnings"]:
                from handlers.punishment_system import warnings_command
                await warnings_command(message)
            elif command in ["/uyarıaşama", "/warnstage"]:
                from handlers.punishment_system import warn_stage_command
                await warn_stage_command(message)
            elif command in ["/mute", "/sustur"]:
                from handlers.punishment_system import mute_command
                await mute_command(message)
            elif command in ["/unmute", "/susturma"]:
                from handlers.punishment_system import unmute_command
                await unmute_command(message)
            elif command in ["/ban", "/yasakla"]:
                from handlers.punishment_system import ban_command
                await ban_command(message)
            elif command in ["/unban", "/yasakkaldır"]:
                from handlers.punishment_system import unban_command
                await unban_command(message)
            else:
                # Bilinmeyen komut için uyarı
                unknown_command_message = f"""
⚠️ **Bilinmeyen Komut**

**Komut:** `{command}`
**Grup:** {message.chat.title}

❌ **Bu komut henüz tanımlanmamış veya kullanılamıyor.**

💡 **Kullanılabilir Komutlar:**
• `/start` - Ana menü
• `/menu` - Profil menüsü
• `/kirvekayit` - Kayıt sistemi
• `/kirvegrup` - Grup kayıt sistemi
• `/grupbilgi` - Grup bilgileri
• `/botlog` - Log grubu ayarlama
• `/cekilisler` - Aktif çekilişler
• `/cekilisyap` - Çekiliş oluştur (Admin)
• `/adminpanel` - Admin paneli (Admin)
• `/adminstats` - Admin istatistikleri (Admin)
• `/sistemistatistik` - Sistem istatistikleri (Admin)

🔔 **Not:** Komutlar grup chatinde silinir ve özel mesajda yanıtlanır.
                """
                
                await temp_bot.send_message(
                    user_id,
                    unknown_command_message,
                    parse_mode="Markdown"
                )
            
            await temp_bot.session.close()
            log_system(f"✅ Grup komutu özelde çalıştırıldı - Command: {command}")
            
        except Exception as e:
            log_error(f"❌ Grup komut işleme hatası: {e}")
            # Hata durumunda kullanıcıya bildir
            try:
                error_message = f"""
❌ **Komut İşleme Hatası**

**Komut:** `{command}`
**Hata:** Sistem hatası oluştu

🔧 **Çözüm:** Birkaç dakika bekleyip tekrar deneyin.
                """
                
                from aiogram import Bot
                from config import get_config
                config = get_config()
                temp_bot = Bot(token=config.BOT_TOKEN)
                await temp_bot.send_message(user_id, error_message, parse_mode="Markdown")
                await temp_bot.session.close()
                
            except Exception as send_error:
                log_error(f"❌ Hata mesajı gönderilemedi: {send_error}")
        
    except Exception as e:
        log_error(f"❌ Grup komut handler hatası: {e}")


if __name__ == "__main__":
    """
    Bot'u çalıştır veya analiz script'ini çalıştır
    
    Kullanım:
    python main.py              # Bot'u çalıştır
    python main.py --analyze    # Zamanlanmış mesajları analiz et
    """
    import sys
    
    # Analiz modu kontrolü
    if len(sys.argv) > 1 and sys.argv[1] == "--analyze":
        # Zamanlanmış mesajları analiz et
        from show_scheduled_messages import analyze_scheduled_messages
        logger.info("🚀 Zamanlanmış Mesajlar Analiz Script'i Başlatılıyor...\n")
        try:
            asyncio.run(analyze_scheduled_messages())
        except KeyboardInterrupt:
            logger.info("\n⏹️ Script kullanıcı tarafından durduruldu!")
        except Exception as e:
            logger.error(f"\n❌ Script hatası: {e}")
            import traceback
            traceback.print_exc()
        sys.exit(0)
    
    # Normal bot modu
    # Logging'i CMD'ye yönlendir
    import logging
    import os
    
    # Logs klasörünü oluştur (yoksa)
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)
    
    # Log dosyası yolu
    log_file_path = os.path.join(logs_dir, 'bot.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # CMD'ye yazdır
            logging.FileHandler(log_file_path, encoding='utf-8')  # Dosyaya da yazdır
        ]
    )
    
    logger.info("🚀 Bot başlatılıyor...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Bot kullanıcı tarafından durduruldu!")
    except Exception as e:
        logger.error(f"❌ Bot hatası: {e}")
        import traceback
        traceback.print_exc() 