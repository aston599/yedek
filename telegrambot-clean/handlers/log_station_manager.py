"""
📊 Log Station Manager - Mevcut Log Sistemini Yönetir
Telegram logger ve detailed logging sistemini geliştirilmiş bir arayüzle yönetir
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from aiogram import Router, F, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from config import is_admin
from utils.telegram_logger import get_telegram_logger
from utils.logger import logger

router = Router()

class LogFilter(Enum):
    """Log filtreleri"""
    ALL = "Tümü"
    ERRORS = "Hatalar"
    WARNINGS = "Uyarılar"
    CRITICAL = "Kritik"
    SYSTEM = "Sistem"
    USER = "Kullanıcı"
    ADMIN = "Admin"
    DATABASE = "Veritabanı"
    MARKET = "Market"
    EVENT = "Etkinlik"

# Log istatistikleri (memory-based)
log_stats = {
    'total_received': 0,
    'total_sent': 0,
    'by_level': {
        'DEBUG': 0,
        'INFO': 0,
        'WARNING': 0,
        'ERROR': 0,
        'CRITICAL': 0
    },
    'by_type': {
        'system': 0,
        'user': 0,
        'admin': 0,
        'database': 0,
        'market': 0,
        'event': 0
    },
    'error_count': 0,
    'warning_count': 0,
    'critical_count': 0,
    'last_log_time': None
}

# Log geçmişi (son 100 log - memory-based)
log_history: List[Dict[str, Any]] = []
MAX_LOG_HISTORY = 100

def add_to_log_history(level: str, message: str, severity: int = 3):
    """Log geçmişine ekle"""
    log_entry = {
        'timestamp': datetime.now(),
        'level': level,
        'message': message[:200],  # İlk 200 karakter
        'severity': severity
    }
    
    log_history.append(log_entry)
    
    # Maksimum log sayısını kontrol et
    if len(log_history) > MAX_LOG_HISTORY:
        log_history.pop(0)
    
    # İstatistikleri güncelle
    log_stats['total_received'] += 1
    if level in log_stats['by_level']:
        log_stats['by_level'][level] += 1
    
    if level == 'ERROR':
        log_stats['error_count'] += 1
    elif level == 'WARNING':
        log_stats['warning_count'] += 1
    elif level == 'CRITICAL':
        log_stats['critical_count'] += 1
    
    log_stats['last_log_time'] = datetime.now()

@router.message(Command("logstation", "logmenü", "logpanel", "logyönetim"))
async def log_station_command(message: Message):
    """Log Station menüsü - Mevcut log sistemini yönetir"""
    try:
        if not is_admin(message.from_user.id):
            await message.answer("❌ Bu komut sadece adminler için!")
            return
        
        await show_log_station_menu(message)
        
    except Exception as e:
        logger.error(f"❌ Log station komutu hatası: {e}")
        await message.answer("❌ Log menüsü yüklenirken hata oluştu!")

async def show_log_station_menu(message: Message):
    """Log Station menüsünü göster"""
    try:
        telegram_logger = get_telegram_logger()
        
        # Mevcut log sistemi durumu
        system_status = "✅ Aktif" if telegram_logger else "❌ Pasif"
        queue_size = len(telegram_logger.log_queue) if telegram_logger else 0
        
        message_text = f"""
╔══════════════════════════════╗
║ 📊 <b>LOG STATION</b> 📊 ║
╚══════════════════════════════╝

🔧 <b>SİSTEM DURUMU</b>
{system_status} Telegram Logger
📦 Kuyruk: {queue_size} log
⏰ Son Log: {log_stats['last_log_time'].strftime('%H:%M:%S') if log_stats['last_log_time'] else 'Yok'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>İSTATİSTİKLER</b>
📊 Toplam Alınan: {log_stats['total_received']}
📤 Toplam Gönderilen: {log_stats['total_sent']}
❌ Hatalar: {log_stats['error_count']}
⚠️ Uyarılar: {log_stats['warning_count']}
🚨 Kritik: {log_stats['critical_count']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>HIZLI İŞLEMLER</b>
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Son Loglar", callback_data="log_view_recent"),
                InlineKeyboardButton(text="❌ Hatalar", callback_data="log_view_errors")
            ],
            [
                InlineKeyboardButton(text="🚨 Kritik", callback_data="log_view_critical"),
                InlineKeyboardButton(text="📊 İstatistikler", callback_data="log_stats_detailed")
            ],
            [
                InlineKeyboardButton(text="🔍 Filtrele", callback_data="log_filter_menu"),
                InlineKeyboardButton(text="⚙️ Ayarlar", callback_data="log_settings_menu")
            ],
            [
                InlineKeyboardButton(text="🧹 Kuyruğu Temizle", callback_data="log_clear_queue"),
                InlineKeyboardButton(text="🔄 Yenile", callback_data="log_refresh")
            ]
        ])
        
        await message.answer(
            message_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Log station menü hatası: {e}")

@router.callback_query(F.data.startswith("log_"))
async def log_station_callback(callback: CallbackQuery):
    """Log Station callback handler"""
    try:
        data = callback.data
        
        if data == "log_view_recent":
            await show_recent_logs(callback)
        elif data == "log_view_errors":
            await show_error_logs(callback)
        elif data == "log_view_critical":
            await show_critical_logs(callback)
        elif data == "log_stats_detailed":
            await show_detailed_stats(callback)
        elif data == "log_filter_menu":
            await show_filter_menu(callback)
        elif data == "log_settings_menu":
            await show_settings_menu(callback)
        elif data == "log_clear_queue":
            await clear_queue_confirm(callback)
        elif data == "log_refresh":
            await callback.answer("🔄 Yenilendi!")
            await show_log_station_menu(callback.message)
        elif data == "log_clear_queue_confirm":
            await clear_queue(callback)
        elif data == "log_back":
            await show_log_station_menu(callback.message)
        
    except Exception as e:
        logger.error(f"❌ Log station callback hatası: {e}")
        await callback.answer("❌ Hata oluştu!")

async def show_recent_logs(callback: CallbackQuery):
    """Son log'ları göster"""
    try:
        recent_logs = log_history[-20:]  # Son 20 log
        
        if not recent_logs:
            await callback.answer("📭 Henüz log yok!", show_alert=True)
            return
        
        message = f"""
╔══════════════════════════════╗
║ 📋 <b>SON LOGLAR</b> 📋 ║
╚══════════════════════════════╝

📊 Toplam: {len(recent_logs)} log

        """
        
        for i, log in enumerate(reversed(recent_logs), 1):
            time_str = log['timestamp'].strftime('%H:%M:%S')
            level_emoji = {
                'DEBUG': '🔍',
                'INFO': 'ℹ️',
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '🚨'
            }.get(log['level'], '📝')
            
            message += f"\n{i}. {level_emoji} <code>{time_str}</code> - {log['level']}\n"
            message += f"   {log['message'][:100]}...\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="log_back")]
        ])
        
        await callback.message.edit_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Son log'lar gösterim hatası: {e}")
        await callback.answer("❌ Hata oluştu!")

async def show_error_logs(callback: CallbackQuery):
    """Hata log'larını göster"""
    try:
        error_logs = [log for log in log_history if log['level'] in ['ERROR', 'CRITICAL']]
        error_logs = error_logs[-15:]  # Son 15 hata
        
        if not error_logs:
            await callback.answer("✅ Hata yok!", show_alert=True)
            return
        
        message = f"""
╔══════════════════════════════╗
║ ❌ <b>HATA LOGLARI</b> ❌ ║
╚══════════════════════════════╝

📊 Toplam: {len(error_logs)} hata

        """
        
        for i, log in enumerate(reversed(error_logs), 1):
            time_str = log['timestamp'].strftime('%H:%M:%S')
            emoji = '🚨' if log['level'] == 'CRITICAL' else '❌'
            message += f"\n{i}. {emoji} <code>{time_str}</code> - {log['level']}\n"
            message += f"   {log['message'][:150]}...\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="log_back")]
        ])
        
        await callback.message.edit_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Hata log'ları gösterim hatası: {e}")
        await callback.answer("❌ Hata oluştu!")

async def show_critical_logs(callback: CallbackQuery):
    """Kritik log'ları göster"""
    try:
        critical_logs = [log for log in log_history if log['level'] == 'CRITICAL']
        critical_logs = critical_logs[-10:]  # Son 10 kritik
        
        if not critical_logs:
            await callback.answer("✅ Kritik log yok!", show_alert=True)
            return
        
        message = f"""
╔══════════════════════════════╗
║ 🚨 <b>KRİTİK LOGLAR</b> 🚨 ║
╚══════════════════════════════╝

📊 Toplam: {len(critical_logs)} kritik

        """
        
        for i, log in enumerate(reversed(critical_logs), 1):
            time_str = log['timestamp'].strftime('%H:%M:%S')
            message += f"\n{i}. 🚨 <code>{time_str}</code>\n"
            message += f"   {log['message'][:200]}...\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="log_back")]
        ])
        
        await callback.message.edit_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Kritik log'lar gösterim hatası: {e}")
        await callback.answer("❌ Hata oluştu!")

async def show_detailed_stats(callback: CallbackQuery):
    """Detaylı istatistikleri göster"""
    try:
        telegram_logger = get_telegram_logger()
        
        message = f"""
╔══════════════════════════════╗
║ 📊 <b>DETAYLI İSTATİSTİKLER</b> 📊 ║
╚══════════════════════════════╝

📈 <b>GENEL</b>
📊 Toplam Alınan: {log_stats['total_received']}
📤 Toplam Gönderilen: {log_stats['total_sent']}
💾 Geçmiş Log: {len(log_history)}

🎯 <b>SEVİYE DAĞILIMI</b>
🔍 DEBUG: {log_stats['by_level']['DEBUG']}
ℹ️ INFO: {log_stats['by_level']['INFO']}
⚠️ WARNING: {log_stats['by_level']['WARNING']}
❌ ERROR: {log_stats['by_level']['ERROR']}
🚨 CRITICAL: {log_stats['by_level']['CRITICAL']}

🔧 <b>SİSTEM AYARLARI</b>
        """
        
        if telegram_logger:
            message += f"""
📦 Kuyruk Boyutu: {len(telegram_logger.log_queue)}
⏰ Rate Limit: {telegram_logger.rate_limit_delay} saniye
📊 Min Log: {telegram_logger.min_logs_to_send}
📋 Max Log/Mesaj: {telegram_logger.max_logs_per_message}
            """
        else:
            message += "\n❌ Telegram Logger aktif değil"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="log_back")]
        ])
        
        await callback.message.edit_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ İstatistik gösterim hatası: {e}")
        await callback.answer("❌ Hata oluştu!")

async def show_filter_menu(callback: CallbackQuery):
    """Filtre menüsünü göster"""
    try:
        message = f"""
╔══════════════════════════════╗
║ 🔍 <b>LOG FİLTRELERİ</b> 🔍 ║
╚══════════════════════════════╝

📊 <b>Mevcut Filtreler:</b>
🔍 Tüm log tipleri aktif

💡 <b>Not:</b>
Filtreleme özelliği yakında eklenecek.
Şu an tüm log'lar görüntüleniyor.

        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="log_back")]
        ])
        
        await callback.message.edit_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Filtre menü hatası: {e}")
        await callback.answer("❌ Hata oluştu!")

async def show_settings_menu(callback: CallbackQuery):
    """Ayarlar menüsünü göster"""
    try:
        telegram_logger = get_telegram_logger()
        
        message = f"""
╔══════════════════════════════╗
║ ⚙️ <b>LOG AYARLARI</b> ⚙️ ║
╚══════════════════════════════╝

🔧 <b>Telegram Logger Ayarları</b>
        """
        
        if telegram_logger:
            message += f"""
📦 Kuyruk Boyutu: {len(telegram_logger.log_queue)}/{telegram_logger.log_queue.maxlen}
⏰ Rate Limit: {telegram_logger.rate_limit_delay} saniye
📊 Min Log Gönderim: {telegram_logger.min_logs_to_send}
📋 Max Log/Mesaj: {telegram_logger.max_logs_per_message}
🔧 Log Seviyesi: {telegram_logger.level}
            """
        else:
            message += "\n❌ Telegram Logger aktif değil"
        
        message += f"""

💾 <b>Geçmiş Ayarları</b>
📋 Max Geçmiş: {MAX_LOG_HISTORY}
📊 Mevcut: {len(log_history)}

        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="log_back")]
        ])
        
        await callback.message.edit_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Ayarlar menü hatası: {e}")
        await callback.answer("❌ Hata oluştu!")

async def clear_queue_confirm(callback: CallbackQuery):
    """Kuyruk temizleme onayı"""
    try:
        telegram_logger = get_telegram_logger()
        queue_size = len(telegram_logger.log_queue) if telegram_logger else 0
        
        message = f"""
⚠️ <b>Kuyruğu Temizle</b>

📦 Mevcut kuyruk: {queue_size} log

Kuyruktaki tüm log'lar silinecek. Bu işlem geri alınamaz!

Devam etmek istiyor musunuz?
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Evet, Temizle", callback_data="log_clear_queue_confirm"),
                InlineKeyboardButton(text="❌ İptal", callback_data="log_back")
            ]
        ])
        
        await callback.message.edit_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Kuyruk temizleme onay hatası: {e}")
        await callback.answer("❌ Hata oluştu!")

async def clear_queue(callback: CallbackQuery):
    """Kuyruğu temizle"""
    try:
        telegram_logger = get_telegram_logger()
        
        if telegram_logger:
            cleared_count = len(telegram_logger.log_queue)
            telegram_logger.log_queue.clear()
            await callback.answer(f"✅ {cleared_count} log kuyruktan temizlendi!")
        else:
            await callback.answer("❌ Telegram Logger aktif değil!", show_alert=True)
        
        await show_log_station_menu(callback.message)
        
    except Exception as e:
        logger.error(f"❌ Kuyruk temizleme hatası: {e}")
        await callback.answer("❌ Hata oluştu!")



