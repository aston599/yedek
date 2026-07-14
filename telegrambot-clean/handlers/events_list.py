"""
🎯 Çekiliş Listesi Handler'ı - KirveHub Bot
Aktif çekilişleri listeleme ve yönetim
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config import get_config
from database import db_pool, get_db_pool
from utils.logger import logger

router = Router()

# Bot instance setter
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

async def get_active_events() -> List[Dict]:
    """Aktif etkinlikleri getir"""
    try:
        logger.info("🔍 Aktif etkinlikler getiriliyor...")
        
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool bulunamadı!")
            return []
        
        async with pool.acquire() as conn:
            events = await conn.fetch("""
                SELECT 
                    e.id,
                    e.event_type,
                    e.event_name,
                    e.max_participants,
                    e.created_at,
                    COUNT(ep.user_id) as participant_count
                FROM events e
                LEFT JOIN event_participants ep ON e.id = ep.event_id
                WHERE e.is_active = TRUE
                GROUP BY e.id, e.event_type, e.event_name, e.max_participants, e.created_at
                ORDER BY e.created_at DESC
            """)
        
        result = []
        for event in events:
            result.append({
                'id': event['id'],
                'event_type': event['event_type'],
                'title': event['event_name'],
                'entry_cost': 0,  # Şimdilik 0
                'max_winners': event['max_participants'],
                'description': event['event_name'],
                'created_at': event['created_at'],
                'message_id': None,
                'group_id': None,
                'participant_count': event['participant_count']
            })
            logger.info(f"📋 Çekiliş bulundu: ID={event['id']}, Title={event['event_name']}, Participants={event['participant_count']}")
        
        logger.info(f"📊 Aktif etkinlik sorgusu tamamlandı: {len(result)} sonuç")
        return result
        
    except Exception as e:
        logger.error(f"❌ Get active events hatası: {e}")
        return []

async def list_active_lotteries(message: Message) -> None:
    """Aktif çekilişleri listele - Ayrı mesajlar halinde"""
    try:
        user_id = message.from_user.id
        logger.info(f"🎯 /cekilisler komutu çalıştırıldı - User: {user_id}, Chat: {message.chat.id}")
        
        # Admin kontrolü - GÜVENLİ
        config = get_config()
        is_admin = user_id == config.ADMIN_USER_ID
        
        logger.info(f"🎯 Etkinlik listesi gönderiliyor - User: {user_id}, Admin: {is_admin}")
        
        # Aktif etkinlikleri getir
        events = await get_active_events()
        
        if not events:
            # Aktif çekiliş yok mesajı
            no_events_message = """
🎲 **AKTİF ÇEKİLİŞ YOK**

❌ **Şu anda aktif çekiliş bulunmuyor.**

🔔 **Yeni çekilişler için bildirimleri takip edin!**
            """
            
            await message.reply(no_events_message, parse_mode="Markdown")
            return
        
        # Her çekiliş için ayrı mesaj gönder
        for i, event in enumerate(events, 1):
            event_type = "🎲 Çekiliş" if event.get('event_type') == 'lottery' else "💬 Bonus"
            title = event.get('title', 'Adsız Çekiliş')
            entry_cost = event.get('entry_cost', 0)
            max_winners = event.get('max_winners', 1)
            participant_count = event.get('participant_count', 0)
            created_at = event.get('created_at')
            
            # Çekiliş mesajı
            event_message = f"""
🎯 **ÇEKİLİŞ #{i}**

{event_type} **{title}**

💰 **Katılım:** {entry_cost:.2f} KP
🏆 **Kazanan:** {max_winners} kişi
👥 **Katılımcı:** {participant_count} kişi
"""
            
            if created_at:
                event_message += f"📅 **Tarih:** {created_at.strftime('%d.%m.%Y %H:%M')}\n"
            
            # Admin ID'sini sadece admin'e göster
            if is_admin:
                event_message += f"🆔 **ID:** `{event.get('id')}`\n"
            
            event_message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            
            # Katılım butonu - HERKESE GÖSTER
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"🎯 {i}. Çekilişe Katıl", 
                    callback_data=f"join_event_{event.get('id')}"
                )]
            ])
            
            # Admin için bitirme butonu - SADECE ADMIN'E GÖSTER!
            if is_admin:
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=f"🏁 {i}. Çekilişi Bitir", 
                        callback_data=f"end_event_{event.get('id')}"
                    )
                ])
            
            await message.reply(
                event_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Mesajlar arası kısa bekle
            await asyncio.sleep(0.5)
        
        # Özet mesajı
        summary_message = f"""
📋 **ÇEKİLİŞ ÖZETİ**

🎯 **Toplam Aktif Çekiliş:** {len(events)} adet
👥 **Toplam Katılımcı:** {sum(e.get('participant_count', 0) for e in events)} kişi
💰 **Toplam Ödül Havuzu:** {sum(e.get('entry_cost', 0) * e.get('participant_count', 0) for e in events):.2f} KP
        """
        
        await message.reply(summary_message, parse_mode="Markdown")
        
        logger.info(f"✅ Çekiliş listesi ayrı mesajlar halinde gönderildi: {user_id} - {len(events)} aktif çekiliş")
        
    except Exception as e:
        logger.error(f"❌ Çekiliş listesi hatası: {e}")
        await message.reply("❌ Çekiliş listesi yüklenemedi!")

async def send_lotteries_list_privately(user_id: int, is_admin: bool = False):
    """Özelde çekiliş listesi gönder"""
    try:
        logger.info(f"📱 Özel çekiliş listesi gönderiliyor - User: {user_id}, Admin: {is_admin}")
        
        # Aktif etkinlikleri getir
        events = await get_active_events()
        
        if not events:
            # Aktif çekiliş yok mesajı
            no_events_message = """
🎲 **AKTİF ÇEKİLİŞ YOK**

❌ **Şu anda aktif çekiliş bulunmuyor.**

🔔 **Yeni çekilişler için bildirimleri takip edin!**

💡 **Çekiliş oluşturmak için:** `/cekilisyap`
            """
            
            # Bot instance'ını al
            from config import get_config
            config = get_config()
            from aiogram import Bot
            temp_bot = Bot(token=config.BOT_TOKEN)
            
            await temp_bot.send_message(user_id, no_events_message, parse_mode="Markdown")
            await temp_bot.session.close()
            return
        
        # Her çekiliş için ayrı mesaj gönder
        for i, event in enumerate(events, 1):
            event_type = "🎲 Çekiliş" if event.get('event_type') == 'lottery' else "💬 Bonus"
            title = event.get('title', 'Adsız Çekiliş')
            entry_cost = event.get('entry_cost', 0)
            max_winners = event.get('max_winners', 1)
            participant_count = event.get('participant_count', 0)
            created_at = event.get('created_at')
            
            # Çekiliş mesajı
            event_message = f"""
🎯 **ÇEKİLİŞ #{i}**

{event_type} **{title}**

💰 **Katılım:** {entry_cost:.2f} KP
🏆 **Kazanan:** {max_winners} kişi
👥 **Katılımcı:** {participant_count} kişi
"""
            
            if created_at:
                event_message += f"📅 **Tarih:** {created_at.strftime('%d.%m.%Y %H:%M')}\n"
            
            # Admin ID'sini sadece admin'e göster
            if is_admin:
                event_message += f"🆔 **ID:** `{event.get('id')}`\n"
            
            event_message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            
            # Katılım butonu - HERKESE GÖSTER
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"🎯 {i}. Çekilişe Katıl", 
                    callback_data=f"join_event_{event.get('id')}"
                )]
            ])
            
            # Admin için bitirme butonu - SADECE ADMIN'E GÖSTER!
            if is_admin:
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=f"🏁 {i}. Çekilişi Bitir", 
                        callback_data=f"end_event_{event.get('id')}"
                    )
                ])
            
            # Bot instance'ını al
            from config import get_config
            config = get_config()
            from aiogram import Bot
            temp_bot = Bot(token=config.BOT_TOKEN)
            
            await temp_bot.send_message(
                user_id,
                event_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            await temp_bot.session.close()
            
            # Mesajlar arası kısa bekle
            await asyncio.sleep(0.5)
        
        # Özet mesajı
        summary_message = f"""
📋 **ÇEKİLİŞ ÖZETİ**

🎯 **Toplam Aktif Çekiliş:** {len(events)} adet
👥 **Toplam Katılımcı:** {sum(event.get('participant_count', 0) for event in events)} kişi
💰 **Toplam Ödül Havuzu:** {sum(event.get('entry_cost', 0) * event.get('participant_count', 0) for event in events):.2f} KP
        """
        
        # Bot instance'ını al
        from config import get_config
        config = get_config()
        from aiogram import Bot
        temp_bot = Bot(token=config.BOT_TOKEN)
        
        await temp_bot.send_message(user_id, summary_message, parse_mode="Markdown")
        await temp_bot.session.close()
        
        logger.info(f"✅ Özel çekiliş listesi gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Özel çekiliş listesi hatası: {e}")

async def send_group_lotteries_list(user_id: int):
    """Grup için özel çekiliş listesi - Sadece katılım butonu"""
    try:
        logger.info(f"📱 Grup çekiliş listesi gönderiliyor - User: {user_id}")
        
        # Aktif etkinlikleri getir
        events = await get_active_events()
        
        if not events:
            # Aktif çekiliş yok mesajı
            no_events_message = """
🎲 **AKTİF ÇEKİLİŞ YOK**

❌ **Şu anda aktif çekiliş bulunmuyor.**

🔔 **Yeni çekilişler için bildirimleri takip edin!**

💡 **Çekiliş oluşturmak için:** `/cekilisyap`
            """
            
            # Bot instance'ını al
            from config import get_config
            config = get_config()
            from aiogram import Bot
            temp_bot = Bot(token=config.BOT_TOKEN)
            
            await temp_bot.send_message(user_id, no_events_message, parse_mode="Markdown")
            await temp_bot.session.close()
            return
        
        # Her çekiliş için ayrı mesaj gönder
        for i, event in enumerate(events, 1):
            event_type = "🎲 Çekiliş" if event.get('event_type') == 'lottery' else "💬 Bonus"
            title = event.get('title', 'Adsız Çekiliş')
            entry_cost = event.get('entry_cost', 0)
            max_winners = event.get('max_winners', 1)
            participant_count = event.get('participant_count', 0)
            created_at = event.get('created_at')
            
            # Çekiliş mesajı - GRUP İÇİN ÖZEL FORMAT
            event_message = f"""
🎯 **ÇEKİLİŞ #{i}**

{event_type} **{title}**

💰 **Katılım:** {entry_cost:.2f} KP
🏆 **Kazanan:** {max_winners} kişi
👥 **Katılımcı:** {participant_count} kişi
"""
            
            if created_at:
                event_message += f"📅 **Tarih:** {created_at.strftime('%d.%m.%Y %H:%M')}\n"
            
            event_message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            
            # SADECE KATILIM BUTONU - GRUP İÇİN
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"🎯 {i}. Çekilişe Katıl", 
                    callback_data=f"join_event_{event.get('id')}"
                )]
            ])
            
            # Bot instance'ını al
            from config import get_config
            config = get_config()
            from aiogram import Bot
            temp_bot = Bot(token=config.BOT_TOKEN)
            
            await temp_bot.send_message(
                user_id,
                event_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            await temp_bot.session.close()
            
            # Mesajlar arası kısa bekle
            await asyncio.sleep(0.5)
        
        # Özet mesajı - GRUP İÇİN ÖZEL
        summary_message = f"""
📋 **ÇEKİLİŞ ÖZETİ**

🎯 **Toplam Aktif Çekiliş:** {len(events)} adet
👥 **Toplam Katılımcı:** {sum(event.get('participant_count', 0) for event in events)} kişi
💰 **Toplam Ödül Havuzu:** {sum(event.get('entry_cost', 0) * event.get('participant_count', 0) for event in events):.2f} KP
        """
        
        # Bot instance'ını al
        from config import get_config
        config = get_config()
        from aiogram import Bot
        temp_bot = Bot(token=config.BOT_TOKEN)
        
        await temp_bot.send_message(user_id, summary_message, parse_mode="Markdown")
        await temp_bot.session.close()
        
        logger.info(f"✅ Grup çekiliş listesi gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Grup çekiliş listesi hatası: {e}")

async def create_lotteries_list_message(events: List[Dict], is_admin: bool) -> str:
    """Aktif çekilişleri listeleyen mesaj oluştur"""
    if not events:
        return """
🎲 <b>AKTİF ÇEKİLİŞ YOK</b>

❌ <b>Şu anda aktif çekiliş bulunmuyor.</b>

🔔 <b>Yeni çekilişler için bildirimleri takip edin!</b>

💡 <b>Çekiliş oluşturmak için:</b> <code>/cekilisyap</code>
        """
    
    # Aktif çekilişler varsa listele
    message = "🎲 <b>AKTİF ÇEKİLİŞLER</b>\n\n"
    
    for i, event in enumerate(events, 1):
        event_type = "🎲 Çekiliş" if event.get('event_type') == 'lottery' else "💬 Bonus"
        title = event.get('title', 'Adsız Çekiliş')
        entry_cost = event.get('entry_cost', 0)
        max_winners = event.get('max_winners', 1)
        participant_count = event.get('participant_count', 0)
        created_at = event.get('created_at')
        
        message += f"<b>{i}. {event_type}</b>\n"
        message += f"📝 <b>{title}</b>\n"
        message += f"💰 <b>Katılım:</b> {entry_cost:.2f} KP\n"
        message += f"🏆 <b>Kazanan:</b> {max_winners} kişi\n"
        message += f"👥 <b>Katılımcı:</b> {participant_count} kişi\n"
        
        if created_at:
            message += f"📅 <b>Tarih:</b> {created_at.strftime('%d.%m.%Y %H:%M')}\n"
        
        if is_admin:
            message += f"🆔 <b>ID:</b> <code>{event.get('id')}</code>\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += "💡 <b>Çekiliş oluşturmak için:</b> <code>/cekilisyap</code>"
    
    return message

async def get_active_events_detailed() -> List[Dict]:
    """Aktif etkinlikleri detaylı bilgilerle getir"""
    try:
        # Database pool'u güvenli şekilde al
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool alınamadı!")
            return []
            
        async with pool.acquire() as conn:
            # Ana sorgu - Sadece aktif çekilişler
            query = """
                SELECT 
                    e.id, 
                    e.event_type, 
                    COALESCE(e.title, e.description) as title, 
                    e.entry_cost, 
                    e.max_winners, 
                    e.description, 
                    e.created_at,
                    e.status,
                    e.group_id,
                    e.message_id,
                    COUNT(CASE WHEN ep.withdrew_at IS NULL THEN ep.user_id END) as participant_count
                FROM events e
                LEFT JOIN event_participations ep ON e.id = ep.event_id
                WHERE e.status = 'active' 
                    AND e.completed_at IS NULL
                GROUP BY 
                    e.id, e.event_type, e.title, e.entry_cost, 
                    e.max_winners, e.description, e.created_at, e.status,
                    e.group_id, e.message_id
                ORDER BY e.created_at DESC
            """
            
            events = await conn.fetch(query)
            logger.info(f"📊 Aktif etkinlik sorgusu tamamlandı: {len(events)} sonuç")
            
            result = []
            for event in events:
                event_dict = dict(event)
                
                # Başlık kontrolü
                if not event_dict.get('title'):
                    event_dict['title'] = event_dict.get('description', 'Adsız Çekiliş')
                
                result.append(event_dict)
                logger.info(f"📋 Çekiliş bulundu: ID={event_dict['id']}, Title={event_dict['title']}, Participants={event_dict['participant_count']}, Message_ID={event_dict.get('message_id')}, Group_ID={event_dict.get('group_id')}")
                
            return result
            
    except Exception as e:
        logger.error(f"❌ Get active events detailed hatası: {e}")
        return []

async def create_lotteries_list_keyboard(events: List[Dict], is_admin: bool) -> InlineKeyboardMarkup:
    """Çekiliş listesi için keyboard oluştur"""
    
    buttons = []
    
    # Aktif çekilişler varsa katılım butonları ekle
    if events:
        for i, event in enumerate(events, 1):
            event_type = "🎲 Çekiliş" if event.get('event_type') == 'lottery' else "💬 Bonus"
            title = event.get('title', 'Adsız Çekiliş')
            
            # Katılım butonu
            buttons.append([
                InlineKeyboardButton(
                    text=f"🎯 {i}. {event_type} - {title[:20]}...", 
                    callback_data=f"join_event_{event.get('id')}"
                )
            ])
            
            # Admin için bitirme butonu
            if is_admin:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"🏁 {i}. Etkinliği Bitir", 
                        callback_data=f"end_event_{event.get('id')}"
                    )
                ])
        
        # Yenile butonu
        buttons.append([
            InlineKeyboardButton(text="🔄 Yenile", callback_data="refresh_lotteries_list")
        ])
    
    # Her durumda çekiliş oluşturma butonu
    buttons.append([
        InlineKeyboardButton(text="🎲 Çekiliş Yap", callback_data="create_lottery_command")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========================================
# CALLBACK QUERY HANDLERS
# ========================================

async def refresh_lotteries_list_callback(callback: CallbackQuery):
    """Çekiliş listesini yenile"""
    try:
        user_id = callback.from_user.id
        config = get_config()
        is_admin = user_id == config.ADMIN_USER_ID
        
        # Mevcut mesajı güncelle
        events = await get_active_events_detailed()
        
        # Her durumda aynı mesaj ve keyboard
        message = await create_lotteries_list_message(events, is_admin)
        keyboard = await create_lotteries_list_keyboard(events, is_admin)
        
        try:
            await callback.message.edit_text(
                message,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception as edit_error:
            if "message is not modified" in str(edit_error):
                pass  # Aynı mesaj, güncelleme gerekmiyor
            else:
                raise edit_error
        
        await callback.answer("✅ Liste yenilendi!")
        logger.info(f"✅ Çekiliş listesi yenilendi: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Refresh lotteries list callback hatası: {e}")
        await callback.answer("❌ Yenileme başarısız!", show_alert=True)

# Export fonksiyonları
__all__ = [
    'list_active_lotteries',
    'send_lotteries_list_privately', 
    'refresh_lotteries_list_callback',
    'set_bot_instance'
] 