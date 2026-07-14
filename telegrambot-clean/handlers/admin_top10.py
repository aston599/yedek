"""
🏆 Admin Top 10 Sistemi - KirveHub Bot
Top 10 KP ve mesaj listelerini gösteren admin komutu
"""

import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import get_config
from database import get_db_pool
from utils.logger import logger

router = Router()

# Bot instance
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

@router.message(Command("top10"))
async def top10_command(message: types.Message) -> None:
    """Top 10 KP ve mesaj listesi komutu - Sadece adminler"""
    try:
        print(f"🔥 TOP10 HANDLER ÇALIŞTI! User: {message.from_user.id}")
        logger.info(f"🔥 TOP10 HANDLER ÇALIŞTI! User: {message.from_user.id}")
        
        user_id = message.from_user.id
        username = message.from_user.username or "Unknown"
        config = get_config()
        
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            logger.warning(f"❌ Top10 komutu - Admin değil: {user_id} (@{username})")
            print(f"❌ Top10 komutu - Admin değil: {user_id} (@{username})")
            return
        
        print(f"🏆 Top10 komutu çağrıldı - Admin: {user_id} (@{username})")
        logger.info(f"🏆 Top10 komutu çağrıldı - Admin: {user_id} (@{username})")
        
        # Grup chatindeyse mesajı sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                # Kullanıcının direkt grup için top10 çalıştırmasını istiyorsa, grup bilgisini al
                group_id = message.chat.id
                group_title = message.chat.title or "Bu Grup"
                
                # Top10 listesini oluştur ve gönder
                await send_top10_to_group(message, group_id, group_title)
                
            except Exception as e:
                logger.error(f"❌ Top10 grup mesajı hatası: {e}")
                return
        else:
            # Özel mesajda çalıştırılırsa, admin'in seçim yapmasını iste
            await send_group_selection_menu(message)
        
    except Exception as e:
        logger.error(f"❌ Top10 komutu hatası: {e}")
        if message.chat.type == "private":
            await message.reply("❌ Top10 listesi yüklenirken hata oluştu!")

async def send_group_selection_menu(message: types.Message):
    """Admin'e grup seçim menüsü göster"""
    try:
        # Database'den aktif grupları al
        pool = await get_db_pool()
        if not pool:
            await message.reply("❌ Database bağlantısı hatası!")
            return
        
        async with pool.acquire() as conn:
            # Son 7 günde mesajı olan aktif kayıtlı grupları getir, ana grup en üstte
            groups = await conn.fetch("""
                WITH recent_groups AS (
                    SELECT ds.group_id,
                           COALESCE(rg.group_name, 'Grup ' || ds.group_id::text) AS group_name,
                           SUM(ds.message_count) AS msg
                    FROM daily_stats ds
                    JOIN registered_groups rg ON rg.group_id = ds.group_id
                    WHERE rg.is_active = TRUE
                      AND ds.message_date >= (CURRENT_DATE - INTERVAL '7 days')
                    GROUP BY ds.group_id, rg.group_name
                )
                SELECT group_id, group_name
                FROM recent_groups
                ORDER BY (group_id = -1002231486317) DESC, msg DESC, group_name ASC
                LIMIT 20
            """)
        
        if not groups:
            await message.reply("❌ Aktif grup bulunamadı!")
            return
        
        # Grup seçim butonları
        keyboard_buttons = []
        for group in groups:
            group_id = group['group_id']
            group_name = group['group_name'] or f"Grup {group_id}"
            # Telegram'dan canlı başlık almayı dene
            display_name = group_name
            try:
                chat = await message.bot.get_chat(group_id)
                if getattr(chat, 'title', None):
                    display_name = chat.title
                    # Veritabanını da güncelle (sessizce)
                    try:
                        await (await get_db_pool()).execute(
                            "UPDATE registered_groups SET group_name = $1 WHERE group_id = $2",
                            display_name, group_id
                        )
                    except Exception:
                        pass
            except Exception:
                pass

            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"📊 {display_name}", 
                    callback_data=f"top10_group_{group_id}"
                )
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        response = """
🏆 **TOP 10 LİSTESİ - GRUP SEÇİMİ**

Hangi grubun top 10 listesini görmek istiyorsun?

**📋 Aktif Gruplar:**
        """
        
        await message.reply(
            response,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Grup seçim menüsü hatası: {e}")
        await message.reply("❌ Grup listesi yüklenemedi!")

@router.callback_query(F.data.startswith("top10_group_"))
async def top10_group_callback(callback: types.CallbackQuery):
    """Grup seçimi callback handler"""
    try:
        user_id = callback.from_user.id
        # Admin kontrolü (Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        # Grup ID'sini çıkar
        data = callback.data or ""
        logger.info(f"🔍 Top10 callback data: {data}")
        group_id = int(data.replace("top10_group_", ""))
        
        # Top10 listesini oluştur ve gönder
        await send_top10_to_private(callback, group_id)
        
    except Exception as e:
        logger.error(f"❌ Top10 grup callback hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def send_top10_to_group(message: types.Message, group_id: int, group_title: str):
    """Top10 listesini gruba gönder"""
    try:
        # Top10 verilerini al
        top10_data = await get_top10_data(group_id)
        
        if not top10_data:
            return
        
        # Mesajı oluştur
        response = format_top10_message(top10_data, group_title, is_group=True)
        
        # Gruba gönder
        await message.reply(
            response,
            parse_mode="HTML"
        )
        
        logger.info(f"✅ Top10 listesi gruba gönderildi - Group: {group_id}")
        
    except Exception as e:
        logger.error(f"❌ Top10 grup gönderimi hatası: {e}")

async def send_top10_to_private(callback: types.CallbackQuery, group_id: int):
    """Top10 listesini özel mesajla gönder"""
    try:
        # Top10 verilerini al
        top10_data = await get_top10_data(group_id)
        
        if not top10_data:
            await callback.message.edit_text("❌ Bu grup için veri bulunamadı!")
            return
        
        # Grup bilgisini al
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            group_info = await conn.fetchrow("""
                SELECT group_name FROM registered_groups WHERE group_id = $1
            """, group_id)
        
        group_title = group_info['group_name'] if group_info else f"Grup {group_id}"
        
        # Mesajı oluştur
        response = format_top10_message(top10_data, group_title, is_group=False)
        
        # Geri butonu ekle
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yenile", callback_data=f"top10_group_{group_id}")],
            [InlineKeyboardButton(text="⬅️ Grup Seçimi", callback_data="top10_back")]
        ])
        
        # Özel mesajda güncelle
        await callback.message.edit_text(
            response,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        logger.info(f"✅ Top10 listesi özel mesajla gönderildi - Group: {group_id}")
        
    except Exception as e:
        logger.error(f"❌ Top10 özel mesaj hatası: {e}")

async def get_top10_data(group_id: int) -> dict:
    """Top10 verilerini database'den al"""
    try:
        pool = await get_db_pool()
        if not pool:
            return None
        
        async with pool.acquire() as conn:
            # Top 10 KP kullanıcıları
            top_kp = await conn.fetch("""
                SELECT u.username, u.first_name, u.kirve_points, u.user_id
                FROM users u
                WHERE u.kirve_points > 0
                ORDER BY u.kirve_points DESC
                LIMIT 10
            """)
            
            # Top 10 mesaj kullanıcıları (belirli grup için)
            top_messages = await conn.fetch("""
                SELECT u.username, u.first_name, SUM(ds.message_count) AS total_messages, u.user_id
                FROM daily_stats ds
                JOIN users u ON ds.user_id = u.user_id
                WHERE ds.group_id = $1 AND ds.message_count > 0
                GROUP BY u.user_id, u.username, u.first_name
                ORDER BY total_messages DESC
                LIMIT 10
            """, group_id)
            
            # Eğer grup bazlı mesaj bulunamazsa, genel mesaj istatistiklerini al
            if not top_messages:
                top_messages = await conn.fetch("""
                    SELECT u.username, u.first_name,
                           COALESCE(SUM(ds.message_count), 0) AS total_messages, u.user_id
                    FROM users u
                    LEFT JOIN daily_stats ds ON u.user_id = ds.user_id
                    GROUP BY u.user_id, u.username, u.first_name
                    ORDER BY total_messages DESC
                    LIMIT 10
                """)
            
            # Grup istatistikleri
            group_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT ds.user_id) AS active_users,
                    COALESCE(SUM(ds.message_count), 0) AS total_group_messages,
                    rg.group_name
                FROM daily_stats ds
                LEFT JOIN registered_groups rg ON ds.group_id = rg.group_id
                WHERE ds.group_id = $1
                GROUP BY rg.group_name
            """, group_id)
            
            return {
                'top_kp': top_kp,
                'top_messages': top_messages,
                'group_stats': group_stats
            }
        
    except Exception as e:
        logger.error(f"❌ Top10 veri alma hatası: {e}")
        return None

def format_top10_message(data: dict, group_title: str, is_group: bool = False) -> str:
    """Top10 mesajını formatla"""
    try:
        current_time = datetime.now().strftime('%d.%m.%Y %H:%M')
        
        # Mesaj başlığı
        if is_group:
            response = f"""
🏆 <b>{group_title}</b>
📊 <b>TOP 10 LİDERLİK TABLOSU</b>

"""
        else:
            response = f"""
🏆 <b>TOP 10 LİDERLİK TABLOSU</b>
📍 <b>Grup:</b> {group_title}

"""
        
        # Top 10 KP Listesi
        response += "💎 <b>TOP 10 KIRVE POINT:</b>\n"
        
        if data['top_kp']:
            medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            for i, user in enumerate(data['top_kp']):
                username = user['username'] or user['first_name'] or f"User{user['user_id']}"
                kp = user['kirve_points']
                medal = medals[i] if i < len(medals) else "🏅"
                
                response += f"{medal} <b>{i+1}.</b> @{username} - <b>{kp:.1f} KP</b>\n"
        else:
            response += "❌ KP verisi bulunamadı\n"
        
        response += "\n"
        
        # Top 10 Mesaj Listesi
        response += "💬 <b>TOP 10 MESAJ:</b>\n"
        
        if data['top_messages']:
            medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            for i, user in enumerate(data['top_messages']):
                username = user['username'] or user['first_name'] or f"User{user['user_id']}"
                messages = user['total_messages']
                medal = medals[i] if i < len(medals) else "🏅"
                
                response += f"{medal} <b>{i+1}.</b> @{username} - <b>{messages} mesaj</b>\n"
        else:
            response += "❌ Mesaj verisi bulunamadı\n"
        
        # Grup istatistikleri
        if data['group_stats']:
            stats = data['group_stats']
            response += f"""

📊 <b>GRUP İSTATİSTİKLERİ:</b>
👥 <b>Aktif Kullanıcı:</b> {stats['active_users']} kişi
💬 <b>Toplam Mesaj:</b> {stats['total_group_messages']} adet
"""
        
        # Footer
        response += f"""

📅 <b>Güncellenme:</b> {current_time}
🤖 <b>KirveHub Bot</b> - Top 10 Sistemi
"""
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Top10 mesaj formatlama hatası: {e}")
        return "❌ Mesaj formatlanırken hata oluştu!"

@router.callback_query(lambda c: c.data == "top10_back")
async def top10_back_callback(callback: types.CallbackQuery):
    """Grup seçimine geri dön"""
    try:
        user_id = callback.from_user.id
        
        # Admin kontrolü (DB tabanlı rank: Admin 3+)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Bu işlemi sadece admin yapabilir!", show_alert=True)
            return
        
        # Grup seçim menüsünü tekrar göster
        await send_group_selection_menu_callback(callback)
        
    except Exception as e:
        logger.error(f"❌ Top10 back callback hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

async def send_group_selection_menu_callback(callback: types.CallbackQuery):
    """Grup seçim menüsünü callback için göster"""
    try:
        # Database'den aktif grupları al
        pool = await get_db_pool()
        if not pool:
            await callback.message.edit_text("❌ Database bağlantısı hatası!")
            return
        
        async with pool.acquire() as conn:
            # Son 7 günde mesajı olan aktif kayıtlı gruplar, ana grup üstte
            groups = await conn.fetch("""
                WITH recent_groups AS (
                    SELECT ds.group_id,
                           COALESCE(rg.group_name, 'Grup ' || ds.group_id::text) AS group_name,
                           SUM(ds.message_count) AS msg
                    FROM daily_stats ds
                    JOIN registered_groups rg ON rg.group_id = ds.group_id
                    WHERE rg.is_active = TRUE
                      AND ds.message_date >= (CURRENT_DATE - INTERVAL '7 days')
                    GROUP BY ds.group_id, rg.group_name
                )
                SELECT group_id, group_name
                FROM recent_groups
                ORDER BY (group_id = -1002231486317) DESC, msg DESC, group_name ASC
                LIMIT 20
            """)
        
        if not groups:
            await callback.message.edit_text("❌ Aktif grup bulunamadı!")
            return
        
        # Grup seçim butonları
        keyboard_buttons = []
        for group in groups:
            group_id = group['group_id']
            group_name = group['group_name'] or f"Grup {group_id}"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"📊 {group_name}", 
                    callback_data=f"top10_group_{group_id}"
                )
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        response = """
🏆 **TOP 10 LİSTESİ - GRUP SEÇİMİ**

Hangi grubun top 10 listesini görmek istiyorsun?

**📋 Aktif Gruplar:**
        """
        
        await callback.message.edit_text(
            response,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Grup seçim menüsü callback hatası: {e}")
        await callback.answer("❌ Grup listesi yüklenemedi!", show_alert=True)