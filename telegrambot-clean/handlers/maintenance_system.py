"""
🔧 Bakım Modu Sistemi - KirveHub Bot
/bakim ve /bakimbitis komutları
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from aiogram import Router, Bot
from aiogram.types import Message
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

# Bakım modu durumu (RAM'de tutulur, restart'ta sıfırlanır)
_maintenance_mode = False

def is_maintenance_mode() -> bool:
    """Bakım modu aktif mi?"""
    return _maintenance_mode

def set_maintenance_mode(value: bool):
    """Bakım modunu set et"""
    global _maintenance_mode
    _maintenance_mode = value

async def send_maintenance_notification_to_all() -> dict:
    """Tüm kayıtlı üyelere bakım bildirimi gönder"""
    try:
        if not _bot_instance:
            logger.error("❌ Bot instance yok!")
            return {"success": False, "error": "Bot instance yok"}
        
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database bağlantısı yok!")
            return {"success": False, "error": "Database bağlantısı yok"}
        
        logger.info("🔔 Bakım modu bildirimi başlatılıyor...")
        
        # Tüm kayıtlı kullanıcıları al
        async with pool.acquire() as conn:
            users = await conn.fetch("""
                SELECT user_id, first_name, username 
                FROM users 
                WHERE is_registered = TRUE
                ORDER BY last_activity DESC
            """)
        
        if not users:
            logger.info("📭 Bildirim gönderilecek kullanıcı bulunamadı")
            return {"success": True, "sent": 0, "failed": 0}
        
        maintenance_message = f"""
⚠️ <b>BAKIM MODU AKTİF</b> ⚠️

👋 <b>Merhaba değerli KirveHub üyesi!</b>

🛠️ <b>Bot şu anda bakım için geçici olarak durdurulmuştur.</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>BAKIM SIRASINDA:</b>
🚫 Komutlar devre dışı
⏸️ Point kazanımı durdu
🔄 Sistem güncelleniyor

🛡️ <b>VERİLERİNİZ GÜVENDE:</b>
✅ Point'leriniz korunuyor
✅ Hiçbir veri kaybı yok

🕐 <b>Bakım Başlangıç:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}

🔔 <b>Bot tekrar aktif olduğunda bildirim alacaksınız!</b>

💫 <i>KirveHub Ekibi</i> 🚀
        """
        
        success_count = 0
        failed_count = 0
        
        logger.info(f"📬 {len(users)} kullanıcıya bakım bildirimi gönderiliyor...")
        
        for user in users:
            try:
                await _bot_instance.send_message(
                    chat_id=user['user_id'],
                    text=maintenance_message,
                    parse_mode="HTML"
                )
                success_count += 1
                
                # Rate limiting için kısa bekle
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                logger.debug(f"❌ Bildirim gönderilemedi - User: {user['user_id']} - Hata: {e}")
        
        logger.info(f"✅ Bakım bildirimi tamamlandı - Başarılı: {success_count}, Başarısız: {failed_count}")
        
        # Bakım modunu database'e kaydet
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO bot_status (status) 
                VALUES ($1)
            """, f"🛠️ BAKIM MODU - {datetime.now().strftime('%d.%m.%Y %H:%M')} - {success_count} kullanıcıya bildirim gönderildi")
        
        return {"success": True, "sent": success_count, "failed": failed_count}
        
    except Exception as e:
        logger.error(f"❌ Bakım bildirimi hatası: {e}")
        return {"success": False, "error": str(e)}

async def send_maintenance_end_notification() -> dict:
    """Bakım modu bittiğinde tüm kayıtlı üyelere bildirim gönder"""
    try:
        if not _bot_instance:
            logger.error("❌ Bot instance yok!")
            return {"success": False, "error": "Bot instance yok"}
        
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database bağlantısı yok!")
            return {"success": False, "error": "Database bağlantısı yok"}
        
        logger.info("🔔 Bakım bitiş bildirimi başlatılıyor...")
        
        # Tüm kayıtlı kullanıcıları al
        async with pool.acquire() as conn:
            users = await conn.fetch("""
                SELECT user_id, first_name, username 
                FROM users 
                WHERE is_registered = TRUE
                ORDER BY last_activity DESC
            """)
        
        if not users:
            logger.info("📭 Bildirim gönderilecek kullanıcı bulunamadı")
            return {"success": True, "sent": 0, "failed": 0}
        
        end_message = f"""
✅ <b>BAKIM MODU BİTTİ!</b> ✅

👋 <b>Merhaba değerli KirveHub üyesi!</b>

🎉 <b>Bot tekrar aktif hale geldi!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ <b>ARTIK KULLANABİLİRSİNİZ:</b>
✅ Tüm komutlar aktif
✅ Point kazanımı başladı
✅ Sistem güncellendi

🕐 <b>Bakım Bitiş:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}

🎮 <b>Keyifli kullanımlar dileriz!</b>

💫 <i>KirveHub Ekibi</i> 🚀
        """
        
        success_count = 0
        failed_count = 0
        
        logger.info(f"📬 {len(users)} kullanıcıya bakım bitiş bildirimi gönderiliyor...")
        
        for user in users:
            try:
                await _bot_instance.send_message(
                    chat_id=user['user_id'],
                    text=end_message,
                    parse_mode="HTML"
                )
                success_count += 1
                
                # Rate limiting için kısa bekle
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                logger.debug(f"❌ Bildirim gönderilemedi - User: {user['user_id']} - Hata: {e}")
        
        logger.info(f"✅ Bakım bitiş bildirimi tamamlandı - Başarılı: {success_count}, Başarısız: {failed_count}")
        
        # Bakım bitiş durumunu database'e kaydet
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO bot_status (status) 
                VALUES ($1)
            """, f"✅ BAKIM MODU BİTTİ - {datetime.now().strftime('%d.%m.%Y %H:%M')} - {success_count} kullanıcıya bildirim gönderildi")
        
        return {"success": True, "sent": success_count, "failed": failed_count}
        
    except Exception as e:
        logger.error(f"❌ Bakım bitiş bildirimi hatası: {e}")
        return {"success": False, "error": str(e)}

@router.message(Command("bakim"))
async def maintenance_start_command(message: Message):
    """Bakım modunu başlat - Sadece admin"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not is_admin(user_id):
            await message.reply("❌ Bu komutu kullanmak için admin yetkisine sahip olmalısınız!")
            return
        
        # Sadece özel mesajda çalış
        if message.chat.type != "private":
            await message.reply("⚠️ Bu komut sadece özel mesajda kullanılabilir!")
            return
        
        # Bakım modu zaten aktif mi?
        if is_maintenance_mode():
            await message.reply("⚠️ Bakım modu zaten aktif!")
            return
        
        # Bakım modunu aktif et
        set_maintenance_mode(True)
        logger.info(f"🔧 Bakım modu başlatıldı - Admin: {user_id}")
        
        # Bildirim gönder
        await message.reply("🔔 Tüm kayıtlı üyelere bakım bildirimi gönderiliyor...")
        result = await send_maintenance_notification_to_all()
        
        if result.get("success"):
            await message.reply(f"""
✅ <b>BAKIM MODU AKTİF</b>

📊 <b>Bildirim Sonuçları:</b>
✅ Başarılı: {result.get('sent', 0)} kullanıcı
❌ Başarısız: {result.get('failed', 0)} kullanıcı

🛠️ <b>Bakım modu aktif!</b>
• Komutlar devre dışı
• Point kazanımı durdu

🔔 <b>Bakım modunu bitirmek için:</b> /bakimbitis
            """, parse_mode="HTML")
        else:
            await message.reply(f"❌ Bakım bildirimi gönderilirken hata oluştu: {result.get('error', 'Bilinmeyen hata')}")
        
    except Exception as e:
        logger.error(f"❌ Bakım başlatma komutu hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

@router.message(Command("bakimbitis"))
async def maintenance_end_command(message: Message):
    """Bakım modunu bitir - Sadece admin"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not is_admin(user_id):
            await message.reply("❌ Bu komutu kullanmak için admin yetkisine sahip olmalısınız!")
            return
        
        # Sadece özel mesajda çalış
        if message.chat.type != "private":
            await message.reply("⚠️ Bu komut sadece özel mesajda kullanılabilir!")
            return
        
        # Bakım modu aktif mi?
        if not is_maintenance_mode():
            await message.reply("⚠️ Bakım modu zaten kapalı!")
            return
        
        # Bakım modunu kapat
        set_maintenance_mode(False)
        logger.info(f"✅ Bakım modu bitirildi - Admin: {user_id}")
        
        # Bildirim gönder
        await message.reply("🔔 Tüm kayıtlı üyelere bakım bitiş bildirimi gönderiliyor...")
        result = await send_maintenance_end_notification()
        
        if result.get("success"):
            await message.reply(f"""
✅ <b>BAKIM MODU BİTTİ</b>

📊 <b>Bildirim Sonuçları:</b>
✅ Başarılı: {result.get('sent', 0)} kullanıcı
❌ Başarısız: {result.get('failed', 0)} kullanıcı

🎉 <b>Bot tekrar aktif!</b>
• Tüm komutlar aktif
• Point kazanımı başladı
            """, parse_mode="HTML")
        else:
            await message.reply(f"❌ Bakım bitiş bildirimi gönderilirken hata oluştu: {result.get('error', 'Bilinmeyen hata')}")
        
    except Exception as e:
        logger.error(f"❌ Bakım bitiş komutu hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")



