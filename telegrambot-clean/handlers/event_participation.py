"""
🎯 Etkinlik Katılım Sistemi - KirveHub Bot
Etkinliklere katılım, çekilme ve süre kontrolü
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config import get_config
from database import db_pool, get_user_points, add_message_to_user, get_db_pool
from utils.logger import logger

router = Router()

# Bot instance setter
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

async def _send_events_list_privately(user_id: int, is_admin: bool):
    """Etkinlik listesini özel mesajla gönder"""
    try:
        # Kayıt kontrolü (admin hariç)
        if not is_admin:
            from database import is_user_registered
            if not await is_user_registered(user_id):
                await _bot_instance.send_message(user_id, "❌ Bu komutu kullanmak için kayıt olmalısınız!")
                return
        
        # Aktif etkinlikleri al
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool yok!")
            await _bot_instance.send_message(user_id, "❌ Veritabanı bağlantı hatası!")
            return
        
        async with pool.acquire() as conn:
            events = await conn.fetch(
                "SELECT id, event_type, event_name, max_participants, created_at FROM events WHERE is_active = TRUE ORDER BY created_at DESC"
            )
        
        if not events:
            await _bot_instance.send_message(
                user_id,
                "📝 **Aktif Etkinlik Yok**\n\n"
                "Şu anda aktif olan herhangi bir etkinlik bulunmuyor.",
                parse_mode="Markdown"
            )
            return
        
        message_text = "🚀 **AKTİF ETKİNLİKLER** 🚀\n\n"
        for i, event in enumerate(events, 1):
            # Katılımcı sayısını al (şimdilik 0)
            participant_count = 0
            
            event_type = "🎲 Çekiliş" if event['event_type'] == 'lottery' else "💬 Bonus"
            
            message_text += f"**{i}.** {event_type} **{event['event_name']}**\n"
            message_text += f"🏆 **Kazanan:** {event.get('max_participants', 1)} kişi\n"
            message_text += f"👥 **Katılımcı:** {participant_count} kişi\n"
            if is_admin:
                message_text += f"🆔 **ID:** `{event['id']}`\n"
            message_text += f"📅 **Tarih:** {event['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
            message_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        await _bot_instance.send_message(
            user_id,
            message_text,
            parse_mode="Markdown"
        )
        logger.info(f"✅ Etkinlik listesi özel mesajla gönderildi: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Etkinlik listesi gönderilemedi: {e}")

# Katılım verilerini sakla (memory)
participation_data = {}

# @router.message(Command("etkinlikler"))  # MANUEL KAYITLI - ROUTER DEVRESİ DIŞI
async def list_active_events(message: Message):
    """Aktif etkinlikleri listele"""
    try:
        logger.info(f"🎯 list_active_events başlatıldı - User: {message.from_user.id}")
        # Admin kontrolü
        from config import get_config
        config = get_config()
        is_admin = message.from_user.id == config.ADMIN_USER_ID
        logger.info(f"🎯 Admin kontrolü: {is_admin} - User: {message.from_user.id}")
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Etkinlikler komutu mesajı silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE ETKİNLİK LİSTESİ GÖNDER
                if _bot_instance:
                    await _send_events_list_privately(message.from_user.id, is_admin)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        # Sadece kayıtlı kullanıcılar (admin hariç)
        if not is_admin:
            from database import is_user_registered
            if not await is_user_registered(message.from_user.id):
                if message.chat.type == "private":
                    await message.reply("❌ Bu komutu kullanmak için kayıt olmalısınız!")
                else:
                    if _bot_instance:
                        await _bot_instance.send_message(message.from_user.id, "❌ Bu komutu kullanmak için kayıt olmalısınız!")
                return
        
        # Aktif etkinlikleri getir
        logger.info(f"🎯 Aktif etkinlikler getiriliyor - User: {message.from_user.id}")
        from handlers.simple_events import get_active_events
        events = await get_active_events()
        logger.info(f"🎯 Aktif etkinlikler alındı: {len(events)} adet - User: {message.from_user.id}")
        
        if not events:
            response = ("📋 **Aktif Etkinlik Yok**\n\n"
                       "Şu anda aktif etkinlik bulunmuyor.\n"
                       "Yeni etkinlikler için admin ile iletişime geçin.")
            
            if message.chat.type == "private":
                await message.reply(response, parse_mode="Markdown")
            else:
                if _bot_instance:
                    await _bot_instance.send_message(message.from_user.id, response, parse_mode="Markdown")
            return
        
        events_list = "🎯 **Aktif Çekilişler (Admin Görünümü):**\n\n"
        keyboard_buttons = []
        
        for i, event in enumerate(events, 1):
            event_type = "🎲 Çekiliş" if event['event_type'] == 'lottery' else "💬 Bonus"
            events_list += f"**{i}. {event_type}**\n"
            events_list += f"📝 {event['event_name']}\n"
            events_list += f"🏆 Kazanan: {event['max_participants']} kişi\n"
            events_list += f"🆔 ID: `{event['id']}`\n\n"
            
            # Admin için bitirme butonu
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🏁 {i}. Çekilişi Bitir", 
                    callback_data=f"end_event_{event['id']}"
                )
            ])
        
        keyboard_buttons.append([InlineKeyboardButton(text="🔄 Yenile", callback_data="refresh_events")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        # GRUP SESSİZLİK: Yanıtı özel mesajla gönder
        logger.info(f"🎯 Yanıt gönderiliyor - User: {message.from_user.id}, Chat Type: {message.chat.type}")
        if message.chat.type == "private":
            await message.reply(events_list, parse_mode="Markdown", reply_markup=keyboard)
            logger.info(f"✅ Yanıt gönderildi (private) - User: {message.from_user.id}")
        else:
            if _bot_instance:
                await _bot_instance.send_message(message.from_user.id, events_list, parse_mode="Markdown", reply_markup=keyboard)
                logger.info(f"✅ Yanıt gönderildi (group) - User: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ List events hatası: {e}")
        if message.chat.type == "private":
            await message.reply("❌ Bir hata oluştu!")
        else:
            if _bot_instance:
                await _bot_instance.send_message(message.from_user.id, "❌ Bir hata oluştu!")

@router.callback_query(lambda c: c.data and c.data.startswith("join_event_"))
async def join_event_handler(callback: CallbackQuery):
    """Etkinliğe katılım"""
    try:
        user_id = callback.from_user.id
        
        # Kayıt kontrolü
        from database import is_user_registered
        if not await is_user_registered(user_id):
            await callback.answer("❌ Kayıt olmalısınız!", show_alert=True)
            return
        
        # Etkinlik ID'sini al
        event_id = int(callback.data.split("_")[-1])
        
        # Etkinlik bilgilerini getir
        event_info = await get_event_info(event_id)
        if not event_info:
            await callback.answer("❌ Etkinlik bulunamadı!", show_alert=True)
            return
        
        # Database'den katılım kontrolü - Gelişmiş
        from database import can_user_join_event, join_event, get_user_event_participation
        participation = await get_user_event_participation(user_id, event_id)
        
        if participation and participation.get('status') == 'active':
            await callback.answer("❌ Zaten katılmışsınız! Detaylar özel mesajda.", show_alert=True)
            
            # Özel mesajla açıklama
            if _bot_instance:
                try:
                    already_participated_message = f"""
❌ **ZATEN KATILMIŞSINIZ** ❌

🎯 **Etkinlik:** {event_info['event_name']}
📊 **Durum:** Aktif katılım
💰 **Katılım Miktarı:** {participation.get('payment_amount', 0):.2f} KP

💡 **Bilgi:**
• Bu etkinliğe zaten katılmışsınız
• Tekrar katılım yapamazsınız
• Etkinlik bitene kadar bekleyin

🎮 **İyi şanslar!**
                    """
                    await _bot_instance.send_message(
                        user_id,
                        already_participated_message,
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Zaten katılım bildirimi gönderildi: User {user_id}")
                except Exception as e:
                    logger.error(f"❌ Zaten katılım bildirimi gönderilemedi: User {user_id}, Error: {e}")
            
            return
        
        if not await can_user_join_event(user_id, event_id):
            await callback.answer("❌ Etkinlik aktif değil! Detaylar özel mesajda.", show_alert=True)
            
            # Özel mesajla açıklama
            if _bot_instance:
                try:
                    event_inactive_message = f"""
❌ **ETKİNLİK AKTİF DEĞİL** ❌

🎯 **Etkinlik:** {event_info['event_name']}
📊 **Durum:** Kapalı/Bitmiş
🎯 **ID:** {event_id}

💡 **Olası Sebepler:**
• Etkinlik süresi dolmuş
• Etkinlik iptal edilmiş
• Katılım kapalı

📋 **Aktif etkinlikleri görmek için:** /etkinlikler
🎮 **İyi şanslar!**
                    """
                    await _bot_instance.send_message(
                        user_id,
                        event_inactive_message,
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Etkinlik aktif değil bildirimi gönderildi: User {user_id}")
                except Exception as e:
                    logger.error(f"❌ Etkinlik aktif değil bildirimi gönderilemedi: User {user_id}, Error: {e}")
            
            return
        
        # Kullanıcının bakiyesini kontrol et
        user_points = await get_user_points(user_id)
        current_balance = user_points.get('kirve_points', 0)
        
        if current_balance < 0:  # Şimdilik ücretsiz
            # Kısa bildirim
            await callback.answer(
                f"❌ Yetersiz bakiye! Detaylar özel mesajda.",
                show_alert=True
            )
            
            # Özel mesajla detaylı açıklama
            if _bot_instance:
                try:
                    insufficient_balance_message = f"""
❌ **YETERSİZ BAKİYE** ❌

🎯 **Etkinlik:** {event_info['event_name']}
💰 **Gerekli:** 0 KP (Ücretsiz)
💳 **Mevcut:** {current_balance:.2f} KP

💡 **Çözüm Önerileri:**
• Grup sohbetinde mesaj atarak point kazanın
• Günlük limitinizi kontrol edin (5.00 KP max)
• Daha fazla aktif olun ve point biriktirin

📈 **Point kazanmak için:** Grup sohbetinde aktif olun!
🎮 **İyi şanslar!**
                    """
                    await _bot_instance.send_message(
                        user_id,
                        insufficient_balance_message,
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Yetersiz bakiye bildirimi gönderildi: User {user_id}")
                except Exception as e:
                    logger.error(f"❌ Yetersiz bakiye bildirimi gönderilemedi: User {user_id}, Error: {e}")
            
            return
        
        # Bakiyeyi düş (şimdilik ücretsiz)
        success = await add_message_to_user(user_id, 0)
        if not success:
            await callback.answer("❌ Bakiye hatası! Detaylar özel mesajda.", show_alert=True)
            
            # Özel mesajla açıklama
            if _bot_instance:
                try:
                    balance_error_message = f"""
❌ **BAKİYE GÜNCELLEME HATASI** ❌

🎯 **Etkinlik:** {event_info['event_name']}
💰 **Gerekli:** 0 KP (Ücretsiz)
💳 **Mevcut:** {current_balance:.2f} KP

💡 **Olası Sebepler:**
• Database bağlantı sorunu
• Sistem geçici olarak meşgul
• Bakiye güncelleme hatası

🔄 **Çözüm:**
• Birkaç dakika bekleyin
• Tekrar deneyin
• Sorun devam ederse admin ile iletişime geçin

🎮 **İyi şanslar!**
                    """
                    await _bot_instance.send_message(
                        user_id,
                        balance_error_message,
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Bakiye hatası bildirimi gönderildi: User {user_id}")
                except Exception as e:
                    logger.error(f"❌ Bakiye hatası bildirimi gönderilemedi: User {user_id}, Error: {e}")
            
            return
        
        # Database'e katılımı kaydet
        participation_success = await join_event(user_id, event_id, 0)  # Şimdilik ücretsiz
        if not participation_success:
            # Bakiye geri ver
            await add_message_to_user(user_id, 0)
            await callback.answer("❌ Katılım hatası! Detaylar özel mesajda.", show_alert=True)
            
            # Özel mesajla açıklama
            if _bot_instance:
                try:
                    participation_error_message = f"""
❌ **KATILIM KAYDETME HATASI** ❌

🎯 **Etkinlik:** {event_info['event_name']}
💰 **Ödenen:** 0 KP (Ücretsiz)
💳 **Bakiye:** Geri iade edildi

💡 **Olası Sebepler:**
• Database bağlantı sorunu
• Sistem geçici olarak meşgul
• Katılım kaydetme hatası

🔄 **Çözüm:**
• Bakiye geri iade edildi
• Birkaç dakika bekleyin
• Tekrar deneyin

🎮 **İyi şanslar!**
                    """
                    await _bot_instance.send_message(
                        user_id,
                        participation_error_message,
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Katılım hatası bildirimi gönderildi: User {user_id}")
                except Exception as e:
                    logger.error(f"❌ Katılım hatası bildirimi gönderilemedi: User {user_id}, Error: {e}")
            
            return
        
        # Katılım sayısını getir
        from database import get_event_participant_count
        participant_count = await get_event_participant_count(event_id)
        
        # Katılımcı sayısını güncelle
        try:
            # Event type'ı belirle
            event_type = "Genel Çekiliş" if event_info.get('event_type') == 'lottery' else "Chat Bonus"
            
            # Grup mesajını güncelle
            group_message = f"""
🚀 **YENİ ÇEKİLİŞ BAŞLADI!** 🚀

{event_type} **{event_info['event_name']}**

💰 **Katılım:** {event_info.get('entry_cost', 0):.2f} KP
🏆 **Kazanan:** {event_info.get('max_winners', 1)} kişi  
👥 **Katılımcı:** {participant_count} kişi
🎯 **ID:** {event_id}

🎮 **Katılmak için butona tıklayın!**
🍀 **İyi şanslar!**

**Not:** Kayıtlı değilseniz ve Kirve Point'iniz yoksa çekilişe katılamazsınız.
Hala kayıtlı değilseniz, botun özel mesajına gidip **/kirvekayit** komutunu kullanın.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎲 Çekilişe Katıl 🎲", callback_data=f"join_event_{event_id}")]
            ])
            
            await callback.message.edit_text(
                group_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"❌ Grup mesajı güncelleme hatası: {e}")
        
        # Katılım bildirimi - Sadece özel mesajda göster
        await callback.answer("✅ Etkinliğe katıldınız! Detaylar özel mesajda.", show_alert=True)
        
        # Özel mesajla bildirim gönder
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Çekilişten Çekil", callback_data=f"withdraw_event_{event_id}")]
            ])
            
            private_message = f"""
🎉 **Etkinliğe Katıldınız!**

🎯 **Etkinlik:** {event_info['event_name']}
💰 **Ödenen:** {event_info.get('entry_cost', 0):.2f} KP
📅 **Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}
👥 **Katılımcı:** {participant_count} kişi

🎲 **Çekiliş sonucunu bekleyin!**
            """
            
            await _bot_instance.send_message(user_id, private_message, parse_mode="Markdown", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"❌ Özel mesaj gönderme hatası: {e}")
        
        # Admin'e bildirim (sadece log için)
        logger.info(f"✅ Etkinlik katılımı: User {user_id} -> Event {event_id} - {event_info['event_name']}")
        
        logger.info(f"✅ Etkinlik katılımı: User {user_id} -> Event {event_id}")
        
    except Exception as e:
        logger.error(f"❌ Join event hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.callback_query(lambda c: c.data and c.data.startswith("withdraw_event_"))
async def withdraw_event_handler(callback: CallbackQuery):
    """Etkinlikten çekilme"""
    try:
        user_id = callback.from_user.id
        event_id = int(callback.data.split("_")[-1])
        
        # Database'den katılım kontrolü
        from database import get_user_event_participation, withdraw_from_event
        participation = await get_user_event_participation(user_id, event_id)
        
        if not participation:
            await callback.answer("❌ Bu etkinliğe katılmamışsınız!", show_alert=True)
            return
        
        if participation['status'] != 'active':
            await callback.answer("❌ Zaten çekilmişsiniz!", show_alert=True)
            return
        
        # Etkinlik bilgilerini getir
        event_info = await get_event_info(event_id)
        if not event_info:
            await callback.answer("❌ Etkinlik bulunamadı!", show_alert=True)
            return
        
        # Database'den çekilme
        withdraw_success = await withdraw_from_event(user_id, event_id)
        if not withdraw_success:
            await callback.answer("❌ Çekilme işlemi başarısız!", show_alert=True)
            return
        
        # Bakiyeyi geri ver
        success = await add_message_to_user(user_id, participation['payment_amount'])
        if not success:
            await callback.answer("❌ Bakiye geri verilirken hata oluştu!", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"❌ **Çekilişten Çekildiniz!**\n\n"
            f"**🎯 Etkinlik:** {event_info['event_name']}\n"
            f"**💰 Geri Verilen:** {participation['payment_amount']:.2f} KP\n"
            f"**📅 Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"**Bakiyeniz geri verildi!**",
            parse_mode="Markdown"
        )
        
        # Admin'e bildirim (sadece log için)
        logger.info(f"❌ Etkinlik çekilme: User {user_id} -> Event {event_id} - {event_info['event_name']}")
        
        logger.info(f"❌ Etkinlik çekilme: User {user_id} -> Event {event_id}")
        
    except Exception as e:
        logger.error(f"❌ Withdraw event hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.callback_query(lambda c: c.data and c.data.startswith("end_event_"))
async def end_event_handler(callback: CallbackQuery):
    """Etkinlik bitirme - Admin only"""
    try:
        user_id = callback.from_user.id
        
        # Admin kontrolü
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlem sadece admin tarafından yapılabilir!", show_alert=True)
            return
        
        # Etkinlik ID'sini al
        event_id = int(callback.data.split("_")[-1])
        
        # Etkinlik bilgilerini getir
        event_info = await get_event_info(event_id)
        if not event_info:
            await callback.answer("❌ Etkinlik bulunamadı!", show_alert=True)
            return
        
        # Etkinliği bitir
        from database import end_event, get_event_winners, get_event_participant_count, get_event_info_for_end
        
        # Katılımcı sayısını al
        participant_count = await get_event_participant_count(event_id)
        
        # Etkinliği bitir
        success = await end_event(event_id)
        
        if success:
            # Kazananları al (etkinliğin max_winners sayısı kadar)
            event_data = await get_event_info_for_end(event_id)
            max_winners = event_data.get('max_winners', 1) if event_data else 1
            
            winners = await get_event_winners(event_id, max_winners)
            
            # Kazananları etiketle
            winner_tags = []
            for winner in winners:
                if winner['username']:
                    winner_tags.append(f"@{winner['username']}")
                else:
                    winner_tags.append(f"[{winner['first_name']}](tg://user?id={winner['user_id']})")
            
            winner_text = " ".join(winner_tags)
            
            # Sonuç mesajı
            result_message = f"""
╔══════════════════════╗
║   🏁 <b>ÇEKİLİŞ SONUÇLANDI</b> 🏁   ║
╚══════════════════════╝

📊 <b>Çekiliş Detayları:</b>
• 🎯 ID: <code>{event_id}</code>
• 👥 Katılımcı: <code>{participant_count}</code> kişi
• 🏆 Kazanan: <code>{len(winners)}</code> kişi
• 📅 Bitiş: <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>

🎉 <b>KAZANANLAR:</b>
{winner_text}

╔══════════════════════╗
║   🎊 <b>ÇEKİLİŞ TAMAMLANDI</b> 🎊   ║
╚══════════════════════╝
            """
            
            # 1. ÖZEL MESAJDA SONUCU GÖSTER
            try:
                await _bot_instance.send_message(
                    user_id,
                    result_message,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"❌ Özel mesaj gönderme hatası: {e}")
            
            # 2. ÇEKİLİŞİN OLDUĞU GRUPTA DA SONUÇ GÖSTER
            try:
                # end_event sonrası alınan event_data'dan group_id'yi kullan
                announce_group_id = None
                try:
                    event_data_full = await get_event_info_for_end(event_id)
                    if event_data_full:
                        announce_group_id = event_data_full.get('group_id')
                except Exception as _eif:
                    logger.error(f"❌ Etkinlik bilgisi alınamadı (group_id): {_eif}")
                
                if announce_group_id:
                    try:
                        await callback.message.bot.send_message(
                            announce_group_id,
                            result_message,
                            parse_mode="HTML"
                        )
                        logger.info(f"✅ Çekiliş sonucu etkinlik grubuna gönderildi: Group {announce_group_id}")
                    except Exception as send_err:
                        logger.error(f"❌ Çekiliş sonucu grup gönderimi başarısız: Group {announce_group_id}, Error: {send_err}")
                else:
                    # Yedek tablo kontrolü
                    try:
                        from database import get_event_group
                        backup_gid = await get_event_group(event_id)
                    except Exception as be:
                        backup_gid = None
                        logger.warning(f"⚠️ event_groups yedek okuma hatası: {be}")
                    if backup_gid:
                        try:
                            await callback.message.bot.send_message(
                                backup_gid,
                                result_message,
                                parse_mode="HTML"
                            )
                            logger.info(f"✅ Çekiliş sonucu yedek group mapping ile gönderildi: Group {backup_gid}")
                        except Exception as send_err2:
                            logger.error(f"❌ Çekiliş sonucu yedek grup gönderimi başarısız: Group {backup_gid}, Error: {send_err2}")
                    else:
                        logger.info("ℹ️ Etkinliğe bağlı grup bulunamadı, yalnızca özel mesajda gösterildi")
            except Exception as e:
                logger.error(f"❌ Grup sonuç mesajı gönderim blok hatası: {e}")
            
            # Callback mesajını güncelle
            await callback.message.edit_text(
                f"✅ **Etkinlik Bitti!**\n\n"
                f"**🎯 Etkinlik:** {event_info['event_name']}\n"
                f"**👥 Katılımcı:** {participant_count} kişi\n"
                f"**🏆 Kazanan:** {len(winners)} kişi\n"
                f"**📅 Bitiş:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"**✅ Sonuçlar hem özel mesajda hem de grupta gösterildi!**",
                parse_mode="Markdown"
            )
            
            # Kazananlara özel mesaj gönder
            for winner in winners:
                try:
                    winner_message = f"""
🎉 **TEBRİKLER! ÇEKİLİŞİ KAZANDINIZ!** 🎉

**🎯 Etkinlik:** {event_info['event_name']}
**🏆 Kazanan:** {winner['first_name']}
**💸 Katılım Bedeli:** {winner['payment_amount']:.2f} KP
**📅 Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

🎁 **Ödülünüz Hakkında:**
• Çekiliş ödülünüz için yöneticiler kısa süre içinde sizinle iletişime geçecek
• Lütfen bot mesajlarını takip edin
• Ödül teslimi için gerekli bilgiler size özel olarak gönderilecek

🎊 **Tebrikler! Şanslı gününüz!** 🎊
                    """
                    
                    await _bot_instance.send_message(
                        winner['user_id'], 
                        winner_message, 
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"❌ Kazanan mesajı gönderme hatası: {e}")
            
            logger.info(f"✅ Etkinlik bitirildi: Event {event_id} - {event_info['event_name']}")
            
        else:
            await callback.answer("❌ Etkinlik bitirilirken hata oluştu!", show_alert=True)
        
    except Exception as e:
        logger.error(f"❌ End event hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.callback_query(F.data == "event_completed")
async def event_completed_handler(callback: CallbackQuery):
    """Çekiliş sonuçlandı butonu - Hiçbir şey yapma"""
    try:
        await callback.answer("🏁 Bu çekiliş zaten sonuçlandı!", show_alert=True)
        logger.info(f"✅ Çekiliş sonuçlandı butonuna tıklandı: {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Event completed handler hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.callback_query(F.data == "refresh_events")
async def refresh_events_handler(callback: CallbackQuery):
    """Etkinlik listesini yenile"""
    try:
        # Admin kontrolü
        from config import get_config
        config = get_config()
        is_admin = callback.from_user.id == config.ADMIN_USER_ID
        
        from handlers.simple_events import get_active_events
        events = await get_active_events()
        
        if not events:
            await callback.message.edit_text(
                "📋 **Aktif Etkinlik Yok**\n\n"
                "Şu anda aktif etkinlik bulunmuyor.",
                parse_mode="Markdown"
            )
            return
        
        events_list = "🎯 **Aktif Etkinlikler:**\n\n"
        keyboard_buttons = []
        
        for i, event in enumerate(events, 1):
            event_type = "🎲 Çekiliş" if event['event_type'] == 'lottery' else "💬 Bonus"
            events_list += f"**{i}. {event_type}**\n"
            events_list += f"📝 {event['event_name']}\n"
            events_list += f"🏆 Kazanan: {event['max_participants']} kişi\n\n"
            
            # Katılım butonu
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🎯 {i}. Etkinliğe Katıl", 
                    callback_data=f"join_event_{event['id']}"
                )
            ])
            
            # Admin için bitirme butonu
            if is_admin:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"🏁 {i}. Etkinliği Bitir", 
                        callback_data=f"end_event_{event['id']}"
                    )
                ])
        
        keyboard_buttons.append([InlineKeyboardButton(text="🔄 Yenile", callback_data="refresh_events")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            events_list,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Refresh events hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def get_event_info(event_id: int) -> Optional[Dict]:
    """Etkinlik bilgilerini getir"""
    try:
        # Database pool'u güvenli şekilde al
        try:
            pool = await get_db_pool()
            if not pool:
                logger.error("❌ Database pool yok!")
                return None
        except Exception as e:
            logger.error(f"❌ Database import hatası: {e}")
            return None
        
        async with pool.acquire() as conn:
            try:
                # Yeni şema (entry_cost, max_winners var)
                event = await conn.fetchrow("""
                    SELECT 
                        id, 
                        event_type, 
                        event_name, 
                        COALESCE(entry_cost, 0) AS entry_cost,
                        COALESCE(max_winners, GREATEST(max_participants, 1)) AS max_winners,
                        max_participants,
                        created_by, 
                        is_active
                    FROM events 
                    WHERE id = $1 AND is_active = TRUE
                """, event_id)
                if event:
                    return dict(event)
                return None
            except Exception as e:
                # Eski şema (kolonlar yok) için güvenli fallback
                logger.warning(f"⚠️ events.entry_cost veya max_winners yok; fallback kullanılacak: {e}")
                event = await conn.fetchrow("""
                    SELECT id, event_type, event_name, max_participants, created_by, is_active
                    FROM events WHERE id = $1 AND is_active = TRUE
                """, event_id)
                if event:
                    ev = dict(event)
                    ev["entry_cost"] = 0
                    ev["max_winners"] = max(1, int(ev.get("max_participants") or 1))
                    return ev
                return None
            
    except Exception as e:
        logger.error(f"❌ Get event info hatası: {e}")
        return None

# Memory cleanup fonksiyonu
def cleanup_participation_data():
    """Eski katılım verilerini temizle"""
    global participation_data
    current_time = datetime.now()
    to_remove = []
    
    for key, data in participation_data.items():
        # 24 saat eski verileri temizle
        if 'joined_at' in data:
            age = current_time - data['joined_at']
            if age.total_seconds() > 86400:  # 24 saat
                to_remove.append(key)
    
    for key in to_remove:
        del participation_data[key]
        logger.info(f"🧹 Eski katılım verisi temizlendi: {key}") 