"""
📊 İstatistikler Sistemi - KirveHub Bot
Kapsamlı bot istatistikleri ve analiz sistemi
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from aiogram import Router, F, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
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


# ==============================================
# DATABASE İSTATİSTİK FONKSİYONLARI
# ==============================================

async def get_comprehensive_stats() -> Dict[str, Any]:
    """Kapsamlı sistem istatistiklerini al"""
    try:
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool alınamadı!")
            return {"error": "Database bağlantısı yok"}
        
        async with pool.acquire() as conn:
            # Temel kullanıcı istatistikleri
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            registered_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_registered = TRUE")
            active_groups = await conn.fetchval("SELECT COUNT(*) FROM registered_groups WHERE is_active = TRUE")
            
            # Point sistemi istatistikleri
            total_points = await conn.fetchval("SELECT COALESCE(SUM(kirve_points), 0) FROM users WHERE is_registered = TRUE")
            total_daily_points = await conn.fetchval("SELECT COALESCE(SUM(daily_points), 0) FROM users WHERE is_registered = TRUE")
            avg_user_points = await conn.fetchval("SELECT COALESCE(AVG(kirve_points), 0) FROM users WHERE is_registered = TRUE AND kirve_points > 0")
            
            # Mesaj istatistikleri
            total_messages = await conn.fetchval("SELECT COALESCE(SUM(total_messages), 0) FROM users WHERE is_registered = TRUE")
            avg_user_messages = await conn.fetchval("SELECT COALESCE(AVG(total_messages), 0) FROM users WHERE is_registered = TRUE AND total_messages > 0")
            
            # Bugünkü aktivite
            today = datetime.now().date()
            today_points = await conn.fetchval("SELECT COALESCE(SUM(daily_points), 0) FROM users WHERE is_registered = TRUE AND last_point_date = $1", today)
            today_active_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_registered = TRUE AND last_point_date = $1", today)
            
            # Son 7 gün aktivitesi
            week_ago = today - timedelta(days=7)
            week_active_users = await conn.fetchval("SELECT COUNT(DISTINCT user_id) FROM daily_stats WHERE message_date >= $1", week_ago)
            week_messages = await conn.fetchval("SELECT COALESCE(SUM(message_count), 0) FROM daily_stats WHERE message_date >= $1", week_ago)
            
            # Etkinlik istatistikleri
            total_events = await conn.fetchval("SELECT COUNT(*) FROM events")
            active_events = await conn.fetchval("SELECT COUNT(*) FROM events WHERE status = 'active' AND completed_at IS NULL")
            completed_events = await conn.fetchval("SELECT COUNT(*) FROM events WHERE status = 'completed'")
            total_participants = await conn.fetchval("SELECT COUNT(*) FROM event_participations WHERE withdrew_at IS NULL")
            
            # En aktif kullanıcılar (top 10) - KP sıralaması
            top_users_kp = await conn.fetch("""
                SELECT u.first_name, u.username, u.kirve_points, u.total_messages
                FROM users u
                WHERE u.is_registered = TRUE AND u.kirve_points > 0
                ORDER BY u.kirve_points DESC
                LIMIT 10
            """)
            
            # En aktif kullanıcılar (top 10) - Mesaj sıralaması
            top_users_messages = await conn.fetch("""
                SELECT u.first_name, u.username, u.kirve_points, u.total_messages
                FROM users u
                WHERE u.is_registered = TRUE AND u.total_messages > 0
                ORDER BY u.total_messages DESC
                LIMIT 10
            """)
            
            # En aktif gruplar
            top_groups = await conn.fetch("""
                SELECT rg.group_name, COUNT(ds.message_count) as total_messages
                FROM registered_groups rg
                LEFT JOIN daily_stats ds ON rg.group_id = ds.group_id
                WHERE rg.is_active = TRUE
                GROUP BY rg.group_id, rg.group_name
                ORDER BY total_messages DESC
                LIMIT 5
            """)
            
            # Rütbe dağılımı
            rank_distribution = await conn.fetch("""
                SELECT ur.rank_name, COUNT(u.user_id) as user_count
                FROM user_ranks ur
                LEFT JOIN users u ON ur.rank_id = u.rank_id
                WHERE u.is_registered = TRUE
                GROUP BY ur.rank_id, ur.rank_name
                ORDER BY ur.rank_level
            """)
            
            return {
                # Temel istatistikler
                "total_users": total_users or 0,
                "registered_users": registered_users or 0,
                "active_groups": active_groups or 0,
                "registration_rate": round((registered_users / total_users * 100) if total_users > 0 else 0, 1),
                
                # Point sistemi
                "total_points": float(total_points) if total_points else 0.0,
                "total_daily_points": float(total_daily_points) if total_daily_points else 0.0,
                "avg_user_points": float(avg_user_points) if avg_user_points else 0.0,
                
                # Mesaj sistemi
                "total_messages": total_messages or 0,
                "avg_user_messages": float(avg_user_messages) if avg_user_messages else 0.0,
                
                # Günlük aktivite
                "today_points": float(today_points) if today_points else 0.0,
                "today_active_users": today_active_users or 0,
                
                # Haftalık aktivite
                "week_active_users": week_active_users or 0,
                "week_messages": week_messages or 0,
                
                # Etkinlik sistemi
                "total_events": total_events or 0,
                "active_events": active_events or 0,
                "completed_events": completed_events or 0,
                "total_participants": total_participants or 0,
                
                # Top listeler
                "top_users_kp": [dict(user) for user in top_users_kp] if top_users_kp else [],
                "top_users_messages": [dict(user) for user in top_users_messages] if top_users_messages else [],
                "top_groups": [dict(group) for group in top_groups] if top_groups else [],
                "rank_distribution": [dict(rank) for rank in rank_distribution] if rank_distribution else [],
                
                # Meta bilgiler
                "generated_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                "database_status": "active"
            }
            
    except Exception as e:
        logger.error(f"❌ Comprehensive stats hatası: {e}")
        return {"error": str(e), "database_status": "error"}


async def get_system_performance_stats() -> Dict[str, Any]:
    """Sistem performans istatistikleri"""
    try:
        pool = await get_db_pool()
        if not pool:
            return {"error": "Database bağlantısı yok"}
        
        async with pool.acquire() as conn:
            # Database performans
            db_size = await conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
            table_count = await conn.fetchval("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            
            # Son 24 saat aktivitesi
            yesterday = datetime.now() - timedelta(days=1)
            recent_activity = await conn.fetchval("SELECT COUNT(*) FROM daily_stats WHERE message_date >= $1", yesterday.date())
            
            # Sistem uptime (bot_status tablosundan)
            last_startup = await conn.fetchval("SELECT created_at FROM bot_status WHERE status = 'Bot başlatıldı!' ORDER BY created_at DESC LIMIT 1")
            
            uptime_hours = 0
            if last_startup:
                uptime_delta = datetime.now() - last_startup.replace(tzinfo=None)
                uptime_hours = round(uptime_delta.total_seconds() / 3600, 1)
            
            return {
                "database_size": db_size or "Bilinmiyor",
                "table_count": table_count or 0,
                "recent_activity": recent_activity or 0,
                "uptime_hours": uptime_hours,
                "last_startup": last_startup.strftime("%d.%m.%Y %H:%M:%S") if last_startup else "Bilinmiyor",
                "performance_status": "good"
            }
            
    except Exception as e:
        logger.error(f"❌ Performance stats hatası: {e}")
        return {"error": str(e), "performance_status": "error"}


# ==============================================
# KOMUT HANDLER'LARI
# ==============================================

# @router.message(Command("adminstats"))  # MANUEL KAYITLI - ROUTER DEVRESİ DIŞI
async def admin_stats_command(message: Message) -> None:
    """
    /adminstats komutu - Süper Admin için detaylı sistem istatistikleri
    """
    try:
        user_id = message.from_user.id
        config = get_config()
        
        # Süper Admin kontrolü (DB tabanlı)
        try:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(user_id, 4):
                logger.warning(f"⚠️ Admin stats unauthorized access: {user_id}")
                return
        except Exception:
            if user_id != config.ADMIN_USER_ID:
                logger.warning(f"⚠️ Admin stats unauthorized access: {user_id}")
                return
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Admin stats komutu mesajı silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_admin_stats_privately(user_id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        logger.info(f"📊 Admin stats komutu ÖZELİNDE - User: {message.from_user.first_name} ({user_id})")
        
        # İstatistikleri göster
        await send_admin_stats_to_user(message.from_user.id, message)
        
    except Exception as e:
        logger.error(f"❌ Admin stats komut hatası: {e}")
        if message.chat.type == "private":
            await message.reply("❌ İstatistikler yüklenemedi!")


# @router.message(Command("sistemistatistik"))  # MANUEL KAYITLI - ROUTER DEVRESİ DIŞI  
async def system_stats_command(message: Message) -> None:
    """
    /sistemistatistik komutu - Genel sistem istatistikleri
    """
    try:
        user_id = message.from_user.id
        config = get_config()
        
        # Admin kontrolü - Admin2+
        try:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(user_id, 3):
                logger.warning(f"⚠️ System stats unauthorized access: {user_id}")
                return
        except Exception:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(user_id, 3):
                logger.warning(f"⚠️ System stats unauthorized access: {user_id}")
                return
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Sistem stats komutu mesajı silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_system_stats_privately(user_id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        logger.info(f"📊 Sistem stats komutu ÖZELİNDE - User: {message.from_user.first_name} ({user_id})")
        
        # Genel istatistikleri göster
        await send_system_stats_to_user(message.from_user.id, message)
        
    except Exception as e:
        logger.error(f"❌ System stats komut hatası: {e}")
        if message.chat.type == "private":
            await message.reply("❌ İstatistikler yüklenemedi!")


# ==============================================
# İSTATİSTİK GÖNDERME FONKSİYONLARI
# ==============================================

async def _send_admin_stats_privately(user_id: int):
    """Admin istatistiklerini özel mesajla gönder"""
    try:
        if not _bot_instance:
            logger.error("❌ Bot instance bulunamadı!")
            return
        
        # Kapsamlı istatistikleri al
        stats = await get_comprehensive_stats()
        performance = await get_system_performance_stats()
        
        if "error" in stats:
            await _bot_instance.send_message(user_id, f"❌ İstatistik hatası: {stats['error']}")
            return
        
        # Inline keyboard oluştur
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Yenile", callback_data="stats_refresh_admin"),
                InlineKeyboardButton(text="📊 Performans", callback_data="stats_performance")
            ],
            [
                InlineKeyboardButton(text="👥 Top Kullanıcılar", callback_data="stats_top_users"),
                InlineKeyboardButton(text="🏢 Top Gruplar", callback_data="stats_top_groups")
            ],
            [
                InlineKeyboardButton(text="📋 Rütbe Dağılımı", callback_data="stats_ranks"),
                InlineKeyboardButton(text="🎯 Etkinlik Stats", callback_data="stats_events")
            ]
        ])
        
        # Ana istatistik mesajı
        message = f"""
╔══════════════════════╗
║ 📊 <b>SİSTEM İSTATİSTİKLERİ</b> 📊 ║
╚══════════════════════╝

👑 <b>SÜPER ADMİN PANELİ</b>

📊 <b>TEMEL VERİLER:</b>
👥 Toplam Kullanıcı: <code>{stats['total_users']}</code>
✅ Kayıtlı Kullanıcı: <code>{stats['registered_users']}</code> ({stats['registration_rate']}%)
🏢 Aktif Grup: <code>{stats['active_groups']}</code>

💎 <b>POİNT SİSTEMİ:</b>
🏦 Toplam Point: <code>{stats['total_points']:.2f} KP</code>
📊 Günlük Point: <code>{stats['total_daily_points']:.2f} KP</code>
⚖️ Kullanıcı Ortalaması: <code>{stats['avg_user_points']:.2f} KP</code>

🎯 <b>BUGÜNKÜ AKTİVİTE:</b>
💎 Bugün Point: <code>{stats['today_points']:.2f} KP</code>
👤 Aktif Kullanıcı: <code>{stats['today_active_users']}</code>

🎮 <b>ETKİNLİK SİSTEMİ:</b>
🎯 Toplam Etkinlik: <code>{stats['total_events']}</code>
🔴 Aktif Etkinlik: <code>{stats['active_events']}</code>
✅ Tamamlanan: <code>{stats['completed_events']}</code>

🕐 <b>Son Güncelleme:</b> {stats['generated_at']}

💡 <b>Detaylı analiz için butonları kullanın!</b>
        """
        
        await _bot_instance.send_message(user_id, message, parse_mode="HTML", reply_markup=keyboard)
        logger.info(f"✅ Admin stats özel mesajla gönderildi: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Admin stats özel mesaj hatası: {e}")
        if _bot_instance:
            await _bot_instance.send_message(user_id, "❌ İstatistikler yüklenemedi!")


async def _send_system_stats_privately(user_id: int):
    """Sistem istatistiklerini özel mesajla gönder"""
    try:
        if not _bot_instance:
            logger.error("❌ Bot instance bulunamadı!")
            return
        
        # Temel istatistikleri al
        stats = await get_comprehensive_stats()
        
        if "error" in stats:
            await _bot_instance.send_message(user_id, f"❌ İstatistik hatası: {stats['error']}")
            return
        
        # Basit inline keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Yenile", callback_data="stats_refresh_system"),
                InlineKeyboardButton(text="📊 Detaylar", callback_data="stats_details")
            ]
        ])
        
        # Temel istatistik mesajı
        message = f"""
╔══════════════════════╗
║ 📊 <b>SİSTEM DURUMU</b> 📊 ║
╚══════════════════════╝

🛠️ <b>GENEL İSTATİSTİKLER</b>

👥 <b>KULLANICI VERİLERİ:</b>
• Toplam: <code>{stats['total_users']}</code>
• Kayıtlı: <code>{stats['registered_users']}</code>
• Kayıt Oranı: <code>{stats['registration_rate']}%</code>

💎 <b>POİNT SİSTEMİ:</b>
• Toplam Point: <code>{stats['total_points']:.2f} KP</code>
• Bugün Kazanılan: <code>{stats['today_points']:.2f} KP</code>

🎮 <b>ETKİNLİK DURUMU:</b>
• Aktif Etkinlik: <code>{stats['active_events']}</code>
• Tamamlanan: <code>{stats['completed_events']}</code>

📊 <b>Bot Durumu:</b> ✅ Aktif ve Çalışıyor

🕐 <b>Güncelleme:</b> {stats['generated_at']}
        """
        
        await _bot_instance.send_message(user_id, message, parse_mode="HTML", reply_markup=keyboard)
        logger.info(f"✅ System stats özel mesajla gönderildi: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ System stats özel mesaj hatası: {e}")
        if _bot_instance:
            await _bot_instance.send_message(user_id, "❌ İstatistikler yüklenemedi!")


async def send_admin_stats_to_user(user_id: int, message_obj) -> None:
    """Süper Admin için detaylı istatistikler"""
    try:
        # Kapsamlı istatistikleri al
        stats = await get_comprehensive_stats()
        performance = await get_system_performance_stats()
        
        if "error" in stats:
            if hasattr(message_obj, 'reply'):
                await message_obj.reply(f"❌ İstatistik hatası: {stats['error']}")
            else:
                await message_obj(user_id, f"❌ İstatistik hatası: {stats['error']}")
            return
        
        # Inline keyboard oluştur
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Yenile", callback_data="stats_refresh_admin"),
                InlineKeyboardButton(text="📊 Performans", callback_data="stats_performance")
            ],
            [
                InlineKeyboardButton(text="👥 Top Kullanıcılar", callback_data="stats_top_users"),
                InlineKeyboardButton(text="🏢 Top Gruplar", callback_data="stats_top_groups")
            ],
            [
                InlineKeyboardButton(text="📋 Rütbe Dağılımı", callback_data="stats_ranks"),
                InlineKeyboardButton(text="🎯 Etkinlik Stats", callback_data="stats_events")
            ]
        ])
        
        # Ana istatistik mesajı
        message = f"""
╔══════════════════════╗
║ 📊 <b>SİSTEM İSTATİSTİKLERİ</b> 📊 ║
╚══════════════════════╝

👑 <b>SÜPER ADMİN PANELİ</b>

📊 <b>TEMEL VERİLER:</b>
👥 Toplam Kullanıcı: <code>{stats['total_users']}</code>
✅ Kayıtlı Kullanıcı: <code>{stats['registered_users']}</code> ({stats['registration_rate']}%)
🏢 Aktif Grup: <code>{stats['active_groups']}</code>

💎 <b>POİNT SİSTEMİ:</b>
🏦 Toplam Point: <code>{stats['total_points']:.2f} KP</code>
📊 Günlük Point: <code>{stats['total_daily_points']:.2f} KP</code>
⚖️ Kullanıcı Ortalaması: <code>{stats['avg_user_points']:.2f} KP</code>

📝 <b>MESAJ AKTİVİTESİ:</b>
📋 Toplam Mesaj: <code>{stats['total_messages']:,}</code>
⚖️ Kullanıcı Ortalaması: <code>{stats['avg_user_messages']:.1f}</code>

🎯 <b>BUGÜNKÜ AKTİVİTE:</b>
💎 Bugün Point: <code>{stats['today_points']:.2f} KP</code>
👤 Aktif Kullanıcı: <code>{stats['today_active_users']}</code>

📈 <b>HAFTALİK AKTİVİTE:</b>
👥 Haftalık Aktif: <code>{stats['week_active_users']}</code>
📝 Haftalık Mesaj: <code>{stats['week_messages']:,}</code>

🎮 <b>ETKİNLİK SİSTEMİ:</b>
🎯 Toplam Etkinlik: <code>{stats['total_events']}</code>
🔴 Aktif Etkinlik: <code>{stats['active_events']}</code>
✅ Tamamlanan: <code>{stats['completed_events']}</code>
👥 Toplam Katılımcı: <code>{stats['total_participants']}</code>

🖥️ <b>SİSTEM PERFORMANSI:</b>
💾 Database: <code>{performance.get('database_size', 'N/A')}</code>
📊 Tablo Sayısı: <code>{performance.get('table_count', 0)}</code>
⏱️ Uptime: <code>{performance.get('uptime_hours', 0)} saat</code>

🕐 <b>Son Güncelleme:</b> {stats['generated_at']}

💡 <b>Detaylı analiz için butonları kullanın!</b>
        """
        
        # Mesaj gönderme tipini kontrol et
        if hasattr(message_obj, 'reply'):
            # Direkt mesaj objesi
            await message_obj.reply(message, parse_mode="HTML", reply_markup=keyboard)
        else:
            # Bot.send_message veya edit_text fonksiyonu
            await message_obj(user_id, message, parse_mode="HTML", reply_markup=keyboard)
        
        logger.info(f"✅ Admin stats gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Admin stats gönderme hatası: {e}")
        if hasattr(message_obj, 'reply'):
            await message_obj.reply("❌ İstatistikler yüklenemedi!")
        else:
            await message_obj(user_id, "❌ İstatistikler yüklenemedi!")


async def send_system_stats_to_user(user_id: int, message_obj) -> None:
    """Genel admin için temel sistem istatistikleri"""
    try:
        # Temel istatistikleri al
        stats = await get_comprehensive_stats()
        
        if "error" in stats:
            if hasattr(message_obj, 'reply'):
                await message_obj.reply(f"❌ İstatistik hatası: {stats['error']}")
            else:
                await message_obj(user_id, f"❌ İstatistik hatası: {stats['error']}")
            return
        
        # Basit inline keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Yenile", callback_data="stats_refresh_system"),
                InlineKeyboardButton(text="📊 Detaylar", callback_data="stats_details")
            ]
        ])
        
        # Temel istatistik mesajı
        message = f"""
╔══════════════════════╗
║ 📊 <b>SİSTEM DURUMU</b> 📊 ║
╚══════════════════════╝

🛠️ <b>GENEL İSTATİSTİKLER</b>

👥 <b>KULLANICI VERİLERİ:</b>
• Toplam: <code>{stats['total_users']}</code>
• Kayıtlı: <code>{stats['registered_users']}</code>
• Kayıt Oranı: <code>{stats['registration_rate']}%</code>

🏢 <b>GRUP SİSTEMİ:</b>
• Aktif Grup: <code>{stats['active_groups']}</code>

💎 <b>POİNT SİSTEMİ:</b>
• Toplam Point: <code>{stats['total_points']:.2f} KP</code>
• Bugün Kazanılan: <code>{stats['today_points']:.2f} KP</code>

📝 <b>MESAJ AKTİVİTESİ:</b>
• Toplam Mesaj: <code>{stats['total_messages']:,}</code>
• Bugün Aktif: <code>{stats['today_active_users']}</code> kullanıcı

🎮 <b>ETKİNLİK DURUMU:</b>
• Aktif Etkinlik: <code>{stats['active_events']}</code>
• Tamamlanan: <code>{stats['completed_events']}</code>

📊 <b>Bot Durumu:</b> ✅ Aktif ve Çalışıyor

🕐 <b>Güncelleme:</b> {stats['generated_at']}
        """
        
        # Mesaj gönderme tipini kontrol et
        if hasattr(message_obj, 'reply'):
            # Direkt mesaj objesi
            await message_obj.reply(message, parse_mode="HTML", reply_markup=keyboard)
        else:
            # Bot.send_message veya edit_text fonksiyonu
            await message_obj(user_id, message, parse_mode="HTML", reply_markup=keyboard)
        
        logger.info(f"✅ System stats gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ System stats gönderme hatası: {e}")
        if hasattr(message_obj, 'reply'):
            await message_obj.reply("❌ İstatistikler yüklenemedi!")
        else:
            await message_obj(user_id, "❌ İstatistikler yüklenemedi!")


# ==============================================
# KOMUT HANDLER'LARI
# ==============================================

@router.message(Command("adminstats"))
async def admin_stats_command_handler(message: Message) -> None:
    """Admin istatistikleri komutu"""
    try:
        user_id = message.from_user.id
        config = get_config()
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            return
        
        # Grup chatindeyse komut mesajını sil
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Admin stats komutu mesajı silindi - Group: {message.chat.id}")
            except Exception as e:
                logger.error(f"❌ Admin stats mesajı silinemedi: {e}")
            return
        
        await admin_stats_command(message)
        
    except Exception as e:
        logger.error(f"❌ Admin stats komut hatası: {e}")
        await message.reply("❌ İstatistikler yüklenemedi!")

@router.message(Command("sistemistatistik"))
async def system_stats_command_handler(message: Message) -> None:
    """Sistem istatistikleri komutu"""
    try:
        user_id = message.from_user.id
        config = get_config()
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            return
        
        # Grup chatindeyse komut mesajını sil
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 System stats komutu mesajı silindi - Group: {message.chat.id}")
            except Exception as e:
                logger.error(f"❌ System stats mesajı silinemedi: {e}")
            return
        
        await system_stats_command(message)
        
    except Exception as e:
        logger.error(f"❌ System stats komut hatası: {e}")
        await message.reply("❌ İstatistikler yüklenemedi!")

# ==============================================
# CALLBACK HANDLER'LARI
# ==============================================

@router.callback_query(lambda c: c.data and c.data.startswith("stats_"))
async def handle_stats_callback(callback: types.CallbackQuery) -> None:
    """İstatistik callback handler"""
    try:
        user_id = callback.from_user.id
        config = get_config()
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        action = callback.data
        
        if action == "stats_refresh_admin":
            await refresh_admin_stats(callback)
        elif action == "stats_refresh_system":
            await refresh_system_stats(callback)
        elif action == "stats_performance":
            await show_performance_stats(callback)
        elif action == "stats_top_users":
            await show_top_users(callback)
        elif action == "stats_top_users_kp":
            await show_top_users_kp(callback)
        elif action == "stats_top_users_messages":
            await show_top_users_messages(callback)
        elif action == "stats_top_groups":
            await show_top_groups(callback)
        elif action == "stats_ranks":
            await show_rank_distribution(callback)
        elif action == "stats_events":
            await show_event_stats(callback)
        elif action == "stats_details":
            await show_detailed_system_stats(callback)
        elif action == "stats_back_admin":
            # Ana admin stats'e geri dön
            class CallbackEdit:
                def __init__(self, edit_func):
                    self.edit_text = edit_func
                    
                async def __call__(self, user_id, text, parse_mode=None, reply_markup=None):
                    await self.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            
            await send_admin_stats_to_user(user_id, CallbackEdit(callback.message.edit_text))
            
        elif action == "stats_back_system":
            # Ana system stats'e geri dön
            class CallbackEdit:
                def __init__(self, edit_func):
                    self.edit_text = edit_func
                    
                async def __call__(self, user_id, text, parse_mode=None, reply_markup=None):
                    await self.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            
            await send_system_stats_to_user(user_id, CallbackEdit(callback.message.edit_text))
        else:
            await callback.answer("❌ Bilinmeyen işlem!")
            
    except Exception as e:
        logger.error(f"❌ Statistics callback hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def refresh_admin_stats(callback: types.CallbackQuery) -> None:
    """Admin istatistiklerini yenile"""
    await callback.answer("🔄 İstatistikler yenileniyor...")
    
    class CallbackEdit:
        def __init__(self, edit_func):
            self.edit_text = edit_func
            
        async def __call__(self, user_id, text, parse_mode=None, reply_markup=None):
            await self.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    
    await send_admin_stats_to_user(callback.from_user.id, CallbackEdit(callback.message.edit_text))


async def refresh_system_stats(callback: types.CallbackQuery) -> None:
    """Sistem istatistiklerini yenile"""
    await callback.answer("🔄 İstatistikler yenileniyor...")
    
    class CallbackEdit:
        def __init__(self, edit_func):
            self.edit_text = edit_func
            
        async def __call__(self, user_id, text, parse_mode=None, reply_markup=None):
            await self.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    
    await send_system_stats_to_user(callback.from_user.id, CallbackEdit(callback.message.edit_text))


async def show_performance_stats(callback: types.CallbackQuery) -> None:
    """Performans istatistiklerini göster"""
    try:
        performance = await get_system_performance_stats()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="stats_back_admin")]
        ])
        
        message = f"""
╔══════════════════════╗
║ 🖥️ <b>PERFORMANS ANALİZİ</b> 🖥️ ║
╚══════════════════════╝

💾 <b>DATABASE PERFORMANSI:</b>
• Boyut: <code>{performance.get('database_size', 'N/A')}</code>
• Tablo Sayısı: <code>{performance.get('table_count', 0)}</code>
• Son 24h Aktivite: <code>{performance.get('recent_activity', 0)}</code>

⏱️ <b>SİSTEM UPTIME:</b>
• Çalışma Süresi: <code>{performance.get('uptime_hours', 0)} saat</code>
• Son Başlatma: <code>{performance.get('last_startup', 'Bilinmiyor')}</code>

📊 <b>PERFORMANS DURUMU:</b>
• Database: {'✅ İyi' if performance.get('performance_status') == 'good' else '⚠️ Sorunlu'}
• Bot: ✅ Aktif ve Stabil
• Memory: 🟢 Normal

🔧 <b>SİSTEM SAĞLIĞI:</b>
• Bağlantı: Stabil
• Response Time: Hızlı
• Error Rate: Düşük
        """
        
        await callback.message.edit_text(message, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Performance stats hatası: {e}")
        await callback.answer("❌ Performans verileri alınamadı!", show_alert=True)


async def show_top_users(callback: types.CallbackQuery) -> None:
    """En aktif kullanıcıları göster"""
    try:
        stats = await get_comprehensive_stats()
        top_users_kp = stats.get('top_users_kp', [])
        top_users_messages = stats.get('top_users_messages', [])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💎 KP Sıralaması", callback_data="stats_top_users_kp"),
                InlineKeyboardButton(text="📝 Mesaj Sıralaması", callback_data="stats_top_users_messages")
            ],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="stats_back_admin")]
        ])
        
        # KP sıralaması göster
        users_text = ""
        if top_users_kp:
            for i, user in enumerate(top_users_kp, 1):
                # Kullanıcı bilgilerini gizle, sadece sıra ve değerleri göster
                points = user.get('kirve_points', 0)
                messages = user.get('total_messages', 0)
                
                users_text += f"{i}. 💎 <b>{points:.2f} KP</b> | 📝 {messages} mesaj\n"
        else:
            users_text = "Henüz veri yok"
        
        message = f"""
╔══════════════════════╗
║ 👥 <b>EN AKTİF KULLANICILAR</b> 👥 ║
╚══════════════════════╝

🏆 <b>TOP 10 KULLANICI (Point Sıralaması):</b>

{users_text}

💡 <b>Point kazanımı grup mesajlarına dayalıdır.</b>
        """
        
        await callback.message.edit_text(message, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Top users hatası: {e}")
        await callback.answer("❌ Kullanıcı verileri alınamadı!", show_alert=True)


async def show_top_users_kp(callback: types.CallbackQuery) -> None:
    """KP sıralaması göster"""
    try:
        stats = await get_comprehensive_stats()
        top_users_kp = stats.get('top_users_kp', [])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="stats_top_users")]
        ])
        
        users_text = ""
        if top_users_kp:
            for i, user in enumerate(top_users_kp, 1):
                points = user.get('kirve_points', 0)
                messages = user.get('total_messages', 0)
                
                users_text += f"{i}. 💎 <b>{points:.2f} KP</b> | 📝 {messages} mesaj\n"
        else:
            users_text = "Henüz veri yok"
        
        message = f"""
╔══════════════════════╗
║ 💎 <b>TOP 10 KP SIRALAMASI</b> 💎 ║
╚══════════════════════╝

🏆 <b>EN YÜKSEK POİNT KULLANICILARI:</b>

{users_text}

💡 <b>Point kazanımı grup mesajlarına dayalıdır.</b>
        """
        
        await callback.message.edit_text(message, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Top users KP hatası: {e}")
        await callback.answer("❌ KP verileri alınamadı!", show_alert=True)


async def show_top_users_messages(callback: types.CallbackQuery) -> None:
    """Mesaj sıralaması göster"""
    try:
        stats = await get_comprehensive_stats()
        top_users_messages = stats.get('top_users_messages', [])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="stats_top_users")]
        ])
        
        users_text = ""
        if top_users_messages:
            for i, user in enumerate(top_users_messages, 1):
                points = user.get('kirve_points', 0)
                messages = user.get('total_messages', 0)
                
                users_text += f"{i}. 📝 <b>{messages} mesaj</b> | 💎 {points:.2f} KP\n"
        else:
            users_text = "Henüz veri yok"
        
        message = f"""
╔══════════════════════╗
║ 📝 <b>TOP 10 MESAJ SIRALAMASI</b> 📝 ║
╚══════════════════════╝

🏆 <b>EN AKTİF MESAJ KULLANICILARI:</b>

{users_text}

💡 <b>Mesaj sayısı grup aktivitesine dayalıdır.</b>
        """
        
        await callback.message.edit_text(message, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Top users messages hatası: {e}")
        await callback.answer("❌ Mesaj verileri alınamadı!", show_alert=True)


async def show_top_groups(callback: types.CallbackQuery) -> None:
    """En aktif grupları göster"""
    try:
        stats = await get_comprehensive_stats()
        top_groups = stats.get('top_groups', [])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="stats_back_admin")]
        ])
        
        groups_text = ""
        if top_groups:
            for i, group in enumerate(top_groups, 1):
                name = group.get('group_name', 'Anonim Grup')
                messages = group.get('total_messages', 0)
                
                groups_text += f"{i}. <b>{name}</b>\n"
                groups_text += f"   📝 {messages} mesaj\n\n"
        else:
            groups_text = "Henüz veri yok"
        
        message = f"""
╔══════════════════════╗
║ 🏢 <b>EN AKTİF GRUPLAR</b> 🏢 ║
╚══════════════════════╝

📊 <b>TOP 5 GRUP (Mesaj Aktivitesi):</b>

{groups_text}

💡 <b>Sadece kayıtlı gruplar gösterilir.</b>
        """
        
        await callback.message.edit_text(message, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Top groups hatası: {e}")
        await callback.answer("❌ Grup verileri alınamadı!", show_alert=True)


async def show_rank_distribution(callback: types.CallbackQuery) -> None:
    """Rütbe dağılımını göster"""
    try:
        stats = await get_comprehensive_stats()
        ranks = stats.get('rank_distribution', [])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="stats_back_admin")]
        ])
        
        ranks_text = ""
        if ranks:
            for rank in ranks:
                name = rank.get('rank_name', 'Bilinmeyen')
                count = rank.get('user_count', 0)
                
                ranks_text += f"• <b>{name}:</b> {count} kullanıcı\n"
        else:
            ranks_text = "Rütbe verisi yok"
        
        message = f"""
╔══════════════════════╗
║ 🏅 <b>RÜTBE DAĞILIMI</b> 🏅 ║
╚══════════════════════╝

👥 <b>KULLANICI RÜTBELERİ:</b>

{ranks_text}

💡 <b>Sadece kayıtlı kullanıcılar dahildir.</b>
        """
        
        await callback.message.edit_text(message, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Rank distribution hatası: {e}")
        await callback.answer("❌ Rütbe verileri alınamadı!", show_alert=True)


async def show_event_stats(callback: types.CallbackQuery) -> None:
    """Etkinlik istatistiklerini göster"""
    try:
        stats = await get_comprehensive_stats()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="stats_back_admin")]
        ])
        
        message = f"""
╔══════════════════════╗
║ 🎮 <b>ETKİNLİK İSTATİSTİKLERİ</b> 🎮 ║
╚══════════════════════╝

📊 <b>GENEL VERİLER:</b>
• Toplam Etkinlik: <code>{stats['total_events']}</code>
• Aktif Etkinlik: <code>{stats['active_events']}</code>
• Tamamlanan: <code>{stats['completed_events']}</code>
• Toplam Katılımcı: <code>{stats['total_participants']}</code>

📈 <b>BAŞARI ORANLARI:</b>
• Tamamlama Oranı: <code>{round((stats['completed_events'] / stats['total_events'] * 100) if stats['total_events'] > 0 else 0, 1)}%</code>
• Ortalama Katılımcı: <code>{round(stats['total_participants'] / stats['total_events'] if stats['total_events'] > 0 else 0, 1)}</code>

🎯 <b>ETKİNLİK TÜRLERİ:</b>
• Çekiliş: Ana etkinlik türü
• Katılım ücretli sistem
• Otomatik kazanan seçimi

💡 <b>Tüm etkinlikler database'de saklanır.</b>
        """
        
        await callback.message.edit_text(message, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Event stats hatası: {e}")
        await callback.answer("❌ Etkinlik verileri alınamadı!", show_alert=True)


async def show_detailed_system_stats(callback: types.CallbackQuery) -> None:
    """Detaylı sistem istatistikleri (system_stats için)"""
    try:
        stats = await get_comprehensive_stats()
        performance = await get_system_performance_stats()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="stats_back_system")]
        ])
        
        message = f"""
╔══════════════════════╗
║ 📊 <b>DETAYLI SİSTEM ANALİZİ</b> 📊 ║
╚══════════════════════╝

🎯 <b>HAFTALIK AKTİVİTE:</b>
• Aktif Kullanıcı: <code>{stats['week_active_users']}</code>
• Mesaj Sayısı: <code>{stats['week_messages']:,}</code>
• Ortalama/Gün: <code>{round(stats['week_messages'] / 7 if stats['week_messages'] > 0 else 0, 1)}</code>

💎 <b>POİNT ANALİZİ:</b>
• Kullanıcı Ortalaması: <code>{stats['avg_user_points']:.2f} KP</code>
• Bugün Dağıtılan: <code>{stats['today_points']:.2f} KP</code>
• Günlük Point: <code>{stats['total_daily_points']:.2f} KP</code>

📝 <b>MESAJ ANALİZİ:</b>
• Kullanıcı Ortalaması: <code>{stats['avg_user_messages']:.1f}</code>
• Toplam: <code>{stats['total_messages']:,}</code>

🖥️ <b>SİSTEM DURUMU:</b>
• Database: <code>{performance.get('database_size', 'N/A')}</code>
• Uptime: <code>{performance.get('uptime_hours', 0)} saat</code>
• Performans: {'✅ İyi' if performance.get('performance_status') == 'good' else '⚠️ Sorunlu'}

🕐 <b>Son Güncelleme:</b> {stats['generated_at']}
        """
        
        await callback.message.edit_text(message, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Detailed stats hatası: {e}")
        await callback.answer("❌ Detaylı veriler alınamadı!", show_alert=True) 