"""
🎯 Kayıt Teşvik Sistemi - KirveHub Bot
Sadece özel mesajda kayıt teşvik mesajları
"""

import logging
import asyncio
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Set
from aiogram import Bot, types, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from database import is_user_registered, save_user_info, get_db_pool
from config import get_config

logger = logging.getLogger(__name__)

# Router tanımla
router = Router()

# Teşvik sistemi ayarları
recruitment_system_active = True  # Production'da açık
recruitment_interval = 60  # 1 dakika (saniye) - daha esnek
recruitment_message_cooldown = 60  # 1 dakika (saniye) - daha esnek
last_recruitment_time = 0
last_recruited_user = None

# Eksik değişkenleri tanımla
user_recruitment_times: Dict[int, datetime] = {}
last_recruitment_users: Set[int] = set()

# Özel mesaj şablonları (sadece özel mesajda gönderilir)
RECRUITMENT_MESSAGES = [
    "🎯 **Kirvem!** Hala gruba kayıt olmadığını görüyorum. Bana özelden yaz, tüm bonusları anlatayım! 💎",
    "💎 **Kirve!** Kayıt olarak çok daha fazlasını kazanabilirsin. Özelden yaz, detayları vereyim! 🚀",
    "🎮 **Kirvem!** Sistemde kayıtlı değilsin. Özelden yaz, Kirve Point sistemini anlatayım! 💎",
    "💎 **Kirve!** Hala kayıtsız mısın? Özelden yaz, market sistemi ve etkinlikleri anlatayım! 🎯",
    "🚀 **Kirvem!** Kayıt olarak günlük 5 Kirve Point kazanabilirsin. Özelden yaz, her şeyi anlatayım! 💎",
    "💎 **Kirve!** Hala sistemde yoksun. Özelden yaz, KirveHub'ın tüm özelliklerini anlatayım! 🎮",
    "🎯 **Kirvem!** Kayıt olmadan çok şey kaçırıyorsun. Özelden yaz, bonus sistemini anlatayım! 💎",
    "💎 **Kirve!** Hala gruba kayıtlı değilsin. Özelden yaz, çekiliş sistemini keşfet! 🚀",
    "🎮 **Kirvem!** Özelden yaz, günlük 5 KP kazanma sistemini anlatayım! 💎",
    "💎 **Kirve!** Hala sistemde yoksun! Özelden yaz, tüm detayları vereyim! 🎯",
    "🏆 **Kirvem!** Özelden yaz, sıralama sistemini anlatayım! 💎",
    "🎯 **Kirve!** Özelden yaz, hızlı kazanım sistemini anlatayım! 🚀",
    "💎 **Kirve!** Özelden yaz, özel ayrıcalıkları anlatayım! 🎮"
]

# Özel bilgilendirme mesajları
INFO_MESSAGES = [
    "💎 **KİRVE POİNT NEDİR?**\n\nKirve Point, KirveHub'ın özel para birimidir. Sohbet ederek, etkinliklere katılarak ve aktif olarak kazanabilirsin.\n\n🎯 **Günlük 5 Kirve Point** kazanabilirsin!",
    
    "🛍️ **MARKET SİSTEMİ**\n\nKazandığın Kirve Point'lerle market'ten alışveriş yapabilirsin. Freespinler, site bakiyeleri ve daha fazlası!\n\n💎 **Her mesajın point kazandırır!**",
    
    "🎮 **ETKİNLİK SİSTEMİ**\n\nÇekilişler, bonus hunt'lar ve özel etkinliklere katılabilirsin. Büyük ödüller kazanabilirsin!\n\n🚀 **Sadece kayıtlı üyeler katılabilir!**",
    
    "📊 **PROFİL SİSTEMİ**\n\n/menu komutu ile profiline bakabilir, istatistiklerini görebilir ve sıralamadaki yerini takip edebilirsin.\n\n💎 **Detaylı istatistikler seni bekliyor!**",
    
    "🎯 **NASIL KAZANIRIM?**\n\n• Grup sohbetlerinde mesaj yaz\n• Etkinliklere katıl\n• Günlük aktivitelerini tamamla\n• Arkadaşlarını davet et\n\n💎 **Günlük 5 Kirve Point limiti var!**",
    
    "🏆 **SIRALAMA SİSTEMİ**\n\nEn aktif üyeler arasında yer al! Sıralamada yükselerek özel ayrıcalıklar kazanabilirsin.\n\n🚀 **Rekabetçi ortamda yarış!**",
    
    "🎯 **HIZLI KAZANIM**\n\nKayıt olduktan hemen sonra point kazanmaya başlayabilirsin! Her mesajın değeri var.\n\n💎 **Anında kazanım sistemi!**"
]

async def start_recruitment_system():
    """Kayıt teşvik sistemini başlat"""
    global recruitment_system_active
    
    while recruitment_system_active:
        try:
            await send_recruitment_messages()
            await asyncio.sleep(recruitment_interval)
        except Exception as e:
            logger.error(f"❌ Recruitment system hatası: {e}")
            await asyncio.sleep(300)  # 5 dakika bekle

async def send_recruitment_messages():
    """Kayıt teşvik mesajlarını gönder - Sadece özel mesajda"""
    try:
        # Bu fonksiyon artık grup mesajları göndermez
        # Sadece özel mesajda teşvik yapar
        logger.info("📝 Recruitment sistemi - Sadece özel mesajda teşvik yapılır")
        
    except Exception as e:
        logger.error(f"❌ Recruitment messages hatası: {e}")

async def get_unregistered_users_in_group(group_id: int) -> List[int]:
    """Gruptaki kayıt olmayan kullanıcıları al"""
    try:
        pool = await get_db_pool()
        if not pool:
            return []
            
        async with pool.acquire() as conn:
            # Kayıt olmayan kullanıcıları al
            users = await conn.fetch("""
                SELECT DISTINCT u.user_id 
                FROM users u
                LEFT JOIN user_groups ug ON u.user_id = ug.user_id AND ug.group_id = $1
                WHERE ug.user_id IS NULL
                AND u.is_registered = FALSE
                LIMIT 10
            """, group_id)
            
            return [user['user_id'] for user in users]
            
    except Exception as e:
        logger.error(f"❌ Unregistered users hatası: {e}")
        return []

async def handle_recruitment_response(message: Message):
    """Kayıt teşvik mesajına yanıt işle"""
    try:
        user = message.from_user
        
        # Kullanıcı kayıtlı mı kontrol et
        is_registered = await is_user_registered(user.id)
        
        if is_registered:
            # Zaten kayıtlı
            response_text = f"""
✅ **Zaten kayıtlısın {user.first_name}!**

Artık tüm özellikleri kullanabilirsin:

💎 **Point kazanma**
🎮 **Etkinliklere katılma**
🛍️ **Market alışverişi**
📊 **Profil takibi**

/menu komutu ile ana menüye ulaşabilirsin!
            """
        else:
            # Kayıt olmamış - detaylı bilgi ver
            response_text = f"""
🎯 **Hoş geldin {user.first_name}!**

**KirveHub**'a kayıt olarak şunları kazanabilirsin:

💎 **Kirve Point Sistemi**
• Her mesajın **0.02 KP** kazandırır
• Günlük **5 KP** limiti
• Market'te freespinler, bakiyeler

🎮 **Etkinlik Sistemi**
• Çekilişlere katıl
• Bonus hunt'lar
• Özel yarışmalar

🛍️ **Market Sistemi**
• Point'lerini kullan
• Freespinler al
• Site bakiyeleri satın al

📊 **Profil Sistemi**
• İstatistiklerini gör
• Sıralamada yer al
• Başarılarını takip et

**Hemen kayıt olmak için:**
/start komutunu kullan!
            """
        
        await message.reply(response_text, parse_mode="Markdown")
        logger.info(f"✅ Recruitment yanıtı gönderildi - User: {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Recruitment response hatası: {e}")

async def send_recruitment_info(user_id: int, first_name: str):
    """Kayıt bilgilendirme mesajı gönder"""
    try:
        from config import get_config
        from aiogram import Bot
        
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        
        # Rastgele bilgi mesajı seç
        info_message = random.choice(INFO_MESSAGES)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Ana Menü", callback_data="menu_command")],
            [InlineKeyboardButton(text="🛍️ Market", callback_data="market_command")],
            [InlineKeyboardButton(text="🎯 Etkinlikler", callback_data="events_command")],
            [InlineKeyboardButton(text="📊 Profilim", callback_data="profile_command")]
        ])
        
        response_text = f"""
{info_message}

**🎯 Hemen başlamak için:**
/start komutunu kullan ve kayıt ol!
        """
        
        await bot.send_message(
            chat_id=user_id,
            text=response_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        await bot.session.close()
        logger.info(f"✅ Recruitment info gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Recruitment info hatası - User: {user_id}, Error: {e}")

def toggle_recruitment_system(enable: bool):
    """Kayıt teşvik sistemini aç/kapat"""
    global recruitment_system_active
    recruitment_system_active = enable
    logger.info(f"🔄 Recruitment sistemi {'açıldı' if enable else 'kapatıldı'}")

def get_recruitment_status() -> bool:
    """Kayıt teşvik sistemi durumunu al"""
    return recruitment_system_active

def set_recruitment_interval(seconds: int):
    """Kayıt teşvik aralığını ayarla"""
    global recruitment_interval
    recruitment_interval = seconds
    logger.info(f"⏰ Recruitment aralığı ayarlandı: {seconds} saniye")

async def start_recruitment_background():
    """Arka planda recruitment sistemi başlat"""
    asyncio.create_task(start_recruitment_system())

@router.callback_query(F.data.startswith("recruitment_"))
async def handle_recruitment_callback(callback: CallbackQuery):
    """Recruitment callback'lerini işle"""
    try:
        data = callback.data
        user = callback.from_user
        
        if data == "recruitment_info":
            await send_recruitment_info(user.id, user.first_name)
        elif data == "recruitment_register":
            # Kayıt sayfasına yönlendir
            response_text = f"""
🎯 **Kayıt Ol {user.first_name}!**

**KirveHub**'a kayıt olarak tüm özellikleri kullanabilirsin!

**💎 Özellikler:**
• Her mesajın **0.02 KP** kazandırır
• **Market'te** freespinler, bakiyeler
• **Etkinliklere** katıl, bonuslar kazan
• **Sıralamada** yer al

**🎮 Hemen başla:**
/start komutunu kullan!
            """
            
            await callback.message.edit_text(
                response_text,
                parse_mode="Markdown"
            )
        elif data == "recruitment_menu":
            # Ana menüye yönlendir
            from handlers.profile_handler import show_main_menu
            await show_main_menu(callback)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Recruitment callback hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!")

@router.message(Command("recruitment"))
async def recruitment_command(message: Message):
    """Recruitment komutunu işle"""
    try:
        user = message.from_user
        
        # Sadece admin kullanabilir
        from config import get_config
        config = get_config()
        
        if user.id != config.ADMIN_USER_ID:
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        # Recruitment sistemi durumunu göster
        status = get_recruitment_status()
        interval = recruitment_interval
        
        response_text = f"""
🎯 **Recruitment Sistemi Durumu**

**Durum:** {'✅ Aktif' if status else '❌ Pasif'}
**Aralık:** {interval} saniye
**Son güncelleme:** {datetime.now().strftime('%H:%M:%S')}

**Komutlar:**
/recruitment_toggle - Sistemi aç/kapat
/recruitment_interval - Aralığı ayarla
        """
        
        await message.reply(response_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Recruitment command hatası: {e}")

@router.message(Command("recruitment_toggle"))
async def recruitment_toggle_command(message: Message):
    """Recruitment toggle komutunu işle"""
    try:
        user = message.from_user
        
        # Sadece admin kullanabilir
        from config import get_config
        config = get_config()
        
        if user.id != config.ADMIN_USER_ID:
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        # Durumu değiştir
        current_status = get_recruitment_status()
        new_status = not current_status
        toggle_recruitment_system(new_status)
        
        response_text = f"""
🔄 **Recruitment Sistemi {'Açıldı' if new_status else 'Kapatıldı'}**

**Yeni durum:** {'✅ Aktif' if new_status else '❌ Pasif'}
        """
        
        await message.reply(response_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Recruitment toggle hatası: {e}")

@router.message(Command("recruitment_interval"))
async def recruitment_interval_command(message: Message):
    """Recruitment interval komutunu işle"""
    try:
        user = message.from_user
        
        # Sadece admin kullanabilir
        from config import get_config
        config = get_config()
        
        if user.id != config.ADMIN_USER_ID:
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        # Mesajdan saniye al
        text = message.text.split()
        if len(text) < 2:
            await message.reply("❌ Kullanım: /recruitment_interval <saniye>")
            return
        
        try:
            seconds = int(text[1])
            if seconds < 30:
                await message.reply("❌ Minimum 30 saniye olmalı!")
                return
                
            set_recruitment_interval(seconds)
            
            response_text = f"""
⏰ **Recruitment Aralığı Güncellendi**

**Yeni aralık:** {seconds} saniye
**Önceki aralık:** {recruitment_interval} saniye
            """
            
            await message.reply(response_text, parse_mode="Markdown")
            
        except ValueError:
            await message.reply("❌ Geçerli bir sayı girin!")
        
    except Exception as e:
        logger.error(f"❌ Recruitment interval hatası: {e}")

async def check_recruitment_eligibility(user_id: int, username: str, first_name: str, group_name: str) -> bool:
    """Kullanıcının recruitment için uygun olup olmadığını kontrol et"""
    try:
        # Kullanıcı kayıtlı mı kontrol et
        is_registered = await is_user_registered(user_id)
        
        if is_registered:
            return False  # Kayıtlı kullanıcılara recruitment gönderilmez
        
        # Bugün recruitment gönderilmiş mi kontrol et
        if await is_recruitment_sent_today(user_id):
            logger.info(f"⏰ Recruitment bugün gönderilmiş - User: {first_name} ({user_id})")
            return False
        
        # Cooldown kontrolü - 5 dakika
        now = datetime.now()
        if user_id in user_recruitment_times:
            time_diff = now - user_recruitment_times[user_id]
            if time_diff.total_seconds() < 300:  # 5 dakika = 300 saniye
                logger.info(f"⏰ Recruitment cooldown - User: {first_name} ({user_id}), Kalan: {300 - time_diff.total_seconds():.0f}s")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Recruitment eligibility hatası: {e}")
        return False

async def send_recruitment_message(user_id: int, username: str, first_name: str, group_name: str):
    """Kayıt teşvik mesajı gönder - Sadece özel mesajda"""
    try:
        from config import get_config
        from aiogram import Bot
        
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        
        # Rastgele mesaj seç
        message_text = random.choice(RECRUITMENT_MESSAGES)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Detayları Öğren", callback_data="recruitment_info")],
            [InlineKeyboardButton(text="🎮 Hemen Kayıt Ol", callback_data="recruitment_register")],
            [InlineKeyboardButton(text="📊 Ana Menü", callback_data="recruitment_menu")]
        ])
        
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Recruitment zamanını kaydet
        user_recruitment_times[user_id] = datetime.now()
        await mark_recruitment_sent_today(user_id)
        
        await bot.session.close()
        logger.info(f"✅ Recruitment mesajı gönderildi - User: {first_name} ({user_id})")
        
    except Exception as e:
        logger.error(f"❌ Recruitment message hatası - User: {user_id}, Error: {e}")

async def is_recruitment_sent_today(user_id: int) -> bool:
    """Bugün recruitment gönderilmiş mi kontrol et"""
    try:
        pool = await get_db_pool()
        if not pool:
            return False
            
        async with pool.acquire() as conn:
            today = datetime.now().date()
            result = await conn.fetchrow("""
                SELECT COUNT(*) as count
                FROM recruitment_logs
                WHERE user_id = $1 AND sent_date = $2
            """, user_id, today)
            
            return result['count'] > 0 if result else False
            
    except Exception as e:
        logger.error(f"❌ Recruitment sent today hatası: {e}")
        return False

async def mark_recruitment_sent_today(user_id: int) -> None:
    """Recruitment gönderildiğini kaydet"""
    try:
        pool = await get_db_pool()
        if not pool:
            return
            
        async with pool.acquire() as conn:
            today = datetime.now().date()
            await conn.execute("""
                INSERT INTO recruitment_logs (user_id, sent_date)
                VALUES ($1, $2)
                ON CONFLICT (user_id, sent_date)
                DO NOTHING
            """, user_id, today)
            
    except Exception as e:
        logger.error(f"❌ Mark recruitment sent hatası: {e}")

async def send_milestone_notification(user_id: int, first_name: str, new_balance: float) -> None:
    """Milestone bildirimi gönder"""
    try:
        from config import get_config
        from aiogram import Bot
        
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        
        response_text = f"""
🎉 **Tebrikler {first_name}!**

**1.00 KP'ye ulaştın!** 🎯

Artık market'te alışveriş yapabilir ve etkinliklere katılabilirsin!

**💎 Yeni bakiyen:** {new_balance:.2f} KP

**🎮 Hemen kullan:**
/menu komutu ile market'e git!
        """
        
        await bot.send_message(
            chat_id=user_id,
            text=response_text,
            parse_mode="Markdown"
        )
        
        await bot.session.close()
        logger.info(f"🎉 Milestone bildirimi gönderildi - User: {first_name} ({user_id})")
        
    except Exception as e:
        logger.error(f"❌ Milestone notification hatası - User: {user_id}, Error: {e}") 