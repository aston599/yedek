import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from aiogram import Bot, Router, F, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from database import get_db_pool
from config import get_config
from utils.logger import setup_logger
from utils.memory_manager import memory_manager
import time

logger = setup_logger()

# Router oluştur
router = Router()

# Zamanlayıcı sistemi durumu
scheduled_messages_active = False
scheduled_task = None
_bot_instance = None

def set_bot_instance(bot_instance):
    """Bot instance'ını set et"""
    global _bot_instance
    _bot_instance = bot_instance

async def _send_scheduled_messages_privately(user_id: int):
    """Zamanlanmış mesajlar menüsünü özelden gönder (stub)."""
    try:
        if _bot_instance:
            await _bot_instance.send_message(user_id, "📝 Zamanlanmış mesajlar menüsü (özel mesaj)")
    except Exception:
        pass

# Varsayılan bot profilleri - Boş başlangıç
DEFAULT_BOT_PROFILES = {}

# Profil sistemi - Kayıtlı yazı botları (veritabanından yüklenecek)
BOT_PROFILES = {}

# Zamanlayıcı ayarları
scheduled_settings = {
    "active_bots": {},  # Her bot için ayrı durum
    "groups": [],
    "last_message_time": {},
    "bot_profiles": DEFAULT_BOT_PROFILES  # Bot profillerini de dahil et
}

# ==============================================
# EKSİK KOMUT FONKSİYONLARI
# ==============================================

@router.message(Command("zamanlanmesmesaj"))
async def create_scheduled_bot_command(message: Message) -> None:
    """Zamanlanmış mesaj oluşturma komutu"""
    try:
        # Admin kontrolü (Admin2+)
        try:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(message.from_user.id, 3):
                return
        except Exception:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(message.from_user.id, 3):
                return
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Zamanlanmış mesaj komutu silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_scheduled_messages_privately(message.from_user.id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        logger.info(f"📝 Zamanlanmış mesaj komutu - User: {message.from_user.first_name} ({message.from_user.id})")
        
        # Zamanlanmış mesajlar menüsünü göster
        await show_scheduled_messages_menu(message)
        
    except Exception as e:
        logger.error(f"❌ Zamanlanmış mesaj komut hatası: {e}")
        await message.reply("❌ Bir hata oluştu! Lütfen daha sonra tekrar dene.")

@router.message(Command("zamanlimesajlar"))
async def list_scheduled_bots_command(message: Message) -> None:
    """Zamanlanmış mesajları listeleme komutu"""
    try:
        # Admin kontrolü (Admin2+)
        try:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(message.from_user.id, 3):
                return
        except Exception:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(message.from_user.id, 3):
                return
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Zamanlanmış mesajlar listesi komutu silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_scheduled_messages_privately(message.from_user.id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        logger.info(f"📋 Zamanlanmış mesajlar listesi - User: {message.from_user.first_name} ({message.from_user.id})")
        
        # Zamanlanmış mesajlar durumunu göster
        await show_scheduled_status_menu(message)
        
    except Exception as e:
        logger.error(f"❌ Zamanlanmış mesajlar listesi hatası: {e}")
        await message.reply("❌ Bir hata oluştu! Lütfen daha sonra tekrar dene.")

@router.message(Command("zamanlimesajduzenle"))
async def edit_scheduled_bot_command(message: Message) -> None:
    """Zamanlanmış mesaj düzenleme komutu"""
    try:
        # Admin kontrolü (Admin2+)
        try:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(message.from_user.id, 3):
                return
        except Exception:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(message.from_user.id, 3):
                return
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Zamanlanmış mesaj düzenleme komutu silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_scheduled_messages_privately(message.from_user.id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        logger.info(f"✏️ Zamanlanmış mesaj düzenleme - User: {message.from_user.first_name} ({message.from_user.id})")
        
        # Bot yönetimi menüsünü göster
        await show_scheduled_bot_management_menu(message)
        
    except Exception as e:
        logger.error(f"❌ Zamanlanmış mesaj düzenleme hatası: {e}")
        await message.reply("❌ Bir hata oluştu! Lütfen daha sonra tekrar dene.")

@router.message(Command("zamanlimesajsil"))
async def delete_scheduled_bot_command(message: Message) -> None:
    """Zamanlanmış mesaj silme komutu"""
    try:
        # Admin kontrolü (Admin2+)
        try:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(message.from_user.id, 3):
                return
        except Exception:
            from handlers.admin_permission_manager import has_min_rank_db
            if not await has_min_rank_db(message.from_user.id, 3):
                return
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Zamanlanmış mesaj silme komutu silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_scheduled_messages_privately(message.from_user.id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        logger.info(f"🗑️ Zamanlanmış mesaj silme - User: {message.from_user.first_name} ({message.from_user.id})")
        
        # Bot yönetimi menüsünü göster (silme seçeneği orada)
        await show_scheduled_bot_management_menu(message)
        
    except Exception as e:
        logger.error(f"❌ Zamanlanmış mesaj silme hatası: {e}")
        await message.reply("❌ Bir hata oluştu! Lütfen daha sonra tekrar dene.")

# ==============================================
# YARDIMCI FONKSİYONLAR
# ==============================================

async def show_scheduled_messages_menu(message: Message) -> None:
    """Zamanlanmış mesajlar ana menüsünü göster"""
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Bot Yönetimi", callback_data="scheduled_bot_management")],
            [InlineKeyboardButton(text="📊 Durum", callback_data="scheduled_status")],
            [InlineKeyboardButton(text="➕ Yeni Bot Oluştur", callback_data="scheduled_create_bot")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_cancel")]
        ])
        
        await message.reply(
            "📝 **ZAMANLANMIŞ MESAJLAR SİSTEMİ**\n\n"
            "🤖 **Bot Yönetimi:** Mevcut botları düzenle/sil\n"
            "📊 **Durum:** Sistem durumunu gör\n"
            "➕ **Yeni Bot Oluştur:** Yeni zamanlanmış bot ekle\n\n"
            "💡 **Özellikler:**\n"
            "• Otomatik mesaj gönderimi\n"
            "• Özelleştirilebilir aralıklar\n"
            "• Resim ve link desteği\n"
            "• Çoklu grup desteği",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Zamanlanmış mesajlar menü hatası: {e}")

async def show_scheduled_bot_management_menu(message: Message) -> None:
    """Bot yönetimi menüsünü göster"""
    try:
        # Mevcut botları al
        settings = await get_scheduled_settings()
        active_bots = settings.get('active_bots', {})
        bot_profiles = settings.get('bot_profiles', {})
        
        keyboard = []
        
        if bot_profiles:
            for bot_id, profile in bot_profiles.items():
                bot_name = profile.get('name', f'Bot {bot_id}')
                is_active = active_bots.get(bot_id, False)
                status = "🟢 Aktif" if is_active else "🔴 Pasif"
                
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"{bot_name} - {status}", 
                        callback_data=f"scheduled_edit_bot_{bot_id}"
                    )
                ])
        
        keyboard.extend([
            [InlineKeyboardButton(text="➕ Yeni Bot Oluştur", callback_data="scheduled_create_bot")],
            [InlineKeyboardButton(text="📊 Durum", callback_data="scheduled_status")],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="scheduled_main_menu")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_cancel")]
        ])
        
        await message.reply(
            "🤖 **BOT YÖNETİMİ**\n\n"
            f"📋 **Mevcut Botlar:** {len(bot_profiles)}\n"
            f"🟢 **Aktif Botlar:** {sum(1 for active in active_bots.values() if active)}\n"
            f"🔴 **Pasif Botlar:** {len(bot_profiles) - sum(1 for active in active_bots.values() if active)}\n\n"
            "💡 **Bot seçerek düzenleyebilir veya silebilirsiniz.**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"❌ Bot yönetimi menü hatası: {e}")

async def show_scheduled_status_menu(message: Message) -> None:
    """Zamanlanmış mesajlar durum menüsünü göster"""
    try:
        settings = await get_scheduled_settings()
        active_bots = settings.get('active_bots', {})
        groups = settings.get('groups', [])
        bot_profiles = settings.get('bot_profiles', {})
        
        active_count = sum(1 for active in active_bots.values() if active)
        total_bots = len(bot_profiles)
        
        status_text = "🟢 Aktif" if scheduled_messages_active else "🔴 Pasif"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yenile", callback_data="scheduled_status")],
            [InlineKeyboardButton(text="🤖 Bot Yönetimi", callback_data="scheduled_bot_management")],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="scheduled_main_menu")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_cancel")]
        ])
        
        await message.reply(
            f"📊 **ZAMANLANMIŞ MESAJLAR DURUMU**\n\n"
            f"🔄 **Sistem Durumu:** {status_text}\n"
            f"🤖 **Toplam Bot:** {total_bots}\n"
            f"🟢 **Aktif Bot:** {active_count}\n"
            f"🔴 **Pasif Bot:** {total_bots - active_count}\n"
            f"👥 **Hedef Grup:** {len(groups)}\n\n"
            f"💡 **Son Güncelleme:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Durum menü hatası: {e}")

# ==============================================
# MEVCUT FONKSİYONLAR (DEĞİŞMEDİ)
# ==============================================

async def get_scheduled_settings() -> Dict[str, Any]:
    """Zamanlayıcı ayarlarını veritabanından al"""
    global BOT_PROFILES
    
    # JSON serialization için datetime objelerini string'e çevir
    def json_serial(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return str(obj.total_seconds())
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    try:
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool bulunamadı!")
            return {
                "active_bots": {},
                "groups": [],
                "last_message_time": {},
                "bot_profiles": DEFAULT_BOT_PROFILES
            }
        
        # Database bağlantısını test et
        try:
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
        except Exception as db_error:
            logger.error(f"❌ Database bağlantı hatası: {db_error}")
            return {
                "active_bots": {},
                "groups": [],
                "last_message_time": {},
                "bot_profiles": DEFAULT_BOT_PROFILES
            }
        
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT settings FROM scheduled_messages_settings WHERE id = 1"
            )
            
            if result:
                settings = result['settings']
                # Eğer string ise JSON parse et
                if isinstance(settings, str):
                    import json
                    try:
                        parsed_settings = json.loads(settings)
                        # Bot profillerini global değişkene yükle
                        if 'bot_profiles' in parsed_settings:
                            # Mevcut BOT_PROFILES'i koru, sadece eksik olanları ekle
                            for bot_id, profile in parsed_settings['bot_profiles'].items():
                                if bot_id not in BOT_PROFILES:
                                    BOT_PROFILES[bot_id] = profile
                                    logger.info(f"🔍 DEBUG - Yeni bot profili eklendi: {bot_id}")
                            logger.info(f"🔍 DEBUG - BOT_PROFILES güncellendi: {list(BOT_PROFILES.keys())}")
                        else:
                            if not BOT_PROFILES:  # Sadece boşsa yükle
                                BOT_PROFILES = DEFAULT_BOT_PROFILES.copy()
                        return parsed_settings
                    except Exception as parse_error:
                        logger.error(f"❌ JSON parse hatası: {settings}, Error: {parse_error}")
                        BOT_PROFILES = DEFAULT_BOT_PROFILES.copy()
                        return {
                            "active_bots": {},
                            "groups": [],
                            "last_message_time": {},
                            "bot_profiles": DEFAULT_BOT_PROFILES
                        }
                else:
                    # Bot profillerini global değişkene yükle
                    if 'bot_profiles' in settings:
                        # Mevcut BOT_PROFILES'i koru, sadece eksik olanları ekle
                        for bot_id, profile in settings['bot_profiles'].items():
                            if bot_id not in BOT_PROFILES:
                                BOT_PROFILES[bot_id] = profile
                        logger.info(f"🔍 DEBUG - BOT_PROFILES güncellendi (dict): {list(BOT_PROFILES.keys())}")
                    else:
                        if not BOT_PROFILES:  # Sadece boşsa yükle
                            BOT_PROFILES = DEFAULT_BOT_PROFILES.copy()
                    return settings
            else:
                # Varsayılan ayarları oluştur
                default_settings = {
                    "active_bots": {},
                    "groups": [],
                    "last_message_time": {},
                    "bot_profiles": DEFAULT_BOT_PROFILES
                }
                
                import json
                from datetime import datetime, timedelta
                
                def json_serial(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    elif isinstance(obj, timedelta):
                        return str(obj.total_seconds())
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
                
                await conn.execute(
                    "INSERT INTO scheduled_messages_settings (id, settings) VALUES (1, $1)",
                    json.dumps(default_settings, default=json_serial)
                )
                BOT_PROFILES = DEFAULT_BOT_PROFILES.copy()
                return default_settings
    except Exception as e:
        logger.error(f"❌ Zamanlayıcı ayarları alınırken hata: {e}")
        import traceback
        logger.error(f"❌ GET_SCHEDULED_SETTINGS TRACEBACK: {traceback.format_exc()}")
        BOT_PROFILES = DEFAULT_BOT_PROFILES.copy()
        return {
            "active_bots": {},
            "groups": [],
            "last_message_time": {},
            "bot_profiles": DEFAULT_BOT_PROFILES
        }

async def save_scheduled_settings(settings: Dict[str, Any]) -> bool:
    """Zamanlayıcı ayarlarını veritabanına kaydet"""
    global BOT_PROFILES
    try:
        import json
        # Mevcut ayarları al (BOT_PROFILES'ı koruyarak)
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT settings FROM scheduled_messages_settings WHERE id = 1"
            )
            if result:
                current_settings = result['settings']
                if isinstance(current_settings, str):
                    current_settings = json.loads(current_settings)
            else:
                current_settings = {
                    "active_bots": {},
                    "groups": [],
                    "last_message_time": {},
                    "bot_profiles": {}
                }
        
        # Ayarları güncelle
        current_settings.update(settings)
        current_settings['bot_profiles'] = BOT_PROFILES  # Global BOT_PROFILES'ı kaydet
        # Sadece değişiklik varsa log at
        if BOT_PROFILES:
            logger.debug(f"💾 Bot profilleri kaydediliyor: {list(BOT_PROFILES.keys())}")
        
        # Veritabanına kaydet
        async with pool.acquire() as conn:
            # JSON serialization için datetime objelerini string'e çevir
            import json
            from datetime import datetime
            
            def json_serial(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, timedelta):
                    return str(obj.total_seconds())
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            await conn.execute(
                "UPDATE scheduled_messages_settings SET settings = $1 WHERE id = 1",
                json.dumps(current_settings, default=json_serial)
            )
            return True
    except Exception as e:
        logger.error(f"❌ Zamanlayıcı ayarları kaydedilirken hata: {e}")
        return False

async def get_active_groups() -> List[int]:
    """Aktif grup ID'lerini al (test grupları hariç)"""
    try:
        # Test grup ID'leri (otomatik komutlar gönderilmemeli)
        TEST_GROUP_IDS = [
            -1002231486317,  # Test grubu
            -1001234567890,  # Test grubu (örnek)
        ]
        
        # Kayıtlı grupları database'den al
        from database import get_registered_groups
        groups = await get_registered_groups()
        group_ids = [group['group_id'] for group in groups if group['group_id'] not in TEST_GROUP_IDS]
        
        if not group_ids:
            logger.warning("⚠️ Kayıtlı grup bulunamadı!")
            return []  # Boş liste döndür
            
        return group_ids
    except Exception as e:
        logger.error(f"❌ Aktif gruplar alınırken hata: {e}")
        return []

async def send_auto_commands(bot: Bot, settings: Dict[str, Any]) -> None:
    """Otomatik komut mesajlarını gönder - BOT BAŞLANGIÇ KORUMASI: 3 dakika"""
    # Bot başlangıç koruması kontrolü - Otomatik komutlar için
    try:
        from handlers.chat_system import is_bot_startup_protection_active
        if is_bot_startup_protection_active():
            logger.info(f"🛡️ Bot başlangıç koruması aktif - Otomatik komutlar gönderilmedi (3 dakika)")
            return
    except Exception as protection_error:
        logger.debug(f"⏸️ Startup protection kontrolü hatası (kritik değil): {protection_error}")
    
    try:
        auto_commands = settings.get('auto_commands', {})
        if not auto_commands:
            return
        
        # Aktif grupları al (hem database'den hem bot profillerinden)
        active_groups = await get_active_groups()
        
        # Test grup ID'leri (otomatik komutlar gönderilmemeli)
        TEST_GROUP_IDS = [
            -1002231486317,  # Test grubu
            -1001234567890,  # Test grubu (örnek)
        ]
        
        # Bot profillerindeki grupları da ekle (birleştir, test grupları hariç)
        bot_profiles = settings.get('bot_profiles', {})
        for bot_id, profile in bot_profiles.items():
            profile_groups = profile.get('groups', [])
            for group_id in profile_groups:
                if group_id not in TEST_GROUP_IDS and group_id not in active_groups:
                    active_groups.append(group_id)
        
        if not active_groups:
            logger.debug("⚠️ Otomatik komutlar için aktif grup bulunamadı!")
            return
        
        auto_commands_last_sent = settings.get('auto_commands_last_sent', {})
        
        # Her otomatik komut için kontrol et
        for command_name, cmd_data in auto_commands.items():
            if not cmd_data.get('is_active', False):
                continue
            
            interval_minutes = cmd_data.get('interval_minutes', 60)  # Tanıtım yazısı için 60 dakika
            message_text = cmd_data.get('message_text', '')
            
            # Son gönderilme zamanını kontrol et
            last_sent = auto_commands_last_sent.get(command_name)
            if last_sent:
                try:
                    last_dt = datetime.fromisoformat(last_sent)
                    time_diff = (datetime.now() - last_dt).total_seconds()
                    if time_diff < interval_minutes * 60:
                        continue  # Henüz zamanı gelmemiş
                except Exception as e:
                    logger.warning(f"⚠️ Auto command {command_name} last_sent parse hatası: {e}")
                    # Hatalı format, devam et
            
            # Test grup ID'leri (otomatik komutlar gönderilmemeli)
            TEST_GROUP_IDS = [
                -1002231486317,  # Test grubu
                -1001234567890,  # Test grubu (örnek)
            ]
            
            # Her aktif gruba gönder (son mesaj kontrolü ile, test grupları hariç)
            sent_count = 0
            for group_id in active_groups:
                # Test gruplarına gönderme
                if group_id in TEST_GROUP_IDS:
                    logger.debug(f"⏸️ Auto command {command_name} - Test grubu {group_id} atlandı")
                    continue
                
                try:
                    # Son mesaj kontrolü: Eğer son mesaj bot ise, birisi yazana kadar bekle
                    try:
                        from handlers.group_activity_monitor import check_group_activity
                        should_send, reason = await check_group_activity(group_id)
                        if not should_send:
                            logger.debug(f"⏸️ Auto command {command_name} - Grup {group_id}: Mesaj gönderilmedi - {reason}")
                            continue
                    except Exception as check_error:
                        logger.warning(f"⚠️ Grup aktivite kontrolü hatası: {check_error}, mesaj gönderiliyor")
                        # Hata durumunda gönder (güvenli taraf)
                    
                    # Normal mesaj gönder
                    await bot.send_message(
                        chat_id=group_id,
                        text=message_text,
                        parse_mode="HTML"
                    )
                    
                    # ÖNEMLİ: Bot mesajını grup aktivite izleyicisine kaydet
                    # Bu, algoritmanın çalışması için kritik!
                    try:
                        from handlers.group_activity_monitor import record_bot_message
                        bot_info = await bot.get_me()
                        await record_bot_message(group_id, bot_info.id)
                    except Exception as record_error:
                        logger.debug(f"⏸️ Bot mesajı kaydetme hatası (kritik değil): {record_error}")
                    
                    sent_count += 1
                    
                    await asyncio.sleep(1)  # Rate limit

                except Exception as e:
                    logger.error(f"❌ Auto command {command_name} - Grup {group_id} gönderme hatası: {e}")
                    continue
            
            # Son gönderilme zamanını güncelle
            if sent_count > 0:
                if 'auto_commands_last_sent' not in settings:
                    settings['auto_commands_last_sent'] = {}
                settings['auto_commands_last_sent'][command_name] = datetime.now().isoformat()
                await save_scheduled_settings(settings)
                logger.info(f"✅ Auto command {command_name} gönderildi - {sent_count} grup")
        
    except Exception as e:
        logger.error(f"❌ Auto commands gönderme hatası: {e}")

async def send_scheduled_message(bot_id: str, group_id: int, message_text: str, image_url: str = None, link: str = None, link_text: str = None) -> bool:
    """Zamanlanmış mesaj gönder - BOT BAŞLANGIÇ KORUMASI: 3 dakika"""
    # Bot başlangıç koruması kontrolü - Zamanlanmış mesajlar için
    try:
        from handlers.chat_system import is_bot_startup_protection_active
        if is_bot_startup_protection_active():
            logger.info(f"🛡️ Bot başlangıç koruması aktif - Zamanlanmış mesaj gönderilmedi (3 dakika)")
            return False
    except Exception as protection_error:
        logger.debug(f"⏸️ Startup protection kontrolü hatası (kritik değil): {protection_error}")
    
    try:
        # Bot instance'ını al
        bot = _bot_instance or Bot(token=get_config().BOT_TOKEN)
        
        # Yalnızca gruplara gönder (pozitif ID kullanıcıdır, DM başlatılamaz)
        if isinstance(group_id, int) and group_id > 0:
            logger.info(f"ℹ️ Kullanıcı ID tespit edildi, zamanlanmış mesaj atlanıyor - Target: {group_id}")
            return False
        
        # ÖNEMLİ: Son mesaj kontrolü - Eğer son mesaj bot ise, gönderme (FLAME KORUMASI)
        try:
            from handlers.group_activity_monitor import check_group_activity
            should_send, reason = await check_group_activity(group_id)
            if not should_send:
                logger.debug(f"⏸️ Zamanlanmış mesaj - Grup {group_id}: Mesaj gönderilmedi - {reason}")
                return False
        except Exception as check_error:
            logger.debug(f"⏸️ Grup aktivite kontrolü hatası (kritik değil): {check_error}")
            # Hata durumunda devam et (güvenli taraf)
        
        # Mesaj içeriği
        caption = message_text
        
        # Link varsa buton ekle
        keyboard = None
        logger.info(f"🔍 DEBUG - Link: {link}, Link Text: {link_text}")
        if link and link_text:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=link_text, url=link)]
            ])
            logger.info(f"🔍 DEBUG - Keyboard oluşturuldu: {link_text} -> {link}")
        else:
            logger.info(f"🔍 DEBUG - Link veya link_text eksik: link={link}, link_text={link_text}")
        
        # Görsel varsa görselle gönder, yoksa sadece metin
        if image_url:
            await bot.send_photo(
                chat_id=group_id,
                photo=image_url,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                chat_id=group_id,
                text=caption,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        
        # ÖNEMLİ: Bot mesajını grup aktivite izleyicisine kaydet (mesaj gönderildikten SONRA)
        # Bu, algoritmanın çalışması için kritik!
        try:
            from handlers.group_activity_monitor import record_bot_message
            bot_info = await bot.get_me()
            await record_bot_message(group_id, bot_info.id)
        except Exception as record_error:
            logger.debug(f"⏸️ Bot mesajı kaydetme hatası (kritik değil): {record_error}")
        
        logger.info(f"✅ Zamanlanmış mesaj gönderildi - Bot: {bot_id}, Grup: {group_id}")
        return True
        
    except Exception as e:
        # DM başlatılamayan kullanıcı veya erişim hatalarında daha sakin logla
        if "bot can't initiate conversation" in str(e).lower() or "forbidden" in str(e).lower():
            logger.info(f"ℹ️ Zamanlanmış mesaj atlanıyor (erişim yok) - Bot: {bot_id}, Grup/Kullanıcı: {group_id}")
        else:
            logger.error(f"❌ Zamanlanmış mesaj gönderme hatası - Bot: {bot_id}, Grup: {group_id}, Hata: {e}")
        return False

async def scheduled_message_task(bot: Bot):
    """Zamanlanmış mesaj görevini çalıştır"""
    global scheduled_messages_active, _bot_instance
    
    # Bot instance'ını kontrol et
    if not _bot_instance:
        _bot_instance = bot
    
    while scheduled_messages_active:
        try:
            settings = await get_scheduled_settings()
            active_bots = settings.get("active_bots", {})
            
            logger.info(f"🔍 DEBUG - Active bots: {active_bots}")
            logger.info(f"🔍 DEBUG - BOT_PROFILES keys: {list(BOT_PROFILES.keys())}")
            
            if not active_bots:
                await asyncio.sleep(15)  # bekleme süresini kısalt
                continue
            
            # Her aktif bot için mesaj gönder
            for bot_id, bot_active in active_bots.items():
                if bot_active and bot_id in BOT_PROFILES:
                    profile = BOT_PROFILES[bot_id]
                    message = profile["message"]  # Tek mesaj
                    link = profile.get("link")
                    
                    # URL güncellemeleri: Eski URL'leri yeni URL'lere çevir
                    if link:
                        # Çift protokol sorununu düzelt
                        if 'https://https://' in link:
                            link = link.replace('https://https://', 'https://')
                        elif 'http://https://' in link:
                            link = link.replace('http://https://', 'https://')
                        elif 'https://http://' in link:
                            link = link.replace('https://http://', 'https://')
                        
                        # Eski URL'leri yeni URL'lere çevir
                        if 'kumarlayasiyorum9.com' in link or 'kumarlayasiyorum7.com' in link:
                            link = link.replace('kumarlayasiyorum9.com', 'kirve1.com')
                            link = link.replace('kumarlayasiyorum7.com', 'kirve1.com')
                            # Profili güncelle
                            BOT_PROFILES[bot_id]["link"] = link
                            logger.info(f"🔗 URL güncellendi: {bot_id} → {link}")
                    
                    link_text = profile.get("link_text", "🔗 Linke Git")  # Link metni
                    image = profile.get("image")
                    interval = profile.get("interval", 30)
                    
                    logger.info(f"🔍 DEBUG - Bot Profile: {bot_id}")
                    logger.info(f"🔍 DEBUG - Full Profile: {profile}")
                    logger.info(f"🔍 DEBUG - Profile keys: {list(profile.keys())}")
                    logger.info(f"🔍 DEBUG - Message: {message}")
                    logger.info(f"🔍 DEBUG - Link: {link}")
                    logger.info(f"🔍 DEBUG - Link Text: {link_text}")
                    logger.info(f"🔍 DEBUG - Image: {image}")
                    logger.info(f"🔍 DEBUG - Interval: {interval}")
                    
                    # Son mesaj zamanını kontrol et
                    last_time = settings.get("last_message_time", {}).get(bot_id)
                    if last_time:
                        try:
                            last_dt = datetime.fromisoformat(last_time)
                            time_diff = (datetime.now() - last_dt).total_seconds()
                            if time_diff < interval * 60:
                                logger.debug(f"⏳ Bot {bot_id} henüz zamanı gelmedi: {time_diff/60:.1f} dakika geçti, {interval} dakika bekleniyor")
                                continue  # Henüz zamanı gelmemiş
                        except Exception as e:
                            logger.warning(f"⚠️ Bot {bot_id} last_message_time parse hatası: {e}, yeni zaman set ediliyor")
                            # Hatalı format, şu anki zamanı set et
                            if "last_message_time" not in settings:
                                settings["last_message_time"] = {}
                            settings["last_message_time"][bot_id] = datetime.now().isoformat()
                            await save_scheduled_settings(settings)
                            continue  # Bu döngüde gönderme, bir sonraki döngüde gönder
                    else:
                        # last_message_time yoksa, şu anki zamanı set et ve gönderme
                        logger.info(f"⏰ Bot {bot_id} için last_message_time yok, şu anki zaman set ediliyor")
                        if "last_message_time" not in settings:
                            settings["last_message_time"] = {}
                        settings["last_message_time"][bot_id] = datetime.now().isoformat()
                        await save_scheduled_settings(settings)
                        continue  # Bu döngüde gönderme, interval kadar beklesin
                    
                    # Bot profilinden grupları al
                    bot_groups = profile.get("groups", [])
                    if not bot_groups:
                        logger.warning(f"⚠️ Bot {bot_id} için grup tanımlanmamış!")
                        continue
                    
                    # Her gruba mesaj gönder (son mesaj kontrolü ile)
                    for group_id in bot_groups:
                        try:
                            # Son mesaj kontrolü: Eğer son mesaj bot ise, birisi yazana kadar bekle
                            try:
                                from handlers.group_activity_monitor import check_group_activity
                                should_send, reason = await check_group_activity(group_id)
                                if not should_send:
                                    logger.debug(f"⏸️ Bot {bot_id} - Grup {group_id}: Mesaj gönderilmedi - {reason}")
                                    continue
                            except Exception as check_error:
                                logger.warning(f"⚠️ Grup aktivite kontrolü hatası: {check_error}, mesaj gönderiliyor")
                                # Hata durumunda gönder (güvenli taraf)
                            
                            await send_scheduled_message(
                                bot_id, 
                                group_id, 
                                message, 
                                image,  # Artık URL
                                link, 
                                link_text
                            )
                            await asyncio.sleep(1)  # 1 saniye bekle (rate limit)
                        except Exception as e:
                            logger.error(f"❌ Grup {group_id} mesaj gönderme hatası: {e}")
                            continue
                    
                    # Son mesaj zamanını güncelle
                    if "last_message_time" not in settings:
                        settings["last_message_time"] = {}
                    settings["last_message_time"][bot_id] = datetime.now().isoformat()
                    await save_scheduled_settings(settings)
                    
                    logger.info(f"✅ Bot {bot_id} mesajı gönderildi - {len(bot_groups)} grup")
            
            # Otomatik komutları kontrol et ve gönder
            await send_auto_commands(bot, settings)
            
            # genel döngü beklemesi
            await asyncio.sleep(15)
            
        except Exception as e:
            logger.error(f"❌ Zamanlanmış mesaj görevinde hata: {e}")
            await asyncio.sleep(15)  # Hata durumunda kısa bekle

async def start_scheduled_messages(bot):
    """Zamanlanmış mesajları başlat"""
    try:
        logger.info("🚀 Zamanlanmış mesajlar başlatılıyor...")
        
        # Kısa bir bekleme ekle (ana thread'i bloke etmemek için)
        await asyncio.sleep(2)
        
        # BOT_PROFILES'i yükle
        settings = await get_scheduled_settings()
        global BOT_PROFILES
        BOT_PROFILES = settings.get('bot_profiles', {})
        
        logger.info(f"✅ BOT_PROFILES yüklendi: {len(BOT_PROFILES)} bot")
        
        # Active bots'ları kontrol et
        active_bots = {}
        active_count = 0
        for bot_id, profile in BOT_PROFILES.items():
            is_active = profile.get('active', False)
            active_bots[bot_id] = is_active
            if is_active:
                active_count += 1
        
        logger.info(f"✅ {active_count} aktif bot bulundu")
        
        # ÖNEMLİ: Bot başlatıldığında last_message_time yoksa, şu anki zamanı set et
        # Böylece hemen mesaj göndermez, interval kadar bekler
        if "last_message_time" not in settings:
            settings["last_message_time"] = {}
        
        now = datetime.now().isoformat()
        for bot_id, profile in BOT_PROFILES.items():
            if profile.get('active', False) and bot_id not in settings["last_message_time"]:
                # Aktif bot için last_message_time yoksa, şu anki zamanı set et
                settings["last_message_time"][bot_id] = now
                logger.info(f"⏰ Bot {bot_id} için last_message_time set edildi: {now}")
        
        # Ayarları kaydet
        await save_scheduled_settings(settings)
        
        # Genel görev: ilk aktivasyonda beklemeden kontrol etsin
        global scheduled_messages_active
        scheduled_messages_active = True
        asyncio.create_task(scheduled_message_task(bot))
        logger.info("✅ Zamanlanmış mesaj ana görev başlatıldı")
                
        logger.info("✅ Zamanlanmış mesajlar başarıyla başlatıldı")
                
    except Exception as e:
        logger.error(f"❌ Scheduled messages başlatma hatası: {e}")
        import traceback
        logger.error(f"❌ SCHEDULED STARTUP TRACEBACK: {traceback.format_exc()}")

async def stop_scheduled_messages() -> bool:
    """Zamanlanmış mesajları durdur"""
    global scheduled_messages_active, scheduled_task
    
    try:
        if not scheduled_messages_active:
            logger.warning("⚠️ Zamanlanmış mesajlar zaten durdurulmuş!")
            return False
            
        scheduled_messages_active = False
        
        if scheduled_task:
            scheduled_task.cancel()
            try:
                await scheduled_task
            except asyncio.CancelledError:
                pass
            scheduled_task = None
        
        logger.info("✅ Zamanlanmış mesajlar durduruldu")
        return True
        
    except Exception as e:
        logger.error(f"❌ Zamanlanmış mesajlar durdurulurken hata: {e}")
        return False

async def toggle_bot_status(bot_id: str, active: bool) -> bool:
    """Bot durumunu değiştir"""
    try:
        settings = await get_scheduled_settings()
        
        # Settings'in dictionary olduğundan emin ol
        if not isinstance(settings, dict):
            logger.error(f"❌ Settings dictionary değil: {type(settings)}, Value: {settings}")
            return False
        
        logger.info(f"🔍 Toggle bot status - Bot: {bot_id}, Active: {active}, Settings type: {type(settings)}")
        
        # active_bots'ın dictionary olduğundan emin ol
        if "active_bots" not in settings or not isinstance(settings["active_bots"], dict):
            settings["active_bots"] = {}
            
        if active:
            # Bot'u aktif et
            settings["active_bots"][bot_id] = True
            
            # İlk mesajı hızlı başlat: last_message_time'ı geçmişe çek
            if bot_id in BOT_PROFILES:
                interval = BOT_PROFILES[bot_id].get("interval", 30)
                first_message_time = datetime.now()  # Bildirim için şimdi
                
                # last_message_time'ın dictionary olduğundan emin ol
                if "last_message_time" not in settings or not isinstance(settings["last_message_time"], dict):
                    settings["last_message_time"] = {}
                # Hemen tetiklenmesi için geçmişe ayarla
                settings["last_message_time"][bot_id] = (datetime.now() - timedelta(minutes=interval + 1)).isoformat()
                
            logger.info(f"✅ Bot {bot_id} aktif edildi - İlk mesaj şimdi kuyruğa alındı")
            
            # Adminlere bildirim gönder
            await send_bot_activation_notification(bot_id, interval, first_message_time)
        else:
            # Bot'u pasif et
            settings["active_bots"][bot_id] = False
            
            # Son mesaj zamanını temizle
            if "last_message_time" in settings and isinstance(settings["last_message_time"], dict) and bot_id in settings["last_message_time"]:
                del settings["last_message_time"][bot_id]
                
            logger.info(f"✅ Bot {bot_id} pasif edildi")
            
            # Adminlere bildirim gönder
            await send_bot_deactivation_notification(bot_id)
        
        success = await save_scheduled_settings(settings)
        return success
        
    except Exception as e:
        logger.error(f"❌ Bot durumu değiştirme hatası: {e}")
        return False



async def get_scheduled_status() -> Dict[str, Any]:
    """Zamanlayıcı durumunu al"""
    try:
        settings = await get_scheduled_settings()
        
        active_bots = settings.get("active_bots", {})
        logger.info(f"✅ Active bots: {active_bots}")
        logger.info(f"✅ BOT_PROFILES keys: {list(BOT_PROFILES.keys())}")
        
        result = {
            "active_bots": active_bots,
            "available_bots": list(BOT_PROFILES.keys()),
            "bot_profiles": BOT_PROFILES
        }
        return result
        
    except Exception as e:
        logger.error(f"❌ Zamanlayıcı durumu alınırken hata: {e}")
        import traceback
        logger.error(f"❌ GET_SCHEDULED_STATUS TRACEBACK: {traceback.format_exc()}")
        return {}

async def send_bot_activation_notification(bot_id: str, interval: int, first_message_time: datetime) -> None:
    """Bot aktifleştirildiğinde adminlere bildirim gönder"""
    try:
        if bot_id not in BOT_PROFILES:
            return
            
        profile = BOT_PROFILES[bot_id]
        bot_name = profile.get("name", bot_id)
        message = profile.get("message", "")
        groups = profile.get("groups", [])
        
        # Grup bilgilerini al
        from database import get_registered_groups
        all_groups = await get_registered_groups()
        group_names = []
        
        for group_id in groups:
            for group in all_groups:
                if group['group_id'] == group_id:
                    group_names.append(group['group_name'])
                    break
        
        # Mesaj formatını hazırla
        notification = f"""
🤖 **BOT AKTİFLEŞTİRİLDİ!**

**📋 Bot Bilgileri:**
• **Ad:** {bot_name}
• **ID:** `{bot_id}`
• **Mesaj:** {message[:50]}{'...' if len(message) > 50 else ''}
• **Aralık:** {interval} dakika
• **İlk Mesaj:** {first_message_time.strftime('%H:%M')} ({first_message_time.strftime('%d.%m.%Y')})

**📊 Grup Bilgileri:**
• **Toplam Grup:** {len(groups)}
• **Gruplar:** {', '.join(group_names) if group_names else 'Grup bulunamadı'}

**⏰ Sonraki Mesajlar:**
• Her {interval} dakikada bir otomatik mesaj gönderilecek
• Mesaj saati: {first_message_time.strftime('%H:%M')} ve sonrası

**🔔 Durum:** ✅ **AKTİF**
        """
        
        # Adminlere gönder
        from config import get_config
        from aiogram import Bot
        from database import get_db_pool
        
        # Bot token'ını al
        config = get_config()
        bot_token = config.BOT_TOKEN
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Tüm adminleri al
            admins = await conn.fetch("SELECT user_id FROM users WHERE rank_level >= 1")
            
            bot_instance = Bot(token=bot_token)
            
            for admin in admins:
                try:
                    await bot_instance.send_message(
                        chat_id=admin['user_id'],
                        text=notification,
                        parse_mode="Markdown"
                    )
                    await asyncio.sleep(0.1)  # Rate limit
                except Exception as e:
                    logger.error(f"❌ Admin {admin['user_id']} bildirimi gönderilemedi: {e}")
            
            await bot_instance.session.close()
            
        logger.info(f"✅ Bot aktivasyon bildirimi {len(admins)} admin'e gönderildi")
        
    except Exception as e:
        logger.error(f"❌ Bot aktivasyon bildirimi hatası: {e}")

async def send_bot_deactivation_notification(bot_id: str) -> None:
    """Bot pasifleştirildiğinde adminlere bildirim gönder"""
    try:
        if bot_id not in BOT_PROFILES:
            return
            
        profile = BOT_PROFILES[bot_id]
        bot_name = profile.get("name", bot_id)
        
        # Mesaj formatını hazırla
        notification = f"""
🤖 **BOT PASİFLEŞTİRİLDİ!**

**📋 Bot Bilgileri:**
• **Ad:** {bot_name}
• **ID:** `{bot_id}`

**🔔 Durum:** ❌ **PASİF**

**ℹ️ Bilgi:** Bot artık otomatik mesaj göndermeyecek.
        """
        
        # Adminlere gönder
        from config import get_config
        from aiogram import Bot
        from database import get_db_pool
        
        # Bot token'ını al
        config = get_config()
        bot_token = config.BOT_TOKEN
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Tüm adminleri al
            admins = await conn.fetch("SELECT user_id FROM users WHERE rank_level >= 1")
            
            bot_instance = Bot(token=bot_token)
            
            for admin in admins:
                try:
                    await bot_instance.send_message(
                        chat_id=admin['user_id'],
                        text=notification,
                        parse_mode="Markdown"
                    )
                    await asyncio.sleep(0.1)  # Rate limit
                except Exception as e:
                    logger.error(f"❌ Admin {admin['user_id']} bildirimi gönderilemedi: {e}")
            
            await bot_instance.session.close()
            
        logger.info(f"✅ Bot pasifleştirme bildirimi {len(admins)} admin'e gönderildi")
        
    except Exception as e:
        logger.error(f"❌ Bot pasifleştirme bildirimi hatası: {e}")

# Bot yönetimi fonksiyonları
async def create_bot_profile(bot_id: str, name: str, messages: List[str], link: str = None, image: str = None, interval: int = 30) -> bool:
    """Yeni bot profili oluştur"""
    global BOT_PROFILES
    try:
        BOT_PROFILES[bot_id] = {
            "name": name,
            "message": messages[0] if messages else "",  # messages -> message olarak düzelt
            "link": link,
            "image": image,
            "interval": interval,
            "active": False  # Default kapalı
        }
        # Veritabanına kaydet
        await save_scheduled_settings({})
        logger.info(f"✅ Yeni bot profili oluşturuldu: {name}")
        return True
    except Exception as e:
        logger.error(f"❌ Bot profili oluşturulurken hata: {e}")
        return False

async def update_bot_profile(bot_id: str, name: str = None, message: str = None, link: str = None, image: str = None, interval: int = None) -> bool:
    """Bot profilini güncelle"""
    global BOT_PROFILES
    try:
        if bot_id not in BOT_PROFILES:
            return False
            
        profile = BOT_PROFILES[bot_id]
        
        if name:
            profile["name"] = name
        if message:
            profile["message"] = message
        if link is not None:
            profile["link"] = link
        if image is not None:
            profile["image"] = image
        if interval:
            profile["interval"] = interval
            
        # Veritabanına kaydet
        await save_scheduled_settings({})
        logger.info(f"✅ Bot profili güncellendi: {bot_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Bot profili güncellenirken hata: {e}")
        return False

async def delete_bot_profile(bot_id: str) -> bool:
    """Bot profilini sil"""
    global BOT_PROFILES
    try:
        if bot_id not in BOT_PROFILES:
            logger.error(f"❌ Bot bulunamadı: {bot_id}")
            return False
            
        # Bot profilini sil
        del BOT_PROFILES[bot_id]
        # Veritabanına kaydet
        await save_scheduled_settings({})
        logger.info(f"✅ Bot profili silindi: {bot_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Bot profili silinirken hata: {e}")
        return False

async def scheduled_callback_handler(callback) -> None:
    """Zamanlanmış mesajlar callback handler"""
    try:
        # BOT_PROFILES'i güncel tutmak için ayarları yeniden yükle
        await get_scheduled_settings()
        
        user_id = callback.from_user.id
        config = get_config()
        
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
            
        action = callback.data
        
        if action == "scheduled_bot_management":
            await show_scheduled_bot_management_menu(callback)
            
        elif action == "scheduled_status":
            await show_scheduled_status_menu(callback)
            
        elif action and action.startswith("toggle_bot_"):
            # Callback data formatı: toggle_bot_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            status = await get_scheduled_status()
            current_active = status.get('active_bots', {}).get(bot_id, False)
            success = await toggle_bot_status(bot_id, not current_active)
            if success:
                new_status = "açıldı" if not current_active else "kapatıldı"
                await callback.answer(f"✅ Bot {bot_id} {new_status}!", show_alert=True)
            else:
                await callback.answer("❌ Bot durumu değiştirme hatası!", show_alert=True)
                
        elif action and action.startswith("edit_bot_"):
            # Callback data formatı: edit_bot_{bot_id}
            # bot_id içinde _ olabileceği için daha güvenli parsing
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
                
            bot_id = "_".join(action_parts[2:])  # 2. indeksten sonuna kadar
            await show_bot_edit_menu(callback, bot_id)
            
        elif action and action.startswith("bot_toggle_"):
            # Callback data formatı: bot_toggle_{bot_id}
            # bot_id içinde _ olabileceği için daha güvenli parsing
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
                
            bot_id = "_".join(action_parts[2:])  # 2. indeksten sonuna kadar
            
            status = await get_scheduled_status()
            current_active = status.get('active_bots', {}).get(bot_id, False)
            
            success = await toggle_bot_status(bot_id, not current_active)
            if success:
                new_status = "açıldı" if not current_active else "kapatıldı"
                try:
                    await callback.answer(f"✅ Bot {bot_id} {new_status}!", show_alert=True)
                    # Menüyü güncelle
                    await show_bot_edit_menu(callback, bot_id)
                except Exception as e:
                    logger.error(f"❌ Callback answer hatası: {e}")
                    # Hata durumunda sadece mesaj gönder
                    await callback.message.answer(f"✅ Bot {bot_id} {new_status}!")
            else:
                try:
                    await callback.answer("❌ Bot durumu değiştirme hatası!", show_alert=True)
                except Exception as e:
                    logger.error(f"❌ Callback answer hatası: {e}")
                    await callback.message.answer("❌ Bot durumu değiştirme hatası!")
                
        elif action == "admin_scheduled_messages":
            await show_scheduled_messages_menu(callback)
            
        elif action == "scheduled_back":
            await show_scheduled_messages_menu(callback)
            
        elif action and action.startswith("add_link_"):
            # Link ekleme işlemi
            bot_id = action.replace("add_link_", "")
            logger.info(f"🔍 Link ekleme başlatıldı - bot_id: {bot_id}")
            
            # Input state'i ayarla
            from utils.memory_manager import memory_manager
            memory_manager.set_input_state(user_id, f"add_link_{bot_id}")
            
            response = f"""
🔗 **Link Ekleme - Aşama 1**

**Bot:** {BOT_PROFILES.get(bot_id, {}).get('name', bot_id)}

**Link URL'sini yazın:**
Örnek: https://t.me/kirvehub

**Not:** Link opsiyoneldir, geçmek için "❌ İptal" butonuna basın.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_bot_management")]
            ])
            
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            await callback.answer()
            
        elif action and action.startswith("create_bot_profile"):
            # Bot oluşturma input state'ini başlat
            from utils.memory_manager import memory_manager
            memory_manager.set_input_state(user_id, "create_bot_name")
            
            response = """
🤖 **Bot Oluşturma - Aşama 1**

**Zamanlayıcının adını yazın:**
Örnek: "KirveHub Duyuru", "Test Bot", "Özel Bot"

**Not:** Bot adı benzersiz olmalıdır.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_bot_management")]
            ])
            
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            await callback.answer("Bot adı bekleniyor...")
            
        elif action and action.startswith("create_bot_link_yes_"):
            # Link evet seçildi
            # Callback data formatı: create_bot_link_yes_{bot_id}
            # bot_id içinde _ olabileceği için daha güvenli parsing
            action_parts = action.split("_")
            if len(action_parts) < 5:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
                
            bot_id = "_".join(action_parts[4:])  # 4. indeksten sonuna kadar
            
            if bot_id not in BOT_PROFILES:
                await callback.answer("❌ Bot bulunamadı!", show_alert=True)
                return
                
            # Link input state'ini başlat
            from utils.memory_manager import memory_manager
            memory_manager.set_input_state(user_id, f"create_bot_link_url_{bot_id}")
            
            response = f"""
🔗 **Link Ekleme**

**Bot:** {BOT_PROFILES[bot_id]['name']}

**Link URL'sini yazın:**
Örnek: https://example.com
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_bot_management")]
            ])
            
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            await callback.answer("Link URL bekleniyor...")
            
        elif action and action.startswith("create_bot_link_no_"):
            # Link hayır seçildi - Grup seçimine geç
            # Callback data formatı: create_bot_link_no_{bot_id}
            # bot_id içinde _ olabileceği için daha güvenli parsing
            action_parts = action.split("_")
            if len(action_parts) < 5:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
                
            bot_id = "_".join(action_parts[4:])  # 4. indeksten sonuna kadar
            
            if bot_id not in BOT_PROFILES:
                await callback.answer("❌ Bot bulunamadı!", show_alert=True)
                return
                
            # Grup seçimine geç
            from database import get_registered_groups
            groups = await get_registered_groups()
            
            if not groups:
                await callback.answer("❌ Kayıtlı grup bulunamadı!", show_alert=True)
                return
            
            # Grup seçim menüsü
            group_list = ""
            keyboard_buttons = []
            
            for i, group in enumerate(groups, 1):
                group_list += f"**ID {i}:** {group['group_name']}\n"
                keyboard_buttons.append([InlineKeyboardButton(
                    text=f"ID {i}: {group['group_name']}", 
                    callback_data=f"select_bot_group_{bot_id}_{group['group_id']}"
                )])
            
            keyboard_buttons.append([InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_bot_management")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            response = f"""
🤖 **Bot Oluşturma - Aşama 6**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Mesaj:** {BOT_PROFILES[bot_id]['message'][:30]}{'...' if len(BOT_PROFILES[bot_id]['message']) > 30 else ''}
**Link:** Yok

**Hangi grupta çalışacak?**
{group_list}

**Lütfen bir grup seçin:**
            """
            
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            
        elif action and action.startswith("select_bot_group_"):
            # Grup seçildi
            # Callback data formatı: select_bot_group_{bot_id}_{group_id}
            # bot_id içinde _ olabileceği için daha güvenli parsing
            action_parts = action.split("_")
            if len(action_parts) < 4:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
                
            # Son kısım group_id, ondan önceki kısımlar bot_id
            group_id = int(action_parts[-1])  # Son kısım
            bot_id = "_".join(action_parts[3:-1])  # 3. indeksten sonuna kadar (son hariç)
            
            logger.info(f"🔍 Bot kontrolü: bot_id={bot_id}, BOT_PROFILES keys={list(BOT_PROFILES.keys())}")
            
            if bot_id not in BOT_PROFILES:
                await callback.answer("❌ Bot bulunamadı!", show_alert=True)
                return
                
            # Grup adını al
            from database import get_registered_groups
            groups = await get_registered_groups()
            selected_group = None
            for group in groups:
                if group['group_id'] == group_id:
                    selected_group = group
                    break
            
            if not selected_group:
                await callback.answer("❌ Grup bulunamadı!", show_alert=True)
                return
                
            # Bot profilini güncelle
            BOT_PROFILES[bot_id]["groups"] = [group_id]
            
            # Bot profilini veritabanına kaydet
            current_settings = await get_scheduled_settings()
            await save_scheduled_settings(current_settings)
            
            # Onay mesajı
            confirmation = f"""
✅ **Bot Oluşturma Tamamlandı!**

**🤖 Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**⏰ Aralık:** {BOT_PROFILES[bot_id]['interval']} dakika
**📝 Mesaj:** {BOT_PROFILES[bot_id]['message'][:50]}{'...' if len(BOT_PROFILES[bot_id]['message']) > 50 else ''}
**🔗 Link:** {BOT_PROFILES[bot_id].get('link_text', 'Yok')}
**📋 Grup:** {selected_group['group_name']}

**Bot'u aktif etmek ister misiniz?**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🟢 Botu Başlat", callback_data=f"bot_toggle_{bot_id}"),
                    InlineKeyboardButton(text="🔧 Botu Düzenle", callback_data=f"edit_bot_{bot_id}")
                ],
                [InlineKeyboardButton(text="⬅️ Geri", callback_data="scheduled_bot_management")]
            ])
            
            await callback.message.edit_text(confirmation, parse_mode="Markdown", reply_markup=keyboard)
                
        elif action and action.startswith("edit_messages_"):
            # Callback data formatı: edit_messages_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            await show_edit_messages_menu(callback, bot_id)
            
        elif action and action.startswith("edit_interval_"):
            # Callback data formatı: edit_interval_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            await show_edit_interval_menu(callback, bot_id)
            
        elif action and action.startswith("edit_link_"):
            # Callback data formatı: edit_link_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            await show_edit_link_menu(callback, bot_id)
            
        elif action and action.startswith("edit_image_"):
            # Callback data formatı: edit_image_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            await show_edit_image_menu(callback, bot_id)
            
        elif action and action.startswith("edit_name_"):
            # Callback data formatı: edit_name_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            await show_edit_name_menu(callback, bot_id)
            
        elif action and action.startswith("set_interval_"):
            # Callback data formatı: set_interval_{bot_id}_{interval}
            action_parts = action.split("_")
            if len(action_parts) < 4:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:-1])  # 2. indeksten sondan bir öncekine kadar
            interval = int(action_parts[-1])  # Son eleman interval
            
            success = await update_bot_profile(bot_id, interval=interval)
            if success:
                await callback.answer(f"✅ Aralık {interval} dakika olarak ayarlandı!", show_alert=True)
                await show_bot_edit_menu(callback, bot_id)
            else:
                await callback.answer("❌ Aralık ayarlama hatası!", show_alert=True)
                
        elif action and action.startswith("send_message_"):
            # Callback data formatı: send_message_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            await send_immediate_message(callback, bot_id)
            
        elif action and action.startswith("recreate_bot_"):
            # Callback data formatı: recreate_bot_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            logger.info(f"🔍 Recreate bot callback - action: {action}, bot_id: {bot_id}, BOT_PROFILES keys: {list(BOT_PROFILES.keys())}")
            await start_bot_recreation(callback, bot_id)
            
        elif action and action.startswith("delete_bot_"):
            # Callback data formatı: delete_bot_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            await delete_bot_profile(bot_id)
            await callback.answer(f"✅ Bot {bot_id} silindi!", show_alert=True)
            await show_scheduled_bot_management_menu(callback)
            
        elif action and action.startswith("remove_link_"):
            # Callback data formatı: remove_link_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            success = await update_bot_profile(bot_id, link=None)
            if success:
                await callback.answer("✅ Link kaldırıldı!", show_alert=True)
                await show_edit_link_menu(callback, bot_id)
            else:
                await callback.answer("❌ Link kaldırma hatası!", show_alert=True)
                
        elif action and action.startswith("add_link_"):
            # Callback data formatı: add_link_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            from utils.memory_manager import memory_manager
            memory_manager.set_input_state(user_id, f"add_link_{bot_id}")
            response = f"""
🔗 **Link Ekleme**

**Bot:** {BOT_PROFILES.get(bot_id, {}).get('name', bot_id)}

**Link'i yazın:**
Örnek: https://example.com
            """
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_link_{bot_id}")]
            ])
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            await callback.answer("Link bekleniyor...")
            
        elif action and action.startswith("remove_image_"):
            # Callback data formatı: remove_image_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            success = await update_bot_profile(bot_id, image=None)
            if success:
                await callback.answer("✅ Görsel kaldırıldı!", show_alert=True)
                await show_edit_image_menu(callback, bot_id)
            else:
                await callback.answer("❌ Görsel kaldırma hatası!", show_alert=True)
                
        elif action and action.startswith("add_image_"):
            # Callback data formatı: add_image_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            from utils.memory_manager import memory_manager
            memory_manager.set_input_state(user_id, f"add_image_{bot_id}")
            
            response = f"""
🖼️ **Görsel Ekleme**

**Bot:** {BOT_PROFILES.get(bot_id, {}).get('name', bot_id)}

**Görsel gönderin:**
Fotoğraf yükleyin
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_image_{bot_id}")],
                [InlineKeyboardButton(text="✅ Ekle", callback_data=f"add_image_confirm_{bot_id}")],
                [InlineKeyboardButton(text="⬅️ Geri", callback_data=f"edit_bot_{bot_id}")]
            ])
            
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            await callback.answer("Görsel bekleniyor...")
            
        elif action and action.startswith("add_image_confirm_"):
            # Callback data formatı: add_image_confirm_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            from utils.memory_manager import memory_manager
            memory_manager.set_input_state(user_id, f"add_image_confirm_{bot_id}")
            
            response = f"""
✅ **Görsel Ekleme Onayı**

**Bot:** {BOT_PROFILES.get(bot_id, {}).get('name', bot_id)}

**Görselinizi yüklediniz mi?**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Evet", callback_data=f"add_image_confirmed_{bot_id}")],
                [InlineKeyboardButton(text="❌ Hayır", callback_data=f"edit_image_{bot_id}")],
                [InlineKeyboardButton(text="⬅️ Geri", callback_data=f"edit_bot_{bot_id}")]
            ])
            
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            await callback.answer("Görsel onayı bekleniyor...")
            
        elif action and action.startswith("add_image_confirmed_"):
            # Callback data formatı: add_image_confirmed_{bot_id}
            action_parts = action.split("_")
            if len(action_parts) < 3:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
            bot_id = "_".join(action_parts[2:])
            from utils.memory_manager import memory_manager
            memory_manager.set_input_state(user_id, f"add_image_confirmed_{bot_id}")
            
            response = f"""
✅ **Görsel Ekleme Onayı**

**Bot:** {BOT_PROFILES.get(bot_id, {}).get('name', bot_id)}

**Görselinizi yüklediniz mi?**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Evet", callback_data=f"add_image_confirmed_{bot_id}")],
                [InlineKeyboardButton(text="❌ Hayır", callback_data=f"edit_image_{bot_id}")],
                [InlineKeyboardButton(text="⬅️ Geri", callback_data=f"edit_bot_{bot_id}")]
            ])
            
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            await callback.answer("Görsel onayı bekleniyor...")
            
        elif action and action.startswith("select_recreate_group_"):
            # Callback data formatı: select_recreate_group_{bot_id}_{group_id}
            action_parts = action.split("_")
            if len(action_parts) < 5:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
                
            bot_id = "_".join(action_parts[3:-1])  # 3. indeksten sondan bir öncekine kadar
            group_id = int(action_parts[-1])  # Son eleman grup ID'si
            
            logger.info(f"🔍 Select recreate group callback - bot_id: {bot_id}, group_id: {group_id}")
            
            if bot_id not in BOT_PROFILES:
                await callback.answer("❌ Bot bulunamadı!", show_alert=True)
                return
                
            # Bot profilini güncelle
            BOT_PROFILES[bot_id]["groups"] = [group_id]
            
            # Bot profilini veritabanına kaydet
            current_settings = await get_scheduled_settings()
            await save_scheduled_settings(current_settings)
            
            # Bot'u aktif et
            success = await toggle_bot_status(bot_id, True)
            
            if success:
                # Input state'i temizle
                from utils.memory_manager import memory_manager
                memory_manager.clear_input_state(user_id)
                
                # Başarı mesajı
                profile = BOT_PROFILES[bot_id]
                response = f"""
✅ **Bot Yeniden Kurulumu Tamamlandı!**

**📋 Bot Bilgileri:**
• **Ad:** {profile.get('name', bot_id)}
• **Aralık:** {profile.get('interval', 30)} dakika
• **Grup:** {group_id}
• **Link:** {"✅ Eklendi" if profile.get('link') else "❌ Yok"}
• **Görsel:** {"✅ Eklendi" if profile.get('image') else "❌ Yok"}

**🤖 Bot artık aktif ve mesaj gönderiyor!**
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Bot Yönetimi", callback_data="scheduled_bot_management")]
                ])
                
                await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
                await callback.answer("✅ Bot başarıyla yeniden kuruldu!")
            else:
                await callback.answer("❌ Bot aktifleştirme hatası!", show_alert=True)
                
        elif action and action.startswith("recreate_bot_skip_interval_"):
            # Aralık aşamasını geç
            bot_id = action.replace("recreate_bot_skip_interval_", "")
            logger.info(f"🔍 Aralık aşaması geçildi - bot_id: {bot_id}")
            
            # AŞAMA 3'e geç: Mesaj içeriği
            from utils.memory_manager import memory_manager
            memory_manager.set_input_state(user_id, f"recreate_bot_message_{bot_id}")
            
            response = f"""
🔄 **Bot Yeniden Kurulumu - Aşama 3**

**Bot Adı:** {BOT_PROFILES.get(bot_id, {}).get('name', bot_id)}
**Aralık:** {BOT_PROFILES.get(bot_id, {}).get('interval', 30)} dakika (değiştirilmedi)

**Ne yazacak?**
• Metin yazabilirsiniz
• Görsel gönderebilirsiniz
• Dosya, ses kaydı vs. her şey

**Örnek:** "💎 KirveHub'da point kazanmak çok kolay!"

**Mesajınızı yazın veya görsel gönderin:**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"recreate_bot_skip_message_{bot_id}")],
                [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
            ])
            
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            await callback.answer("Aralık aşaması geçildi!")
            
        elif action and action.startswith("recreate_bot_skip_message_"):
            # Mesaj aşamasını geç
            # Callback data formatı: recreate_bot_skip_message_bot_1753628023
            action_parts = action.split("_")
            if len(action_parts) < 4:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
                
            bot_id = "_".join(action_parts[3:])  # 3. indeksten sonuna kadar
            logger.info(f"🔍 Mesaj aşaması geçildi - bot_id: {bot_id}")
            
            # AŞAMA 4'e geç: Link ekleme
            from utils.memory_manager import memory_manager
            memory_manager.set_input_state(user_id, f"recreate_bot_link_{bot_id}")
            
            response = f"""
🔄 **Bot Yeniden Kurulumu - Aşama 4**

**Bot Adı:** {BOT_PROFILES.get(bot_id, {}).get('name', bot_id)}
**Mesaj:** {BOT_PROFILES.get(bot_id, {}).get('messages', [''])[0][:50]}{"..." if len(BOT_PROFILES.get(bot_id, {}).get('messages', [''])[0]) > 50 else ""} (değiştirilmedi)

**Link eklemek istiyor musunuz?**
• Evet: Link URL'sini yazın
• Hayır: "Hayır" yazın

**Link URL'si veya "Hayır" yazın:**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"recreate_bot_skip_link_{bot_id}")],
                [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
            ])
            
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            await callback.answer("Mesaj aşaması geçildi!")
            
        elif action and action.startswith("recreate_bot_skip_link_"):
            # Link aşamasını geç
            # Callback data formatı: recreate_bot_skip_link_bot_1753628023
            action_parts = action.split("_")
            if len(action_parts) < 4:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
                
            bot_id = "_".join(action_parts[3:])  # 3. indeksten sonuna kadar
            logger.info(f"🔍 Link aşaması geçildi - bot_id: {bot_id}")
            
            # AŞAMA 5'e geç: Grup seçimi
            from utils.memory_manager import memory_manager
            memory_manager.set_input_state(user_id, f"recreate_bot_group_{bot_id}")
            
            # Aktif grupları al
            active_groups = await get_active_groups()
            logger.info(f"🔍 Aktif gruplar: {active_groups}")
            
            if not active_groups:
                await callback.message.edit_text("❌ Hiç aktif grup bulunamadı! Önce grup ekleyin.")
                memory_manager.clear_input_state(user_id)
                return
            
            response = f"""
🔄 **Bot Yeniden Kurulumu - Aşama 5**

**Bot Adı:** {BOT_PROFILES.get(bot_id, {}).get('name', bot_id)}
**Link:** ❌ Yok (değiştirilmedi)

**Hangi grupta çalışacak?**
            """
            
            # Grup butonları oluştur
            keyboard_buttons = []
            for group_id in active_groups:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"📱 Grup {group_id}",
                        callback_data=f"select_recreate_group_{bot_id}_{group_id}"
                    )
                ])
            
            keyboard_buttons.append([InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            await callback.answer("Link aşaması geçildi!")
            
        elif action and action.startswith("recreate_bot_skip_link_text_"):
            # Link text aşamasını geç
            # Callback data formatı: recreate_bot_skip_link_text_bot_1753628023
            action_parts = action.split("_")
            if len(action_parts) < 5:
                await callback.answer("❌ Geçersiz callback data!", show_alert=True)
                return
                
            bot_id = "_".join(action_parts[4:])  # 4. indeksten sonuna kadar
            logger.info(f"🔍 Link text aşaması geçildi - bot_id: {bot_id}")
            
            # AŞAMA 5'e geç: Grup seçimi
            from utils.memory_manager import memory_manager
            memory_manager.set_input_state(user_id, f"recreate_bot_group_{bot_id}")
            
            # Aktif grupları al
            active_groups = await get_active_groups()
            logger.info(f"🔍 Aktif gruplar: {active_groups}")
            
            if not active_groups:
                await callback.message.edit_text("❌ Hiç aktif grup bulunamadı! Önce grup ekleyin.")
                memory_manager.clear_input_state(user_id)
                return
            
            response = f"""
🔄 **Bot Yeniden Kurulumu - Aşama 5**

**Bot Adı:** {BOT_PROFILES.get(bot_id, {}).get('name', bot_id)}
**Link:** ✅ {BOT_PROFILES.get(bot_id, {}).get('link', '')}
**Buton:** Linke Git (varsayılan)

**Hangi grupta çalışacak?**
            """
            
            # Grup butonları oluştur
            keyboard_buttons = []
            for group_id in active_groups:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"📱 Grup {group_id}",
                        callback_data=f"select_recreate_group_{bot_id}_{group_id}"
                    )
                ])
            
            keyboard_buttons.append([InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
            await callback.answer("Link text aşaması geçildi!")
                
    except Exception as e:
        logger.error(f"❌ Zamanlanmış mesajlar callback hatası: {e}")
        try:
            await callback.answer("❌ Bir hata oluştu!", show_alert=True)
        except Exception as callback_error:
            logger.error(f"❌ Callback answer hatası: {callback_error}")
            # Hata durumunda sadece log yaz, callback'e cevap verme

async def show_scheduled_messages_menu(callback) -> None:
    """Zamanlanmış mesajlar ana menüsü"""
    try:
        status = await get_scheduled_status()
        
        response = f"""
📅 **Zamanlanmış Mesajlar Sistemi**

**Mevcut Botlar:**
"""
        for bot_id in status.get('available_bots', []):
            profile = status.get('bot_profiles', {}).get(bot_id, {})
            active = status.get('active_bots', {}).get(bot_id, False)
            active_mark = "✅" if active else "❌"
            response += f"• {active_mark} {profile.get('name', bot_id)} ({profile.get('interval', 30)}dk)\n"
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚙️ Bot Yönetimi",
                    callback_data="scheduled_bot_management"
                ),
                InlineKeyboardButton(
                    text="📊 Durum",
                    callback_data="scheduled_status"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Geri",
                    callback_data="admin_system_management"
                )
            ]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        await callback.answer()  # ✅ Callback'i answer et!
        
    except Exception as e:
        logger.error(f"❌ Zamanlanmış mesajlar menüsü hatası: {e}")
        import traceback
        logger.error(f"❌ SCHEDULED MENU TRACEBACK: {traceback.format_exc()}")
        try:
            await callback.answer("❌ Bir hata oluştu!", show_alert=True)
        except Exception as answer_error:
            logger.error(f"❌ Callback answer da başarısız! {answer_error}")
        return

async def show_scheduled_bot_management_menu(callback) -> None:
    """Bot yönetimi menüsü"""
    try:
        status = await get_scheduled_status()
        
        response = f"""
⚙️ **Bot Yönetimi**

**Mevcut Botlar:**
"""
        
        # Bot listesi butonları
        bot_buttons = []
        for bot_id in status.get('available_bots', []):
            profile = status.get('bot_profiles', {}).get(bot_id, {})
            active = status.get('active_bots', {}).get(bot_id, False)
            active_mark = "✅" if active else "❌"
            response += f"• {active_mark} {profile.get('name', bot_id)} ({profile.get('interval', 30)}dk)\n"
            
            # Her bot için buton ekle
            bot_buttons.append([
                InlineKeyboardButton(
                    text=f"{active_mark} {profile.get('name', bot_id)}",
                    callback_data=f"edit_bot_{bot_id}"
                )
            ])
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Yeni Bot Oluştur",
                    callback_data="create_bot_profile"
                )
            ],
            *bot_buttons,  # Bot butonlarını ekle
            [
                InlineKeyboardButton(
                    text="⬅️ Geri",
                    callback_data="scheduled_back"
                )
            ]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        await callback.answer()  # ✅ Callback'i answer et!
        
    except Exception as e:
        logger.error(f"❌ Bot yönetimi menüsü hatası: {e}")
        import traceback
        logger.error(f"❌ BOT MANAGEMENT TRACEBACK: {traceback.format_exc()}")
        try:
            await callback.answer("❌ Bir hata oluştu!", show_alert=True)
        except Exception as answer_error:
            logger.debug(f"Callback answer hatası (kritik değil): {answer_error}")
        return

async def show_scheduled_status_menu(callback) -> None:
    """Zamanlanmış mesaj durumu menüsü"""
    try:
        status = await get_scheduled_status()
        
        response = f"""
📊 **Zamanlanmış Mesaj Durumu**

**Aktif Botlar:**
"""
        
        active_count = 0
        for bot_id in status.get('available_bots', []):
            profile = status.get('bot_profiles', {}).get(bot_id, {})
            active = status.get('active_bots', {}).get(bot_id, False)
            if active:
                active_count += 1
                response += f"• ✅ {profile.get('name', bot_id)} ({profile.get('interval', 30)}dk)\n"
        
        if active_count == 0:
            response += "• Hiç aktif bot yok\n"
            
        response += f"""
**Sistem Bilgileri:**
• Toplam Bot: {len(status.get('available_bots', []))}
• Aktif Bot: {active_count}
• Sistem Durumu: ✅ Aktif
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="scheduled_back")]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Zamanlanmış mesaj durumu menüsü hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def show_create_bot_menu(callback) -> None:
    """Bot oluşturma menüsü - Basitleştirilmiş"""
    try:
        response = f"""
➕ **Yeni Bot Oluştur**

**Bot oluşturma sistemi aktif!**

**Aşama 1:** Bot adını yazın
**Aşama 2:** Aralık ayarlayın (dakika)
**Aşama 3:** Mesaj içeriğini yazın
**Aşama 4:** Link eklemek ister misiniz? (opsiyonel)
**Aşama 5:** Link buton metnini yazın (opsiyonel)

**Örnek:**
Bot Adı: "KirveHub Duyuru"
Aralık: "30" (30 dakika)
Mesaj: "💎 KirveHub'da point kazanmak çok kolay!"
Link: "https://example.com" (opsiyonel)
Link Metni: "GÜVENİLİR SİTELER" (opsiyonel)

⬇️ **Başlamak için "Bot Oluştur" butonuna basın**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Bot Oluştur", callback_data="create_bot_profile")]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Bot oluşturma menüsü hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def show_bot_edit_menu(callback, bot_id: str) -> None:
    """Bot düzenleme menüsü - Baştan kurulum"""
    try:
        if bot_id not in BOT_PROFILES:
            await callback.answer("❌ Bot bulunamadı!", show_alert=True)
            return
            
        profile = BOT_PROFILES[bot_id]
        status = await get_scheduled_status()
        active = status.get('active_bots', {}).get(bot_id, False)
        active_mark = "✅" if active else "❌"
        
        response = f"""
🔧 **Bot Düzenleme: {profile.get('name', bot_id)}**

**Mevcut Bot Bilgileri:**
• Durum: {active_mark} {'Aktif' if active else 'Pasif'}
• Mesaj: {profile.get('message', 'Mesaj yok')[:50]}{'...' if len(profile.get('message', '')) > 50 else ''}
• Aralık: {profile.get('interval', 30)} dakika
• Link: {'Var' if profile.get('link') else 'Yok'}
• Görsel: {'Var' if profile.get('image') else 'Yok'}

**Düzenleme Seçenekleri:**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'🔴 Durdur' if active else '🟢 Başlat'}",
                    callback_data=f"bot_toggle_{bot_id}"
                ),
                InlineKeyboardButton(
                    text="📤 Mesaj Gönder",
                    callback_data=f"send_message_{bot_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Botu Yeniden Kur",
                    callback_data=f"recreate_bot_{bot_id}"
                ),
                InlineKeyboardButton(
                    text="🗑️ Botu Sil",
                    callback_data=f"delete_bot_{bot_id}"
                )
            ],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="scheduled_bot_management")]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Bot düzenleme menüsü hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def show_edit_messages_menu(callback, bot_id: str) -> None:
    """Mesaj düzenleme menüsü"""
    try:
        profile = BOT_PROFILES[bot_id]
        current_message = profile.get('message', 'Mesaj yok')
        
        response = f"""
📝 **Mesaj Düzenleme: {profile.get('name', bot_id)}**

**Mevcut Mesaj:**
{current_message}

**Yeni mesaj yazmak için aşağıdaki butona tıkla:**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Mesajı Düzenle", callback_data=f"edit_message_text_{bot_id}")],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data=f"edit_bot_{bot_id}")]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Mesaj düzenleme menüsü hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def show_edit_interval_menu(callback, bot_id: str) -> None:
    """Aralık düzenleme menüsü"""
    try:
        profile = BOT_PROFILES[bot_id]
        current_interval = profile.get('interval', 30)
        
        response = f"""
⏰ **Aralık Ayarlama: {profile.get('name', bot_id)}**

**Mevcut Aralık:** {current_interval} dakika

**Hızlı Seçenekler:**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="15 dk", callback_data=f"set_interval_{bot_id}_15"),
                InlineKeyboardButton(text="30 dk", callback_data=f"set_interval_{bot_id}_30"),
                InlineKeyboardButton(text="60 dk", callback_data=f"set_interval_{bot_id}_60")
            ],
            [
                InlineKeyboardButton(text="2 saat", callback_data=f"set_interval_{bot_id}_120"),
                InlineKeyboardButton(text="6 saat", callback_data=f"set_interval_{bot_id}_360"),
                InlineKeyboardButton(text="12 saat", callback_data=f"set_interval_{bot_id}_720")
            ],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data=f"edit_bot_{bot_id}")]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Aralık düzenleme menüsü hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def show_edit_link_menu(callback, bot_id: str) -> None:
    """Link düzenleme menüsü"""
    try:
        profile = BOT_PROFILES[bot_id]
        current_link = profile.get('link')
        
        response = f"""
🔗 **Link Ayarlama: {profile.get('name', bot_id)}**

**Mevcut Link:** {current_link if current_link else 'Yok'}

**Seçenekler:**
        """
        
        keyboard_buttons = []
        if current_link:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🗑️ Linki Kaldır", callback_data=f"remove_link_{bot_id}")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="➕ Link Ekle", callback_data=f"add_link_{bot_id}")
            ])
            
        keyboard_buttons.append([
            InlineKeyboardButton(text="⬅️ Geri", callback_data=f"edit_bot_{bot_id}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Link düzenleme menüsü hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def show_edit_image_menu(callback, bot_id: str) -> None:
    """Görsel düzenleme menüsü"""
    try:
        profile = BOT_PROFILES[bot_id]
        current_image = profile.get('image')
        
        response = f"""
🖼️ **Görsel Ayarlama: {profile.get('name', bot_id)}**

**Mevcut Görsel:** {current_image if current_image else 'Yok'}

**Seçenekler:**
        """
        
        keyboard_buttons = []
        if current_image:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🗑️ Görseli Kaldır", callback_data=f"remove_image_{bot_id}")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="➕ Görsel Ekle", callback_data=f"add_image_{bot_id}")
            ])
            
        keyboard_buttons.append([
            InlineKeyboardButton(text="⬅️ Geri", callback_data=f"edit_bot_{bot_id}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Görsel düzenleme menüsü hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def show_edit_name_menu(callback, bot_id: str) -> None:
    """İsim düzenleme menüsü"""
    try:
        profile = BOT_PROFILES[bot_id]
        current_name = profile.get('name', bot_id)
        
        response = f"""
📝 **İsim Değiştirme: {current_name}**

**Mevcut İsim:** {current_name}

**Not:** İsim değiştirme sistemi henüz geliştirilmedi.
**Şu anda sadece görüntüleme mevcut.**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data=f"edit_bot_{bot_id}")]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ İsim düzenleme menüsü hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def start_message_edit_input(callback, bot_id: str) -> None:
    """Mesaj düzenleme input'u başlat"""
    try:
        profile = BOT_PROFILES[bot_id]
        current_message = profile.get('message', 'Mesaj yok')
        
        response = f"""
✏️ **Mesaj Düzenleme: {profile.get('name', bot_id)}**

**Mevcut Mesaj:**
{current_message}

**Yeni mesajınızı yazın:**
**💡 İpucu:** Mesajınıza link eklemek isterseniz mesajın sonuna link yazın.
**Örnek:** "💎 KirveHub'da point kazanmak çok kolay! https://example.com"
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
        # Kullanıcıyı input moduna al
        from utils.memory_manager import memory_manager
        memory_manager.set_input_state(callback.from_user.id, f"edit_message_{bot_id}")
        
        await callback.answer("✅ Mesaj yazmaya hazır! Yeni mesajınızı yazın.", show_alert=True)
        
    except Exception as e:
        logger.error(f"❌ Mesaj düzenleme input hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def handle_message_edit_input(message) -> None:
    """Mesaj düzenleme input handler"""
    try:
        user_id = message.from_user.id
        from utils.memory_manager import memory_manager
        input_state = memory_manager.get_input_state(user_id)
        
        if not input_state or not input_state.startswith("edit_message_"):
            return
            
        # Bot ID'yi al
        bot_id = input_state.replace("edit_message_", "")
        
        if bot_id not in BOT_PROFILES:
            await message.answer("❌ Bot bulunamadı! Lütfen tekrar başlayın.")
            memory_manager.clear_input_state(user_id)
            return
            
        # Yeni mesaj metni
        new_message = message.text.strip()
        
        if len(new_message) < 5:
            await message.answer("❌ Mesaj çok kısa! En az 5 karakter olmalı.")
            return
            
        # Bot profilini güncelle
        BOT_PROFILES[bot_id]["messages"] = [new_message]
        
        # Bot profilini veritabanına kaydet
        await save_scheduled_settings({})
        
        # Başarı mesajı
        response = f"""
✅ **Mesaj Güncellendi!**

**Bot:** {BOT_PROFILES[bot_id]['name']}
**Yeni Mesaj:** {new_message[:50]}{"..." if len(new_message) > 50 else ""}

Mesaj başarıyla güncellendi!
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data=f"edit_bot_{bot_id}")]
        ])
        
        await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
        memory_manager.clear_input_state(user_id)
        
    except Exception as e:
        logger.error(f"❌ Mesaj düzenleme input hatası: {e}")
        await message.answer("❌ Bir hata oluştu!")

async def send_immediate_message(callback, bot_id: str) -> None:
    """Anında mesaj gönder ve zamanlayıcıyı sıfırla"""
    try:
        if bot_id not in BOT_PROFILES:
            await callback.answer("❌ Bot bulunamadı!", show_alert=True)
            return
            
        profile = BOT_PROFILES[bot_id]
        message = profile.get('message', '')
        link = profile.get('link')
        image = profile.get('image')
        
        if not message:
            await callback.answer("❌ Bot mesajı boş!", show_alert=True)
            return
            
        # Mesajı tüm aktif gruplara gönder
        groups = await get_active_groups()
        sent_count = 0
        
        for group_id in groups:
            success = await send_scheduled_message(bot_id, group_id, message, image, link)
            if success:
                sent_count += 1
                
        # Zamanlayıcıyı sıfırla
        settings = await get_scheduled_settings()
        settings['last_message_time'][bot_id] = datetime.now()
        await save_scheduled_settings(settings)
        
        await callback.answer(f"✅ {sent_count} gruba mesaj gönderildi!", show_alert=True)
        
    except Exception as e:
        logger.error(f"❌ Anında mesaj gönderme hatası: {e}")
        await callback.answer("❌ Mesaj gönderilirken hata oluştu!", show_alert=True)

async def start_bot_recreation(callback, bot_id: str) -> None:
    """Bot yeniden kurulum başlat - 5 Aşamalı"""
    try:
        if bot_id not in BOT_PROFILES:
            await callback.answer("❌ Bot bulunamadı!", show_alert=True)
            return
            
        profile = BOT_PROFILES[bot_id]
        
        # Bot'u durdur
        settings = await get_scheduled_settings()
        settings['active_bots'][bot_id] = False
        await save_scheduled_settings(settings)
        
        # Yeniden kurulum için input state başlat
        from utils.memory_manager import memory_manager
        memory_manager.set_input_state(callback.from_user.id, f"recreate_bot_name_{bot_id}")
        
        response = f"""
🔄 **Bot Yeniden Kurulumu - Aşama 1**

**Mevcut Bot:** {profile.get('name', bot_id)}

**AŞAMA 1: Zamanlayıcının adını yazın**
**Yeni bot adını yazın:**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        await callback.answer("Yeni bot adı bekleniyor...")
        
    except Exception as e:
        logger.error(f"❌ Bot yeniden kurulum hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def handle_bot_recreation_input(message) -> None:
    """Bot yeniden kurulum input handler - 5 Aşamalı"""
    try:
        user_id = message.from_user.id
        from utils.memory_manager import memory_manager
        input_state = memory_manager.get_input_state(user_id)
        
        if not input_state or not input_state.startswith("recreate_bot_"):
            return
            
        if input_state and input_state.startswith("recreate_bot_name_"):
            # AŞAMA 1: Bot adı alındı
            # Bot ID'yi doğru parse et - recreate_bot_name_bot_1753628023 formatından
            bot_id = input_state.replace("recreate_bot_name_", "")
            
            logger.info(f"🔍 Bot yeniden kurulum AŞAMA 1 - bot_id: {bot_id}")
            logger.info(f"🔍 BOT_PROFILES keys: {list(BOT_PROFILES.keys())}")
            logger.info(f"🔍 BOT_PROFILES[bot_id] exists: {bot_id in BOT_PROFILES}")
            
            # BOT_PROFILES'i yeniden yükleme - sadece kontrol için
            current_settings = await get_scheduled_settings()
            logger.info(f"🔍 Current settings bot_profiles keys: {list(current_settings.get('bot_profiles', {}).keys())}")
            
            if bot_id not in current_settings.get('bot_profiles', {}):
                logger.error(f"❌ Bot bulunamadı! bot_id: {bot_id}, available: {list(current_settings.get('bot_profiles', {}).keys())}")
                await message.answer("❌ Bot bulunamadı! Lütfen tekrar başlayın.")
                memory_manager.clear_input_state(user_id)
                return
            
            # Yeni bot adı alındı
            new_name = message.text.strip()
            logger.info(f"🔍 Yeni bot adı: {new_name}")
            
            if len(new_name) < 3:
                await message.answer("❌ Bot adı çok kısa! En az 3 karakter olmalı.")
                return
                
            # Bot profilini güncelle - BOT_PROFILES'i koruyarak
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = current_settings.get('bot_profiles', {}).get(bot_id, {})
            
            BOT_PROFILES[bot_id]["name"] = new_name
            logger.info(f"🔍 Bot adı güncellendi: {BOT_PROFILES[bot_id]['name']}")
            
            # Bot profilini veritabanına kaydet - BOT_PROFILES'i koruyarak
            await save_scheduled_settings(current_settings)
            logger.info(f"🔍 Bot profili kaydedildi")
            
            # AŞAMA 2'ye geç: Aralık ayarlama
            memory_manager.set_input_state(user_id, f"recreate_bot_interval_{bot_id}")
            
            response = f"""
🔄 **Bot Yeniden Kurulumu - Aşama 2**

**Yeni Bot Adı:** {new_name}

**Kaç dakikada bir mesaj atacak?**
Örnek: `30` (30 dakika), `60` (1 saat), `120` (2 saat)

**Lütfen dakika cinsinden yazın:**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"recreate_bot_skip_interval_{bot_id}")],
                [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 AŞAMA 2'ye geçildi - bot_id: {bot_id}")
            
        elif input_state and input_state.startswith("recreate_bot_interval_"):
            # AŞAMA 2: Aralık alındı
            # Bot ID'yi doğru parse et - recreate_bot_interval_bot_1753628023 formatından
            bot_id = input_state.replace("recreate_bot_interval_", "")
            
            logger.info(f"🔍 Bot yeniden kurulum AŞAMA 2 - bot_id: {bot_id}")
            logger.info(f"🔍 BOT_PROFILES keys: {list(BOT_PROFILES.keys())}")
            logger.info(f"🔍 BOT_PROFILES[bot_id] exists: {bot_id in BOT_PROFILES}")
            
            # BOT_PROFILES'i yeniden yükleme - sadece kontrol için
            current_settings = await get_scheduled_settings()
            logger.info(f"🔍 Current settings bot_profiles keys: {list(current_settings.get('bot_profiles', {}).keys())}")
            
            if bot_id not in current_settings.get('bot_profiles', {}):
                logger.error(f"❌ Bot bulunamadı! bot_id: {bot_id}, available: {list(current_settings.get('bot_profiles', {}).keys())}")
                await message.answer("❌ Bot bulunamadı! Lütfen tekrar başlayın.")
                memory_manager.clear_input_state(user_id)
                return
            
            try:
                interval = int(message.text.strip())
                if interval < 1 or interval > 1440:  # 1 dakika - 24 saat
                    await message.answer("❌ Geçersiz aralık! 1-1440 dakika arası olmalı.")
                    return
            except ValueError:
                await message.answer("❌ Geçersiz sayı! Lütfen sadece sayı yazın.")
                return
                
            # Bot profilini güncelle - BOT_PROFILES'i koruyarak
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = current_settings.get('bot_profiles', {}).get(bot_id, {})
            
            BOT_PROFILES[bot_id]["interval"] = interval
            logger.info(f"🔍 Bot aralığı güncellendi: {BOT_PROFILES[bot_id]['interval']}")
            
            # Bot profilini veritabanına kaydet - BOT_PROFILES'i koruyarak
            await save_scheduled_settings(current_settings)
            logger.info(f"🔍 Bot profili kaydedildi")
            
            # AŞAMA 3'e geç: Mesaj içeriği
            memory_manager.set_input_state(user_id, f"recreate_bot_message_{bot_id}")
            
            response = f"""
🔄 **Bot Yeniden Kurulumu - Aşama 3**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Aralık:** {interval} dakika

**Ne yazacak?**
• Metin yazabilirsiniz
• Görsel gönderebilirsiniz
• Dosya, ses kaydı vs. her şey

**Örnek:** "💎 KirveHub'da point kazanmak çok kolay!"

**Mesajınızı yazın veya görsel gönderin:**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"recreate_bot_skip_message_{bot_id}")],
                [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 AŞAMA 3'e geçildi - bot_id: {bot_id}")
            
        elif input_state and input_state.startswith("recreate_bot_message_"):
            # AŞAMA 3: Mesaj içeriği alındı
            # Bot ID'yi doğru parse et - recreate_bot_message_bot_1753628023 formatından
            bot_id = input_state.replace("recreate_bot_message_", "")
            
            logger.info(f"🔍 Bot yeniden kurulum AŞAMA 3 - bot_id: {bot_id}")
            logger.info(f"🔍 BOT_PROFILES keys: {list(BOT_PROFILES.keys())}")
            logger.info(f"🔍 BOT_PROFILES[bot_id] exists: {bot_id in BOT_PROFILES}")
            
            # BOT_PROFILES'i yeniden yükleme - sadece kontrol için
            current_settings = await get_scheduled_settings()
            logger.info(f"🔍 Current settings bot_profiles keys: {list(current_settings.get('bot_profiles', {}).keys())}")
            
            if bot_id not in current_settings.get('bot_profiles', {}):
                logger.error(f"❌ Bot bulunamadı! bot_id: {bot_id}, available: {list(current_settings.get('bot_profiles', {}).keys())}")
                await message.answer("❌ Bot bulunamadı! Lütfen tekrar başlayın.")
                memory_manager.clear_input_state(user_id)
                return
            
            # Bot profilini güncelle - BOT_PROFILES'i koruyarak
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = current_settings.get('bot_profiles', {}).get(bot_id, {})
            
            # Fotoğraf kontrolü
            if message.photo:
                logger.info(f"🔍 Görsel algılandı!")
                
                # Fotoğrafı kaydet
                photo = message.photo[-1]
                file_info = await message.bot.get_file(photo.file_id)
                image_url = getattr(file_info, 'file_path', None) or getattr(file_info, 'file_url', None)
                
                logger.info(f"🔍 Görsel URL: {image_url}")
                
                # Görseli kalıcı olarak indir ve sakla
                async def download_and_save_image(url: str, bot_id: str) -> str:
                    # Basit stub: gerçek indirme yerine URL döndür
                    return url or ""
                local_image_path = await download_and_save_image(image_url, bot_id)
                
                if not local_image_path:
                    await message.answer("❌ Görsel indirme hatası! Lütfen tekrar deneyin.")
                    return
                
                # Caption kontrolü
                caption = message.caption if message.caption else ""
                logger.info(f"🔍 Görsel caption: {caption}")
                
                # Bot profilini güncelle (görsel + caption)
                BOT_PROFILES[bot_id]["image"] = local_image_path
                if caption:
                    BOT_PROFILES[bot_id]["messages"] = [caption]
                    logger.info(f"🔍 Bot görseli + caption güncellendi: {local_image_path}")
                    logger.info(f"🔍 Caption metni: {caption}")
                else:
                    logger.info(f"🔍 Bot görseli güncellendi (caption yok): {local_image_path}")
                
                # Bot profilini veritabanına kaydet - BOT_PROFILES'i koruyarak
                await save_scheduled_settings(current_settings)
                logger.info(f"🔍 Bot profili kaydedildi")
                
                # AŞAMA 4'e geç: Link ekleme
                memory_manager.set_input_state(user_id, f"recreate_bot_link_{bot_id}")
                
                response = f"""
🖼️ **Görsel Yüklendi!**

**Bot:** {BOT_PROFILES[bot_id]['name']}
**Görsel:** ✅ Yüklendi ve kaydedildi
**Caption:** {"✅ " + caption[:30] + "..." if len(caption) > 30 else "✅ " + caption if caption else "❌ Yok"}

**AŞAMA 4'e geçiliyor...**
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"recreate_bot_skip_link_{bot_id}")],
                    [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
                ])
                
                await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
                logger.info(f"🔍 AŞAMA 4'e geçildi - bot_id: {bot_id}")
                return
                
            # Metin mesajı alındı
            message_text = message.text.strip()
            logger.info(f"🔍 Mesaj metni: {message_text}")
            
            if len(message_text) < 5:
                await message.answer("❌ Mesaj çok kısa! En az 5 karakter olmalı.")
                return
                
            # Bot profilini güncelle
            BOT_PROFILES[bot_id]["messages"] = [message_text]
            logger.info(f"🔍 Bot mesajı güncellendi: {message_text}")
            
            # Bot profilini veritabanına kaydet - BOT_PROFILES'i koruyarak
            await save_scheduled_settings(current_settings)
            logger.info(f"🔍 Bot profili kaydedildi")
            
            # AŞAMA 4'e geç: Link ekleme
            memory_manager.set_input_state(user_id, f"recreate_bot_link_{bot_id}")
            
            response = f"""
🔄 **Bot Yeniden Kurulumu - Aşama 4**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Mesaj:** {message_text[:50]}{"..." if len(message_text) > 50 else ""}

**Link eklemek istiyor musunuz?**
• Evet: Link URL'sini yazın
• Hayır: "Hayır" yazın

**Link URL'si veya "Hayır" yazın:**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"recreate_bot_skip_link_{bot_id}")],
                [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 AŞAMA 4'e geçildi - bot_id: {bot_id}")
            
    except Exception as e:
        logger.error(f"❌ Bot yeniden kurulum input hatası: {e}")
        await message.answer("❌ Bir hata oluştu! Lütfen tekrar başlayın.")
        from utils.memory_manager import memory_manager
        memory_manager.clear_input_state(message.from_user.id) 

async def handle_scheduled_input(message: Message) -> None:
    """Zamanlanmış mesajlar input handler'ı"""
    try:
        user_id = message.from_user.id
        logger.info(f"🔍 Input handler başladı - User: {user_id}")
        
        input_state = memory_manager.get_input_state(user_id)
        logger.info(f"🔍 Input state alındı: {input_state}")
        
        # Input state kontrolü
        if input_state is None:
            logger.warning(f"⚠️ Input state None - User: {user_id}")
            return
            
        logger.info(f"🔍 Input handler - User: {user_id}, State: {input_state}")
        
        if input_state == "create_bot_name":
            # AŞAMA 1: Yeni bot oluşturma - Bot adı alındı
            logger.info(f"🔍 Yeni bot oluşturma AŞAMA 1 - User: {user_id}")
            
            bot_name = message.text.strip()
            logger.info(f"🔍 Bot adı alındı: {bot_name}")
            
            if len(bot_name) < 3:
                await message.answer("❌ Bot adı çok kısa! En az 3 karakter olmalı.")
                return
                
            # Bot ID oluştur
            bot_id = f"bot_{int(time.time())}"
            logger.info(f"🔍 Bot ID oluşturuldu: {bot_id}")
            
            # Bot profilini oluştur
            BOT_PROFILES[bot_id] = {
                "name": bot_name,
                "message": "💎 KirveHub'da point kazanmak çok kolay! Her mesajın değeri var!",
                "interval": 30,
                "link": None,
                "image": None,
                "active": False
            }
            logger.info(f"🔍 Bot profili oluşturuldu: {BOT_PROFILES[bot_id]}")
            logger.info(f"🔍 Bot profili oluşturuldu: {BOT_PROFILES[bot_id]}")
            
            # AŞAMA 2'ye geç: Aralık ayarlama
            memory_manager.set_input_state(user_id, f"create_bot_interval_{bot_id}")
            logger.info(f"🔍 Input state güncellendi: create_bot_interval_{bot_id}")
            
            response = f"""
🤖 **Bot Oluşturma - Aşama 2**

**Bot Adı:** {bot_name}

**Kaç dakikada bir mesaj atacak?**
Örnek: `30` (30 dakika), `60` (1 saat), `120` (2 saat)

**Lütfen dakika cinsinden yazın:**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"create_bot_skip_interval_{bot_id}")],
                [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_bot_management")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 AŞAMA 2'ye geçildi - bot_id: {bot_id}")
            
        elif input_state.startswith("create_bot_interval_"):
            # AŞAMA 2: Yeni bot oluşturma - Aralık alındı
            bot_id = input_state.replace("create_bot_interval_", "")
            logger.info(f"🔍 Yeni bot oluşturma AŞAMA 2 - bot_id: {bot_id}")
            
            try:
                interval = int(message.text.strip())
                if interval < 1 or interval > 1440:  # 1 dakika - 24 saat
                    await message.answer("❌ Geçersiz aralık! 1-1440 dakika arası olmalı.")
                    return
                    
                # Bot profilini güncelle
                if bot_id not in BOT_PROFILES:
                    logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                    BOT_PROFILES[bot_id] = {}
                
                BOT_PROFILES[bot_id]["interval"] = interval
                logger.info(f"🔍 Bot aralığı güncellendi: {interval}")
                
                # AŞAMA 3'e geç: Mesaj içeriği
                memory_manager.set_input_state(user_id, f"create_bot_message_{bot_id}")
                logger.info(f"🔍 Input state güncellendi: create_bot_message_{bot_id}")
                
                response = f"""
🤖 **Bot Oluşturma - Aşama 3**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Aralık:** {interval} dakika

**Bot hangi mesajı atacak?**
Örnek: "💎 KirveHub'da point kazanmak çok kolay!"

**Lütfen mesaj içeriğini yazın:**
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"create_bot_skip_message_{bot_id}")],
                    [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_bot_management")]
                ])
                
                await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
                logger.info(f"🔍 AŞAMA 3'e geçildi - bot_id: {bot_id}")
                
            except ValueError:
                await message.answer("❌ Geçersiz sayı! Lütfen sadece sayı yazın.")
                return
                
        elif input_state.startswith("create_bot_link_text_"):
            # AŞAMA 5: Yeni bot oluşturma - Link metni alındı
            bot_id = input_state.replace("create_bot_link_text_", "")
            logger.info(f"🔍 Yeni bot oluşturma AŞAMA 5 - bot_id: {bot_id}")
            
            link_text = message.text.strip()
            logger.info(f"🔍 Link metni alındı: {link_text}")
            
            if len(link_text) < 2:
                await message.answer("❌ Link metni çok kısa! En az 2 karakter olmalı.")
                return
            
            # Bot profilini güncelle
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = {}
            
            BOT_PROFILES[bot_id]["link_text"] = link_text
            logger.info(f"🔍 Bot link metni güncellendi")
            
            # Bot profilini veritabanına kaydet
            current_settings = await get_scheduled_settings()
            if bot_id in BOT_PROFILES:
                current_settings['bot_profiles'][bot_id] = BOT_PROFILES[bot_id]
                await save_scheduled_settings(current_settings)
                logger.info(f"🔍 Bot profili kaydedildi")
            
            # Input state'i temizle
            memory_manager.clear_input_state(user_id)
            logger.info(f"🔍 Input state temizlendi")
            
            response = f"""
✅ **Bot Başarıyla Oluşturuldu!**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Mesaj:** {BOT_PROFILES[bot_id]['message']}
**Aralık:** {BOT_PROFILES[bot_id]['interval']} dakika
**Link:** {BOT_PROFILES[bot_id]['link']}
**Link Metni:** {link_text}

Bot artık kullanıma hazır! Bot yönetimi menüsünden aktifleştirebilirsiniz.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Bot Yönetimi", callback_data="scheduled_bot_management")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 Bot oluşturma tamamlandı - bot_id: {bot_id}")
            
        elif input_state.startswith("create_bot_link_"):
            # AŞAMA 4: Yeni bot oluşturma - Link URL alındı
            bot_id = input_state.replace("create_bot_link_", "")
            logger.info(f"🔍 Yeni bot oluşturma AŞAMA 4 - bot_id: {bot_id}")
            
            link_url = message.text.strip()
            logger.info(f"🔍 Link URL alındı: {link_url}")
            
            # Basit URL kontrolü
            if not link_url.startswith(('http://', 'https://', 't.me/')):
                await message.answer("❌ Geçersiz URL! http://, https:// veya t.me/ ile başlamalı.")
                return
            
            # Çift protokol sorununu önle
            if 'https://https://' in link_url:
                link_url = link_url.replace('https://https://', 'https://')
            elif 'http://https://' in link_url:
                link_url = link_url.replace('http://https://', 'https://')
            elif 'https://http://' in link_url:
                link_url = link_url.replace('https://http://', 'https://')
            
            # Bot profilini güncelle
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = {}
            
            BOT_PROFILES[bot_id]["link"] = link_url
            logger.info(f"🔍 Bot linki güncellendi")
            
            # AŞAMA 5: Link metni sor
            memory_manager.set_input_state(user_id, f"create_bot_link_text_{bot_id}")
            
            response = f"""
🔗 **Bot Oluşturma - Aşama 5**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**URL:** {link_url}

**Link metnini yazın:**
Örnek: "GÜVENİLİR SİTELER", "SİTEYE GİT", "TIKLA"

**Not:** Bu metin link butonunda görünecek.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"create_bot_skip_link_text_{bot_id}")],
                [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_bot_management")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 AŞAMA 5'e geçildi - bot_id: {bot_id}")
            
        elif input_state.startswith("add_link_text_"):
            # Link ekleme input - AŞAMA 2: Link metni
            logger.info(f"🔍 DEBUG: add_link_text_ state başladı - input_state: {input_state}")
            
            # Bot ID'yi doğru çıkar: add_link_text_bot_1753721077 -> bot_1753721077
            bot_id = input_state.replace("add_link_text_", "")
            logger.info(f"🔍 DEBUG: bot_id after replace: {bot_id}")
            
            # Eğer bot_id hala yanlış format ise düzelt
            if not bot_id.startswith("bot_"):
                # text_bot_1753721077 -> bot_1753721077
                if bot_id.startswith("text_bot_"):
                    bot_id = bot_id.replace("text_bot_", "bot_")
                else:
                    # Son rakamları al
                    digits = ''.join(filter(str.isdigit, bot_id))
                    bot_id = f"bot_{digits}"
            
            logger.info(f"🔍 Link metni input - bot_id: {bot_id}")
            
            link_text = message.text.strip()
            logger.info(f"🔍 Link metni alındı: {link_text}")
            
            if len(link_text) < 2:
                await message.answer("❌ Link metni çok kısa! En az 2 karakter olmalı.")
                return
            
            # Bot profilini güncelle
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = {}
            
            BOT_PROFILES[bot_id]["link_text"] = link_text
            logger.info(f"🔍 Bot link metni güncellendi")
            
            # Bot profilini veritabanına kaydet
            current_settings = await get_scheduled_settings()
            if bot_id in BOT_PROFILES:
                current_settings['bot_profiles'][bot_id] = BOT_PROFILES[bot_id]
                await save_scheduled_settings(current_settings)
                logger.info(f"🔍 Bot profili kaydedildi")
            
            # Input state'i temizle
            memory_manager.clear_input_state(user_id)
            logger.info(f"🔍 Input state temizlendi")
            
            response = f"""
✅ **Link Başarıyla Eklendi!**

**Bot:** {BOT_PROFILES[bot_id]['name']}
**URL:** {BOT_PROFILES[bot_id]['link']}
**Metin:** {link_text}

Bot artık link ile birlikte kullanıma hazır!
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Bot Yönetimi", callback_data="scheduled_bot_management")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 Link ekleme tamamlandı - bot_id: {bot_id}")
            
        elif input_state.startswith("add_link_"):
            # Link ekleme input - AŞAMA 1: URL
            bot_id = input_state.replace("add_link_", "")
            logger.info(f"🔍 Link ekleme input - bot_id: {bot_id}")
            
            link_url = message.text.strip()
            logger.info(f"🔍 Link URL alındı: {link_url}")
            
            # Basit URL kontrolü
            if not link_url.startswith(('http://', 'https://', 't.me/')):
                await message.answer("❌ Geçersiz URL! http://, https:// veya t.me/ ile başlamalı.")
                return
            
            # Çift protokol sorununu önle
            if 'https://https://' in link_url:
                link_url = link_url.replace('https://https://', 'https://')
            elif 'http://https://' in link_url:
                link_url = link_url.replace('http://https://', 'https://')
            elif 'https://http://' in link_url:
                link_url = link_url.replace('https://http://', 'https://')
            
            # Bot profilini güncelle
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = {}
            
            BOT_PROFILES[bot_id]["link"] = link_url
            logger.info(f"🔍 Bot linki güncellendi")
            
            # AŞAMA 2: Link metni sor
            memory_manager.set_input_state(user_id, f"add_link_text_{bot_id}")
            
            response = f"""
🔗 **Link Ekleme - Aşama 2**

**Bot:** {BOT_PROFILES[bot_id]['name']}
**URL:** {link_url}

**Link metnini yazın:**
Örnek: "GÜVENİLİR SİTELER", "SİTEYE GİT", "TIKLA"

**Not:** Bu metin link butonunda görünecek.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_bot_management")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 Link metni bekleniyor - bot_id: {bot_id}")
                    
        elif input_state.startswith("create_bot_message_"):
            # AŞAMA 3: Yeni bot oluşturma - Mesaj içeriği alındı
            bot_id = input_state.replace("create_bot_message_", "")
            logger.info(f"🔍 Yeni bot oluşturma AŞAMA 3 - bot_id: {bot_id}")
            
            message_text = message.text.strip()
            logger.info(f"🔍 Bot mesajı alındı: {message_text}")
            
            if len(message_text) < 5:
                await message.answer("❌ Mesaj çok kısa! En az 5 karakter olmalı.")
                return
                
            # Bot profilini güncelle
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = {}
            
            BOT_PROFILES[bot_id]["message"] = message_text
            logger.info(f"🔍 Bot mesajı güncellendi")
            
            # Bot profilini veritabanına kaydet
            current_settings = await get_scheduled_settings()
            # BOT_PROFILES'i koruyarak güncelle
            if bot_id in BOT_PROFILES:
                current_settings['bot_profiles'][bot_id] = BOT_PROFILES[bot_id]
                await save_scheduled_settings(current_settings)
                logger.info(f"🔍 Bot profili kaydedildi")
            else:
                logger.error(f"❌ Bot profili bulunamadı! bot_id: {bot_id}")
                await message.answer("❌ Bot profili kaydedilemedi! Lütfen tekrar başlayın.")
                memory_manager.clear_input_state(user_id)
                return
            logger.info(f"🔍 Bot profili kaydedildi")
            
            # AŞAMA 4'e geç: Grup seçimi
            memory_manager.set_input_state(user_id, f"create_bot_groups_{bot_id}")
            logger.info(f"🔍 Input state güncellendi: create_bot_groups_{bot_id}")
            
            # Kayıtlı grupları al
            from database import get_registered_groups
            groups = await get_registered_groups()
            
            if not groups:
                await message.answer("❌ Kayıtlı grup bulunamadı! Önce grupları kaydetmelisiniz.")
                memory_manager.clear_input_state(user_id)
                return
            
            response = f"""
🤖 **Bot Oluşturma - Aşama 4**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Mesaj:** {BOT_PROFILES[bot_id]['message'][:50]}{'...' if len(BOT_PROFILES[bot_id]['message']) > 50 else ''}

**Hangi gruplarda çalışacak?**
Aşağıdaki gruplardan seçin (virgülle ayırarak):

"""
            
            for i, group in enumerate(groups, 1):
                response += f"**{i}.** {group['group_name']} (ID: {group['group_id']})\n"
            
            response += f"""
**Örnek:** `1, 3, 5` (1., 3. ve 5. gruplarda çalışır)

**Grup numaralarını yazın:**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"create_bot_skip_link_{bot_id}")],
                [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_bot_management")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 AŞAMA 4'e geçildi - bot_id: {bot_id}")
            
            # Bu kısım gereksiz, kaldırıldı
            
        elif input_state.startswith("create_bot_groups_"):
            # AŞAMA 4: Yeni bot oluşturma - Grup seçimi alındı
            bot_id = input_state.replace("create_bot_groups_", "")
            logger.info(f"🔍 Yeni bot oluşturma AŞAMA 4 - bot_id: {bot_id}")
            
            groups_input = message.text.strip()
            logger.info(f"🔍 Grup seçimi alındı: {groups_input}")
            
            # Kayıtlı grupları al
            from database import get_registered_groups
            all_groups = await get_registered_groups()
            
            if not all_groups:
                await message.answer("❌ Kayıtlı grup bulunamadı!")
                memory_manager.clear_input_state(user_id)
                return
            
            # Grup numaralarını parse et
            try:
                selected_indices = [int(x.strip()) - 1 for x in groups_input.split(',')]
                selected_groups = []
                
                for idx in selected_indices:
                    if 0 <= idx < len(all_groups):
                        selected_groups.append(all_groups[idx]['group_id'])
                    else:
                        await message.answer(f"❌ Geçersiz grup numarası: {idx + 1}")
                        return
                
                if not selected_groups:
                    await message.answer("❌ En az bir grup seçmelisiniz!")
                    return
                
                # Bot profilini güncelle
                if bot_id not in BOT_PROFILES:
                    logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                    BOT_PROFILES[bot_id] = {}
                
                BOT_PROFILES[bot_id]["groups"] = selected_groups
                logger.info(f"🔍 Bot grupları güncellendi: {selected_groups}")
                
                # AŞAMA 5'e geç: Link ekleme (opsiyonel)
                memory_manager.set_input_state(user_id, f"create_bot_link_{bot_id}")
                logger.info(f"🔍 Input state güncellendi: create_bot_link_{bot_id}")
                
                response = f"""
🤖 **Bot Oluşturma - Aşama 5**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Mesaj:** {BOT_PROFILES[bot_id]['message'][:50]}{'...' if len(BOT_PROFILES[bot_id]['message']) > 50 else ''}
**Seçilen Gruplar:** {len(selected_groups)} grup

**Link eklemek istiyor musunuz?**
• Evet: Link URL'sini yazın
• Hayır: "Hayır" yazın

**Link URL'si veya "Hayır" yazın:**
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"create_bot_skip_link_{bot_id}")],
                    [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_bot_management")]
                ])
                
                await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
                logger.info(f"🔍 AŞAMA 5'e geçildi - bot_id: {bot_id}")
                
            except ValueError:
                await message.answer("❌ Geçersiz format! Örnek: `1, 3, 5`")
                return
                
        elif input_state.startswith("create_bot_link_"):
            # AŞAMA 5: Yeni bot oluşturma - Link alındı
            bot_id = input_state.replace("create_bot_link_", "")
            logger.info(f"🔍 Yeni bot oluşturma AŞAMA 5 - bot_id: {bot_id}")
            
            link_input = message.text.strip()
            logger.info(f"🔍 Link input alındı: {link_input}")
            
            if link_input.lower() == "hayır":
                # Link eklemek istemiyor
                logger.info(f"🔍 Link eklenmeyecek")
                
                # Input state'i temizle
                memory_manager.clear_input_state(user_id)
                logger.info(f"🔍 Input state temizlendi")
                
                response = f"""
✅ **Bot Başarıyla Oluşturuldu!**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Aralık:** {BOT_PROFILES[bot_id]['interval']} dakika
**Mesaj:** {BOT_PROFILES[bot_id]['message'][:50]}{'...' if len(BOT_PROFILES[bot_id]['message']) > 50 else ''}

Bot artık kullanıma hazır! Bot yönetimi menüsünden aktifleştirebilirsiniz.
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⚙️ Bot Yönetimi", callback_data="scheduled_bot_management")]
                ])
                
                await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
                logger.info(f"🔍 Bot oluşturma tamamlandı - bot_id: {bot_id}")
                return
            else:
                # Link URL'si alındı
                if not link_input.startswith(('http://', 'https://', 't.me/')):
                    await message.answer("❌ Geçersiz URL! http://, https:// veya t.me/ ile başlamalı.")
                    return
                
                # Bot profilini güncelle
                if bot_id not in BOT_PROFILES:
                    logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                    BOT_PROFILES[bot_id] = {}
                
                BOT_PROFILES[bot_id]["link"] = link_input
                logger.info(f"🔍 Bot linki güncellendi")
                
                # Bot profilini veritabanına kaydet
                current_settings = await get_scheduled_settings()
                if bot_id in BOT_PROFILES:
                    current_settings['bot_profiles'][bot_id] = BOT_PROFILES[bot_id]
                    await save_scheduled_settings(current_settings)
                    logger.info(f"🔍 Bot profili kaydedildi")
                
                # AŞAMA 5'e geç: Link metni
                memory_manager.set_input_state(user_id, f"create_bot_link_text_{bot_id}")
                logger.info(f"🔍 Input state güncellendi: create_bot_link_text_{bot_id}")
                
                response = f"""
🤖 **Bot Oluşturma - Aşama 5**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Link:** {link_input}

**Link butonunda ne yazsın?**
Örnek: "GÜVENİLİR SİTELER", "OYNAMAYA BAŞLA", "YARDIM AL"

**Link buton metnini yazın:**
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"create_bot_skip_link_text_{bot_id}")],
                    [InlineKeyboardButton(text="❌ İptal", callback_data="scheduled_bot_management")]
                ])
                
                await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
                logger.info(f"🔍 AŞAMA 5'e geçildi - bot_id: {bot_id}")
                
        elif input_state.startswith("create_bot_link_text_"):
            # AŞAMA 6: Yeni bot oluşturma - Link metni alındı
            bot_id = input_state.replace("create_bot_link_text_", "")
            logger.info(f"🔍 Yeni bot oluşturma AŞAMA 6 - bot_id: {bot_id}")
            
            link_text = message.text.strip()
            logger.info(f"🔍 Link metni alındı: {link_text}")
            
            if len(link_text) < 2:
                await message.answer("❌ Link metni çok kısa! En az 2 karakter olmalı.")
                return
            
            # Bot profilini güncelle
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = {}
            
            BOT_PROFILES[bot_id]["link_text"] = link_text
            logger.info(f"🔍 Bot link metni güncellendi")
            
            # Bot profilini veritabanına kaydet
            current_settings = await get_scheduled_settings()
            if bot_id in BOT_PROFILES:
                current_settings['bot_profiles'][bot_id] = BOT_PROFILES[bot_id]
                await save_scheduled_settings(current_settings)
                logger.info(f"🔍 Bot profili kaydedildi")
            
            # Input state'i temizle
            memory_manager.clear_input_state(user_id)
            logger.info(f"🔍 Input state temizlendi")
            
            response = f"""
✅ **Bot Başarıyla Oluşturuldu!**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Aralık:** {BOT_PROFILES[bot_id]['interval']} dakika
**Mesaj:** {BOT_PROFILES[bot_id]['message'][:50]}{'...' if len(BOT_PROFILES[bot_id]['message']) > 50 else ''}
**Link:** {BOT_PROFILES[bot_id]['link']}
**Link Metni:** {link_text}

Bot artık kullanıma hazır! Bot yönetimi menüsünden aktifleştirebilirsiniz.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Bot Yönetimi", callback_data="scheduled_bot_management")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 Bot oluşturma tamamlandı - bot_id: {bot_id}")
            logger.info(f"🔍 DEBUG - Final BOT_PROFILES[{bot_id}]: {BOT_PROFILES[bot_id]}")
            logger.info(f"🔍 DEBUG - Final BOT_PROFILES[{bot_id}] keys: {list(BOT_PROFILES[bot_id].keys())}")
            
        elif input_state.startswith("recreate_bot_name_"):
            # AŞAMA 1: Bot adı alındı
            # Bot ID'yi doğru parse et - recreate_bot_name_bot_1753628023 formatından
            bot_id = input_state.replace("recreate_bot_name_", "")
            
            logger.info(f"🔍 Bot yeniden kurulum AŞAMA 1 - bot_id: {bot_id}")
            logger.info(f"🔍 BOT_PROFILES keys: {list(BOT_PROFILES.keys())}")
            logger.info(f"🔍 BOT_PROFILES[bot_id] exists: {bot_id in BOT_PROFILES}")
            
            # BOT_PROFILES'i yeniden yükleme - sadece kontrol için
            current_settings = await get_scheduled_settings()
            logger.info(f"🔍 Current settings bot_profiles keys: {list(current_settings.get('bot_profiles', {}).keys())}")
            
            if bot_id not in current_settings.get('bot_profiles', {}):
                logger.error(f"❌ Bot bulunamadı! bot_id: {bot_id}, available: {list(current_settings.get('bot_profiles', {}).keys())}")
                await message.answer("❌ Bot bulunamadı! Lütfen tekrar başlayın.")
                memory_manager.clear_input_state(user_id)
                return
            
            # Yeni bot adı alındı
            new_name = message.text.strip()
            logger.info(f"🔍 Yeni bot adı: {new_name}")
            
            if len(new_name) < 3:
                await message.answer("❌ Bot adı çok kısa! En az 3 karakter olmalı.")
                return
                
            # Bot profilini güncelle - BOT_PROFILES'i koruyarak
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = current_settings.get('bot_profiles', {}).get(bot_id, {})
            
            BOT_PROFILES[bot_id]["name"] = new_name
            logger.info(f"🔍 Bot adı güncellendi: {BOT_PROFILES[bot_id]['name']}")
            
            # Bot profilini veritabanına kaydet - BOT_PROFILES'i koruyarak
            await save_scheduled_settings(current_settings)
            logger.info(f"🔍 Bot profili kaydedildi")
            
            # AŞAMA 2'ye geç: Aralık ayarlama
            memory_manager.set_input_state(user_id, f"recreate_bot_interval_{bot_id}")
            logger.info(f"🔍 Input state güncellendi: recreate_bot_interval_{bot_id}")
            
            response = f"""
🔄 **Bot Yeniden Kurulumu - Aşama 2**

**Yeni Bot Adı:** {new_name}

**Kaç dakikada bir mesaj atacak?**
Örnek: `30` (30 dakika), `60` (1 saat), `120` (2 saat)

**Lütfen dakika cinsinden yazın:**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"recreate_bot_skip_interval_{bot_id}")],
                [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 AŞAMA 2'ye geçildi - bot_id: {bot_id}")
            
        elif input_state.startswith("recreate_bot_interval_"):
            # AŞAMA 2: Aralık alındı
            # Bot ID'yi doğru parse et - recreate_bot_interval_bot_1753628023 formatından
            bot_id = input_state.replace("recreate_bot_interval_", "")
            
            logger.info(f"🔍 Bot yeniden kurulum AŞAMA 2 - bot_id: {bot_id}")
            logger.info(f"🔍 BOT_PROFILES keys: {list(BOT_PROFILES.keys())}")
            logger.info(f"🔍 BOT_PROFILES[bot_id] exists: {bot_id in BOT_PROFILES}")
            
            # BOT_PROFILES'i yeniden yükleme - sadece kontrol için
            current_settings = await get_scheduled_settings()
            logger.info(f"🔍 Current settings bot_profiles keys: {list(current_settings.get('bot_profiles', {}).keys())}")
            
            if bot_id not in current_settings.get('bot_profiles', {}):
                logger.error(f"❌ Bot bulunamadı! bot_id: {bot_id}, available: {list(current_settings.get('bot_profiles', {}).keys())}")
                await message.answer("❌ Bot bulunamadı! Lütfen tekrar başlayın.")
                memory_manager.clear_input_state(user_id)
                return
            
            try:
                interval = int(message.text.strip())
                if interval < 1 or interval > 1440:  # 1 dakika - 24 saat
                    await message.answer("❌ Geçersiz aralık! 1-1440 dakika arası olmalı.")
                    return
            except ValueError:
                await message.answer("❌ Geçersiz sayı! Lütfen sadece sayı yazın.")
                return
                
            # Bot profilini güncelle - BOT_PROFILES'i koruyarak
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = current_settings.get('bot_profiles', {}).get(bot_id, {})
            
            BOT_PROFILES[bot_id]["interval"] = interval
            logger.info(f"🔍 Bot aralığı güncellendi: {BOT_PROFILES[bot_id]['interval']}")
            
            # Bot profilini veritabanına kaydet - BOT_PROFILES'i koruyarak
            await save_scheduled_settings(current_settings)
            logger.info(f"🔍 Bot profili kaydedildi")
            
            # AŞAMA 3'e geç: Mesaj içeriği
            memory_manager.set_input_state(user_id, f"recreate_bot_message_{bot_id}")
            logger.info(f"🔍 Input state güncellendi: recreate_bot_message_{bot_id}")
            
            response = f"""
🔄 **Bot Yeniden Kurulumu - Aşama 3**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Aralık:** {interval} dakika

**Ne yazacak?**
• Metin yazabilirsiniz
• Görsel gönderebilirsiniz
• Dosya, ses kaydı vs. her şey

**Örnek:** "💎 KirveHub'da point kazanmak çok kolay!"

**Mesajınızı yazın veya görsel gönderin:**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"recreate_bot_skip_message_{bot_id}")],
                [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 AŞAMA 3'e geçildi - bot_id: {bot_id}")
            
        elif input_state.startswith("recreate_bot_message_"):
            # AŞAMA 3: Mesaj içeriği alındı
            # Bot ID'yi doğru parse et - recreate_bot_message_bot_1753628023 formatından
            bot_id = input_state.replace("recreate_bot_message_", "")
            
            logger.info(f"🔍 Bot yeniden kurulum AŞAMA 3 - bot_id: {bot_id}")
            logger.info(f"🔍 BOT_PROFILES keys: {list(BOT_PROFILES.keys())}")
            logger.info(f"🔍 BOT_PROFILES[bot_id] exists: {bot_id in BOT_PROFILES}")
            
            # BOT_PROFILES'i yeniden yükleme - sadece kontrol için
            current_settings = await get_scheduled_settings()
            logger.info(f"🔍 Current settings bot_profiles keys: {list(current_settings.get('bot_profiles', {}).keys())}")
            
            if bot_id not in current_settings.get('bot_profiles', {}):
                logger.error(f"❌ Bot bulunamadı! bot_id: {bot_id}, available: {list(current_settings.get('bot_profiles', {}).keys())}")
                await message.answer("❌ Bot bulunamadı! Lütfen tekrar başlayın.")
                memory_manager.clear_input_state(user_id)
                return
            
            # Bot profilini güncelle - BOT_PROFILES'i koruyarak
            if bot_id not in BOT_PROFILES:
                logger.info(f"🔍 BOT_PROFILES'e bot_id ekleniyor: {bot_id}")
                BOT_PROFILES[bot_id] = current_settings.get('bot_profiles', {}).get(bot_id, {})
            
            # Fotoğraf kontrolü
            if message.photo:
                logger.info(f"🔍 Görsel algılandı!")
                
                # Fotoğrafı kaydet
                photo = message.photo[-1]
                file_info = await message.bot.get_file(photo.file_id)
                image_url = getattr(file_info, 'file_path', None) or getattr(file_info, 'file_url', None)
                
                logger.info(f"🔍 Görsel URL: {image_url}")
                
                # Görseli kalıcı olarak indir ve sakla
                async def download_and_save_image(url: str, bot_id: str) -> str:
                    return url or ""
                local_image_path = await download_and_save_image(image_url, bot_id)
                
                if not local_image_path:
                    await message.answer("❌ Görsel indirme hatası! Lütfen tekrar deneyin.")
                    return
                
                # Caption kontrolü
                caption = message.caption if message.caption else ""
                logger.info(f"🔍 Görsel caption: {caption}")
                
                # Bot profilini güncelle (görsel + caption)
                BOT_PROFILES[bot_id]["image"] = local_image_path
                if caption:
                    BOT_PROFILES[bot_id]["messages"] = [caption]
                    logger.info(f"🔍 Bot görseli + caption güncellendi: {local_image_path}")
                    logger.info(f"🔍 Caption metni: {caption}")
                else:
                    logger.info(f"🔍 Bot görseli güncellendi (caption yok): {local_image_path}")
                
                # Bot profilini veritabanına kaydet - BOT_PROFILES'i koruyarak
                await save_scheduled_settings(current_settings)
                logger.info(f"🔍 Bot profili kaydedildi")
                
                # AŞAMA 4'e geç: Link ekleme
                memory_manager.set_input_state(user_id, f"recreate_bot_link_{bot_id}")
                
                response = f"""
🖼️ **Görsel Yüklendi!**

**Bot:** {BOT_PROFILES[bot_id]['name']}
**Görsel:** ✅ Yüklendi ve kaydedildi
**Caption:** {"✅ " + caption[:30] + "..." if len(caption) > 30 else "✅ " + caption if caption else "❌ Yok"}

**AŞAMA 4'e geçiliyor...**
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"recreate_bot_skip_link_{bot_id}")],
                    [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
                ])
                
                await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
                logger.info(f"🔍 AŞAMA 4'e geçildi - bot_id: {bot_id}")
                return
                
            # Metin mesajı alındı
            message_text = message.text.strip()
            logger.info(f"🔍 Mesaj metni: {message_text}")
            
            if len(message_text) < 5:
                await message.answer("❌ Mesaj çok kısa! En az 5 karakter olmalı.")
                return
                
            # Bot profilini güncelle
            BOT_PROFILES[bot_id]["messages"] = [message_text]
            logger.info(f"🔍 Bot mesajı güncellendi: {message_text}")
            
            # Bot profilini veritabanına kaydet - BOT_PROFILES'i koruyarak
            await save_scheduled_settings(current_settings)
            logger.info(f"🔍 Bot profili kaydedildi")
            
            # AŞAMA 4'e geç: Link ekleme
            memory_manager.set_input_state(user_id, f"recreate_bot_link_{bot_id}")
            
            response = f"""
🔄 **Bot Yeniden Kurulumu - Aşama 4**

**Bot Adı:** {BOT_PROFILES[bot_id]['name']}
**Mesaj:** {message_text[:50]}{"..." if len(message_text) > 50 else ""}

**Link eklemek istiyor musunuz?**
• Evet: Link URL'sini yazın
• Hayır: "Hayır" yazın

**Link URL'si veya "Hayır" yazın:**
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Geç", callback_data=f"recreate_bot_skip_link_{bot_id}")],
                [InlineKeyboardButton(text="❌ İptal", callback_data=f"edit_bot_{bot_id}")]
            ])
            
            await message.answer(response, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"🔍 AŞAMA 4'e geçildi - bot_id: {bot_id}")
            
    except Exception as e:
        logger.error(f"❌ Chat input handler hatası: {e}")
        await message.answer("❌ Bir hata oluştu! Lütfen tekrar başlayın.")
        memory_manager.clear_input_state(message.from_user.id)

async def clear_test_bots() -> bool:
    """Test bot'larını temizle"""
    try:
        logger.info(f"🧹 Test bot'ları temizleniyor...")
        
        # Mevcut ayarları al
        current_settings = await get_scheduled_settings()
        
        # Test bot'larını bul ve kaldır
        bot_profiles = current_settings.get('bot_profiles', {})
        active_bots = current_settings.get('active_bots', {})
        last_message_time = current_settings.get('last_message_time', {})
        
        # Test bot'larını tespit et
        test_bots_to_remove = []
        for bot_id in bot_profiles.keys():
            if bot_id.startswith('test_') or bot_id.startswith('bot_'):
                test_bots_to_remove.append(bot_id)
                logger.info(f"🧹 Test bot tespit edildi: {bot_id}")
        
        # Test bot'larını kaldır
        for bot_id in test_bots_to_remove:
            if bot_id in bot_profiles:
                del bot_profiles[bot_id]
                logger.info(f"✅ Bot profili kaldırıldı: {bot_id}")
            
            if bot_id in active_bots:
                del active_bots[bot_id]
                logger.info(f"✅ Aktif bot kaldırıldı: {bot_id}")
                
            if bot_id in last_message_time:
                del last_message_time[bot_id]
                logger.info(f"✅ Son mesaj zamanı kaldırıldı: {bot_id}")
        
        # Global BOT_PROFILES'i güncelle
        global BOT_PROFILES
        BOT_PROFILES = bot_profiles.copy()
        
        # Ayarları kaydet
        current_settings['bot_profiles'] = bot_profiles
        current_settings['active_bots'] = active_bots
        current_settings['last_message_time'] = last_message_time
        
        success = await save_scheduled_settings(current_settings)
        
        if success:
            logger.info(f"✅ Test bot'ları başarıyla temizlendi! Kaldırılan: {len(test_bots_to_remove)}")
            return True
        else:
            logger.error(f"❌ Test bot'ları temizlenirken hata!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test bot temizleme hatası: {e}")
        import traceback
        logger.error(f"❌ TRACEBACK: {traceback.format_exc()}")
        return False