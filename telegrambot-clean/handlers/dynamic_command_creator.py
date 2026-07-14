"""
⚙️ Dinamik Komut Oluşturucu - KirveHub Bot
Admin'lerin özel komutlar oluşturabilmesi için sistem
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
# FSM import kaldırıldı - Manuel state management kullanılıyor
# Not: Gelecekte FSM'e geçilebilir, şu an manuel state management yeterli

from config import get_config
from database import get_db_pool
from utils.logger import logger

router = Router()

# Global variables
_bot_instance = None
command_creation_states = {}  # Komut oluşturma durumları
command_creation_timestamps = {}  # Komut oluşturma zamanları (TTL için)

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

# Memory leak önleme - Cleanup fonksiyonu
async def cleanup_old_command_states():
    """Eski komut oluşturma durumlarını temizle (TTL: 1 saat)"""
    import time
    current_time = time.time()
    to_delete = []
    
    for user_id, timestamp in command_creation_timestamps.items():
        if current_time - timestamp > 3600:  # 1 saat
            to_delete.append(user_id)
    
    for user_id in to_delete:
        if user_id in command_creation_states:
            del command_creation_states[user_id]
        if user_id in command_creation_timestamps:
            del command_creation_timestamps[user_id]
        logger.info(f"🧹 Eski komut oluşturma durumu temizlendi - User: {user_id}")
    
    if to_delete:
        logger.info(f"🧹 Toplam {len(to_delete)} eski komut durumu temizlendi")

# ==============================================
# KOMUT OLUŞTURMA SÜRECİ
# ==============================================

async def start_command_creation(callback: types.CallbackQuery) -> None:
    """Komut oluşturma sürecini başlat"""
    try:
        user_id = callback.from_user.id
        config = get_config()
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        # Komut oluşturma durumunu başlat
        import time
        command_creation_states[user_id] = {
            "step": "command_name",
            "data": {},
            "created_at": time.time()
        }
        command_creation_timestamps[user_id] = time.time()
        
        logger.info(f"🔧 Komut oluşturma başlatıldı - User: {user_id}")
        
        response = """
🔧 **DİNAMİK KOMUT OLUŞTURUCU**

**Adım 1/5: Komut Adı**

📝 **Komut adını yazın (başına ! ekleyin):**

**Örnekler:**
• `!siteler`
• `!oyun`
• `!bonus`
• `!yardim`

**Lütfen komut adını yazın:**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data="cancel_command_creation")]
        ])
        
        await callback.message.edit_text(
            response,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Komut oluşturma başlatma hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def handle_command_creation_input(message: types.Message) -> None:
    """Komut oluşturma adım girişlerini handle et"""
    try:
        user_id = message.from_user.id
        config = get_config()
        
        logger.info(f"🔧 DEBUG - handle_command_creation_input çağrıldı - User: {user_id}, Text: {message.text}")
        
        # TAM YETKİ: Komut oluşturma input yakalandı
        logger.info(f"✅ TAM YETKİ: KOMUT OLUŞTURMA INPUT YAKALANDI - User: {user_id}, Text: '{message.text}'")
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            logger.info(f"❌ Admin değil - User: {user_id}")
            return
        
        # Debug: Komut oluşturma durumu
        logger.info(f"🔧 KOMUT OLUŞTURMA DURUMU - User: {user_id}, States: {list(command_creation_states.keys())}")
        if user_id in command_creation_states:
            logger.info(f"🔧 KOMUT OLUŞTURMA AKTİF - User: {user_id}, Step: {command_creation_states[user_id].get('step', 'unknown')}")
        else:
            logger.info(f"🔧 KOMUT OLUŞTURMA PASİF - User: {user_id}")
        
        # Komut oluşturma sürecinde mi?
        if user_id not in command_creation_states:
            logger.info(f"❌ Komut oluşturma sürecinde değil - User: {user_id}")
            return  # Süreçte değilse normal handler'lara geç
        
        # Mesaj komut mu? Eğer komut ise normal handler'lara geç
        if message.text and message.text.startswith('/'):
            logger.info(f"❌ Komut mesajı - User: {user_id}, Text: {message.text}")
            return  # Komutları normal handler'lara bırak
        
        # ! ile başlayan mesajlar - KOMUT OLUŞTURMA SÜRECİNDE İSE İŞLE
        if message.text and message.text.startswith('!'):
            # Komut oluşturma sürecinde ise bu mesajı işle
            logger.info(f"✅ Komut oluşturma sürecinde ! mesajı - User: {user_id}, Text: {message.text}")
            # Bu mesajı işlemeye devam et, normal handler'lara bırakma
        
        process_data = command_creation_states[user_id]
        current_step = process_data["step"]
        
        logger.info(f"🔧 Komut oluşturma mesajı - User: {user_id}, Step: {current_step}, Text: {message.text}")
        
        # Adım işleme
        if current_step == "command_name":
            await handle_command_name_input(message, process_data)
        elif current_step == "command_scope":
            await handle_command_scope_input(message, process_data)
        elif current_step == "reply_text":
            await handle_reply_text_input(message, process_data)
        elif current_step == "button_text":
            await handle_button_text_input(message, process_data)
        elif current_step == "button_url":
            await handle_button_url_input(message, process_data)
        else:
            logger.warning(f"⚠️ Bilinmeyen adım: {current_step}")
        
    except Exception as e:
        logger.error(f"❌ Komut oluşturma input hatası: {e}")


async def handle_command_name_input(message: types.Message, process_data: dict) -> None:
    """Komut adı girişi"""
    try:
        user_id = message.from_user.id
        command_name = message.text.strip()
        
        # Komut adı kontrolü
        if not command_name.startswith('!'):
            await message.reply("❌ Komut adı ! ile başlamalı! Örnek: `!siteler`")
            return
        
        if len(command_name) < 2:
            await message.reply("❌ Komut adı çok kısa! Örnek: `!siteler`")
            return
        
        if len(command_name) > 20:
            await message.reply("❌ Komut adı çok uzun! Maksimum 20 karakter.")
            return
        
        process_data["data"]["command_name"] = command_name
        process_data["step"] = "command_scope"
        
        logger.info(f"✅ Komut adı kaydedildi: {command_name}")
        
        response = """
🔧 **DİNAMİK KOMUT OLUŞTURUCU**

**Adım 2/5: Kullanım Yeri**

📋 **Komut nerede kullanılacak?**

**1** - Sadece grup chatlerinde
**2** - Sadece özel mesajlarda  
**3** - Hem grup hem özel mesajlarda

**Lütfen bir seçenek yazın (1, 2 veya 3):**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data="cancel_command_creation")]
        ])
        
        await message.reply(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Komut adı input hatası: {e}")


async def handle_command_scope_input(message: types.Message, process_data: dict) -> None:
    """Kullanım yeri girişi"""
    try:
        user_id = message.from_user.id
        scope_text = message.text.strip()
        
        try:
            scope = int(scope_text)
            if scope not in [1, 2, 3]:
                await message.reply("❌ Geçersiz seçenek! 1, 2 veya 3 yazın.")
                return
        except ValueError:
            await message.reply("❌ Geçersiz sayı! 1, 2 veya 3 yazın.")
            return
        
        process_data["data"]["scope"] = scope
        process_data["step"] = "reply_text"
        
        scope_names = {1: "Grup", 2: "Özel", 3: "Her ikisi"}
        logger.info(f"✅ Kullanım yeri kaydedildi: {scope_names[scope]}")
        
        response = """
🔧 **DİNAMİK KOMUT OLUŞTURUCU**

**Adım 3/5: Yanıt Metni**

📝 **Komut yazıldığında bot ne cevap versin?**

**Örnekler:**
• "Güvenip oynayabileceğiniz sitelere aşağıdan ulaşabilirsiniz kirvelerim"
• "En iyi bonus siteleri için tıklayın"
• "Yardım için aşağıdaki butona tıklayın"

**Lütfen yanıt metnini yazın:**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data="cancel_command_creation")]
        ])
        
        await message.reply(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Kullanım yeri input hatası: {e}")


async def handle_reply_text_input(message: types.Message, process_data: dict) -> None:
    """Yanıt metni girişi"""
    try:
        user_id = message.from_user.id
        reply_text = message.text.strip()
        
        if len(reply_text) < 5:
            await message.reply("❌ Yanıt metni çok kısa! En az 5 karakter olmalı.")
            return
        
        if len(reply_text) > 1000:
            await message.reply("❌ Yanıt metni çok uzun! Maksimum 1000 karakter.")
            return
        
        process_data["data"]["reply_text"] = reply_text
        process_data["step"] = "button_text"
        
        logger.info(f"✅ Yanıt metni kaydedildi: {reply_text[:50]}...")
        
        response = """
🔧 **DİNAMİK KOMUT OLUŞTURUCU**

**Adım 4/5: Buton Metni**

📋 **Komutun tıklanabilir butonunda ne yazsın?**

**Örnekler:**
• "GÜVENİLİR SİTELER"
• "OYNAMAYA BAŞLA"
• "YARDIM AL"
• "BONUS SİTELERİ"

**Lütfen buton metnini yazın (boş bırakabilirsiniz):**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Atlayın", callback_data="skip_button_text")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="cancel_command_creation")]
        ])
        
        await message.reply(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Yanıt metni input hatası: {e}")


async def handle_button_text_input(message: types.Message, process_data: dict) -> None:
    """Buton metni girişi"""
    try:
        user_id = message.from_user.id
        button_text = message.text.strip()
        
        if len(button_text) > 64:
            await message.reply("❌ Buton metni çok uzun! Maksimum 64 karakter.")
            return
        
        process_data["data"]["button_text"] = button_text if button_text else None
        process_data["step"] = "button_url"
        
        logger.info(f"✅ Buton metni kaydedildi: {button_text}")
        
        response = """
🔧 **DİNAMİK KOMUT OLUŞTURUCU**

**Adım 5/5: Buton Bağlantısı**

🔗 **Butonun bağlantısı ne olsun?**

**Örnekler:**
• "https://www.kumarlayasiyorum9.com"
• "https://www.site.com"
• "https://t.me/kirvehub"

**Lütfen bağlantıyı yazın (boş bırakabilirsiniz):**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Atlayın", callback_data="skip_button_url")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="admin_command_creator")]
        ])
        
        await message.reply(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Buton metni input hatası: {e}")


async def handle_button_url_input(message: types.Message, process_data: dict) -> None:
    """Buton bağlantısı girişi ve komut oluşturma"""
    try:
        user_id = message.from_user.id
        button_url = message.text.strip()
        
        # URL kontrolü (opsiyonel)
        if button_url and not button_url.startswith(('http://', 'https://', 't.me/')):
            await message.reply("❌ Geçersiz URL! http://, https:// veya t.me/ ile başlamalı.")
            return
        
        if button_url and len(button_url) > 256:
            await message.reply("❌ URL çok uzun! Maksimum 256 karakter.")
            return
        
        process_data["data"]["button_url"] = button_url if button_url else None
        
        # Komutu veritabanına kaydet
        success = await save_custom_command(user_id, process_data["data"])
        
        if success:
            success_message = f"""
✅ **KOMUT BAŞARIYLA OLUŞTURULDU!**

🔧 **Komut:** `{process_data["data"]["command_name"]}`
📋 **Kullanım:** {get_scope_name(process_data["data"]["scope"])}
📝 **Yanıt:** {process_data["data"]["reply_text"][:50]}...
"""
            
            if process_data["data"]["button_text"]:
                success_message += f"🔘 **Buton:** {process_data['data']['button_text']}\n"
            
            if process_data["data"]["button_url"]:
                success_message += f"🔗 **Bağlantı:** {process_data['data']['button_url']}\n"
            
            success_message += "\n**Komut artık kullanıma hazır!**"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 Yeni Komut Oluştur", callback_data="admin_command_creator")],
                [InlineKeyboardButton(text="📋 Komutları Listele", callback_data="list_custom_commands")]
            ])
            
        else:
            success_message = """
❌ **KOMUT OLUŞTURULAMADI!**

**Hata:** Veritabanı kayıt hatası
**Çözüm:** Lütfen tekrar deneyin
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Tekrar Dene", callback_data="admin_command_creator")]
            ])
        
        await message.reply(success_message, parse_mode="Markdown", reply_markup=keyboard)
        
        # Durumu temizle
        if user_id in command_creation_states:
            del command_creation_states[user_id]
        
    except Exception as e:
        logger.error(f"❌ Buton URL input hatası: {e}")


async def save_custom_command(user_id: int, command_data: dict) -> bool:
    """Komutu veritabanına kaydet"""
    try:
        from database import add_custom_command
        
        success = await add_custom_command(
            command_name=command_data["command_name"],
            scope=command_data["scope"],
            response_message=command_data["reply_text"],
            button_text=command_data.get("button_text"),
            button_url=command_data.get("button_url"),
            created_by=user_id
        )
        
        if success:
            logger.info(f"✅ Dinamik komut kaydedildi: {command_data['command_name']}")
        else:
            logger.error(f"❌ Dinamik komut kaydedilemedi: {command_data['command_name']}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Komut kaydetme hatası: {e}")
        return False


def get_scope_name(scope: int) -> str:
    """Scope numarasından isim döndür"""
    scope_names = {
        1: "Sadece Grup",
        2: "Sadece Özel", 
        3: "Her İkisi"
    }
    return scope_names.get(scope, "Bilinmeyen")


# ==============================================
# CALLBACK HANDLERS
# ==============================================

async def handle_skip_button_text(callback: types.CallbackQuery) -> None:
    """Buton metni atlama"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in command_creation_states:
            await callback.answer("❌ Komut oluşturma süreci bulunamadı!", show_alert=True)
            return
        
        process_data = command_creation_states[user_id]
        process_data["data"]["button_text"] = None
        process_data["step"] = "button_url"
        
        response = """
🔧 **DİNAMİK KOMUT OLUŞTURUCU**

**Adım 5/5: Buton Bağlantısı**

🔗 **Butonun bağlantısı ne olsun?**

**Örnekler:**
• "https://www.kumarlayasiyorum9.com"
• "https://www.site.com"
• "https://t.me/kirvehub"

**Lütfen bağlantıyı yazın (boş bırakabilirsiniz):**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Atlayın", callback_data="skip_button_url")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="cancel_command_creation")]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Skip button text hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def handle_skip_button_url(callback: types.CallbackQuery) -> None:
    """Buton URL atlama ve komut oluşturma"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in command_creation_states:
            await callback.answer("❌ Komut oluşturma süreci bulunamadı!", show_alert=True)
            return
        
        process_data = command_creation_states[user_id]
        process_data["data"]["button_url"] = None
        
        # Komutu veritabanına kaydet
        success = await save_custom_command(user_id, process_data["data"])
        
        if success:
            success_message = f"""
✅ **KOMUT BAŞARIYLA OLUŞTURULDU!**

🔧 **Komut:** `{process_data["data"]["command_name"]}`
📋 **Kullanım:** {get_scope_name(process_data["data"]["scope"])}
📝 **Yanıt:** {process_data["data"]["reply_text"][:50]}...
"""
            
            if process_data["data"]["button_text"]:
                success_message += f"🔘 **Buton:** {process_data['data']['button_text']}\n"
            
            success_message += "\n**Komut artık kullanıma hazır!**"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 Yeni Komut Oluştur", callback_data="admin_command_creator")],
                [InlineKeyboardButton(text="📋 Komutları Listele", callback_data="list_custom_commands")]
            ])
            
        else:
            success_message = """
❌ **KOMUT OLUŞTURULAMADI!**

**Hata:** Veritabanı kayıt hatası
**Çözüm:** Lütfen tekrar deneyin
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Tekrar Dene", callback_data="admin_command_creator")]
            ])
        
        await callback.message.edit_text(success_message, parse_mode="Markdown", reply_markup=keyboard)
        
        # Durumu temizle
        if user_id in command_creation_states:
            del command_creation_states[user_id]
        
    except Exception as e:
        logger.error(f"❌ Skip button URL hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def cancel_command_creation(callback: types.CallbackQuery) -> None:
    """Komut oluşturma sürecini iptal et"""
    try:
        user_id = callback.from_user.id
        config = get_config()
        
        # Admin kontrolü (DB tabanlı)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        # Süreci iptal et
        if user_id in command_creation_states:
            del command_creation_states[user_id]
            logger.info(f"🔧 Komut oluşturma iptal edildi - User: {user_id}")
        
        response = """
❌ **KOMUT OLUŞTURMA İPTAL EDİLDİ**

Komut oluşturma süreci iptal edildi.
Normal bot kullanımına geri döndünüz.

**Kullanılabilir Komutlar:**
• `/adminpanel` - Admin paneli
• `/menu` - Kullanıcı menüsü
• `/yardim` - Yardım
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Yeni Komut Oluştur", callback_data="admin_command_creator")],
            [InlineKeyboardButton(text="📋 Komutları Listele", callback_data="list_custom_commands")]
        ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Komut oluşturma iptal hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def force_cancel_command_creation(user_id: int) -> bool:
    """Komut oluşturma sürecini zorla iptal et"""
    try:
        if user_id in command_creation_states:
            del command_creation_states[user_id]
            logger.info(f"🔧 Komut oluşturma zorla iptal edildi - User: {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Komut oluşturma iptal hatası: {e}")
        return False


async def list_custom_commands_handler(callback: types.CallbackQuery) -> None:
    """Komutları listele"""
    try:
        user_id = callback.from_user.id
        config = get_config()
        
        # Admin kontrolü (DB tabanlı)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        from database import list_custom_commands
        commands = await list_custom_commands()
        
        # Debug log ekle
        logger.info(f"🔍 Komut listesi alındı - Toplam: {len(commands)} komut")
        for cmd in commands:
            logger.info(f"📋 Komut: {cmd}")
        
        if not commands:
            response = """
📋 **DİNAMİK KOMUTLAR**

❌ **Henüz komut oluşturulmamış.**

Komut oluşturmak için "🔧 Yeni Komut Oluştur" butonuna tıklayın.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 Yeni Komut Oluştur", callback_data="admin_command_creator")],
                [InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="admin_back")]
            ])
            
        else:
            response = f"""
📋 **DİNAMİK KOMUTLAR**

**Toplam:** {len(commands)} komut

"""
            
            for i, cmd in enumerate(commands[:10], 1):  # İlk 10 komut
                scope_name = get_scope_name(cmd["scope"])
                response += f"**ID: {cmd['id']}** `{cmd['command_name']}` - {scope_name}\n"
                response += f"   📝 {cmd['response_message'][:30]}...\n"
                if cmd.get('button_text'):
                    response += f"   🔘 {cmd['button_text']}\n"
                response += f"   📅 {cmd['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
            
            if len(commands) > 10:
                response += f"... ve {len(commands) - 10} komut daha\n\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 Yeni Komut Oluştur", callback_data="admin_command_creator")],
                [InlineKeyboardButton(text="🗑️ Komut Sil", callback_data="delete_custom_command")],
                [InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="admin_back")]
            ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Komut listesi hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


# ==============================================
# KOMUT SİLME HANDLER'LARI
# ==============================================

async def delete_custom_command_handler(callback: types.CallbackQuery) -> None:
    """Komut silme handler'ı"""
    try:
        user_id = callback.from_user.id
        config = get_config()
        
        # Admin kontrolü (DB tabanlı)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        # Komutları listele
        from database import list_custom_commands
        commands = await list_custom_commands()
        
        if not commands:
            response = """
🗑️ **KOMUT SİLME**

❌ **Silinecek komut bulunamadı.**

Henüz hiç komut oluşturulmamış.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 Yeni Komut Oluştur", callback_data="admin_command_creator")],
                [InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="admin_back")]
            ])
            
        else:
            response = f"""
🗑️ **KOMUT SİLME**

**Silmek için ID yazın:**

"""
            
            for i, cmd in enumerate(commands[:10], 1):  # İlk 10 komut
                scope_name = get_scope_name(cmd["scope"])
                response += f"**ID: {cmd['id']}** `{cmd['command_name']}` - {scope_name}\n"
                response += f"   📝 {cmd['response_message'][:30]}...\n\n"
            
            if len(commands) > 10:
                response += f"... ve {len(commands) - 10} komut daha\n\n"
            
            response += """
**Kullanım:** `/komutsil ID`
**Örnek:** `/komutsil 1`

Komut ID'sini yazıp gönderin.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Ana Menü", callback_data="admin_back")]
            ])
        
        await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Komut silme listesi hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)





# ==============================================
# KOMUT ÇALIŞTIRMA HANDLER'LARI
# ==============================================

async def handle_custom_command(message: types.Message) -> None:
    """Dinamik komutları handle et"""
    try:
        user_id = message.from_user.id
        
        # Komut oluşturma sürecinde mi? Eğer evetse bu handler'ı çalıştırma
        if user_id in command_creation_states:
            # Komut oluşturma sürecinde olan kullanıcılar için dinamik komutları çalıştırma
            return
        
        # Mesaj boş mu kontrol et
        if not message.text:
            return
        
        # Mesaj ! ile başlıyor mu kontrol et - SADECE ! ile başlayan komutlar için
        if not message.text.startswith('!'):
            return
        
        command_text = message.text.strip()
        
        # Komut adını al
        command_name = command_text.split()[0] if command_text else ""
        
        if not command_name.startswith('!'):
            return
        
        # 🌐 ÖZEL KOMUT: !siteler - Site listesi (site_manager.py'de işlenir)
        # EN ÖNCE KONTROL ET - Bu komutu dynamic handler'a bırakma!
        if command_name.lower() == "!siteler":
            logger.debug(f"🌐 !siteler komutu site_manager'a bırakılıyor - User: {user_id}")
            return  # site_manager.py handler'ına bırak, burada işlem yapma
        
        # 📢 ÖZEL KOMUT: !tanitim - Bot tanıtım mesajı (main.py'de işlenir)
        if command_name.lower() == "!tanitim":
            logger.debug(f"📢 !tanitim komutu main.py'ye bırakılıyor - User: {user_id}")
            return  # main.py handler'ına bırak, burada işlem yapma
        
        # 🛡️ ÖZEL KOMUT: !mod, !modlar, !modekle, !modsil - Mod yönetimi (mod_handler.py'de işlenir)
        if command_name.lower() in ["!mod", "!modlar", "!modekle", "!modsil"]:
            logger.debug(f"🛡️ Mod komutu mod_handler'a bırakılıyor - User: {user_id}, Command: {command_name}")
            return  # mod_handler.py handler'ına bırak, burada işlem yapma
        
        # 🚫 ADMIN KOMUTLARI - Bu komutları dynamic handler yakalamaz, admin handler'lar işler
        ADMIN_COMMANDS = [
            '!marketfix', '!kategoriekle', '!kategoriliste', '!kategorisil', '!kategoriduzenle',
            '!siteekle', '!sitelistele', '!siteguncelle', '!sitesil',  # Site yönetimi (admin only)
            '!modekle', '!modsil',  # Mod yönetimi (admin only)
            '!adminpanel', '!kplog', '!grouplog', '!siparisler',
            '!sil', '!kick', '!ban', '!unban', '!warn'
        ]
        # NOT: !siteler HERKES için erişilebilir, bu yüzden whitelist'te DEĞİL!
        if command_name.lower() in ADMIN_COMMANDS:
            logger.info(f"⚠️ Admin komutu tespit edildi, atlanıyor: {command_name}")
            return  # Admin komutlarını kendi handler'larına bırak
        
        # 🛍️ ÖZEL KOMUT: !market - Grupta mesaj sil, özelden market aç
        if command_name.lower() == "!market":
            logger.info(f"🛍️ !market komutu yakalandı - User: {user_id}, Chat Type: {message.chat.type}")
            
            # Grupta ise mesajı sil (Rate limiter ile)
            if message.chat.type in ["group", "supergroup"]:
                from utils.safe_message_delete import safe_delete_message
                await safe_delete_message(message, reason="!market command")
            
            # Özelden market menüsünü aç - Evrensel fonksiyon kullan
            try:
                from handlers.market_callbacks import show_market_menu_universal
                
                # Evrensel market menüsünü göster
                success = await show_market_menu_universal(user_id, message=message)
                
                if success:
                    logger.info(f"✅ Market menüsü özelden gönderildi - User: {user_id}")
                else:
                    raise Exception("Market menu failed")
                
            except Exception as e:
                error_msg = str(e).lower()
                logger.error(f"❌ Market menüsü gönderme hatası: {e}", exc_info=True)
                
                # Kullanıcı botu başlatmamış
                if "bot was blocked" in error_msg or "user is deactivated" in error_msg or "chat not found" in error_msg:
                    try:
                        await message.reply(
                            "⚠️ **Market menüsünü açabilmem için beni özel mesajdan başlatmalısın!**\n\n"
                            "👉 [@KirveLastBot](https://t.me/KirveLastBot) - /start",
                            parse_mode="Markdown"
                        )
                    except Exception as send_error:
                        logger.debug(f"Market mesajı gönderme hatası (kritik değil): {send_error}")
                else:
                    try:
                        await message.reply(
                            "❌ Market menüsü yüklenirken hata oluştu!\n"
                            "Lütfen /menu komutu ile menüden Market'e gidin.",
                            parse_mode="Markdown"
                        )
                    except Exception as send_error:
                        logger.error(f"❌ Hata mesajı gönderilemedi: {send_error}")
            
            return  # !market işlendi, fonksiyondan çık
        
        # Scope belirle ve komut ara
        current_scope = 1 if message.chat.type != "private" else 2
        
        # Debug log
        logger.info(f"🔍 Dinamik komut aranıyor - Command: {command_name}, Scope: {current_scope}, Chat Type: {message.chat.type}")
        
        # Komutu veritabanından al
        from database import get_custom_command
        
        # Debug: Komut adını kontrol et
        logger.info(f"🔍 Komut adı: '{command_name}'")
        
        # Önce mevcut scope için ara
        command = await get_custom_command(command_name, current_scope)
        
        # Eğer bulunamadıysa, scope 3 (her ikisi) için de ara
        if not command:
            logger.info(f"🔍 Komut bulunamadı, scope 3 deneniyor - Command: {command_name}")
            command = await get_custom_command(command_name, 3)
        
        if command:
            logger.info(f"✅ Komut bulundu - Command: {command_name}, Response: {command.get('response_message', 'Yok')[:50]}...")
        else:
            logger.info(f"❌ Komut bulunamadı - Command: {command_name}")
            # Debug: Database'deki tüm komutları listele
            from database import list_custom_commands
            all_commands = await list_custom_commands()
            logger.info(f"🔍 Database'deki tüm komutlar: {all_commands}")
        
        if not command:
            return  # Komut bulunamadı, normal handler'lara geç
        
        # Yanıt oluştur
        reply_text = command.get("response_message", "Yanıt bulunamadı")
        
        # Buton varsa ekle
        keyboard = None
        if command.get("button_text") and command.get("button_url"):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=command["button_text"], url=command["button_url"])]
            ])
        
        # Yanıtı gönder
        await message.reply(reply_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Dinamik komut hatası: {e}")


# ==============================================
# ROUTER KAYITLARI - MANUEL HANDLER KULLANILDIĞI İÇİN KALDIRILDI
# ==============================================

# Router kayıtları kaldırıldı - Manuel handler kullanılıyor
# Callback handler'ları main.py'de manuel olarak kaydediliyor 

# Dinamik komut oluşturma sistemi - Genişletilmiş
async def create_link_command(command_name: str, link: str, description: str = "") -> bool:
    """Link komutu oluştur (!siteler gibi)"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Komut verilerini hazırla
            command_data = {
                "command": command_name,
                "type": "link",
                "content": link,
                "description": description,
                "active": True,
                "created_at": datetime.now().isoformat(),
                "usage_count": 0
            }
            
            # Database'e kaydet
            await conn.execute(
                    """
                    INSERT INTO custom_commands (command_name, scope, response_message, button_text, button_url, created_by, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (command_name, scope) DO UPDATE SET
                    response_message = $3, button_text = $4, button_url = $5, is_active = $7, updated_at = CURRENT_TIMESTAMP
                    """,
                    command_data["command"], command_data["scope"], command_data["content"],
                    command_data.get("button_text"), command_data.get("button_url"), command_data["created_by"],
                    command_data["active"]
                )
            
            logger.info(f"✅ Link komutu oluşturuldu: !{command_name}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Link komutu oluşturulurken hata: {e}")
        return False

async def create_scheduled_message_command(command_name: str, message: str, interval: int, profile: str = "default") -> bool:
    """Zamanlanmış mesaj komutu oluştur"""
    try:
        # Önce zamanlanmış mesaj oluştur
        from handlers.scheduled_messages import create_scheduled_message
        success = await create_scheduled_message(
            name=f"Komut: !{command_name}",
            message=message,
            interval=interval,
            profile=profile
        )
        
        if success:
            # Komut verilerini hazırla
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                command_data = {
                    "command": command_name,
                    "type": "scheduled_message",
                    "content": message,
                    "description": f"Zamanlanmış mesaj - {interval}dk aralık",
                    "active": True,
                    "created_at": datetime.now().isoformat(),
                    "usage_count": 0
                }
                
                # Database'e kaydet
                await conn.execute(
                    """
                    INSERT INTO custom_commands (command_name, scope, response_message, button_text, button_url, created_by, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (command_name, scope) DO UPDATE SET
                    response_message = $3, button_text = $4, button_url = $5, is_active = $7, updated_at = CURRENT_TIMESTAMP
                    """,
                    command_data["command"], command_data["scope"], command_data["content"],
                    command_data.get("button_text"), command_data.get("button_url"), command_data["created_by"],
                    command_data["active"]
                )
                
                logger.info(f"✅ Zamanlanmış mesaj komutu oluşturuldu: !{command_name}")
                return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"❌ Zamanlanmış mesaj komutu oluşturulurken hata: {e}")
        return False

async def get_all_custom_commands() -> List[Dict[str, Any]]:
    """Tüm özel komutları al"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.fetch(
                "SELECT * FROM custom_commands ORDER BY created_at DESC"
            )
            return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"❌ Özel komutlar alınırken hata: {e}")
        return []

async def toggle_custom_command(command_name: str, active: bool) -> bool:
    """Özel komutu aktif/pasif yap"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE custom_commands SET is_active = $1 WHERE command_name = $2",
                active, command_name
            )
            logger.info(f"✅ Komut durumu güncellendi: !{command_name} -> {active}")
            return True
    except Exception as e:
        logger.error(f"❌ Komut durumu güncellenirken hata: {e}")
        return False

async def delete_custom_command(command_name: str) -> bool:
    """Özel komutu sil"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM custom_commands WHERE command = $1",
                command_name
            )
            logger.info(f"✅ Komut silindi: !{command_name}")
            return True
    except Exception as e:
        logger.error(f"❌ Komut silinirken hata: {e}")
        return False 