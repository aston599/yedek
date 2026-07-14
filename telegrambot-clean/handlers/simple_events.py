"""
🎯 Basit Çekiliş Sistemi - KirveHub Bot
Sadece /cekilisyap komutu ve callback query'ler
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import types

from config import get_config
from handlers.admin_permission_manager import has_min_rank_db
from database import db_pool, get_registered_groups, get_db_pool
from utils.logger import logger

router = Router()

# Bot instance setter
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

async def _send_lottery_menu_privately(user_id: int):
    """Çekiliş menüsünü özel mesajla gönder"""
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Çekilişi Başlat", callback_data="lottery_type_lottery")],
            [InlineKeyboardButton(text="📋 Çekiliş Listesi", callback_data="lottery_list")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
        ])
        
        await _bot_instance.send_message(
            user_id,
            "🎯 **Çekiliş Yönetimi**\n\n"
            "Hangi tür çekiliş oluşturmak istiyorsunuz?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        logger.info(f"✅ Çekiliş menüsü özel mesajla gönderildi: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Çekiliş menüsü gönderilemedi: {e}")

# Geçici veri saklama (memory) - ARTIK KULLANILMIYOR! Memory manager kullan
# lottery_data = {}  # DEPRECATED: memory_manager.set_lottery_data() kullan

# Memory cleanup fonksiyonu - Artık memory_manager kullanıyor
async def cleanup_old_lottery_data():
    """Eski lottery data'ları temizle - Memory manager ile"""
    try:
        from utils.memory_manager import memory_manager
        # Memory manager'ın cache cleanup'ı otomatik çalışıyor
        # Gerekirse manuel temizlik buradan tetiklenebilir
        cache_manager = memory_manager.get_cache_manager()
        cache_manager.cleanup_expired()
        logger.info("🧹 Lottery data cleanup tamamlandı (memory_manager)")
    except Exception as e:
        logger.error(f"❌ Lottery data cleanup hatası: {e}")

async def create_lottery_command(message: Message):
    """Çekiliş oluşturma komutu - Hem message hem callback için"""
    try:
        # Admin kontrolü (DB tabanlı rank)
        user_id = message.from_user.id
        if not await has_min_rank_db(user_id, 3):
            return
        
        # Rate limiting - aynı kullanıcıdan 10 saniyede bir
        user_id = message.from_user.id
        current_time = datetime.now()
        
        # Memory manager kullanarak rate limiting kontrolü
        from utils.memory_manager import memory_manager
        existing_data = memory_manager.get_lottery_data(user_id)
        if existing_data:
            last_activity = existing_data.get('last_activity')
            if last_activity and (current_time - last_activity).total_seconds() < 10:
                await message.reply("⏳ Çok hızlı! 10 saniye bekleyin.")
                return
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Çekiliş komutu mesajı silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE ÇEKİLİŞ MENÜSÜ GÖNDER
                if _bot_instance:
                    await _send_lottery_menu_privately(user_id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        # Çekiliş türü seçim menüsü
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Çekilişi Başlat", callback_data="lottery_type_lottery")],
            [InlineKeyboardButton(text="📋 Çekiliş Listesi", callback_data="lottery_list")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
        ])
        
        await message.reply(
            "🎯 **Çekiliş Yönetimi**\n\n"
            "Hangi tür çekiliş oluşturmak istiyorsunuz?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Çekiliş komutu hatası: {e}")

async def create_lottery_callback(callback: CallbackQuery):
    """Çekiliş oluşturma callback'i"""
    try:
        # Admin kontrolü (DB tabanlı rank)
        if not await has_min_rank_db(callback.from_user.id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        # Rate limiting - aynı kullanıcıdan 10 saniyede bir
        user_id = callback.from_user.id
        current_time = datetime.now()
        
        # Memory manager kullanarak rate limiting kontrolü
        from utils.memory_manager import memory_manager
        existing_data = memory_manager.get_lottery_data(user_id)
        if existing_data:
            last_activity = existing_data.get('last_activity')
            if last_activity and (current_time - last_activity).total_seconds() < 10:
                await callback.answer("⏳ Çok hızlı! 10 saniye bekleyin.", show_alert=True)
                return
        
        # Çekiliş türü seçim menüsü
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Çekilişi Başlat", callback_data="lottery_type_lottery")],
            [InlineKeyboardButton(text="📋 Çekiliş Listesi", callback_data="lottery_list")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
        ])
        
        await callback.message.edit_text(
            "🎯 **Çekiliş Yönetimi**\n\n"
            "Hangi tür çekiliş oluşturmak istiyorsunuz?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Çekiliş callback hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.message(Command("cekilisyap"))
async def create_lottery_command_wrapper(message: Message):
    """Çekiliş oluşturma komutu wrapper"""
    await create_lottery_command(message)

@router.message(Command("cekilisler"))
async def list_lottery_command(message: Message):
    """Aktif çekilişleri listele komutu"""
    try:
        logger.info(f"🎯 /cekilisler komutu alındı - User: {message.from_user.id}")
        from handlers.event_participation import list_active_events
        await list_active_events(message)
        logger.info(f"✅ /cekilisler komutu tamamlandı - User: {message.from_user.id}")
    except Exception as e:
        logger.error(f"❌ List lottery command hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

@router.callback_query(F.data == "lottery_type_lottery")
async def select_lottery_type(callback: CallbackQuery):
    """Genel çekiliş türü seçildi"""
    try:
        # Admin kontrolü (DB tabanlı)
        if not await has_min_rank_db(callback.from_user.id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        # Memory manager kullanarak veriyi başlat
        user_id = callback.from_user.id
        from utils.memory_manager import memory_manager
        
        lottery_data = {
            "type": "lottery",
            "step": "cost",
            "created_at": datetime.now()
        }
        
        memory_manager.set_lottery_data(user_id, lottery_data)
        memory_manager.set_input_state(user_id, "lottery_cost")
        
        logger.info(f"🎯 LOTTERY DATA SET - User: {user_id}, Step: cost, Data: {lottery_data}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
        ])
        
        await callback.message.edit_text(
            "🎲 **Genel Çekiliş Oluşturma**\n\n"
            "Katılım ücreti kaç Kirve Point olsun?\n"
            "Örnek: `10` veya `5.50`\n\n"
            "**Lütfen ücreti yazın:**",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Lottery type selection hatası: {e}")

@router.callback_query(F.data == "lottery_type_bonus")
async def select_bonus_type(callback: CallbackQuery):
    """Chat bonus türü seçildi"""
    try:
        # Admin kontrolü (DB tabanlı)
        if not await has_min_rank_db(callback.from_user.id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        # Geçici veriyi başlat - Memory manager kullan
        user_id = callback.from_user.id
        from utils.memory_manager import memory_manager
        
        bonus_data = {
            "type": "bonus",
            "step": "duration",
            "created_at": datetime.now()
        }
        
        memory_manager.set_lottery_data(user_id, bonus_data)
        logger.info(f"🎯 BONUS DATA SET - User: {user_id}, Step: duration, Data: {bonus_data}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
        ])
        
        await callback.message.edit_text(
            "💬 **Chat Bonus Oluşturma**\n\n"
            "Bonus süresi kaç dakika olsun?\n"
            "Örnek: `30` veya `60`\n\n"
            "**Lütfen süreyi yazın:**",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Bonus type selection hatası: {e}")

@router.callback_query(F.data == "lottery_list")
async def show_lottery_list(callback: CallbackQuery):
    """Aktif çekilişleri listele"""
    try:
        # Admin kontrolü (DB tabanlı)
        if not await has_min_rank_db(callback.from_user.id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        events = await get_active_events()
        
        if not events:
            await callback.message.edit_text(
                "📋 **Aktif Çekiliş Yok**\n\n"
                "Şu anda aktif çekiliş bulunmuyor.",
                parse_mode="Markdown"
            )
            return
        
        event_list = ""
        for event in events:
            event_list += f"• **{event['title']}** - {event['entry_cost']} KP\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="lottery_back_to_menu")],
            [InlineKeyboardButton(text="❌ Kapat", callback_data="lottery_cancel")]
        ])
        
        await callback.message.edit_text(
            f"📋 **Aktif Çekilişler**\n\n{event_list}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Event list hatası: {e}")

@router.callback_query(F.data == "lottery_cancel")
async def cancel_lottery_creation(callback: CallbackQuery):
    """Çekiliş oluşturmayı iptal et"""
    try:
        # Admin kontrolü (DB tabanlı)
        if not await has_min_rank_db(callback.from_user.id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        # Geçici veriyi temizle - Memory manager kullan
        user_id = callback.from_user.id
        from utils.memory_manager import memory_manager
        
        existing_data = memory_manager.get_lottery_data(user_id)
        if existing_data:
            memory_manager.clear_lottery_data(user_id)
            logger.info(f"🧹 Çekiliş iptal edildi ve data temizlendi - User: {user_id}")
        
        await callback.message.edit_text(
            "❌ **Çekiliş oluşturma iptal edildi!**",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"❌ Event cancellation hatası: {e}")

@router.callback_query(F.data == "lottery_back_to_menu")
async def back_to_lottery_menu(callback: CallbackQuery):
    """Ana çekiliş menüsüne geri dön"""
    try:
        # Admin kontrolü (DB tabanlı)
        if not await has_min_rank_db(callback.from_user.id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        # Çekiliş türü seçim menüsü
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Çekilişi Başlat", callback_data="lottery_type_lottery")],
            [InlineKeyboardButton(text="📋 Çekiliş Listesi", callback_data="lottery_list")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
        ])
        
        await callback.message.edit_text(
            "🎯 **Çekiliş Yönetimi**\n\n"
            "Hangi tür çekiliş oluşturmak istiyorsunuz?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Back to menu hatası: {e}")

# Mesaj handler'ları - Çekiliş veri girişi için (MANUEL HANDLER)
async def handle_lottery_input(message: Message):
    """Çekiliş veri girişi handler'ı"""
    try:
        user_id = message.from_user.id
        
        # DEBUG: Her mesajı logla
        logger.info(f"🎯 LOTTERY INPUT HANDLER - User: {user_id}, Text: {message.text}")
        
        # Admin kontrolü (DB tabanlı rank)
        if not await has_min_rank_db(user_id, 3):
            logger.info(f"❌ Admin değil - User: {user_id}")
            return
        
        # Memory manager kullanarak event info'yu al
        from utils.memory_manager import memory_manager
        event_info = memory_manager.get_lottery_data(user_id)
        if not event_info:
            logger.info(f"❌ Lottery data yok - User: {user_id}")
            return  # Normal mesaj, bu handler'ı atla
        
        step = event_info.get("step")
        
        logger.info(f"🎯 Event input - User: {user_id}, Step: {step}, Text: {message.text}")
        
        if step == "cost":
            await handle_cost_input(message, event_info)
        elif step == "winners":
            await handle_winners_input(message, event_info)
        elif step == "description":
            await handle_description_input(message, event_info)
        elif step == "duration":
            await handle_duration_input(message, event_info)
        elif step == "multiplier":
            await handle_multiplier_input(message, event_info)
        else:
            logger.info(f"❌ Bilinmeyen step: {step} - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Event input handler hatası: {e}")

async def handle_cost_input(message: Message, event_info: Dict):
    """Katılım ücreti input handler'ı"""
    try:
        user_id = message.from_user.id
        
        try:
            cost = float(message.text)
            if cost <= 0:
                await message.reply("❌ Ücret pozitif olmalı!")
                return
        except ValueError:
            await message.reply("❌ Geçersiz ücret! Örnek: `10` veya `5.50`")
            return
        
        # Event info'yu güncelle
        event_info["entry_cost"] = cost
        event_info["step"] = "winners"
        
        # Memory manager'a kaydet
        from utils.memory_manager import memory_manager
        memory_manager.set_lottery_data(user_id, event_info)
        
        logger.info(f"🎯 COST INPUT COMPLETED - User: {user_id}, Cost: {cost}, Next step: winners")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
        ])
        
        await message.reply(
            "🎯 **Kaç kişi kazanacak?**\n\n"
            "Örnek: `3` veya `5`\n\n"
            "**Lütfen kazanan sayısını yazın:**",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Cost input hatası: {e}")

async def handle_winners_input(message: Message, event_info: Dict):
    """Kazanan sayısı input handler'ı"""
    try:
        user_id = message.from_user.id
        
        try:
            winners = int(message.text)
            if winners <= 0:
                await message.reply("❌ Kazanan sayısı pozitif olmalı!")
                return
        except ValueError:
            await message.reply("❌ Geçersiz sayı! Örnek: `3` veya `5`")
            return
        
        event_info["max_winners"] = winners
        event_info["step"] = "description"
        
        # Memory manager'a kaydet
        from utils.memory_manager import memory_manager
        memory_manager.set_lottery_data(user_id, event_info)
        
        logger.info(f"🎯 WINNERS INPUT COMPLETED - User: {user_id}, Winners: {winners}, Next step: description")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
        ])
        
        await message.reply(
            "📝 **Çekiliş açıklaması yazın**\n\n"
            "Örnek: `1000 TL Steam Kartı Çekilişi`\n\n"
            "**Lütfen açıklamayı yazın:**",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Winners input hatası: {e}")

async def handle_description_input(message: Message, event_info: Dict):
    """Açıklama input handler'ı"""
    try:
        user_id = message.from_user.id
        
        description = message.text.strip()
        if len(description) < 5:
            await message.reply("❌ Açıklama çok kısa! En az 5 karakter olmalı.")
            return
        
        event_info["description"] = description
        event_info["step"] = "group_selection"
        
        # Memory manager'a kaydet
        from utils.memory_manager import memory_manager
        memory_manager.set_lottery_data(user_id, event_info)
        
        logger.info(f"🎯 DESCRIPTION INPUT COMPLETED - User: {user_id}, Description: {description[:50]}..., Next step: group_selection")
        
        # Grup listesini getir
        from database import get_registered_groups
        groups = await get_registered_groups()
        
        if not groups:
            await message.reply("❌ Kayıtlı grup bulunamadı! Önce grupları kaydetmeniz gerekiyor.")
            return
        
        # Grup seçim menüsü
        group_list = ""
        keyboard_buttons = []
        
        for i, group in enumerate(groups, 1):
            group_list += f"**ID {i}:** {group['group_name']}\n"
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"ID {i}: {group['group_name']}", 
                callback_data=f"select_group_{group['group_id']}"
            )])
        
        keyboard_buttons.append([InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.reply(
            f"📋 **Hangi grupta paylaşılsın?**\n\n{group_list}\n"
            "**Lütfen bir grup seçin:**",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Description input hatası: {e}")

async def handle_duration_input(message: Message, event_info: Dict):
    """Süre input handler'ı (Chat Bonus için)"""
    try:
        user_id = message.from_user.id
        
        try:
            duration = int(message.text)
            if duration <= 0:
                await message.reply("❌ Süre pozitif olmalı!")
                return
        except ValueError:
            await message.reply("❌ Geçersiz süre! Örnek: `30` veya `60`")
            return
        
        event_info["duration_minutes"] = duration
        event_info["step"] = "multiplier"
        
        # Memory manager'a kaydet
        from utils.memory_manager import memory_manager
        memory_manager.set_lottery_data(user_id, event_info)
        
        logger.info(f"🎯 DURATION INPUT COMPLETED - User: {user_id}, Duration: {duration} minutes, Next step: multiplier")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
        ])
        
        await message.reply(
            "💬 **Bonus çarpanı kaç olsun?**\n\n"
            "Örnek: `2.00` (2x bonus) veya `1.50` (1.5x bonus)\n\n"
            "**Lütfen çarpanı yazın:**",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Duration input hatası: {e}")

async def handle_multiplier_input(message: Message, event_info: Dict):
    """Çarpan input handler'ı"""
    try:
        user_id = message.from_user.id
        
        try:
            multiplier = float(message.text)
            if multiplier <= 0:
                await message.reply("❌ Çarpan pozitif olmalı!")
                return
        except ValueError:
            await message.reply("❌ Geçersiz çarpan! Örnek: `2.00` veya `1.50`")
            return
        
        event_info["bonus_multiplier"] = multiplier
        
        # Memory manager'a kaydet
        from utils.memory_manager import memory_manager
        memory_manager.set_lottery_data(user_id, event_info)
        
        logger.info(f"🎯 MULTIPLIER INPUT COMPLETED - User: {user_id}, Multiplier: {multiplier}x, Ready for confirmation")
        
        # Onay mesajı
        confirmation = f"""
✅ **Chat Bonus Onayı**

**🎯 Tür:** Chat Bonus
**⏰ Süre:** {event_info['duration_minutes']} dakika
**💎 Çarpan:** {event_info['bonus_multiplier']}x
**📝 Açıklama:** {event_info.get('description', 'Chat Bonus Etkinliği')}

**Onaylıyor musunuz?**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Onayla", callback_data="lottery_confirm_create")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
        ])
        
        await message.reply(
            confirmation,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Multiplier input hatası: {e}")

@router.callback_query(lambda c: c.data and c.data.startswith("select_group_"))
async def select_group_for_event(callback: CallbackQuery):
    """Çekiliş için grup seçimi"""
    try:
        # Admin kontrolü (DB tabanlı)
        if not await has_min_rank_db(callback.from_user.id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        user_id = callback.from_user.id
        
        # Memory manager kullanarak event info'yu al
        from utils.memory_manager import memory_manager
        event_info = memory_manager.get_lottery_data(user_id)
        if not event_info:
            logger.error(f"❌ Çekiliş verisi bulunamadı - User: {user_id}")
            await callback.answer("❌ Çekiliş verisi bulunamadı!", show_alert=True)
            return
        
        # Seçilen grup ID'sini al
        group_id = int(callback.data.split("_")[-1])
        event_info["selected_group_id"] = group_id
        
        # Memory manager'a geri kaydet
        memory_manager.set_lottery_data(user_id, event_info)
        
        logger.info(f"🎯 GROUP SELECTED - User: {user_id}, Group ID: {group_id}")
        
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
        
        # Onay mesajı
        if event_info["type"] == "lottery":
            confirmation = f"""
✅ **Çekiliş Onayı**

**🎯 Tür:** Genel Çekiliş
**💰 Katılım Ücreti:** {event_info['entry_cost']:.2f} KP
**🏆 Kazanan Sayısı:** {event_info['max_winners']} kişi
**📝 Açıklama:** {event_info['description']}
**📋 Paylaşılacak Grup:** {selected_group['group_name']}

**Onaylıyor musunuz?**
            """
        else:  # bonus type
            confirmation = f"""
✅ **Chat Bonus Onayı**

**🎯 Tür:** Chat Bonus
**⏰ Süre:** {event_info['duration_minutes']} dakika
**💎 Çarpan:** {event_info['bonus_multiplier']}x
**📝 Açıklama:** {event_info['description']}
**📋 Paylaşılacak Grup:** {selected_group['group_name']}

**Onaylıyor musunuz?**
            """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Onayla", callback_data="lottery_confirm_create")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="lottery_cancel")]
        ])
        
        await callback.message.edit_text(
            confirmation,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Group selection hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.callback_query(F.data == "lottery_confirm_create")
async def confirm_lottery_creation(callback: CallbackQuery):
    """Çekiliş oluşturmayı onayla"""
    try:
        # Admin kontrolü (DB tabanlı)
        if not await has_min_rank_db(callback.from_user.id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        user_id = callback.from_user.id
        
        # Memory manager kullanarak event info'yu al
        from utils.memory_manager import memory_manager
        event_info = memory_manager.get_lottery_data(user_id)
        if not event_info:
            logger.error(f"❌ Çekiliş verisi bulunamadı - User: {user_id}")
            await callback.answer("❌ Çekiliş verisi bulunamadı!", show_alert=True)
            return
        
        logger.info(f"🎯 LOTTERY CREATION CONFIRMED - User: {user_id}, Event Info: {event_info}")
        
        # Etkinliği oluştur
        success, event_id = await create_event_in_db(event_info, user_id)
        
        if success:
            event_type = "Genel Çekiliş" if event_info["type"] == "lottery" else "Chat Bonus"
            
            # Admin'e bildirim
            await callback.message.edit_text(
                f"✅ **Çekiliş Oluşturuldu!**\n\n"
                f"**🎯 Tür:** {event_type}\n"
                f"**📝 Açıklama:** {event_info.get('description', 'Çekiliş')}\n"
                f"**💰 Katılım Ücreti:** {event_info.get('entry_cost', 0):.2f} KP\n"
                f"**🏆 Kazanan Sayısı:** {event_info.get('max_winners', 1)} kişi\n"
                f"**📋 Grup ID:** {event_info.get('selected_group_id', 'N/A')}\n"
                f"**🎯 Çekiliş ID:** {event_id}\n\n"
                f"**Çekiliş başarıyla oluşturuldu!**\n\n"
                f"💡 **Not:** Çekiliş sonuçları otomatik olarak grupta gösterilecek!",
                parse_mode="Markdown"
            )
            
            # Grup seçildiyse gruba da bildirim gönder
            if event_info.get('selected_group_id'):
                try:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🎲 Çekilişe Katıl 🎲", callback_data=f"join_event_{event_id}")]
                    ])
                    
                    group_message = f"""
🚀 **YENİ ÇEKİLİŞ BAŞLADI!** 🚀

{event_type} **{event_info.get('event_name', event_info.get('description', 'Çekiliş'))}**

💰 **Katılım:** {event_info.get('entry_cost', 0):.2f} KP
🏆 **Kazanan:** {event_info.get('max_winners', 1)} kişi  
👥 **Katılımcı:** 0 kişi
🎯 **ID:** {event_id}

🎮 **Katılmak için butona tıklayın!**
🍀 **İyi şanslar!**

**Not:** Kayıtlı değilseniz ve Kirve Point'iniz yoksa çekilişe katılamazsınız.
Hala kayıtlı değilseniz, botun özel mesajına gidip **/kirvekayit** komutunu kullanın.
                    """
                    
                    # Grup mesajını gönder ve message_id'yi al
                    sent_message = await _bot_instance.send_message(
                        event_info['selected_group_id'],
                        group_message,
                        parse_mode="Markdown",
                        reply_markup=keyboard
                    )
                    
                    logger.info(f"✅ Grup bildirimi gönderildi: {event_info['selected_group_id']}")

                    # events.group_id alanını da doldur (sonuçları aynı gruba atmak için)
                    try:
                        # Önce ana tabloyu dene; başarısızsa yedek tabloya yaz
                        pool = await get_db_pool()
                        async with pool.acquire() as conn:
                            try:
                                await conn.execute(
                                    "UPDATE events SET group_id = $1 WHERE id = $2",
                                    event_info['selected_group_id'],
                                    event_id,
                                )
                                logger.info(f"✅ Event.group_id güncellendi - Event: {event_id}, Group: {event_info['selected_group_id']}")
                            except Exception as e_upd:
                                logger.warning(f"⚠️ Event.group_id kolonuna yazılamadı, yedek tabloya geçiliyor: {e_upd}")
                                from database import upsert_event_group
                                await upsert_event_group(event_id, event_info['selected_group_id'])
                                logger.info(f"✅ event_groups eşlemesi yazıldı - Event: {event_id}, Group: {event_info['selected_group_id']}")
                    except Exception as e_upd2:
                        logger.warning(f"⚠️ Event group mapping kaydedilemedi: {e_upd2}")
                    
                except Exception as e:
                    logger.error(f"❌ Grup bildirimi hatası: {e}")
        else:
            await callback.message.edit_text(
                "❌ **Çekiliş oluşturulurken hata oluştu!**\n\n"
                "Lütfen tekrar deneyin veya sistem yöneticisi ile iletişime geçin.",
                parse_mode="Markdown"
            )
        
        # Geçici veriyi temizle
        memory_manager.clear_lottery_data(user_id)
        logger.info(f"🧹 Lottery data temizlendi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Event confirmation hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def create_event_in_db(event_info: Dict, admin_id: int) -> tuple[bool, int]:
    """Etkinliği database'e kaydet"""
    try:
        logger.info(f"🎯 Event creation başlatılıyor: {event_info}")
        
        # Database pool'u güvenli şekilde al
        try:
            pool = await get_db_pool()
            if not pool:
                logger.error("❌ Database pool yok!")
                return False, 0
        except Exception as e:
            logger.error(f"❌ Database import hatası: {e}")
            return False, 0
        
        async with pool.acquire() as conn:
            if event_info["type"] == "lottery":
                title = f"Çekiliş: {event_info.get('description', 'Genel Çekiliş')}"
                logger.info(f"🎲 Lottery event oluşturuluyor: {title}")
                
                await conn.execute("""
                    INSERT INTO events (event_type, event_name, max_participants, created_by, is_active)
                    VALUES ($1, $2, $3, $4, $5)
                """, "lottery", title, event_info["max_winners"], admin_id, True)
            else:
                title = f"Bonus: {event_info.get('description', 'Chat Bonus')}"
                logger.info(f"🎁 Bonus event oluşturuluyor: {title}")
                
                await conn.execute("""
                    INSERT INTO events (event_type, event_name, created_by, is_active)
                    VALUES ($1, $2, $3, $4)
                """, "bonus", title, admin_id, True)
            
            # Oluşturulan etkinliğin ID'sini al
            event_id = await conn.fetchval("SELECT id FROM events WHERE created_by = $1 ORDER BY created_at DESC LIMIT 1", admin_id)
            
            # Event info'ya ID ve title'ı ekle
            event_info['id'] = event_id
            event_info['title'] = title
            event_info['event_type'] = event_info["type"]  # lottery veya bonus
            
            logger.info(f"✅ Etkinlik başarıyla oluşturuldu: {title} - ID: {event_id}")
            return True, event_id
            
    except Exception as e:
        logger.error(f"❌ Event creation DB hatası: {e}")
        logger.error(f"❌ Event info: {event_info}")
        
        # Database bağlantı hatası kontrolü
        if "connection" in str(e).lower() or "pool" in str(e).lower():
            logger.error("❌ Database bağlantı sorunu!")
        elif "timeout" in str(e).lower():
            logger.error("❌ Database timeout!")
        elif "permission" in str(e).lower():
            logger.error("❌ Database yetki sorunu!")
        
        return False, 0

async def get_active_events() -> list:
    """Aktif etkinlikleri getir"""
    try:
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool yok!")
            return []
        
        async with pool.acquire() as conn:
            events = await conn.fetch("""
                SELECT id, event_type, event_name, max_participants, created_at
                FROM events WHERE is_active = TRUE
                ORDER BY created_at DESC
            """)
            
            logger.info(f"✅ Aktif etkinlikler getirildi: {len(events)} adet")
            return [dict(event) for event in events]
            
    except Exception as e:
        logger.error(f"❌ Get active events hatası: {e}")
        return []

# Export fonksiyonları
__all__ = [
    'create_lottery_command',
    'create_lottery_callback',
    'lottery_data',
    'set_bot_instance',
    'get_active_events'
] 

@router.message(Command("grupid"))
async def grup_id_command(message: Message):
    await message.reply(f"Bu grubun/sohbetin ID'si: `{message.chat.id}`", parse_mode="Markdown") 