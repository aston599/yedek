"""
🔔 Sistem Bildirimleri Modülü
Bot startup/shutdown durumunda kullanıcı bildirimleri
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from aiogram import Bot

from database import db_pool
import database
from config import get_config

logger = logging.getLogger(__name__)


async def send_maintenance_notification() -> None:
    """
    Bot kapanırken tüm aktif üyelere bakım modu bildirimi gönder
    """
    try:
        # Database pool'u dinamik olarak al
        current_db_pool = database.db_pool
        if not current_db_pool:
            logger.warning("⚠️ Database bağlantısı yok - bildirim gönderilemedi")
            return
            
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        
        logger.info("🔔 Bakım modu bildirimi başlatılıyor...")
        
        # Tüm kayıtlı kullanıcıları al (son 90 gün aktif)
        async with current_db_pool.acquire() as conn:
            users = await conn.fetch("""
                SELECT user_id, first_name, username, last_activity 
                FROM users 
                WHERE is_registered = TRUE 
                  AND last_activity >= NOW() - INTERVAL '90 days'
                ORDER BY last_activity DESC
            """)
        
        if not users:
            logger.info("📭 Bildirim gönderilecek aktif kullanıcı bulunamadı")
            await bot.session.close()
            return
        
        maintenance_message = f"""
⚠️ **BAKIM MODU AKTİF** ⚠️

👋 **Merhaba değerli KirveHub üyesi!**

🛠️ **Bot şu anda bakım için geçici olarak durdurulmuştur.**

━━━━━━

⚠️ **BAKIM SIRASINDA:**
🚫 Komutlar devre dışı
⏸️ Point kazanımı durdu
🔄 Sistem güncelleniyor

🛡️ **VERİLERİNİZ GÜVENDE:**
✅ Point'leriniz korunuyor
✅ Hiçbir veri kaybı yok

🕐 **Bakım Başlangıç:** `{datetime.now().strftime('%d.%m.%Y %H:%M')}`

🔔 **Bot tekrar aktif olduğunda bildirim alacaksınız!**

💫 _KirveHub Ekibi_ 🚀
        """
        
        success_count = 0
        failed_count = 0
        
        logger.info(f"📬 {len(users)} kullanıcıya bakım bildirimi gönderiliyor...")
        
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user['user_id'],
                    text=maintenance_message,
                    parse_mode="Markdown"
                )
                success_count += 1
                
                # Rate limiting için kısa bekle
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                logger.debug(f"❌ Bildirim gönderilemedi - User: {user['user_id']} - Hata: {e}")
        
        await bot.session.close()
        
        logger.info(f"✅ Bakım bildirimi tamamlandı - Başarılı: {success_count}, Başarısız: {failed_count}")
        
        # Bakım modunu database'e kaydet
        if current_db_pool:
            async with current_db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO bot_status (status) 
                    VALUES ('🛠️ BAKIM MODU - Bot kapatıldı, kullanıcılara bildirim gönderildi')
                """)
        
    except Exception as e:
        logger.error(f"❌ Bakım bildirimi hatası: {e}")


async def send_startup_notification() -> None:
    """
    Bot açılırken sadece adminlere bildirim gönder
    """
    try:
        # Database pool'u dinamik olarak al
        current_db_pool = database.db_pool
        if not current_db_pool:
            logger.warning("⚠️ Database bağlantısı yok - bildirim gönderilemedi")
            return
            
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        
        logger.info("🔔 Admin startup bildirimi başlatılıyor...")
        
        # Sadece admin kullanıcıları al
        async with current_db_pool.acquire() as conn:
            admins = await conn.fetch("""
                SELECT user_id, first_name, username, last_activity 
                FROM users 
                WHERE is_registered = TRUE 
                  AND (user_id = $1 OR is_admin = TRUE)
                  AND last_activity >= NOW() - INTERVAL '90 days'
                ORDER BY last_activity DESC
            """, config.ADMIN_USER_ID)
        
        if not admins:
            logger.info("📭 Bildirim gönderilecek admin bulunamadı")
            await bot.session.close()
            return
        
        startup_message = f"""
🎊 **BOT YENİDEN AKTİF!** 🎊

🌟 **Hoş geldiniz değerli Admin!**

🚀 **Bot başarıyla yeniden başlatıldı!**

━━━━━━

✅ **SİSTEM DURUMU:**
🤖 Bot: Çevrimiçi ve hazır
💎 Point: Aktif ve kayıt ediyor
🎯 Etkinlikler: Katılıma açık
📊 Log Sistemi: Aktif ve çalışıyor

⏰ **Aktif Olma:** `{datetime.now().strftime('%d.%m.%Y %H:%M')}`

🎮 **Keyifli kullanımlar dileriz!** 
💫 _KirveHub Ekibi_ 🚀
        """
        
        success_count = 0
        failed_count = 0
        
        logger.info(f"📬 {len(admins)} admin'e startup bildirimi gönderiliyor...")
        
        for admin in admins:
            try:
                await bot.send_message(
                    chat_id=admin['user_id'],
                    text=startup_message,
                    parse_mode="Markdown"
                )
                success_count += 1
                
                # Rate limiting için kısa bekle
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                logger.debug(f"❌ Admin bildirimi gönderilemedi - User: {admin['user_id']} - Hata: {e}")
        
        await bot.session.close()
        
        logger.info(f"✅ Admin startup bildirimi tamamlandı - Başarılı: {success_count}, Başarısız: {failed_count}")
        
        # Startup durumunu database'e kaydet
        if current_db_pool:
            async with current_db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO bot_status (status) 
                    VALUES ('🚀 AKTİF - Bot başlatıldı, adminlere bildirim gönderildi')
                """)
        
    except Exception as e:
        logger.error(f"❌ Admin startup bildirimi hatası: {e}")


async def send_emergency_broadcast(message: str, admin_id: int) -> None:
    """
    Acil durum toplu duyuru sistemi
    """
    try:
        current_db_pool = database.db_pool
        if not current_db_pool:
            logger.warning("⚠️ Database bağlantısı yok - duyuru gönderilemedi")
            return
            
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        
        logger.info("📢 Acil durum duyurusu başlatılıyor...")
        
        # Tüm kayıtlı kullanıcıları al
        async with current_db_pool.acquire() as conn:
            users = await conn.fetch("""
                SELECT user_id, first_name, username 
                FROM users 
                WHERE is_registered = TRUE 
                ORDER BY last_activity DESC
            """)
        
        if not users:
            logger.info("📭 Duyuru gönderilecek kullanıcı bulunamadı")
            await bot.session.close()
            return
        
        emergency_message = f"""
🚨 **ACİL DUYURU** 🚨

{message}

📅 **Duyuru Zamanı:** `{datetime.now().strftime('%d.%m.%Y %H:%M')}`

💬 _KirveHub Yönetimi_ 🚀
        """
        
        success_count = 0
        failed_count = 0
        
        logger.info(f"📬 {len(users)} kullanıcıya acil duyuru gönderiliyor...")
        
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user['user_id'],
                    text=emergency_message,
                    parse_mode="Markdown"
                )
                success_count += 1
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                logger.debug(f"❌ Duyuru gönderilemedi - User: {user['user_id']} - Hata: {e}")
        
        await bot.session.close()
        
        logger.info(f"✅ Acil duyuru tamamlandı - Başarılı: {success_count}, Başarısız: {failed_count}")
        
        # Duyuru durumunu database'e kaydet
        if current_db_pool:
            async with current_db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO bot_status (status) 
                    VALUES ($1)
                """, f"📢 ACİL DUYURU - Admin {admin_id} tarafından toplu duyuru gönderildi")
        
    except Exception as e:
        logger.error(f"❌ Acil duyuru hatası: {e}")


async def get_notification_stats() -> Dict[str, Any]:
    """
    Bildirim istatistiklerini al (admin paneli için)
    """
    try:
        # Database pool'u dinamik olarak al
        current_db_pool = database.db_pool
        if not current_db_pool:
            return {}
            
        async with current_db_pool.acquire() as conn:
            # Aktif kullanıcı sayıları
            total_registered = await conn.fetchval("""
                SELECT COUNT(*) FROM users WHERE is_registered = TRUE
            """)
            
            active_30d = await conn.fetchval("""
                SELECT COUNT(*) FROM users 
                WHERE is_registered = TRUE 
                  AND last_activity >= NOW() - INTERVAL '30 days'
            """)
            
            active_7d = await conn.fetchval("""
                SELECT COUNT(*) FROM users 
                WHERE is_registered = TRUE 
                  AND last_activity >= NOW() - INTERVAL '7 days'
            """)
            
            # Son bot status
            last_status = await conn.fetchval("""
                SELECT status FROM bot_status 
                ORDER BY created_at DESC LIMIT 1
            """)
            
            return {
                "total_registered": total_registered or 0,
                "active_30_days": active_30d or 0,
                "active_7_days": active_7d or 0,
                "last_bot_status": last_status,
                "notification_ready": True
            }
            
    except Exception as e:
        logger.error(f"❌ Notification stats hatası: {e}")
        return {"notification_ready": False, "error": str(e)} 