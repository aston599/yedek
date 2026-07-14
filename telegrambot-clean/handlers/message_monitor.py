#!/usr/bin/env python3
"""
📱 KirveHub Bot - Message Monitor
Grup mesajlarını izle ve point sistemi uygula
"""

import logging
import random
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from handlers.membership_levels import get_level_info_by_messages, format_level_display, check_level_up, get_random_avatar_file
from aiogram.types import Message
from database import get_db_pool, save_user_info, is_user_registered, is_group_registered, add_message_to_user, get_user_points_cached, register_user, db_pool
from .smart_response_system import get_smart_response

# Sabit değişkenler (Migration sonrası yeni değerler)
# NOT: Bu değerler database'deki system_settings tablosundan alınır
# Fallback değerler (database'den alınamazsa kullanılır)
# MARKET ENDEKSLİ KAZANIM SİSTEMİ - Market görseline göre ayarlandı
# Market: 20.000 KP = 5000 TL → 1 TL = 4 KP (sabit oran)
# Hesaplamalar:
#   - 1000 TL = 4000 KP
#   - 2500 TL = 10000 KP
#   - 5000 TL = 20000 KP
#   - 10000 TL = 40000 KP
# Hedef: 1000 TL için 4000 KP = 30 gün (1 ay) → Günlük 133.33 KP
# Mesaj başına 2.00 KP → 133.33 KP / 2.00 = 66-67 mesaj/gün (makul)
DEFAULT_POINT_PER_MESSAGE = 2.00  # Mesaj başına 2.00 KP (1 mesaj = 2.00 KP) - Market endeksli
DAILY_POINT_LIMIT = 133.33         # Günlük 133.33 KP limiti (market endeksli - 1000 TL için 30 gün)
WEEKLY_POINT_LIMIT = 800.0         # Haftalık 800 KP limiti (market endeksli - 6 gün x 133.33 KP)

logger = logging.getLogger(__name__)

# Kayıt teşvik mesajları için cooldown cache'i (10 dakika - tekrarı önlemek için)
registration_encouragement_cooldown: Dict[int, datetime] = {}
REGISTRATION_ENCOURAGEMENT_COOLDOWN_MINUTES = 10  # 10 dakika cooldown

# KP ödülü sonrası rastgele cooldown (3-5 dakika) için kullanıcı bazlı takip
award_cooldown_until: Dict[int, datetime] = {}

# Point bildirimi cooldown (15 dakika) - Kullanıcı bazlı son bildirim zamanı
# YENİ SİSTEM: Mesaj başına 0.20 KP kazanıldığı için cooldown artırıldı - DENGELEME
point_notification_cooldown: Dict[int, datetime] = {}
POINT_NOTIFICATION_COOLDOWN_MINUTES = 30  # 30 dakika cooldown (spam önleme için artırıldı)
POINT_NOTIFICATION_THRESHOLD = 2.00  # Her 2.00 KP artışında bildirim gönder (dengeleme için artırıldı)

# Kayıt olmayan kullanıcılara teşvik mesajı gönderme fonksiyonu
async def send_registration_encouragement(user_id: int, first_name: str, group_name: str) -> None:
    """Kayıt olmayan kullanıcılara teşvik mesajı gönder (1 dakika cooldown)"""
    try:
        # ÖNEMLİ: Kayıt kontrolü - Kayıtlı kullanıcılara mesaj gönderme!
        is_registered = await is_user_registered(user_id)
        if is_registered:
            logger.debug(f"⏸️ Kayıtlı kullanıcı - Kayıt mesajı gönderilmedi - User: {first_name} ({user_id})")
            return
        
        # Cooldown kontrolü - 10 dakika (tekrarı önlemek için)
        now = datetime.now()
        if user_id in registration_encouragement_cooldown:
            last_sent = registration_encouragement_cooldown[user_id]
            time_diff = (now - last_sent).total_seconds() / 60  # dakika
            
            if time_diff < REGISTRATION_ENCOURAGEMENT_COOLDOWN_MINUTES:
                logger.debug(f"⏰ Kayıt teşvik cooldown - User: {first_name} ({user_id}), Kalan: {REGISTRATION_ENCOURAGEMENT_COOLDOWN_MINUTES - time_diff:.1f} dk")
                return
        
        from config import get_config
        from aiogram import Bot
        
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎮 Hemen Kayıt Ol", callback_data="start_command")]
            ])
            
            encouragement_text = f"""
**Hey {first_name}!** 👋

**{group_name}** grubunda sohbet ediyorsun ama henüz **KirveHub**'a kayıt olmamışsın!

**💎 Kayıt ol ve kazan:**
• Her mesajın point kazandırır
• **Market'te** freespinler, bakiyeler al
• **Etkinliklere** katıl, bonuslar kazan
• **Sıralamada** yer al

**🎮 Hemen kayıt ol:**
Kayıt ol butonuna bas veya `/start` yaz!

**💡 Kayıt olmadan point kazanamazsın!**
            """
            
            await bot.send_message(
                chat_id=user_id,
                text=encouragement_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Cooldown'u güncelle
            registration_encouragement_cooldown[user_id] = now
            
            logger.info(f"🎯 Kayıt teşvik mesajı gönderildi - User: {first_name} ({user_id})")
            
        except Exception as send_error:
            if "Forbidden: bot can't initiate conversation" in str(send_error):
                logger.info(f"ℹ️ Kullanıcı bot ile konuşmaya izin vermemiş - User: {first_name} ({user_id})")
            elif "Bad Request: message to delete not found" in str(send_error):
                logger.info(f"ℹ️ Mesaj zaten silinmiş - User: {first_name} ({user_id})")
            elif "Bad Request: message to be replied not found" in str(send_error):
                logger.info(f"ℹ️ Yanıtlanacak mesaj bulunamadı - User: {first_name} ({user_id})")
            else:
                logger.error(f"❌ Kayıt teşvik mesajı hatası - User: {user_id}, Error: {send_error}")
        finally:
            # Bot session'ını her durumda kapat
            try:
                await bot.session.close()
            except Exception:
                pass
        
    except Exception as e:
        logger.error(f"❌ Kayıt teşvik mesajı hatası - User: {user_id}, Error: {e}")

SIMULATE = os.getenv("SIMULATE", "0").lower() in ("1", "true", "yes")

# Sistem ayarlarını getiren fonksiyon
async def get_system_settings() -> dict:
    """Sistem ayarlarını getir"""
    try:
        pool = await get_db_pool()
        if not pool:
            return {
                'points_per_message': DEFAULT_POINT_PER_MESSAGE,
                'daily_limit': DAILY_POINT_LIMIT,
                'weekly_limit': WEEKLY_POINT_LIMIT
            }
            
        async with pool.acquire() as conn:
            # Admin panel ile aynı tabloyu kullan (system_settings)
            row = await conn.fetchrow(
                """
                SELECT points_per_message, daily_limit, weekly_limit
                FROM system_settings WHERE id = 1
                """
            )
            if row:
                # DB'de points_per_message doğrudan KP değeri olarak saklanır (ör: 0.04)
                ppm = float(row['points_per_message']) if row['points_per_message'] is not None else DEFAULT_POINT_PER_MESSAGE
                return {
                    'points_per_message': ppm,
                    'daily_limit': float(row['daily_limit']) if row['daily_limit'] is not None else DAILY_POINT_LIMIT,
                    'weekly_limit': float(row['weekly_limit']) if row['weekly_limit'] is not None else WEEKLY_POINT_LIMIT,
                }
            return {
                'points_per_message': DEFAULT_POINT_PER_MESSAGE,
                'daily_limit': DAILY_POINT_LIMIT,
                'weekly_limit': WEEKLY_POINT_LIMIT
            }
            
    except Exception as e:
        logger.error(f"❌ Sistem ayarları hatası: {e}")
        return {
            'points_per_message': DEFAULT_POINT_PER_MESSAGE,
            'daily_limit': DAILY_POINT_LIMIT,
            'weekly_limit': WEEKLY_POINT_LIMIT
        }

# Flood koruması için user mesaj cache'i  
user_last_message: Dict[int, datetime] = {}
user_message_count: Dict[int, int] = {}
user_last_messages: Dict[int, List[str]] = {}  # Son mesajları takip et
user_message_timestamps: Dict[int, List[datetime]] = {}  # Mesaj zamanlarını takip et

# Point sistemi ayarları (dinamik)
async def get_dynamic_settings():
    """Database'den dinamik ayarları al"""
    try:
        # Aynı dosyadaki get_system_settings fonksiyonunu kullan
        settings = await get_system_settings()
        
        return {
            'flood_interval': 1.0,  # 1.0s - daha akıcı
            'min_message_length': 3,
            'messages_for_point': 2,  # 2 mesaja bir puan
            'daily_limit': settings.get('daily_limit', 5.0),
            'weekly_limit': settings.get('weekly_limit', 20.0)
        }
    except Exception as e:
        logger.error(f"❌ Dinamik ayarlar alınamadı: {e}")
        return {
            'flood_interval': 1.0,
            'min_message_length': 3,
            'messages_for_point': 2,
            'daily_limit': 5.0,
            'weekly_limit': 20.0
        }



async def update_daily_stats(user_id: int, group_id: int):
    """Günlük istatistikleri güncelle"""
    try:
        from database import db_pool
        if not db_pool:
            return
            
        async with db_pool.acquire() as conn:
            # Bugünün tarihini al
            today = datetime.now().date()
            
            # Daily stats tablosunu güncelle
            await conn.execute("""
                INSERT INTO daily_stats (user_id, group_id, message_date, message_count)
                VALUES ($1, $2, $3, 1)
                ON CONFLICT (user_id, group_id, message_date)
                DO UPDATE SET message_count = daily_stats.message_count + 1
            """, user_id, group_id, today)
            
            # Users tablosundaki total_messages'ı güncelle
            await conn.execute("""
                UPDATE users 
                SET total_messages = total_messages + 1,
                    last_activity = NOW()
                WHERE user_id = $1
            """, user_id)
            
            logger.info(f"📊 Daily stats ve total_messages güncellendi - User: {user_id}, Group: {group_id}")
            
    except Exception as e:
        logger.error(f"⚠️ Daily stats tablosu hatası: {e}")

async def monitor_group_message(message: Message) -> None:
    """
    Grup mesajlarını izle ve point sistemi uygula
    """
    # TAM YETKİ: BU FONKSİYON AKTİF
    # return  # Bu satırı kaldırdık
    
    try:
        user = message.from_user
        chat = message.chat
        
        # TAM YETKİ: Özel mesajları tamamen engelle
        if message.chat.type == "private":
            return  # Hiçbir şey yapma, hiç log yazma
        
        # PRIVACY MODE DISABLED OPTİMİZASYONU: Gereksiz log'ları azalt
        # Sadece önemli olaylar için log yaz (performans için)
        # logger.info(f"🔍 MONITOR GROUP MESSAGE ÇAĞRILDI - User: {user.first_name}, Chat: {chat.id}")
        
        # ÖNEMLİ: Tüm mesajları (bot dahil) grup aktivite izleyicisine kaydet
        # Bu, zamanlanmış mesajlar algoritması için kritik!
        try:
            from handlers.group_activity_monitor import record_group_message
            await record_group_message(message)
        except Exception as record_error:
            logger.debug(f"⏸️ Grup mesajı kaydetme hatası (kritik değil): {record_error}")
        
        # ÖNEMLİ: Mod aktivite takibi - Mod mesajlarını kaydet
        try:
            from handlers.mod_handler import record_mod_activity, is_moderator
            if await is_moderator(user.id):
                await record_mod_activity(chat.id, user.id)
        except Exception as mod_activity_error:
            logger.debug(f"⏸️ Mod aktivite kayıt hatası (kritik değil): {mod_activity_error}")
        
        # Bot mesajlarını yoksay (point sistemi için)
        if user.is_bot:
            logger.info(f"🤖 Bot mesajı yoksayıldı - User: {user.first_name}")
            return
            
        # Grup kayıtlı mı kontrol et
        is_group_registered_result = await is_group_registered(chat.id)
        if not is_group_registered_result:
            # Gereksiz log - sadece debug modda
            logger.debug(f"❌ Grup kayıtlı değil - Chat: {chat.id}")
            return
        
        # Kullanıcı bilgilerini kaydet
        await save_user_info(user.id, user.username, user.first_name, user.last_name)
        
        # Kullanıcı kayıtlı mı kontrol et
        is_registered = await is_user_registered(user.id)
        # PRIVACY MODE DISABLED OPTİMİZASYONU: Gereksiz log'ları azalt
        # logger.info(f"👤 Kullanıcı kayıt durumu - User: {user.first_name} ({user.id}), Registered: {is_registered}")
        
        # OTOMATİK KAYIT SİSTEMİ KALDIRILDI - Sadece manuel kayıt
        # if not is_registered:
        #     try:
        #         await register_user(user.id)
        #         logger.info(f"✅ Otomatik kayıt - User: {user.first_name} ({user.id})")
        #         is_registered = True
        #     except Exception as e:
        #         logger.error(f"❌ Otomatik kayıt hatası - User: {user.first_name} ({user.id}), Error: {e}")
        
        # KAYIT DURUMU KONTROLÜ - Sadece gerçekten kayıtsız olanlara mesaj at
        # PRIVACY MODE DISABLED OPTİMİZASYONU: Gereksiz log'ları azalt
        # if not is_registered:
        #     logger.info(f"🎯 Gerçekten kayıtsız kullanıcı - User: {user.first_name} ({user.id})")
        # else:
        #     logger.info(f"💎 Gerçekten kayıtlı kullanıcı - User: {user.first_name} ({user.id})")
        
        # Otomatik siteler listesi kontrolü (10 dakikada bir)
        try:
            from handlers.site_manager import show_site_list_auto
            # Bot instance'ı site_manager'dan al (set_bot_instance ile set edilmiş)
            await show_site_list_auto(chat.id)
        except Exception as site_error:
            logger.debug(f"⏸️ Otomatik siteler listesi kontrolü hatası: {site_error}")
        
        # Her durumda mesaj sayısını kaydet (kayıtlı olmayanlar için de)
        # Mesaj sayısı her zaman kaydedilir
        await update_daily_stats(user.id, chat.id)
        # PRIVACY MODE DISABLED OPTİMİZASYONU: Gereksiz log'ları azalt
        # logger.info(f"📊 Mesaj sayısı kaydedildi - User: {user.first_name} ({user.id})")
        
        # 💬 CHAT SİSTEMİ - AKILLI YANIT SİSTEMİ
        # Bot başlangıç koruması kontrolü - Chat sistemi 3 dakika sonra aktifleşir
        try:
            from handlers.chat_system import handle_chat_message, send_chat_response, is_bot_startup_protection_active
            from handlers.chat_message_handler import handle_chat_message as handle_chat_message_new
            from utils.cooldown_manager import cooldown_manager
            
            # Bot başlangıç koruması aktifse chat sistemini devre dışı bırak (komutlar çalışır)
            if is_bot_startup_protection_active():
                logger.debug(f"🛡️ Bot başlangıç koruması aktif - Chat sistemi devre dışı (3 dakika)")
                # Chat sistemi devre dışı ama kayıt teşvik handler'ı çalışabilir (sadece özelden)
                # await handle_chat_message_new(message)  # Başlangıçta da devre dışı
            else:
                # Akıllı yanıt sistemi (tek kanal) - 3 dakika sonra aktif
                response = await handle_chat_message(message)
                if response:
                    logger.info(f"🤖 SMART RESPONSE - User: {user.first_name} ({user.id}), Response: {response}")
                    await send_chat_response(message, response)
                    # Mesajı kaydet ki ardışık cevaplar engellensin
                    await cooldown_manager.record_user_message(message.from_user.id)
                else:
                    # Sadece akıllı yanıt üretmediyse kayıt teşvik handler'ını çalıştır
                    await handle_chat_message_new(message)
            
        except Exception as chat_error:
            logger.error(f"❌ Chat handler hatası - User: {user.first_name} ({user.id}), Error: {chat_error}")
        
        # 🎭 INTERACTIVE FEATURES - Emoji reaksiyonları ve eğlenceli özellikler
        try:
            from handlers.interactive_features import process_interactive_features
            await process_interactive_features(message)
        except Exception as interactive_error:
            logger.error(f"❌ Interactive features hatası - User: {user.first_name} ({user.id}), Error: {interactive_error}")
        
        if not is_registered:
            logger.info(f"🎯 Kayıt olmayan kullanıcı - User: {user.first_name} ({user.id})")
            
            # Kayıt olmayan kullanıcılara teşvik mesajı gönder (cooldown ile)
            try:
                await send_registration_encouragement(user.id, user.first_name, chat.title)
            except Exception as e:
                logger.error(f"❌ Kayıt teşvik mesajı hatası - User: {user.id}, Error: {e}")
        else:
            logger.info(f"💎 Kayıtlı kullanıcı - User: {user.first_name} ({user.id})")
            
            # Kayıtlı kullanıcılar için yeni point sistemi
            # 5 saniye flood protection kontrolü
            flood_check = await check_flood_protection(user.id)
            logger.info(f"⏰ Flood check - User: {user.first_name} ({user.id}), Result: {flood_check}")
            
            if flood_check:
                # Kullanıcının toplam mesaj ve mevcut bakiyesini al (DB'den taze veri)
                try:
                    from database import get_db_pool
                    pool = await get_db_pool()
                    async with pool.acquire() as conn:
                        row = await conn.fetchrow(
                            """
                            SELECT total_messages, kirve_points, daily_points, last_point_date
                            FROM users WHERE user_id = $1
                            """,
                            user.id,
                        )
                        total_messages = (row["total_messages"] or 0) if row else 0
                        current_balance = {
                            "kirve_points": float(row["kirve_points"]) if row and row["kirve_points"] is not None else 0.0,
                            "daily_points": float(row["daily_points"]) if row and row["daily_points"] is not None else 0.0,
                            "total_messages": total_messages,
                            "last_point_date": row["last_point_date"] if row else None,
                            "weekly_points": 0.0,
                        }
                except Exception:
                    current_balance = await get_user_points_cached(user.id)
                    total_messages = current_balance.get('total_messages', 0) if current_balance else 0
                
                # Eski mesaj sayısını kaydet (update_daily_stats daha önce artırdı, bu yüzden 1 azalt)
                old_total_messages = total_messages - 1 if total_messages > 0 else 0
                # Yeni mesaj sayısı (update_daily_stats daha önce artırdı, bu yüzden mevcut değer doğru)
                new_total_messages = total_messages
                
                # Dinamik mesaj sayısında point kazanılır
                settings = await get_dynamic_settings()
                messages_for_point = settings['messages_for_point']
                
                logger.info(f"📝 Mesaj sayısı - User: {user.first_name} ({user.id}), Current: {new_total_messages}, For point: {messages_for_point}")
                
                if new_total_messages % messages_for_point == 0:
                    # Ödül cooldown kontrolü (3-5 dakika rastgele)
                    now_time = datetime.now()
                    cooldown_until = award_cooldown_until.get(user.id)
                    if cooldown_until and now_time < cooldown_until:
                        remaining = int((cooldown_until - now_time).total_seconds())
                        logger.info(
                            f"⏳ Ödül cooldown aktif - User: {user.first_name} ({user.id}), Kalan: {remaining}s"
                        )
                        # Eşik dolsa bile cooldown sürerken KP verilmez
                        return
                    old_balance = current_balance.get('kirve_points', 0.0) if current_balance else 0.0
                    
                    # Günlük limit kontrolü
                    daily_points = current_balance.get('daily_points', 0.0) if current_balance else 0.0
                    system_settings = await get_system_settings()
                    daily_limit = system_settings.get('daily_limit', 133.33)  # Market endeksli: 133.33 KP/gün (1000 TL için 30 gün)
                    
                    if daily_points >= daily_limit:
                        logger.info(f"⏰ Günlük limit doldu - User: {user.first_name} ({user.id}), Daily: {daily_points}/{daily_limit}")
                        await send_daily_limit_notification(user.id, user.first_name, daily_limit)
                        return
                    
                    # Dinamik point miktarını al (system_settings'ten doğrudan)
                    sys_settings = await get_system_settings()
                    # Puan ayarı 0 veya negatifse güvenli varsayılanı kullan
                    try:
                        dynamic_point_amount = float(sys_settings.get('points_per_message', DEFAULT_POINT_PER_MESSAGE))
                    except Exception:
                        # Ayar okunamazsa yalnızca o zaman varsayılanı kullan
                        dynamic_point_amount = DEFAULT_POINT_PER_MESSAGE

                    # Haftalık limit ve clamp hesapları
                    weekly_points = current_balance.get('weekly_points', 0.0) if current_balance else 0.0
                    system_settings_limits = await get_system_settings()
                    weekly_limit = system_settings_limits.get('weekly_limit', 800.0)  # Market endeksli: 800 KP/hafta (1000 TL için 30 gün)

                    remaining_daily = max(0.0, daily_limit - daily_points)
                    remaining_weekly = max(0.0, weekly_limit - weekly_points)
                    logger.info(
                        f"💰 Award calc - PPM: {dynamic_point_amount}, rem_daily: {remaining_daily}, rem_weekly: {remaining_weekly}"
                    )
                    awarded_amount = min(dynamic_point_amount, remaining_daily, remaining_weekly)
                    # Güvenlik: Limitler pozitifken ödül 0 çıkarsa (PPM=0 gibi), varsayılanla öde
                    if awarded_amount <= 0 and (remaining_daily > 0 and remaining_weekly > 0):
                        logger.warning("⚠️ Award 0 hesaplandı; PPM muhtemelen 0. Varsayılan PPM ile ödül verilecek.")
                        safe_award = max(dynamic_point_amount, DEFAULT_POINT_PER_MESSAGE)
                        awarded_amount = min(safe_award, remaining_daily, remaining_weekly)

                    if awarded_amount <= 0:
                        # Haftalık veya günlük limit nedeniyle ödeme yapılamıyor
                        if remaining_daily <= 0:
                            await send_daily_limit_notification(user.id, user.first_name, daily_limit)
                        if remaining_weekly <= 0:
                            await send_weekly_limit_notification(user.id, user.first_name, weekly_limit)
                        logger.info(
                            f"⏰ Limit nedeniyle puan verilmedi - User: {user.first_name} ({user.id}), "
                            f"Daily: {daily_points}/{daily_limit}, Weekly: {weekly_points}/{weekly_limit}, "
                            f"PPM: {dynamic_point_amount}, Award: {awarded_amount}"
                        )
                        return

                    # DB'ye point yaz (users + daily_stats)
                    try:
                        pool = await get_db_pool()
                        if pool:
                            async with pool.acquire() as conn:
                                # Users tablosunu güncelle: kirve_points, daily_points, last_point_date
                                await conn.execute(
                                    """
                                    UPDATE users
                                    SET 
                                        kirve_points = COALESCE(kirve_points, 0) + $1,
                                        daily_points = CASE 
                                            WHEN last_point_date = CURRENT_DATE THEN COALESCE(daily_points, 0) + $1
                                            ELSE $1
                                        END,
                                        last_point_date = CURRENT_DATE,
                                        last_activity = NOW()
                                    WHERE user_id = $2
                                    """,
                                    awarded_amount,
                                    user.id,
                                )

                                # daily_stats'ta points_earned'ı güncelle (message_count daha önce güncellendi)
                                await conn.execute(
                                    """
                                    INSERT INTO daily_stats (user_id, group_id, message_date, message_count, points_earned)
                                    VALUES ($1, $2, CURRENT_DATE, 0, $3)
                                    ON CONFLICT (user_id, group_id, message_date)
                                    DO UPDATE SET 
                                        points_earned = daily_stats.points_earned + EXCLUDED.points_earned
                                    """,
                                    user.id,
                                    chat.id,
                                    awarded_amount,
                                )

                            # Kullanıcı puan cache'ini temizle
                            try:
                                from utils.memory_manager import memory_manager
                                cache_manager = memory_manager.get_cache_manager()
                                cache_key = f"user_points_{user.id}"
                                if hasattr(cache_manager, "clear_cache"):
                                    cache_manager.clear_cache()
                                elif hasattr(cache_manager, "delete_cache"):
                                    cache_manager.delete_cache(cache_key)
                                else:
                                    cache_manager._cache.pop(cache_key, None)
                            except Exception:
                                pass
                    except Exception as write_err:
                        logger.error(f"❌ Point DB yazma hatası - User: {user.id}, Error: {write_err}")
                    
                    # Level up bildirimi kontrol et (DEPRECATED - level_up_notification modülü kaldırıldı)
                    # try:
                    #     from handlers.level_up_notification import check_and_send_level_up
                    #     from database import get_db_pool
                    #     
                    #     pool = await get_db_pool()
                    #     if pool:
                    #         async with pool.acquire() as conn:
                    #             # Son level up log'unu kontrol et
                    #             last_level_up = await conn.fetchval("""
                    #                 SELECT details FROM system_logs 
                    #                 WHERE log_level = 'LEVEL_UP' 
                    #                 AND details LIKE $1
                    #                 ORDER BY created_at DESC 
                    #                 LIMIT 1
                    #             """, f"User: {user.id}%")
                    #             
                    #             if last_level_up:
                    #                 # Log'dan bilgileri çıkar
                    #                 import re
                    #                 match = re.search(r'User: (\d+), Level: (\d+), Old Rank: (\w+), New Rank: (\w+), Messages: (\d+)', last_level_up)
                    #                 if match:
                    #                     user_id, level, old_rank, new_rank, message_count = match.groups()
                    #                     await check_and_send_level_up(int(user_id), old_rank, new_rank, int(message_count), int(level))
                    # except Exception as e:
                    #     logger.warning(f"⚠️ Level up bildirimi hatası: {e}")
                    
                    # Yeni bakiyeyi al
                    new_balance = old_balance + awarded_amount
                    new_daily_points = daily_points + awarded_amount
                    
                    # Üyelik seviyesi atlama kontrolü (mesaj sayısına göre)
                    level_up_info = check_level_up(old_total_messages, new_total_messages)
                    if level_up_info:
                        await send_level_up_notification(
                            user.id,
                            user.first_name,
                            level_up_info
                        )
                    
                    # Point bildirimi gönder (DENGELEME: Her 2.00 KP artışında, 30 dakika cooldown ile)
                    # YENİ SİSTEM: Mesaj başına 0.20 KP kazanıldığı için bildirim sıklığı azaltıldı
                    # Cooldown kontrolü
                    should_send_notification = False
                    now = datetime.now()
                    
                    if user.id in point_notification_cooldown:
                        last_notification = point_notification_cooldown[user.id]
                        time_diff = (now - last_notification).total_seconds() / 60  # dakika
                        
                        if time_diff >= POINT_NOTIFICATION_COOLDOWN_MINUTES:
                            # Cooldown doldu, bildirim gönderebiliriz
                            should_send_notification = True
                        else:
                            # Cooldown aktif
                            logger.debug(f"⏰ Point bildirimi cooldown - User: {user.id}, Kalan: {POINT_NOTIFICATION_COOLDOWN_MINUTES - time_diff:.1f} dk")
                    else:
                        # İlk bildirim, gönderebiliriz
                        should_send_notification = True
                    
                    # 2.00 KP artışı kontrolü (DENGELEME: Her 2.00 KP artışında bildirim)
                    # Eski balance'ın 2.00'ün katı olup olmadığını kontrol et
                    old_balance_rounded_to_200 = int(old_balance / 2.0) * 2.0  # 2.00'e yuvarla
                    new_balance_rounded_to_200 = int(new_balance / 2.0) * 2.0  # 2.00'e yuvarla
                    
                    # Eğer 2.00 KP artışı varsa VE cooldown dolmuşsa bildirim gönder
                    if should_send_notification and new_balance_rounded_to_200 > old_balance_rounded_to_200:
                        await send_private_point_notification(
                            user.id, 
                            user.first_name, 
                            new_balance, 
                            new_total_messages, 
                            chat.title, 
                            awarded_amount
                        )
                        # Cooldown'u güncelle
                        point_notification_cooldown[user.id] = now
                        logger.debug(f"✅ Point bildirimi gönderildi - User: {user.id}, Balance: {new_balance:.2f} KP (2.00 KP artışı)")
                    
                    # Milestone kontrolü - Sadece 1.00 KP'ye ulaştı mı? (diğer milestone'lar kapalı)
                    if old_balance < 1.0 and new_balance >= 1.0:
                        await send_milestone_notification(user.id, user.first_name, new_balance)
                    
                    # Haftalık limit kontrolü
                    weekly_points = current_balance.get('weekly_points', 0.0) if current_balance else 0.0
                    new_weekly_points = weekly_points + awarded_amount
                    
                    # Haftalık limit kontrolü (ayar bazlı)
                    if weekly_points < weekly_limit and new_weekly_points >= weekly_limit:
                        await send_weekly_limit_notification(user.id, user.first_name, weekly_limit)
                    
                    logger.info(f"💎 Point eklendi - User: {user.first_name} ({user.id}), Points: +{awarded_amount}, New Balance: {new_balance:.2f}, Daily: {new_daily_points:.2f}/{daily_limit}, Mesaj: {new_total_messages}")
                    # Yeni ödül cooldown süresini ayarla (3-5 dakika rastgele)
                    cooldown_seconds = random.randint(180, 300)
                    award_cooldown_until[user.id] = datetime.now() + timedelta(seconds=cooldown_seconds)
                    logger.info(
                        f"⏳ Ödül cooldown ayarlandı - User: {user.first_name} ({user.id}), Süre: {cooldown_seconds}s"
                    )
                else:
                    # Eşik dolmadı bilgisi
                    try:
                        remainder = new_total_messages % messages_for_point
                        remaining = messages_for_point - remainder if remainder != 0 else 0
                        logger.info(
                            f"📝 Mesaj sayısı artırıldı - User: {user.first_name} ({user.id}), Mesaj: {new_total_messages}/{messages_for_point}"
                        )
                        if remaining > 0:
                            logger.info(
                                f"⏳ Eşik dolmadı - User: {user.first_name} ({user.id}), Kalan mesaj: {remaining}"
                            )
                    except Exception:
                        logger.info(
                            f"📝 Mesaj sayısı artırıldı - User: {user.first_name} ({user.id}), Mesaj: {new_total_messages}/{messages_for_point}"
                        )
            else:
                # Dinamik flood/cooldown süresini göster
                try:
                    _dyn = await get_dynamic_settings()
                    _cooldown = _dyn.get('flood_interval', 1.5)
                except Exception:
                    _cooldown = 1.5
                logger.info(f"⏰ Mesaj cooldown - User: {user.first_name} ({user.id}) {float(_cooldown)} saniye beklemeli")
            
    except Exception as e:
        logger.error(f"❌ Group message handler hatası: {e}")

    # (tekleştirildi) ikinci entegrasyon bloğu kaldırıldı


async def check_flood_protection(user_id: int) -> bool:
    """
    Flood koruması kontrolü
    """
    try:
        now = datetime.now()
        
        # Son mesaj zamanını kontrol et
        if user_id in user_last_message:
            time_diff = now - user_last_message[user_id]
            
            # Dinamik flood interval al
            settings = await get_dynamic_settings()
            flood_interval = settings['flood_interval']
            
            # Çok hızlı mesaj gönderiyorsa
            if time_diff.total_seconds() < flood_interval:
                logger.info(f"⏰ Flood protection - User: {user_id}, Time diff: {time_diff.total_seconds():.1f}s, Limit: {flood_interval}s")
                return False
        else:
            # İlk mesaj - zaman farkı hesaplanamaz
            logger.info(f"🆕 İlk mesaj - User: {user_id}")
        
        # Son mesaj zamanını güncelle
        user_last_message[user_id] = now
        return True
        
    except Exception as e:
        logger.error(f"❌ Flood protection hatası: {e}")
        return True  # Hata durumunda izin ver


async def check_message_uniqueness(user_id: int, message_text: str) -> bool:
    """
    Mesaj benzersizlik kontrolü - Kelime tekrarı koruması (Daha esnek)
    """
    try:
        current_time = datetime.now()
        
        # Kullanıcının son mesajlarını al
        if user_id not in user_last_messages:
            user_last_messages[user_id] = []
        if user_id not in user_message_timestamps:
            user_message_timestamps[user_id] = []
        
        last_messages = user_last_messages[user_id]
        timestamps = user_message_timestamps[user_id]
        
        # Zaman kontrolü - Son 60 saniyede aynı mesaj varsa spam
        if len(timestamps) >= 1:
            for i, timestamp in enumerate(timestamps):
                time_diff = (current_time - timestamp).total_seconds()
                if time_diff < 60 and last_messages[i] == message_text:
                    logger.info(f"⚠️ Aynı mesaj tekrarı tespit edildi - User: {user_id}")
                    return False
        
        # Son 3 mesajı kontrol et (daha esnek)
        for last_msg in last_messages:
            # Mesajlar çok benzer mi kontrol et
            if await calculate_similarity(message_text, last_msg) > 0.85:  # %85 benzerlik (daha esnek)
                logger.info(f"⚠️ Benzer mesaj tespit edildi - User: {user_id}")
                return False
        
        # Yeni mesajı listeye ekle
        last_messages.append(message_text)
        timestamps.append(current_time)
        
        # Listeyi 3 mesajla sınırla (daha esnek)
        if len(last_messages) > 3:
            last_messages.pop(0)
            timestamps.pop(0)
        
        user_last_messages[user_id] = last_messages
        user_message_timestamps[user_id] = timestamps
        return True
        
    except Exception as e:
        logger.error(f"❌ Message uniqueness hatası: {e}")
        return True  # Hata durumunda geç


async def send_daily_limit_notification(user_id: int, first_name: str, daily_limit: float) -> None:
    """Günlük limit dolu bildirimi"""
    try:
        if SIMULATE:
            return
        from config import get_config
        from aiogram import Bot
        
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        try:
            message = f"""
🎯 **GÜNLÜK LİMİT DOLU!**

Merhaba {first_name}! 

📅 **Günlük kazanım limitinizi doldurdunuz!**
💰 **Limit:** {daily_limit} Kirve Point

⏰ **Tekrar kazanmak için 24 saatin geçmesini bekleyin.**

🔄 **Yarın tekrar aktif olacaksınız!**
            """
            
            await bot.send_message(
                user_id,
                message,
                parse_mode="Markdown"
            )
        finally:
            try:
                await bot.session.close()
            except Exception:
                pass
        
        logger.info(f"📅 Günlük limit bildirimi gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Günlük limit bildirimi hatası: {e}")


async def send_weekly_limit_notification(user_id: int, first_name: str, weekly_limit: float) -> None:
    """Haftalık limit dolu bildirimi"""
    try:
        if SIMULATE:
            return
        from config import get_config
        from aiogram import Bot
        
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        try:
            message = f"""
🎯 **HAFTALIK LİMİT DOLU!**

Merhaba {first_name}! 

📊 **Haftalık kazanım limitinizi doldurdunuz!**
💰 **Limit:** {weekly_limit} Kirve Point

⏰ **Tekrar kazanmak için haftanın sonunu bekleyin.**

🔄 **Pazartesi tekrar aktif olacaksınız!**
            """
            
            await bot.send_message(
                user_id,
                message,
                parse_mode="Markdown"
            )
        finally:
            try:
                await bot.session.close()
            except Exception:
                pass
        
        logger.info(f"📊 Haftalık limit bildirimi gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Haftalık limit bildirimi hatası: {e}")


async def calculate_similarity(text1: str, text2: str) -> float:
    """
    İki metin arasındaki benzerlik oranını hesapla
    """
    try:
        # Basit benzerlik hesaplama
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
            
        return intersection / union
        
    except Exception as e:
        logger.error(f"❌ Similarity calculation hatası: {e}")
        return 0.0


async def cleanup_flood_cache() -> None:
    """
    Eski flood cache verilerini temizle (bellek tasarrufu)
    """
    try:
        now = datetime.now()
        cutoff_time = now - timedelta(hours=1)  # 1 saat öncesini temizle
        
        # Eski mesaj zamanlarını temizle
        old_users = [
            user_id for user_id, last_time in user_last_message.items()
            if last_time < cutoff_time
        ]
        
        for user_id in old_users:
            user_last_message.pop(user_id, None)
            user_last_messages.pop(user_id, None)  # Mesaj geçmişini de temizle
            
        if old_users:
            logger.info(f"🧹 Flood cache temizlendi - {len(old_users)} kullanıcı")
            
    except Exception as e:
        logger.error(f"❌ Flood cache cleanup hatası: {e}")


# Periyodik temizlik için background task
async def start_cleanup_task():
    """
    Her 30 dakikada bir cache temizliği yap
    """
    while True:
        try:
            await asyncio.sleep(1800)  # 30 dakika bekle
            await cleanup_flood_cache()
        except Exception as e:
            logger.error(f"❌ Cleanup task hatası: {e}")
            await asyncio.sleep(60)  # Hata durumunda 1 dakika bekle


async def get_dynamic_point_amount() -> float:
    """Admin panel ile aynı kaynaktan (system_settings) point_per_message'i al."""
    try:
        pool = await get_db_pool()
        if not pool:
            return 0.04
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT points_per_message
                FROM system_settings WHERE id = 1
                """
            )
            if row and row['points_per_message'] is not None:
                # DB'de 0.04 gibi saklanıyor; panel fonksiyonları 100'e bölüyor ama burada doğrudan kullanıyoruz
                return float(row['points_per_message'])
            return 0.04
    except Exception as e:
        logger.error(f"❌ Dinamik point miktarı alınamadı: {e}")
        return 0.04


async def get_random_notification_image() -> Optional[str]:
    """
    Rastgele bir bildirim görseli seç
    """
    try:
        from pathlib import Path
        
        # Görseller klasörü
        images_dir = Path("assets/point_notifications")
        
        if not images_dir.exists():
            images_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"📁 Görseller klasörü oluşturuldu: {images_dir}")
            return None
        
        # Desteklenen görsel formatları
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        
        # Klasördeki tüm görselleri bul
        images = []
        for ext in allowed_extensions:
            images.extend(list(images_dir.glob(f"*{ext}")))
            images.extend(list(images_dir.glob(f"*{ext.upper()}")))
        
        if not images:
            logger.debug(f"📷 Görsel bulunamadı: {images_dir}")
            return None
        
        # Rastgele bir görsel seç
        selected_image = random.choice(images)
        logger.debug(f"📷 Görsel seçildi: {selected_image.name}")
        return str(selected_image)
        
    except Exception as e:
        logger.error(f"❌ Görsel seçme hatası: {e}")
        return None

async def send_private_point_notification(user_id: int, first_name: str, total_points: float, total_messages: int, group_name: str, earned_points: float = 0.04, is_milestone: bool = False) -> None:
    """
    Kullanıcıya özel mesajla point bildirimi gönder (görsel ile)
    """
    try:
        if SIMULATE:
            return
        from aiogram import Bot
        from aiogram.types import FSInputFile
        from config import get_config
        
        config = get_config()
        
        # Geçici bot instance
        temp_bot = Bot(token=config.BOT_TOKEN)
        try:
            # Rastgele görsel seç
            image_path = await get_random_notification_image()
            
            if is_milestone:
                # 1.00 point milestone bildirimi
                notification = f"""
🎊 ┌─────────────────────────────────┐ 🎊
🏆 │      **MILESTONE BAŞARISI!**       │ 🏆
🎊 └─────────────────────────────────┘ 🎊

🌟 **Tebrikler {first_name}!**

🎯 **{int(total_points)}.00 KP** hedefine ulaştınız! 

━━━━━━━━━━━━━━━━━━━━━━

📊 **MEVCUT DURUMUNUZ:**
💰 **Toplam Point:** `{total_points:.2f} KP`
📝 **Mesaj Sayısı:** `{total_messages}`
🏛️ **Aktif Grup:** {group_name}

━━━━━━━━━━━━━━━━━━━━━━

🎉 **Her 2.00 KP'de özel bildirim alırsınız!**

📱 _Detaylı profil için:_ `/menu`
🎮 **Böyle devam edin!** ✨
                """
            else:
                # Normal point kazanım bildirimi - Daha estetik format
                emoji_variations = [
                    "💎", "✨", "🌟", "🎯", "🔥", "⚡", "💫", "🎊"
                ]
                selected_emoji = random.choice(emoji_variations)
                
                # Üyelik seviyesi bilgisi (mesaj sayısına göre)
                level_info = get_level_info_by_messages(total_messages)
                level_display = format_level_display(total_messages)
                
                notification = f"""
{selected_emoji} **Point Kazandın!** {selected_emoji}

━━━━━━━━━━━━━━━━━━━━━━

👋 **Merhaba {first_name}!** 

🎯 **{group_name}** grubunda sohbet ederek **{earned_points:.2f} KP** kazandın!

━━━━━━━━━━━━━━━━━━━━━━

📊 **MEVCUT DURUMUNUZ:**

💰 **Toplam Point:** `{total_points:.2f} KP`
🏆 **Üyelik Seviyesi:** {level_display}
📝 **Mesaj Sayısı:** `{total_messages:,}`
🏛️ **Aktif Grup:** {group_name}

━━━━━━━━━━━━━━━━━━━━━━

💡 **Devam edebilirsin!** Her 2.00 KP'de bildirim alırsın! 🚀

🎮 **Daha fazla kazanmak için sohbete devam et!** ✨
                """
            
            # Rastgele avatar seç
            avatar_file = get_random_avatar_file() if not is_milestone else None
            
            # Avatar varsa avatar ile gönder, yoksa görsel ile, yoksa sadece metin
            if avatar_file:
                try:
                    await temp_bot.send_photo(
                        chat_id=user_id,
                        photo=avatar_file,
                        caption=notification,
                        parse_mode="Markdown"
                    )
                    logger.debug(f"✅ Point bildirimi avatar ile gönderildi - User: {user_id}")
                    return
                except Exception as avatar_error:
                    logger.warning(f"⚠️ Avatar gönderme hatası, görsel deneniyor: {avatar_error}")
            
            # Avatar yoksa görsel ile gönder
            if image_path:
                try:
                    photo = FSInputFile(image_path)
                    await temp_bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption=notification,
                        parse_mode="Markdown"
                    )
                    logger.debug(f"✅ Point bildirimi görsel ile gönderildi - User: {user_id}, Image: {image_path}")
                except Exception as photo_error:
                    logger.warning(f"⚠️ Görsel gönderme hatası, sadece metin gönderiliyor: {photo_error}")
                    await temp_bot.send_message(
                        chat_id=user_id,
                        text=notification,
                        parse_mode="Markdown"
                    )
            else:
                await temp_bot.send_message(
                    chat_id=user_id,
                    text=notification,
                    parse_mode="Markdown"
                )
                logger.debug(f"✅ Point bildirimi gönderildi (görsel yok) - User: {user_id}")
        finally:
            # Bot session'ını her durumda kapat
            try:
                await temp_bot.session.close()
            except Exception:
                pass
        
    except Exception as e:
        logger.error(f"❌ Point bildirimi gönderilemedi: {e}")


async def send_level_up_notification(user_id: int, first_name: str, level_up_info: Dict) -> None:
    """
    Seviye atlama bildirimi gönder
    """
    try:
        from aiogram import Bot
        from aiogram.types import FSInputFile
        from config import get_config
        from handlers.membership_levels import get_level_icon_file, get_random_avatar_file
        
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        try:
            old_level_info = level_up_info['old_level_info']
            new_level_info = level_up_info['new_level_info']
            new_messages = level_up_info['new_messages']
            
            # Seviye ikonu al (SEVİYE ATLAMA BİLDİRİMİNDE ÖNCELİKLİ)
            level_icon = get_level_icon_file(level_up_info['new_level'])
            
            # Avatar yedek olarak (seviye ikonu yoksa)
            avatar_file = get_random_avatar_file()
            
            notification = f"""
🎊 ┌─────────────────────────────────┐ 🎊
🏆 │      **SEVİYE ATLADIN!**          │ 🏆
🎊 └─────────────────────────────────┘ 🎊

🌟 **Tebrikler {first_name}!**

{old_level_info['emoji']} **{old_level_info['name']}** → {new_level_info['emoji']} **{new_level_info['name']}**

━━━━━━━━━━━━━━━━━━━━━━

📝 **Toplam Mesaj:** `{new_messages:,} mesaj`
🏆 **Yeni Seviye:** {new_level_info['emoji']} {new_level_info['name']}

━━━━━━━━━━━━━━━━━━━━━━

🎉 **Harika bir başarı!** Daha yüksek seviyelere ulaşmak için sohbete devam et!

🎮 **Tebrikler!** ✨
            """
            
            # ÖNCE SEVİYE İKONU DENE (seviye atlama bildirimi için en uygun)
            if level_icon:
                try:
                    await bot.send_photo(
                        user_id,
                        photo=level_icon,
                        caption=notification,
                        parse_mode="Markdown"
                    )
                    logger.debug(f"🎉 Seviye atlama bildirimi gönderildi (SEVİYE İKONU ile) - User: {user_id}, Level: {new_level_info['name']}")
                    return
                except Exception as icon_error:
                    logger.warning(f"⚠️ Seviye ikonu gönderme hatası: {icon_error}, avatar deneniyor...")
            
            # Seviye ikonu yoksa veya hata verirse avatar dene
            if avatar_file:
                try:
                    await bot.send_photo(
                        user_id,
                        photo=avatar_file,
                        caption=notification,
                        parse_mode="Markdown"
                    )
                    logger.debug(f"🎉 Seviye atlama bildirimi avatar ile gönderildi - User: {user_id}, Level: {new_level_info['name']}")
                    return
                except Exception as avatar_error:
                    logger.warning(f"⚠️ Avatar gönderme hatası: {avatar_error}, sadece metin gönderiliyor...")
            
            # Hiçbiri yoksa sadece metin gönder
            await bot.send_message(
                user_id,
                notification,
                parse_mode="Markdown"
            )
            logger.debug(f"🎉 Seviye atlama bildirimi gönderildi (sadece metin) - User: {user_id}, Level: {new_level_info['name']}")
        finally:
            # Bot session'ını her durumda kapat
            try:
                await bot.session.close()
            except Exception:
                pass
        
    except Exception as e:
        logger.error(f"❌ Seviye atlama bildirimi gönderilemedi: {e}")

async def check_new_user_recruitment(user_id: int, first_name: str, group_name: str, message_length: int, message: Message = None) -> None:
    """Yeni kullanıcı teşvik sistemi - Sıralı sistem"""
    try:
        # DEBUG: Kullanıcı bilgilerini logla
        logger.info(f"🔍 Recruitment kontrolü - User: {user_id}, Name: {first_name}, Group: {group_name}")
        
        # Günlük limit kontrolü (kullanıcı başına 1 kez) - TEST İÇİN KAPALI
        # daily_sent = await is_recruitment_sent_today(user_id)
        # if daily_sent:
        #     logger.info(f"⏰ Günlük limit: User {user_id} için bugün zaten teşvik gönderilmiş")
        #     return
            
        # Kullanıcının toplam mesaj sayısını kontrol et
        pool = await get_db_pool()
        if not pool:
            logger.error(f"❌ Database pool bulunamadı - User: {user_id}")
            return
            
        async with pool.acquire() as conn:
            # Son 7 günde toplam mesaj sayısını al
            total_messages = await conn.fetchval("""
                SELECT COALESCE(SUM(message_count), 0)
                FROM daily_stats 
                WHERE user_id = $1 
                  AND message_date >= CURRENT_DATE - INTERVAL '7 days'
            """, user_id)
            
            logger.info(f"📊 Mesaj sayısı kontrolü - User: {user_id}, Total: {total_messages}")
            
            # Aktif kullanıcı kontrolü (spam önlemi)
            if total_messages <= 50:  # En fazla 50 mesaj atmış olanlar (PRODUCTION AYARI)
                logger.info(f"🎯 Teşvik gönderiliyor - User: {user_id}, Messages: {total_messages}")
                await send_new_user_recruitment(user_id, first_name, group_name, total_messages, message)
            else:
                logger.info(f"📊 Çok mesaj atmış kullanıcı - User: {user_id}, Messages: {total_messages}")
            
    except Exception as e:
        logger.error(f"❌ New user recruitment hatası: {e}")

async def send_new_user_recruitment(user_id: int, first_name: str, group_name: str, message_count: int, original_message: Message = None) -> None:
    """Yeni kullanıcıya teşvik mesajı gönder - Sıralı sistem"""
    try:
        if SIMULATE:
            return
        from aiogram import Bot
        from config import get_config
        import random
        from datetime import datetime
        config = get_config()
        
        # SIRALI SİSTEM: Kullanıcı bazlı cooldown kontrolü - AÇIK
        from handlers.recruitment_system import user_recruitment_times, recruitment_message_cooldown
        
        current_time = datetime.now()
        
        # Bu kullanıcıya son ne zaman teşvik gönderildi?
        last_time = user_recruitment_times.get(user_id)
        if last_time:
            time_diff = (current_time - last_time).total_seconds()
            if time_diff < recruitment_message_cooldown:
                remaining_time = recruitment_message_cooldown - time_diff
                logger.info(f"⏰ Kullanıcı cooldown: User {user_id} için henüz çok erken ({remaining_time:.0f}s kaldı)")
                return
        
        # Geçici bot instance
        temp_bot = Bot(token=config.BOT_TOKEN)
        try:
            # 1. GRUP REPLY MESAJI (kısa ve etkili - özelden yazmaya yönlendirici)
            if original_message:
                group_reply_messages = [
                    "🎯 Kirvem! Özelden yaz, tüm bonusları anlatayım! 💎",
                    "💎 Kirve! Hala kayıtsız mısın? Özelden yaz, detayları vereyim! 🚀",
                    "🎮 Kirvem! Özelden yaz, Kirve Point sistemini anlatayım! 💎",
                    "💎 Kirve! Sistemde yoksun! Özelden yaz, her şeyi anlatayım! 🎯",
                    "🚀 Kirvem! Özelden yaz, market ve etkinlikleri anlatayım! 💎",
                    "💎 Kirve! Hala gruba kayıtlı değilsin! Özelden yaz! 🎮",
                    "🎯 Kirvem! Özelden yaz, günlük 5 KP kazanma sistemini anlatayım! 💎",
                    "💎 Kirve! Kayıt olmadan çok şey kaçırıyorsun! Özelden yaz! 🚀",
                    "🎮 Kirvem! Özelden yaz, çekiliş ve bonus sistemini anlatayım! 💎",
                    "💎 Kirve! Hala sistemde yoksun! Özelden yaz, tüm detayları vereyim! 🎯",
                    "🏆 Kirvem! Özelden yaz, sıralama sistemini anlatayım! 💎",
                    "🎯 Kirve! Özelden yaz, hızlı kazanım sistemini anlatayım! 🚀",
                    "💎 Kirvem! Özelden yaz, özel ayrıcalıkları anlatayım! 🎮"
                ]
                
                reply_message = random.choice(group_reply_messages)
                
                try:
                    await temp_bot.send_message(
                        chat_id=original_message.chat.id,
                        text=reply_message,
                        reply_to_message_id=original_message.message_id
                    )
                    logger.debug(f"💬 Grup reply gönderildi - User: {user_id}, Group: {group_name}")
                except Exception as e:
                    logger.error(f"❌ Grup reply hatası: {e}")
            
            # 2. ÖZEL MESAJ (detaylı bilgilendirme) - KAPALI
            # ÖZEL MESAJ KAPALI - TELEGRAM KISITLAMASI
            # Bot sadece daha önce mesaj atmış kullanıcılara özel mesaj gönderebilir
            # Bu yüzden sadece grup reply kullanıyoruz
            
            # Kullanıcı bazlı cooldown kaydı - AÇIK
            user_recruitment_times[user_id] = current_time
            
            logger.debug(f"🎯 Yeni kullanıcı teşviki tamamlandı - User: {user_id}, Messages: {message_count} (sadece grup reply)")
        finally:
            # Bot session'ını her durumda kapat
            try:
                await temp_bot.session.close()
            except Exception:
                pass
        
    except Exception as e:
        logger.error(f"❌ New user recruitment hatası: {e}")

async def auto_recruit_user(user_id: int, first_name: str, group_name: str) -> None:
    """
    Kayıtsız kullanıcıya auto-recruitment mesajı gönder (günde 1 kez)
    """
    try:
        # Bugün bu kullanıcıya mesaj gönderildi mi kontrol et
        if await is_recruitment_sent_today(user_id):
            return
            
        from aiogram import Bot
        from config import get_config
        config = get_config()
        
        # Geçici bot instance
        temp_bot = Bot(token=config.BOT_TOKEN)
        try:
            recruitment_message = f"""
🎯 **Merhaba {first_name}!**

**{group_name}** grubunda mesajlaşıyorsun fakat kayıt olarak çok daha fazlasını kazanabilirsin! 

💎 **Kayıt olduktan sonra:**
• Otomatik sistem aktif olur
• Özel etkinliklere katılabilirsin  
• Market'ten alışveriş yapabilirsin
• Sıralamada yükselirsin

🚀 **Detaylar için bana özel mesaj at!**

_Komutlar: /start veya /kirvekayit_
            """
            
            await temp_bot.send_message(
                chat_id=user_id,
                text=recruitment_message,
                parse_mode="Markdown"
            )
            
            # Bugün gönderildi olarak işaretle
            await mark_recruitment_sent_today(user_id)
            
            logger.info(f"🎯 Auto-recruitment gönderildi - User: {user_id} - Group: {group_name}")
        finally:
            # Bot session'ını her durumda kapat
            try:
                await temp_bot.session.close()
            except Exception:
                pass
        
    except Exception as e:
        logger.error(f"❌ Auto-recruitment gönderilemedi: {e}")


async def is_recruitment_sent_today(user_id: int) -> bool:
    """Bugün bu kullanıcıya recruitment mesajı gönderildi mi?"""
    try:
        if not db_pool:
            return False
            
        from datetime import date
        today = date.today()
        
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT 1 FROM daily_stats 
                WHERE user_id = $1 AND message_date = $2 AND character_count = -1
            """, user_id, today)
            
            return result is not None
            
    except Exception as e:
        logger.error(f"❌ Recruitment check hatası: {e}")
        return False


async def mark_recruitment_sent_today(user_id: int) -> None:
    """Bugün recruitment gönderildi olarak işaretle"""
    try:
        if not db_pool:
            return
            
        from datetime import date
        today = date.today()
        
        async with db_pool.acquire() as conn:
            # character_count = -1 → recruitment marker
            await conn.execute("""
                INSERT INTO daily_stats (user_id, group_id, message_date, message_count, character_count)
                VALUES ($1, 0, $2, 0, -1)
                ON CONFLICT (user_id, group_id, message_date) DO NOTHING
            """, user_id, today)
            
    except Exception as e:
        logger.error(f"❌ Recruitment marking hatası: {e}") 

async def send_milestone_notification(user_id: int, first_name: str, new_balance: float) -> None:
    """Milestone bildirimi gönder (1.00 KP'ye ulaşınca)"""
    try:
        from config import get_config
        from aiogram import Bot
        
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        try:
            # Milestone mesajları
            milestone_messages = [
                f"""
🎉 **TEBRİKLER! İLK MİLESTONE'A ULAŞTIN!** 🎉

Merhaba {first_name}! 

💰 **Yeni Bakiyen:** {new_balance:.2f} KP
🎯 **Milestone:** 1.00 KP'ye ulaştın!

🚀 **Artık şunları yapabilirsin:**
✅ Market'ten ürün alabilirsin
✅ Etkinliklere katılabilirsin
✅ Sıralamada yer alabilirsin

💡 **İpucu:** Günlük 5.00 KP limitini doldurmaya devam et!

🎮 **Devam et ve daha fazla kazan!** 💎
                """,
                f"""
🏆 **MİLESTONE BAŞARISI!** 🏆

Merhaba {first_name}! 

💰 **Bakiyen:** {new_balance:.2f} KP
🎯 **Başarı:** İlk 1.00 KP'ye ulaştın!

🎉 **Bu başarının anlamı:**
✅ Sistemde aktif kullanıcısın
✅ Point kazanma sistemini öğrendin
✅ Topluluğa katkı sağlıyorsun

💎 **Devam et ve daha fazla kazan!**

🎮 **İyi şanslar!** 🚀
                """,
                f"""
💎 **1.00 KP MİLESTONE!** 💎

Merhaba {first_name}! 

💰 **Yeni Bakiyen:** {new_balance:.2f} KP
🎯 **Başarı:** İlk milestone'a ulaştın!

🌟 **Bu ne anlama geliyor:**
✅ Point sistemini anladın
✅ Aktif bir üyesin
✅ Market'e erişim kazandın

🎮 **Şimdi market'ten ürün alabilirsin!**

💫 **Devam et ve daha fazla kazan!** 🚀
                """
            ]
            
            # Rastgele mesaj seç
            import random
            message = random.choice(milestone_messages)
            
            await bot.send_message(
                user_id,
                message,
                parse_mode="Markdown"
            )
            
            logger.debug(f"🎉 Milestone bildirimi gönderildi - User: {user_id}, Balance: {new_balance}")
        finally:
            # Bot session'ını her durumda kapat
            try:
                await bot.session.close()
            except Exception:
                pass
        
    except Exception as e:
        logger.error(f"❌ Milestone bildirimi hatası: {e}") 