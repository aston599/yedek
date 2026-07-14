"""
Profil handler - Kullanici profil sistemi
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user_points, get_user_points_cached, get_user_rank, get_today_stats, get_market_history, get_system_stats, get_user_info
from utils.logger import logger
from handlers.membership_levels import get_level_info_by_messages, format_level_display, get_next_level_info

# Bot instance setter
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

async def menu_command(message: types.Message) -> None:
    """
    /menu komutu - Kullanici profil menusu
    """
    try:
        user = message.from_user
        
        # Kullanici kayitli mi kontrol et
        from database import is_user_registered
        if not await is_user_registered(user.id):
            await message.answer(
                "Henuz kayit olmadınız!\n"
                "Kayit olmak icin /kirvekayit komutunu kullanın.",
                reply_to_message_id=message.message_id
            )
            return
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Menu komutu mesajı silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_menu_privately(user.id)
                else:
                    # _bot_instance yoksa doğrudan message.bot ile gönder
                    try:
                        await message.bot.send_message(user.id, "📋 Menü yükleniyor, lütfen bekleyin...")
                        await _send_menu_privately(user.id)
                    except Exception as dm_err:
                        logger.error(f"❌ Özelden menü gönderilemedi: {dm_err}")
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        logger.info(f"/menu komutu - User: {user.first_name} ({user.id})")
        
        # Detaylı log
        from handlers.detailed_logging_system import log_command_execution
        await log_command_execution(
            user_id=user.id,
            username=user.username or user.first_name,
            command="menu",
            chat_id=message.chat.id,
            chat_type=message.chat.type
        )
        
        # Database bağlantısını kontrol et (kısa süreli retry ile)
        from database import get_db_pool
        pool = await get_db_pool()
        if not pool:
            import asyncio
            for _ in range(3):
                await asyncio.sleep(0.5)
                pool = await get_db_pool()
                if pool:
                    break
        if not pool:
            await message.answer(
                "❌ Database bağlantısı geçici olarak kullanılamıyor. Lütfen birkaç saniye sonra tekrar /menu yazın.",
                reply_to_message_id=message.message_id
            )
            return
        
        # Kullanici verilerini al - Hata kontrolü ile
        try:
            user_points = await get_user_points_cached(user.id)  # Cache'li versiyon kullan
            user_rank = await get_user_rank(user.id)
            today_stats = await get_today_stats(user.id)
            weekly_stats = await get_weekly_stats(user.id)
            user_info = await get_user_info(user.id)  # registration_date için
            market_history = await get_market_history(user.id)
            system_stats = await get_system_stats()
        except Exception as db_error:
            logger.error(f"❌ Database veri alma hatası: {db_error}")
            await message.answer(
                "❌ Profil bilgileri yüklenirken hata oluştu!\n"
                "Lütfen daha sonra tekrar deneyin.",
                reply_to_message_id=message.message_id
            )
            return
        
        # Ana menü butonları
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Profil Detayları", callback_data="profile_detailed"),
                InlineKeyboardButton(text="🏆 Sıralama", callback_data="profile_ranking")
            ],
            [
                InlineKeyboardButton(text="🛍️ Market", callback_data="profile_market"),
                InlineKeyboardButton(text="❓ Yardım", callback_data="profile_help")
            ],
            [
                InlineKeyboardButton(text="🎮 Etkinlikler", callback_data="profile_events")
            ],
            [
                InlineKeyboardButton(text="⚠️ Uyarılarım", callback_data="profile_warnings")
            ],
            [
                InlineKeyboardButton(text="❌ Kapat", callback_data="profile_close")
            ]
        ])
        
        # Üyelik seviyesi bilgisi (mesaj sayısına göre)
        total_points = user_points.get('kirve_points', 0)
        total_messages = user_points.get('total_messages', 0)
        level_info = get_level_info_by_messages(total_messages)
        level_display = format_level_display(total_messages)
        next_level = get_next_level_info(total_messages)
        
        # Ana profil mesajı
        profile_response = f"""
╔══════════════════════╗
║ 👤 <b>{user.first_name}'IN PROFİLİ</b> 👤 ║
╚══════════════════════╝

💎 <b>POINT DURUMU</b>
💰 <b>Toplam Point:</b> <code>{total_points:.2f} KP</code>

🏆 <b>ÜYELİK SEVİYESİ</b>
{level_display}
        
🏅 <b>RÜTBE BİLGİLERİ</b>
👑 <b>Rütbe:</b> {user_rank.get('rank_name', 'Üye')}
⭐ <b>Seviye:</b> {user_rank.get('rank_level', 1)}

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Bir sonraki seviye bilgisi
        if next_level:
            profile_response += f"""
🎯 <b>SONRAKİ SEVİYE:</b> {next_level['emoji']} {next_level['name']}
📊 <b>Gereken Mesaj:</b> <code>{next_level['messages_needed']:,} mesaj</code>

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        profile_response += "<i>Profilinizi geliştirmek için grup sohbetlerine katılın!</i>"
        
        await message.answer(
            profile_response,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        logger.info(f"Profil menüsü gösterildi - User: {user.id}")
        
    except Exception as e:
        logger.error(f"/menu handler hatası: {e}")
        await message.answer(
            "Profil bilgileri yüklenirken hata oluştu!\n"
            "Lütfen daha sonra tekrar deneyin.",
            reply_to_message_id=message.message_id
        )

async def _send_menu_privately(user_id: int):
    """Menu'yu özel mesajla gönder"""
    try:
        if not _bot_instance:
            logger.error("❌ Bot instance bulunamadı!")
            return
        
        # Database bağlantısını kontrol et (kısa süreli retry ile)
        from database import get_db_pool
        pool = await get_db_pool()
        if not pool:
            import asyncio
            for _ in range(3):
                await asyncio.sleep(0.5)
                pool = await get_db_pool()
                if pool:
                    break
        if not pool:
            await _bot_instance.send_message(
                user_id,
                "❌ Database bağlantısı geçici olarak kullanılamıyor. Lütfen birkaç saniye sonra tekrar /menu yazın."
            )
            return
        
        # Kullanici verilerini al - Hata kontrolü ile
        try:
            user_points = await get_user_points_cached(user_id)  # Cache'li versiyon kullan
            user_rank = await get_user_rank(user_id)
            market_history = await get_market_history(user_id)
            system_stats = await get_system_stats()
        except Exception as db_error:
            logger.error(f"❌ Database veri alma hatası: {db_error}")
            await _bot_instance.send_message(
                user_id,
                "❌ Profil bilgileri yüklenirken hata oluştu!\nLütfen daha sonra tekrar deneyin."
            )
            return
        
        # Kullanıcı bilgilerini al
        from database import get_user_info
        user_info = await get_user_info(user_id)
        user_name = user_info.get('first_name', 'Kullanıcı') if user_info else 'Kullanıcı'
        
        # Ana menü butonları
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Profil Detayları", callback_data="profile_detailed"),
                InlineKeyboardButton(text="🏆 Sıralama", callback_data="profile_ranking")
            ],
            [
                InlineKeyboardButton(text="🛍️ Market", callback_data="profile_market"),
                InlineKeyboardButton(text="❓ Yardım", callback_data="profile_help")
            ],
            [
                InlineKeyboardButton(text="🎮 Etkinlikler", callback_data="profile_events")
            ],
            [
                InlineKeyboardButton(text="⚠️ Uyarılarım", callback_data="profile_warnings")
            ],
            [
                InlineKeyboardButton(text="❌ Kapat", callback_data="profile_close")
            ]
        ])
        
        # Üyelik seviyesi bilgisi (mesaj sayısına göre)
        total_points = user_points.get('kirve_points', 0)  # total_points tanımlandı
        total_messages = user_points.get('total_messages', 0)
        level_info = get_level_info_by_messages(total_messages)
        level_display = format_level_display(total_messages)
        next_level = get_next_level_info(total_messages)
        
        # Ana profil mesajı
        profile_response = f"""
╔══════════════════════╗
║ 👤 <b>{user_name}'IN PROFİLİ</b> 👤 ║
╚══════════════════════╝

💎 <b>POINT DURUMU</b>
💰 <b>Toplam Point:</b> <code>{total_points:.2f} KP</code>

🏆 <b>ÜYELİK SEVİYESİ</b>
{level_display}
        
🏅 <b>RÜTBE BİLGİLERİ</b>
👑 <b>Rütbe:</b> {user_rank.get('rank_name', 'Üye')}
⭐ <b>Seviye:</b> {user_rank.get('rank_level', 1)}

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Bir sonraki seviye bilgisi
        if next_level:
            profile_response += f"""
🎯 <b>SONRAKİ SEVİYE:</b> {next_level['emoji']} {next_level['name']}
📊 <b>Gereken Mesaj:</b> <code>{next_level['messages_needed']:,} mesaj</code>

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        profile_response += "<i>Profilinizi geliştirmek için grup sohbetlerine katılın!</i>"
        
        await _bot_instance.send_message(
            user_id,
            profile_response,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        logger.info(f"Profil menüsü özel mesajla gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Private menu hatası: {e}")
        if _bot_instance:
            await _bot_instance.send_message(user_id, "❌ Profil bilgileri yüklenemedi!")
        else:
            logger.error("❌ Bot instance bulunamadı - private menu hatası")


async def show_menu_from_callback(callback: types.CallbackQuery) -> None:
    """Callback için özel menu fonksiyonu"""
    try:
        user = callback.from_user
        user_id = user.id
        
        # Database bağlantısını kontrol et
        from database import get_db_pool
        pool = await get_db_pool()
        if not pool:
            await callback.answer("❌ Database bağlantısı kurulamadı!", show_alert=True)
            return
        
        # Kullanici verilerini al - Hata kontrolü ile
        try:
            user_points = await get_user_points_cached(user_id)  # Cache'li versiyon kullan
            user_rank = await get_user_rank(user_id)
            today_stats = await get_today_stats(user_id)
            weekly_stats = await get_weekly_stats(user_id)
            user_info = await get_user_info(user_id)  # registration_date için
            market_history = await get_market_history(user_id)
            system_stats = await get_system_stats()
        except Exception as db_error:
            logger.error(f"❌ Database veri alma hatası: {db_error}")
            await callback.answer("❌ Profil bilgileri yüklenirken hata oluştu!", show_alert=True)
            return
        
        # Ana menü butonları
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Profil Detayları", callback_data="profile_detailed"),
                InlineKeyboardButton(text="🏆 Sıralama", callback_data="profile_ranking")
            ],
            [
                InlineKeyboardButton(text="🛍️ Market", callback_data="profile_market"),
                InlineKeyboardButton(text="❓ Yardım", callback_data="profile_help")
            ],
            [
                InlineKeyboardButton(text="🎮 Etkinlikler", callback_data="profile_events")
            ],
            [
                InlineKeyboardButton(text="⚠️ Uyarılarım", callback_data="profile_warnings")
            ],
            [
                InlineKeyboardButton(text="❌ Kapat", callback_data="profile_close")
            ]
        ])
        
        # Üyelik seviyesi bilgisi (mesaj sayısına göre)
        total_points = user_points.get('kirve_points', 0)
        total_messages = user_points.get('total_messages', 0)
        level_info = get_level_info_by_messages(total_messages)
        level_display = format_level_display(total_messages)
        next_level = get_next_level_info(total_messages)
        
        # Ana profil mesajı
        profile_response = f"""
╔══════════════════════╗
║ 👤 <b>{user.first_name}'IN PROFİLİ</b> 👤 ║
╚══════════════════════╝

💎 <b>POINT DURUMU</b>
💰 <b>Toplam Point:</b> <code>{total_points:.2f} KP</code>

🏆 <b>ÜYELİK SEVİYESİ</b>
{level_display}
        
🏅 <b>RÜTBE BİLGİLERİ</b>
👑 <b>Rütbe:</b> {user_rank.get('rank_name', 'Üye')}
⭐ <b>Seviye:</b> {user_rank.get('rank_level', 1)}

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Bir sonraki seviye bilgisi
        if next_level:
            profile_response += f"""
🎯 <b>SONRAKİ SEVİYE:</b> {next_level['emoji']} {next_level['name']}
📊 <b>Gereken Mesaj:</b> <code>{next_level['messages_needed']:,} mesaj</code>

━━━━━━━━━━━━━━━━━━━━━━
"""
        
        profile_response += "<i>Profilinizi geliştirmek için grup sohbetlerine katılın!</i>"
        
        # Mesajı güncelle
        await callback.message.edit_text(
            profile_response,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        logger.info(f"Profil menüsü gösterildi - User: {user.id}")
        
    except Exception as e:
        logger.error(f"Show menu from callback hatası: {e}")
        await callback.answer("Profil bilgileri yüklenirken hata oluştu!", show_alert=True)


async def profile_callback_handler(callback: types.CallbackQuery) -> None:
    """
    Profil menüsü callback'lerini işle
    """
    try:
        user = callback.from_user
        data = callback.data
        
        # Rate limiting - callback spam önlemi
        from utils.rate_limiter import rate_limiter
        await rate_limiter.wait_if_needed(user.id, "callback")
        
        # Memory management - cache kontrolü
        from utils.memory_manager import memory_manager
        cache_key = f"profile_callback_{user.id}_{data}"
        cached_result = memory_manager.get_cache_manager().get_cache(cache_key)
        if cached_result:
            logger.info(f"Cache hit - User: {user.id}, Data: {data}")
            return
        
        logger.info(f"Profil callback - User: {user.first_name} ({user.id}) - Data: {data}")
        
        # Hızlı response - timeout önlemi (en başta)
        try:
            await callback.answer()
        except Exception as answer_error:
            logger.warning(f"Callback answer hatası: {answer_error}")
            # Answer başarısız olsa bile devam et
        
        if data == "menu_command":
            # Ana menü callback'i
            logger.info(f"Ana menü butonu tıklandı - User: {callback.from_user.id}")
            await show_menu_from_callback(callback)
        elif data == "profile_detailed":
            await show_detailed_stats(callback)
        elif data == "profile_ranking":
            await show_ranking(callback)
        elif data == "profile_market":
            logger.info(f"Market butonu tıklandı - User: {callback.from_user.id}")
            from handlers.market_callbacks import show_market_menu_universal
            await show_market_menu_universal(callback.from_user.id, callback=callback)
        elif data == "profile_help":
            logger.info(f"Yardım butonu tıklandı - User: {callback.from_user.id}")
            await show_help_menu(callback)
        elif data == "profile_events":
            logger.info(f"Etkinlikler butonu tıklandı - User: {callback.from_user.id}")
            from handlers.events_list import list_active_lotteries
            await list_active_lotteries(callback.message)
        elif data == "profile_main":
            logger.info(f"Profil ana menü butonu tıklandı - User: {callback.from_user.id}")
            await menu_command(callback.message)
        elif data == "profile_command":
            logger.info(f"Profil komutu butonu tıklandı - User: {callback.from_user.id}")
            await menu_command(callback.message)
        elif data == "profile_stats":
            logger.info(f"İstatistikler butonu tıklandı - User: {callback.from_user.id}")
            from handlers.statistics_system import system_stats_command
            await system_stats_command(callback.message)
        # Market ürünleri callback'leri devre dışı bırakıldı (ürünler kaldırıldı)
        # elif data and data.startswith("view_product_"):
        #     logger.info(f"VIEW PRODUCT CALLBACK - Data: {data}")
        #     from handlers.market_system import show_product_details_modern
        #     await show_product_details_modern(callback, data)
        # elif data and data.startswith("buy_product_"):
        #     from handlers.market_system import handle_buy_product_modern
        #     await handle_buy_product_modern(callback, data)
        # elif data and data.startswith("confirm_buy_"):
        #     from handlers.market_system import confirm_buy_product_modern
        #     await confirm_buy_product_modern(callback, data)
        elif data == "my_orders":
            logger.info(f"Siparişlerim butonu tıklandı - User: {callback.from_user.id}")
            try:
                from handlers.market_system import show_my_orders
                await show_my_orders(callback)
            except Exception as e:
                logger.error(f"❌ Siparişlerim hatası: {e}", exc_info=True)
                try:
                    await callback.answer("❌ Bir hata oluştu!", show_alert=True)
                except:
                    pass  # Query timeout - sessizce geç
        elif data == "profile_orders":
            logger.info(f"Profil siparişlerim butonu tıklandı - User: {callback.from_user.id}")
            try:
                from handlers.market_system import show_my_orders
                await show_my_orders(callback)
            except Exception as e:
                logger.error(f"❌ Profil siparişlerim hatası: {e}", exc_info=True)
                try:
                    await callback.answer("❌ Bir hata oluştu!", show_alert=True)
                except:
                    pass  # Query timeout - sessizce geç
        elif data == "profile_back":
            logger.info(f"Profil geri butonu tıklandı - User: {callback.from_user.id}")
            await menu_command(callback.message)
        elif data == "insufficient_balance":
            # Alert gösterme, sadece log yaz
            logger.warning(f"Yetersiz bakiye - User: {user.id}")
            await callback.answer("Yetersiz bakiye!", show_alert=True)
        elif data == "ranking_top_kp":
            await show_top_kp_ranking(callback)
        elif data == "ranking_top_messages":
            await show_top_messages_ranking(callback)
        elif data == "profile_warnings":
            logger.info(f"Uyarılarım butonu tıklandı - User: {callback.from_user.id}")
            await show_user_warnings(callback)
        elif data == "profile_close":
            # Menüyü kapat
            try:
                await callback.message.delete()
            except:
                await callback.answer("Menü kapatıldı!")
        else:
            logger.warning(f"Bilinmeyen profil callback: {data}")
            await callback.answer("Bilinmeyen işlem!", show_alert=True)
            
    except Exception as e:
        logger.error(f"Profile callback handler hatası: {e}")
        try:
            await callback.answer("İşlem sırasında hata oluştu!", show_alert=True)
        except:
            pass


async def show_help_menu(callback: types.CallbackQuery) -> None:
    """Yardım menüsü göster"""
    try:
        response = f"""
╔══════════════════════╗
║ ❓ <b>KİRVEHUB YARDIM MERKEZİ</b> ❓ ║
╚══════════════════════╝

💎 <b>POINT SİSTEMİ</b>
• Grup sohbetlerinde aktif ol, point kazan!
• Point'lerini market'te harcayabilirsin

🛍️ <b>MARKET SİSTEMİ</b>
• Point'lerinle freespinler, bakiyeler al
• Admin onayından sonra kodlar gönderilir
• Satın alma işlemi geri alınamaz

🏆 <b>SIRALAMA SİSTEMİ</b>
• Top 10 KP sıralaması
• Top 10 mesaj sıralaması
• Kendi sıralamanı gör

🎮 <b>ETKİNLİKLER</b>
• Çekilişlere katıl
• Point'lerinle özel ödüller kazan
• Aktif etkinlikleri takip et

📊 <b>PROFİL SİSTEMİ</b>
• Detaylı istatistiklerin
• Haftalık ve günlük kazanımların
• Aktivite geçmişin

💡 <b>İPUÇLARI</b>
• Grup sohbetlerine aktif katıl
• Günlük limitini doldurmaya çalış
• Etkinlikleri kaçırma
• Market'ten faydalan

🔧 <b>DESTEK</b>
Sorun yaşarsan admin ile iletişime geç!
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Ana Menüye Dön", callback_data="profile_back")]
        ])
        
        await callback.message.edit_text(
            response,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Yardım menü hatası: {e}")
        await callback.answer("Yardım menüsü yüklenirken hata oluştu!", show_alert=True)


async def show_detailed_stats(callback: types.CallbackQuery) -> None:
    """Detaylı istatistikler göster"""
    try:
        user = callback.from_user
        
        # Detaylı veriler
        user_points = await get_user_points_cached(user.id)  # Cache'li versiyon kullan
        user_info = await get_user_info(user.id)  # registration_date ve last_activity için
        today_stats = await get_today_stats(user.id)
        weekly_stats = await get_weekly_stats(user.id)
        
        response = f"""
╔══════════════════════╗
║ 📊 <b>DETAYLI İSTATİSTİKLER</b> 📊 ║
╚══════════════════════╝

💎 <b>POINT DETAYLARI</b>
💰 <b>Toplam Point:</b> <code>{user_points.get('kirve_points', 0):.2f} KP</code>
📅 <b>Günlük Kazanım:</b> <code>{user_points.get('daily_points', 0):.2f} KP</code>
📊 <b>Haftalık Kazanım:</b> <code>{weekly_stats.get('weekly_points', 0):.2f} KP</code>

💬 <b>MESAJ İSTATİSTİKLERİ</b>
📝 <b>Toplam Mesaj:</b> {user_points.get('total_messages', 0)}
📅 <b>Bugünkü Mesaj:</b> {today_stats.get('message_count', 0)}
📊 <b>Bu Hafta:</b> {weekly_stats.get('weekly_messages', 0)}

⏰ <b>ZAMAN BİLGİLERİ</b>
📅 <b>Kayıt Tarihi:</b> {user_info.get('registration_date', 'Bilinmiyor')}
🕐 <b>Son Aktivite:</b> {today_stats.get('last_activity', 'Bilinmiyor')}
⏱️ <b>Aktif Süre:</b> {today_stats.get('active_duration', 'Bilinmiyor')}
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Ana Menüye Dön", callback_data="profile_back")]
        ])
        
        await callback.message.edit_text(
            response,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Detaylı stats hatası: {e}")
        await callback.answer("İstatistikler yüklenirken hata oluştu!", show_alert=True)


async def show_ranking(callback: types.CallbackQuery) -> None:
    """Sıralama göster"""
    try:
        user = callback.from_user
        
        # Sıralama verileri
        ranking_data = await get_user_ranking(user.id)
        
        response = f"""
╔══════════════════════╗
║ 🏆 <b>SIRALAMA DURUMU</b> 🏆 ║
╚══════════════════════╝

👤 <b>SENİN DURUMUN</b>
💰 <b>Point Sıralaması:</b> #{ranking_data.get('point_rank', 'N/A')}
💬 <b>Mesaj Sıralaması:</b> #{ranking_data.get('message_rank', 'N/A')}

🏅 <b>SIRALAMA BİLGİLERİ</b>
📊 <b>Toplam Katılımcı:</b> {ranking_data.get('total_participants', 'N/A')}
🎖️ <b>Senin Seviyen:</b> {ranking_data.get('user_level', 'N/A')}
⭐ <b>Aktiflik Puanın:</b> {ranking_data.get('activity_score', 'N/A')}
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💎 Top 10 KP", callback_data="ranking_top_kp"),
                InlineKeyboardButton(text="📝 Top 10 Mesaj", callback_data="ranking_top_messages")
            ],
            [InlineKeyboardButton(text="⬅️ Ana Menüye Dön", callback_data="profile_back")]
        ])
        
        await callback.message.edit_text(
            response,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ranking hatası: {e}")
        await callback.answer("Sıralama bilgileri yüklenirken hata oluştu!", show_alert=True)


async def show_market_menu(callback: types.CallbackQuery) -> None:
    """Market menüsü göster"""
    try:
        from handlers.market_system import show_market_menu_modern
        await show_market_menu_modern(callback)
        
    except Exception as e:
        logger.error(f"Market menü hatası: {e}")
        await callback.answer("Market menüsü yüklenirken hata oluştu!", show_alert=True)


async def show_top_kp_ranking(callback: types.CallbackQuery) -> None:
    """Top 10 KP sıralaması göster"""
    try:
        from database import get_db_pool
        pool = await get_db_pool()
        if not pool:
            await callback.answer("Database bağlantısı yok!", show_alert=True)
            return
        
        async with pool.acquire() as conn:
            # Top 10 KP sıralaması
            top_kp_users = await conn.fetch("""
                SELECT u.first_name, u.username, u.kirve_points, u.total_messages
                FROM users u
                WHERE u.is_registered = TRUE AND u.kirve_points > 0
                ORDER BY u.kirve_points DESC
                LIMIT 10
            """)
            
            # Kullanıcının kendi sıralaması
            user_id = callback.from_user.id
            user_rank = await conn.fetchval("""
                SELECT COUNT(*) + 1
                FROM users u
                WHERE u.is_registered = TRUE AND u.kirve_points > (
                    SELECT kirve_points FROM users WHERE user_id = $1
                )
            """, user_id)
            
            user_points = await conn.fetchval("""
                SELECT kirve_points FROM users WHERE user_id = $1
            """, user_id)
            
            # Sıralama listesi oluştur - HTML formatında
            ranking_text = ""
            for i, user in enumerate(top_kp_users, 1):
                points = user.get('kirve_points', 0)
                name = user.get('first_name', 'Anonim')
                # Özel karakterleri escape et
                name = name.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
                
                ranking_text += f"{i}. 💎 <b>{points:.2f} KP</b> | 👤 {name}\n"
            
            response = f"""
╔══════════════════════╗
║ 💎 <b>TOP 10 KP SIRALAMASI</b> 💎 ║
╚══════════════════════╝

{ranking_text}

👤 <b>SENİN DURUMUN</b>
🏆 <b>Sıralama:</b> #{user_rank or 'N/A'}
💰 <b>Point:</b> {user_points or 0:.2f} KP
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Sıralamaya Dön", callback_data="profile_ranking")]
            ])
            
            await callback.message.edit_text(
                response,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
    except Exception as e:
        logger.error(f"Top KP ranking hatası: {e}")
        await callback.answer("KP sıralaması yüklenirken hata oluştu!", show_alert=True)


async def show_top_messages_ranking(callback: types.CallbackQuery) -> None:
    """Top 10 mesaj sıralaması göster"""
    try:
        from database import get_db_pool
        pool = await get_db_pool()
        if not pool:
            await callback.answer("Database bağlantısı yok!", show_alert=True)
            return
        
        async with pool.acquire() as conn:
            # Top 10 mesaj sıralaması
            top_message_users = await conn.fetch("""
                SELECT u.first_name, u.username, u.kirve_points, u.total_messages
                FROM users u
                WHERE u.is_registered = TRUE AND u.total_messages > 0
                ORDER BY u.total_messages DESC
                LIMIT 10
            """)
            
            # Kullanıcının kendi sıralaması
            user_id = callback.from_user.id
            user_rank = await conn.fetchval("""
                SELECT COUNT(*) + 1
                FROM users u
                WHERE u.is_registered = TRUE AND u.total_messages > (
                    SELECT total_messages FROM users WHERE user_id = $1
                )
            """, user_id)
            
            user_messages = await conn.fetchval("""
                SELECT total_messages FROM users WHERE user_id = $1
            """, user_id)
            
            # Sıralama listesi oluştur - HTML formatında
            ranking_text = ""
            for i, user in enumerate(top_message_users, 1):
                messages = user.get('total_messages', 0)
                name = user.get('first_name', 'Anonim')
                # Özel karakterleri escape et
                name = name.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
                
                ranking_text += f"{i}. 📝 <b>{messages} mesaj</b> | 👤 {name}\n"
            
            response = f"""
╔══════════════════════╗
║ 📝 <b>TOP 10 MESAJ SIRALAMASI</b> 📝 ║
╚══════════════════════╝

{ranking_text}

👤 <b>SENİN DURUMUN</b>
🏆 <b>Sıralama:</b> #{user_rank or 'N/A'}
📝 <b>Mesaj:</b> {user_messages or 0} mesaj
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Sıralamaya Dön", callback_data="profile_ranking")]
            ])
            
            await callback.message.edit_text(
                response,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
    except Exception as e:
        logger.error(f"Top messages ranking hatası: {e}")
        await callback.answer("Mesaj sıralaması yüklenirken hata oluştu!", show_alert=True)


# Kaldırılan fonksiyonlar: show_top_general_ranking ve show_detailed_ranking_analysis


# Yardımcı fonksiyonlar
async def get_weekly_stats(user_id: int) -> Dict[str, Any]:
    """Haftalık istatistikler"""
    try:
        from database import get_db_pool
        pool = await get_db_pool()
        if not pool:
            return {'weekly_points': 0.0, 'weekly_messages': 0}
        
        async with pool.acquire() as conn:
            # Bu haftanın başlangıcını hesapla
            from datetime import date, timedelta
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            
            # Haftalık point ve mesaj sayısını al
            weekly_data = await conn.fetchrow("""
                SELECT 
                    COALESCE(SUM(points_earned), 0) as weekly_points,
                    COALESCE(SUM(message_count), 0) as weekly_messages
                FROM daily_stats 
                WHERE user_id = $1 AND message_date >= $2
            """, user_id, week_start)
            
            if weekly_data:
                return {
                    'weekly_points': float(weekly_data['weekly_points'] or 0),
                    'weekly_messages': int(weekly_data['weekly_messages'] or 0)
                }
            
            return {'weekly_points': 0.0, 'weekly_messages': 0}
            
    except Exception as e:
        logger.error(f"Weekly stats hatası: {e}")
        return {'weekly_points': 0.0, 'weekly_messages': 0}


async def get_user_ranking(user_id: int) -> Dict[str, Any]:
    """Kullanıcı sıralama bilgileri"""
    try:
        from database import get_db_pool
        pool = await get_db_pool()
        if not pool:
            return {
                'global_rank': 'N/A',
                'point_rank': 'N/A', 
                'message_rank': 'N/A',
                'next_competitor': 'Yok',
                'points_needed': 0.0
            }
        
        async with pool.acquire() as conn:
            # Kullanıcının point ve mesaj sayısını al
            user_data = await conn.fetchrow("""
                SELECT kirve_points, total_messages 
                FROM users 
                WHERE user_id = $1
            """, user_id)
            
            if not user_data:
                return {
                    'global_rank': 'N/A',
                    'point_rank': 'N/A', 
                    'message_rank': 'N/A',
                    'next_competitor': 'Yok',
                    'points_needed': 0.0
                }
            
            user_points = float(user_data['kirve_points'] or 0)
            user_messages = int(user_data['total_messages'] or 0)
            
            # Point sıralaması
            point_rank = await conn.fetchval("""
                SELECT COUNT(*) + 1 
                FROM users 
                WHERE kirve_points > $1 AND is_registered = true
            """, user_points)
            
            # Mesaj sıralaması
            message_rank = await conn.fetchval("""
                SELECT COUNT(*) + 1 
                FROM users 
                WHERE total_messages > $1 AND is_registered = true
            """, user_messages)
            
            # Genel sıralama (point + mesaj kombinasyonu)
            general_rank = await conn.fetchval("""
                SELECT COUNT(*) + 1 
                FROM users 
                WHERE (kirve_points + total_messages * 0.1) > $1 AND is_registered = true
            """, user_points + user_messages * 0.1)
            
            # Toplam katılımcı sayısı
            total_participants = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM users 
                WHERE is_registered = true
            """)
            
            # Kullanıcı seviyesi (point bazlı)
            user_level = "Yeni Üye"
            if user_points >= 10.0:
                user_level = "Aktif Üye"
            elif user_points >= 5.0:
                user_level = "Orta Seviye"
            elif user_points >= 1.0:
                user_level = "Başlangıç"
            
            # Aktiflik puanı (point + mesaj kombinasyonu)
            activity_score = user_points + (user_messages * 0.01)
            
            # Milestone sistemi
            milestones = [1.0, 5.0, 10.0, 25.0, 50.0, 100.0]
            next_milestone = "N/A"
            milestone_points_needed = 0.0
            
            for milestone in milestones:
                if user_points < milestone:
                    next_milestone = f"{milestone:.0f} KP"
                    milestone_points_needed = milestone - user_points
                    break
            
            # Limit sıfırlama zamanı
            from datetime import datetime, timedelta
            now = datetime.now()
            tomorrow = now + timedelta(days=1)
            next_week = now + timedelta(days=7 - now.weekday())
            
            daily_reset = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            weekly_reset = next_week.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Hangi limit daha yakın
            if daily_reset < weekly_reset:
                limit_reset_time = f"Günlük: {daily_reset.strftime('%d.%m.%Y %H:%M')}"
            else:
                limit_reset_time = f"Haftalık: {weekly_reset.strftime('%d.%m.%Y %H:%M')}"
            
            return {
                'global_rank': general_rank or 'N/A',
                'point_rank': point_rank or 'N/A',
                'message_rank': message_rank or 'N/A',
                'total_participants': total_participants or 'N/A',
                'user_level': user_level,
                'activity_score': f"{activity_score:.2f}",
                'next_milestone': next_milestone,
                'milestone_points_needed': milestone_points_needed,
                'daily_limit': 5.00,
                'weekly_limit': 20.00,
                'limit_reset_time': limit_reset_time
            }
            
    except Exception as e:
        logger.error(f"Ranking hatası: {e}")
        return {
            'global_rank': 'N/A',
            'point_rank': 'N/A',
            'message_rank': 'N/A', 
            'next_competitor': 'Yok',
            'points_needed': 0.0
        } 

async def siparislerim_command(message: types.Message) -> None:
    """Siparişlerim komutu"""
    try:
        user = message.from_user
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Siparişlerim komutu mesajı silindi - Group: {message.chat.id}")
                if _bot_instance:
                    await _send_siparislerim_privately(user.id)
                return
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        await _send_siparislerim_privately(user.id)
        
    except Exception as e:
        logger.error(f"❌ Siparişlerim komutu hatası: {e}")
        await message.reply("❌ Siparişler yüklenirken hata oluştu!")


async def _send_siparislerim_privately(user_id: int):
    """Siparişlerim bilgisini özel mesajla gönder"""
    try:
        from handlers.market_system import show_my_orders
        from aiogram.types import CallbackQuery
        
        # Mock callback oluştur
        mock_callback = type('MockCallback', (), {
            'from_user': type('MockUser', (), {'id': user_id})(),
            'message': type('MockMessage', (), {'edit_text': lambda *args, **kwargs: None})()
        })()
        
        await show_my_orders(mock_callback)
        
    except Exception as e:
        logger.error(f"❌ Özel siparişlerim gönderme hatası: {e}")
        if _bot_instance:
            await _bot_instance.send_message(
                user_id,
                "❌ Siparişler yüklenirken hata oluştu!"
            )


async def siralama_command(message: types.Message) -> None:
    """Sıralama komutu"""
    try:
        user = message.from_user
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Sıralama komutu mesajı silindi - Group: {message.chat.id}")
                if _bot_instance:
                    await _send_siralama_privately(user.id)
                return
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        await _send_siralama_privately(user.id)
        
    except Exception as e:
        logger.error(f"❌ Sıralama komutu hatası: {e}")
        await message.reply("❌ Sıralama yüklenirken hata oluştu!")


async def _send_siralama_privately(user_id: int):
    """Sıralama bilgisini özel mesajla gönder"""
    try:
        # Mock callback oluştur
        mock_callback = type('MockCallback', (), {
            'from_user': type('MockUser', (), {'id': user_id})(),
            'message': type('MockMessage', (), {'edit_text': lambda *args, **kwargs: None})()
        })()
        
        await show_ranking(mock_callback)
        
    except Exception as e:
        logger.error(f"❌ Özel sıralama gönderme hatası: {e}")
        if _bot_instance:
            await _bot_instance.send_message(
                user_id,
                "❌ Sıralama yüklenirken hata oluştu!"
            )


async def profil_command(message: types.Message) -> None:
    """Profil komutu (menu ile aynı)"""
    try:
        user = message.from_user
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Profil komutu mesajı silindi - Group: {message.chat.id}")
                if _bot_instance:
                    await _send_profil_privately(user.id)
                return
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        await _send_profil_privately(user.id)
        
    except Exception as e:
        logger.error(f"❌ Profil komutu hatası: {e}")
        await message.reply("❌ Profil yüklenirken hata oluştu!")


async def _send_profil_privately(user_id: int):
    """Profil bilgisini özel mesajla gönder"""
    try:
        if _bot_instance:
            await _send_menu_privately(user_id)
        
    except Exception as e:
        logger.error(f"❌ Özel profil gönderme hatası: {e}")
        if _bot_instance:
            await _bot_instance.send_message(
                user_id,
                "❌ Profil yüklenirken hata oluştu!"
            )

async def show_user_warnings(callback: types.CallbackQuery) -> None:
    """Kullanıcının uyarılarını göster"""
    try:
        user = callback.from_user
        user_id = user.id
        
        # Database'den kullanıcının tüm gruplardaki uyarılarını getir
        from database import get_db_pool
        from datetime import datetime
        
        pool = await get_db_pool()
        if not pool:
            await callback.answer("❌ Database bağlantısı kurulamadı!", show_alert=True)
            return
        
        async with pool.acquire() as conn:
            # Tüm gruplardaki uyarıları getir
            warnings_data = await conn.fetch("""
                SELECT 
                    w.group_id,
                    w.warning_number,
                    w.reason,
                    w.created_at,
                    w.warned_by,
                    rg.group_name,
                    rg.group_username,
                    COUNT(*) OVER (PARTITION BY w.group_id) as total_warnings_in_group
                FROM warnings w
                LEFT JOIN registered_groups rg ON rg.group_id = w.group_id
                WHERE w.user_id = $1 AND w.is_active = TRUE
                ORDER BY w.group_id, w.created_at DESC
            """, user_id)
            
            # Grup bazında uyarıları organize et
            groups_warnings = {}
            for row in warnings_data:
                group_id = row['group_id']
                if group_id not in groups_warnings:
                    groups_warnings[group_id] = {
                        'group_name': row['group_name'] or f"Grup {group_id}",
                        'group_username': row['group_username'],
                        'total_warnings': row['total_warnings_in_group'],
                        'warnings': []
                    }
                groups_warnings[group_id]['warnings'].append({
                    'warning_number': row['warning_number'],
                    'reason': row['reason'],
                    'created_at': row['created_at'],
                    'warned_by': row['warned_by']
                })
        
        # Uyarı mesajı oluştur
        if not groups_warnings:
            warning_message = """
⚠️ <b>UYARI DURUMU</b>

✅ <b>Tebrikler!</b>

Hiçbir grupta aktif uyarınız bulunmuyor.

━━━━━━━━━━━━━━━━━━━━━━

💡 <b>Bilgi:</b>
• Uyarılar grup bazında takip edilir
• Her grup için ayrı uyarı sayısı tutulur
• 3 uyarı sonrası kalıcı ban uygulanır
            """
        else:
            warning_message = "⚠️ <b>UYARI DURUMU</b>\n\n"
            
            total_groups = len(groups_warnings)
            total_warnings = sum(g['total_warnings'] for g in groups_warnings.values())
            
            warning_message += f"📊 <b>Genel Durum:</b>\n"
            warning_message += f"• Toplam Grup: {total_groups}\n"
            warning_message += f"• Toplam Uyarı: {total_warnings}\n\n"
            warning_message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            # Her grup için detaylı bilgi
            for group_id, group_data in groups_warnings.items():
                group_name = group_data['group_name']
                total = group_data['total_warnings']
                
                warning_message += f"📌 <b>{group_name}</b>\n"
                warning_message += f"⚠️ <b>Uyarı Sayısı:</b> {total}/3\n"
                
                # Uyarı durumu
                if total == 1:
                    warning_message += "🔇 <b>Durum:</b> 1. uyarı (5 dk mute)\n"
                elif total == 2:
                    warning_message += "🔇 <b>Durum:</b> 2. uyarı (30 dk mute)\n"
                elif total >= 3:
                    warning_message += "🚫 <b>Durum:</b> 3. uyarı (Kalıcı ban)\n"
                else:
                    warning_message += "✅ <b>Durum:</b> Uyarı yok\n"
                
                # Son uyarı detayları
                if group_data['warnings']:
                    last_warning = group_data['warnings'][0]
                    warning_date = last_warning['created_at']
                    if isinstance(warning_date, datetime):
                        warning_date_str = warning_date.strftime('%d.%m.%Y %H:%M')
                    else:
                        warning_date_str = str(warning_date)
                    
                    warning_message += f"📅 <b>Son Uyarı:</b> {warning_date_str}\n"
                    if last_warning['reason']:
                        reason_short = last_warning['reason'][:50] + "..." if len(last_warning['reason']) > 50 else last_warning['reason']
                        warning_message += f"💬 <b>Sebep:</b> {reason_short}\n"
                
                warning_message += "\n"
            
            warning_message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            warning_message += "⚠️ <b>Önemli:</b>\n"
            warning_message += "• 1. uyarı: 5 dakika susturma\n"
            warning_message += "• 2. uyarı: 30 dakika susturma\n"
            warning_message += "• 3. uyarı: Kalıcı ban\n\n"
            warning_message += "Lütfen kurallara uyun! 🙏"
        
        # Geri dön butonu
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="menu_command")],
            [InlineKeyboardButton(text="❌ Kapat", callback_data="profile_close")]
        ])
        
        # Mesajı güncelle
        await callback.message.edit_text(
            warning_message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        logger.info(f"Uyarı durumu gösterildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Uyarı görüntüleme hatası: {e}")
        await callback.answer("❌ Uyarılar yüklenirken hata oluştu!", show_alert=True) 