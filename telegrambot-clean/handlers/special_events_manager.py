"""
🎯 Özel Etkinlikler Yönetim Sistemi - KirveHub Bot
Yazı Yazma Etkinliği ve Mesaj Yarışı Etkinliği
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import get_config, is_admin
from database import get_db_pool, is_user_registered
from handlers.admin_permission_manager import has_min_rank_db
from utils.logger import logger

router = Router()

# Bot instance setter
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

# FSM States
class WritingEventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_duration = State()
    waiting_for_multiplier = State()
    waiting_for_confirmation = State()

class MessageRaceEventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_duration = State()
    waiting_for_winners = State()
    waiting_for_rewards = State()
    waiting_for_confirmation = State()

# Aktif etkinlikler cache (performans için)
active_events_cache: Dict[int, Dict] = {}
event_stats_cache: Dict[int, Dict] = {}  # {event_id: {user_id: message_count}}

# ============================================================================
# YAZI YAZMA ETKİNLİĞİ (Writing Event)
# ============================================================================

async def get_active_writing_event(group_id: int = None) -> Optional[Dict]:
    """Aktif yazı yazma etkinliğini getir"""
    try:
        pool = await get_db_pool()
        if not pool:
            return None
        
        async with pool.acquire() as conn:
            if group_id:
                event = await conn.fetchrow("""
                    SELECT id, title, description, duration_minutes, bonus_multiplier, 
                           created_at, ends_at, status, event_config
                    FROM events
                    WHERE event_type = 'writing_event' 
                      AND status = 'active'
                      AND (group_id = $1 OR group_id = 0)
                    ORDER BY created_at DESC
                    LIMIT 1
                """, group_id)
            else:
                event = await conn.fetchrow("""
                    SELECT id, title, description, duration_minutes, bonus_multiplier, 
                           created_at, ends_at, status, event_config
                    FROM events
                    WHERE event_type = 'writing_event' 
                      AND status = 'active'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
            
            if event:
                return dict(event)
            return None
    except Exception as e:
        logger.error(f"❌ Get active writing event hatası: {e}")
        return None

async def create_writing_event(
    title: str,
    description: str,
    duration_hours: int,
    kp_multiplier: float,
    group_id: int = 0,
    created_by: int = None
) -> tuple[bool, int]:
    """Yazı yazma etkinliği oluştur"""
    try:
        pool = await get_db_pool()
        if not pool:
            return False, 0
        
        duration_minutes = duration_hours * 60
        ends_at = datetime.now() + timedelta(hours=duration_hours)
        
        async with pool.acquire() as conn:
            # Önce mevcut aktif etkinliği kontrol et
            existing = await conn.fetchrow("""
                SELECT id FROM events 
                WHERE event_type = 'writing_event' 
                  AND status = 'active'
                  AND (group_id = $1 OR group_id = 0)
                LIMIT 1
            """, group_id)
            
            if existing:
                logger.warning(f"⚠️ Zaten aktif bir yazı yazma etkinliği var: {existing['id']}")
                return False, existing['id']
            
            # Yeni etkinlik oluştur
            event_id = await conn.fetchval("""
                INSERT INTO events (
                    event_type, title, description, duration_minutes, 
                    bonus_multiplier, status, created_by, group_id,
                    created_at, ends_at, event_config
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """, 
                'writing_event',
                title,
                description,
                duration_minutes,
                kp_multiplier,
                'active',
                created_by,
                group_id,
                datetime.now(),
                ends_at,
                {'kp_multiplier': kp_multiplier, 'duration_hours': duration_hours}
            )
            
            # Cache'e ekle
            active_events_cache[event_id] = {
                'type': 'writing_event',
                'multiplier': kp_multiplier,
                'ends_at': ends_at
            }
            
            logger.info(f"✅ Yazı yazma etkinliği oluşturuldu: {title} (ID: {event_id})")
            return True, event_id
            
    except Exception as e:
        logger.error(f"❌ Create writing event hatası: {e}", exc_info=True)
        return False, 0

async def end_writing_event(event_id: int) -> bool:
    """Yazı yazma etkinliğini bitir"""
    try:
        pool = await get_db_pool()
        if not pool:
            return False
        
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE events 
                SET status = 'completed', completed_at = NOW()
                WHERE id = $1 AND event_type = 'writing_event'
            """, event_id)
            
            # Cache'den kaldır
            if event_id in active_events_cache:
                del active_events_cache[event_id]
            
            logger.info(f"✅ Yazı yazma etkinliği bitirildi: {event_id}")
            return True
    except Exception as e:
        logger.error(f"❌ End writing event hatası: {e}")
        return False

# ============================================================================
# MESAJ YARIŞI ETKİNLİĞİ (Message Race Event)
# ============================================================================

async def get_active_message_race_event(group_id: int = None) -> Optional[Dict]:
    """Aktif mesaj yarışı etkinliğini getir"""
    try:
        pool = await get_db_pool()
        if not pool:
            return None
        
        async with pool.acquire() as conn:
            if group_id:
                event = await conn.fetchrow("""
                    SELECT id, title, description, duration_minutes, 
                           created_at, ends_at, status, event_config
                    FROM events
                    WHERE event_type = 'message_race_event' 
                      AND status = 'active'
                      AND (group_id = $1 OR group_id = 0)
                    ORDER BY created_at DESC
                    LIMIT 1
                """, group_id)
            else:
                event = await conn.fetchrow("""
                    SELECT id, title, description, duration_minutes, 
                           created_at, ends_at, status, event_config
                    FROM events
                    WHERE event_type = 'message_race_event' 
                      AND status = 'active'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
            
            if event:
                return dict(event)
            return None
    except Exception as e:
        logger.error(f"❌ Get active message race event hatası: {e}")
        return None

async def create_message_race_event(
    title: str,
    description: str,
    duration_hours: int,
    top_winners: int,
    rewards: List[float],  # [1. ödül, 2. ödül, 3. ödül, ...]
    group_id: int = 0,
    created_by: int = None
) -> tuple[bool, int]:
    """Mesaj yarışı etkinliği oluştur"""
    try:
        pool = await get_db_pool()
        if not pool:
            return False, 0
        
        duration_minutes = duration_hours * 60
        ends_at = datetime.now() + timedelta(hours=duration_hours)
        
        async with pool.acquire() as conn:
            # Önce mevcut aktif etkinliği kontrol et
            existing = await conn.fetchrow("""
                SELECT id FROM events 
                WHERE event_type = 'message_race_event' 
                  AND status = 'active'
                  AND (group_id = $1 OR group_id = 0)
                LIMIT 1
            """, group_id)
            
            if existing:
                logger.warning(f"⚠️ Zaten aktif bir mesaj yarışı etkinliği var: {existing['id']}")
                return False, existing['id']
            
            # Yeni etkinlik oluştur
            event_id = await conn.fetchval("""
                INSERT INTO events (
                    event_type, title, description, duration_minutes, 
                    max_winners, status, created_by, group_id,
                    created_at, ends_at, event_config
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """, 
                'message_race_event',
                title,
                description,
                duration_minutes,
                top_winners,
                'active',
                created_by,
                group_id,
                datetime.now(),
                ends_at,
                {'top_winners': top_winners, 'rewards': rewards, 'duration_hours': duration_hours}
            )
            
            # Cache'e ekle
            active_events_cache[event_id] = {
                'type': 'message_race_event',
                'top_winners': top_winners,
                'rewards': rewards,
                'ends_at': ends_at
            }
            
            # İstatistik cache'i başlat
            event_stats_cache[event_id] = {}
            
            logger.info(f"✅ Mesaj yarışı etkinliği oluşturuldu: {title} (ID: {event_id})")
            return True, event_id
            
    except Exception as e:
        logger.error(f"❌ Create message race event hatası: {e}", exc_info=True)
        return False, 0

async def record_message_for_race(event_id: int, user_id: int) -> None:
    """Mesaj yarışı için mesaj kaydet"""
    try:
        if event_id not in event_stats_cache:
            event_stats_cache[event_id] = {}
        
        if user_id not in event_stats_cache[event_id]:
            event_stats_cache[event_id][user_id] = 0
        
        event_stats_cache[event_id][user_id] += 1
        
    except Exception as e:
        logger.error(f"❌ Record message for race hatası: {e}")

async def get_message_race_leaderboard(event_id: int, limit: int = 10) -> List[Dict]:
    """Mesaj yarışı liderlik tablosunu getir"""
    try:
        if event_id not in event_stats_cache:
            return []
        
        # Sıralama yap
        leaderboard = []
        for user_id, message_count in event_stats_cache[event_id].items():
            leaderboard.append({
                'user_id': user_id,
                'message_count': message_count
            })
        
        # Mesaj sayısına göre sırala (yüksekten düşüğe)
        leaderboard.sort(key=lambda x: x['message_count'], reverse=True)
        
        return leaderboard[:limit]
    except Exception as e:
        logger.error(f"❌ Get leaderboard hatası: {e}")
        return []

async def end_message_race_event(event_id: int) -> bool:
    """Mesaj yarışı etkinliğini bitir ve ödülleri dağıt"""
    try:
        pool = await get_db_pool()
        if not pool:
            return False
        
        # Liderlik tablosunu al
        leaderboard = await get_message_race_leaderboard(event_id, limit=50)
        
        if not leaderboard:
            logger.warning(f"⚠️ Mesaj yarışı etkinliğinde katılımcı yok: {event_id}")
            await end_writing_event(event_id)  # Sadece durumu güncelle
            return True
        
        # Etkinlik bilgilerini al
        async with pool.acquire() as conn:
            event = await conn.fetchrow("""
                SELECT event_config, max_winners FROM events WHERE id = $1
            """, event_id)
            
            if not event:
                return False
            
            event_config = event.get('event_config', {}) if isinstance(event.get('event_config'), dict) else {}
            rewards = event_config.get('rewards', [])
            top_winners = event.get('max_winners', 3)
            
            # Kazananları belirle ve ödül dağıt
            winners = []
            for i, entry in enumerate(leaderboard[:top_winners]):
                user_id = entry['user_id']
                message_count = entry['message_count']
                reward = rewards[i] if i < len(rewards) else 0.0
                
                if reward > 0:
                    # Ödül dağıt
                    from database import add_message_to_user
                    await add_message_to_user(user_id, 0)  # group_id = 0 (özel etkinlik)
                    # Ödül miktarını ekle
                    await conn.execute("""
                        UPDATE users 
                        SET kirve_points = kirve_points + $1
                        WHERE user_id = $2
                    """, reward, user_id)
                    
                    logger.info(f"🏆 Mesaj yarışı ödülü: User {user_id}, {message_count} mesaj, {reward} KP")
                
                winners.append({
                    'user_id': user_id,
                    'message_count': message_count,
                    'reward': reward,
                    'rank': i + 1
                })
            
            # Etkinliği bitir
            await conn.execute("""
                UPDATE events 
                SET status = 'completed', 
                    completed_at = NOW(),
                    winners = $1::jsonb
                WHERE id = $2
            """, winners, event_id)
            
            # Cache'den kaldır
            if event_id in active_events_cache:
                del active_events_cache[event_id]
            if event_id in event_stats_cache:
                del event_stats_cache[event_id]
            
            logger.info(f"✅ Mesaj yarışı etkinliği bitirildi: {event_id}, {len(winners)} kazanan")
            return True
            
    except Exception as e:
        logger.error(f"❌ End message race event hatası: {e}", exc_info=True)
        return False

# ============================================================================
# KOMUTLAR
# ============================================================================

@router.message(Command("ozel etkinlik"))
async def special_events_menu_command(message: Message):
    """Özel etkinlikler menüsü"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not await has_min_rank_db(user_id, 3):
            return
        
        # Grup sessizlik
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
            
            if _bot_instance:
                await _send_special_events_menu_privately(user_id)
            return
        
        await _send_special_events_menu_privately(user_id)
        
    except Exception as e:
        logger.error(f"❌ Special events menu hatası: {e}")

async def _send_special_events_menu_privately(user_id: int):
    """Özel etkinlikler menüsünü özel mesajla gönder"""
    try:
        if not _bot_instance:
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Yazı Yazma Etkinliği", callback_data="special_event_writing")],
            [InlineKeyboardButton(text="🏆 Mesaj Yarışı Etkinliği", callback_data="special_event_race")],
            [InlineKeyboardButton(text="📊 Aktif Etkinlikler", callback_data="special_event_list")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="special_event_cancel")]
        ])
        
        await _bot_instance.send_message(
            user_id,
            "🎯 **Özel Etkinlikler Yönetimi**\n\n"
            "Hangi tür etkinlik oluşturmak istiyorsunuz?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"❌ Special events menu gönderilemedi: {e}")

@router.message(Command("yaziyazma"))
async def writing_event_command(message: Message, state: FSMContext):
    """Yazı yazma etkinliği oluşturma komutu"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not await has_min_rank_db(user_id, 3):
            return
        
        # Grup sessizlik
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
            
            if _bot_instance:
                await _bot_instance.send_message(
                    user_id,
                    "✍️ **Yazı Yazma Etkinliği Oluştur**\n\n"
                    "Etkinlik başlığını yazın:",
                    parse_mode="Markdown"
                )
                await state.set_state(WritingEventStates.waiting_for_title)
            return
        
        await message.reply(
            "✍️ **Yazı Yazma Etkinliği Oluştur**\n\n"
            "Etkinlik başlığını yazın:",
            parse_mode="Markdown"
        )
        await state.set_state(WritingEventStates.waiting_for_title)
        
    except Exception as e:
        logger.error(f"❌ Writing event command hatası: {e}")

@router.message(Command("mesajyarisi"))
async def message_race_command(message: Message, state: FSMContext):
    """Mesaj yarışı etkinliği oluşturma komutu"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not await has_min_rank_db(user_id, 3):
            return
        
        # Grup sessizlik
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
            
            if _bot_instance:
                await _bot_instance.send_message(
                    user_id,
                    "🏆 **Mesaj Yarışı Etkinliği Oluştur**\n\n"
                    "Etkinlik başlığını yazın:",
                    parse_mode="Markdown"
                )
                await state.set_state(MessageRaceEventStates.waiting_for_title)
            return
        
        await message.reply(
            "🏆 **Mesaj Yarışı Etkinliği Oluştur**\n\n"
            "Etkinlik başlığını yazın:",
            parse_mode="Markdown"
        )
        await state.set_state(MessageRaceEventStates.waiting_for_title)
        
    except Exception as e:
        logger.error(f"❌ Message race command hatası: {e}")

# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

@router.callback_query(F.data.startswith("special_event_"))
async def special_events_callback_handler(callback: CallbackQuery, state: FSMContext):
    """Özel etkinlikler callback handler"""
    try:
        data = callback.data
        user_id = callback.from_user.id
        
        # Admin kontrolü
        if not await has_min_rank_db(user_id, 3):
            await callback.answer("❌ Yetkiniz yok!", show_alert=True)
            return
        
        if data == "special_event_writing":
            await callback.message.edit_text(
                "✍️ **Yazı Yazma Etkinliği Oluştur**\n\n"
                "Etkinlik başlığını yazın:",
                parse_mode="Markdown"
            )
            await state.set_state(WritingEventStates.waiting_for_title)
            await callback.answer()
            
        elif data == "special_event_race":
            await callback.message.edit_text(
                "🏆 **Mesaj Yarışı Etkinliği Oluştur**\n\n"
                "Etkinlik başlığını yazın:",
                parse_mode="Markdown"
            )
            await state.set_state(MessageRaceEventStates.waiting_for_title)
            await callback.answer()
            
        elif data == "special_event_list":
            await show_active_special_events(callback)
            await callback.answer()
            
        elif data == "special_event_cancel":
            await callback.message.delete()
            await callback.answer("❌ İptal edildi")
            
    except Exception as e:
        logger.error(f"❌ Special events callback hatası: {e}")

async def show_active_special_events(callback: CallbackQuery):
    """Aktif özel etkinlikleri göster"""
    try:
        pool = await get_db_pool()
        if not pool:
            await callback.answer("❌ Database bağlantısı yok!", show_alert=True)
            return
        
        async with pool.acquire() as conn:
            events = await conn.fetch("""
                SELECT id, event_type, title, description, duration_minutes, 
                       bonus_multiplier, created_at, ends_at, status
                FROM events
                WHERE event_type IN ('writing_event', 'message_race_event')
                  AND status = 'active'
                ORDER BY created_at DESC
            """)
        
        if not events:
            await callback.message.edit_text(
                "📊 **Aktif Özel Etkinlikler**\n\n"
                "❌ Şu anda aktif özel etkinlik yok.",
                parse_mode="Markdown"
            )
            return
        
        text = "📊 **Aktif Özel Etkinlikler**\n\n"
        for event in events:
            event_type = event['event_type']
            if event_type == 'writing_event':
                icon = "✍️"
                multiplier = event.get('bonus_multiplier', 1.0)
                text += f"{icon} **{event['title']}**\n"
                text += f"   KP Çarpanı: x{multiplier}\n"
            elif event_type == 'message_race_event':
                icon = "🏆"
                text += f"{icon} **{event['title']}**\n"
                text += f"   Mesaj Yarışı\n"
            
            duration = event.get('duration_minutes', 0)
            if duration > 0:
                hours = duration // 60
                text += f"   Süre: {hours} saat\n"
            
            ends_at = event.get('ends_at')
            if ends_at:
                remaining = ends_at - datetime.now()
                if remaining.total_seconds() > 0:
                    hours = int(remaining.total_seconds() // 3600)
                    minutes = int((remaining.total_seconds() % 3600) // 60)
                    text += f"   Kalan: {hours}s {minutes}d\n"
            
            text += f"   ID: {event['id']}\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yenile", callback_data="special_event_list")],
            [InlineKeyboardButton(text="⬅️ Geri", callback_data="special_event_menu")]
        ])
        
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"❌ Show active special events hatası: {e}")

# ============================================================================
# FSM HANDLERS - Yazı Yazma Etkinliği
# ============================================================================

@router.message(WritingEventStates.waiting_for_title)
async def writing_event_title_handler(message: Message, state: FSMContext):
    """Yazı yazma etkinliği başlık handler"""
    try:
        title = message.text.strip()
        if len(title) < 3:
            await message.reply("❌ Başlık en az 3 karakter olmalı!")
            return
        
        await state.update_data(title=title)
        await message.reply(
            "✅ Başlık kaydedildi!\n\n"
            "Etkinlik açıklamasını yazın:",
            parse_mode="Markdown"
        )
        await state.set_state(WritingEventStates.waiting_for_description)
        
    except Exception as e:
        logger.error(f"❌ Writing event title handler hatası: {e}")

@router.message(WritingEventStates.waiting_for_description)
async def writing_event_description_handler(message: Message, state: FSMContext):
    """Yazı yazma etkinliği açıklama handler"""
    try:
        description = message.text.strip()
        await state.update_data(description=description)
        await message.reply(
            "✅ Açıklama kaydedildi!\n\n"
            "Etkinlik süresini saat cinsinden yazın (örn: 2):",
            parse_mode="Markdown"
        )
        await state.set_state(WritingEventStates.waiting_for_duration)
        
    except Exception as e:
        logger.error(f"❌ Writing event description handler hatası: {e}")

@router.message(WritingEventStates.waiting_for_duration)
async def writing_event_duration_handler(message: Message, state: FSMContext):
    """Yazı yazma etkinliği süre handler"""
    try:
        try:
            duration_hours = int(message.text.strip())
            if duration_hours < 1 or duration_hours > 168:  # Max 1 hafta
                await message.reply("❌ Süre 1-168 saat arasında olmalı!")
                return
        except ValueError:
            await message.reply("❌ Geçerli bir sayı girin!")
            return
        
        await state.update_data(duration_hours=duration_hours)
        await message.reply(
            "✅ Süre kaydedildi!\n\n"
            "KP çarpanını yazın (örn: 2, 2.5, 3):",
            parse_mode="Markdown"
        )
        await state.set_state(WritingEventStates.waiting_for_multiplier)
        
    except Exception as e:
        logger.error(f"❌ Writing event duration handler hatası: {e}")

@router.message(WritingEventStates.waiting_for_multiplier)
async def writing_event_multiplier_handler(message: Message, state: FSMContext):
    """Yazı yazma etkinliği çarpan handler"""
    try:
        try:
            multiplier = float(message.text.strip())
            if multiplier < 1.0 or multiplier > 10.0:
                await message.reply("❌ Çarpan 1.0-10.0 arasında olmalı!")
                return
        except ValueError:
            await message.reply("❌ Geçerli bir sayı girin!")
            return
        
        data = await state.get_data()
        title = data.get('title')
        description = data.get('description')
        duration_hours = data.get('duration_hours')
        
        # Onay mesajı
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Oluştur", callback_data="writing_event_confirm")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="writing_event_cancel")]
        ])
        
        await message.reply(
            f"📋 **Etkinlik Özeti**\n\n"
            f"**Başlık:** {title}\n"
            f"**Açıklama:** {description}\n"
            f"**Süre:** {duration_hours} saat\n"
            f"**KP Çarpanı:** x{multiplier}\n\n"
            f"Etkinliği oluşturmak istiyor musunuz?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        await state.update_data(multiplier=multiplier)
        await state.set_state(WritingEventStates.waiting_for_confirmation)
        
    except Exception as e:
        logger.error(f"❌ Writing event multiplier handler hatası: {e}")

@router.callback_query(F.data == "writing_event_confirm")
async def writing_event_confirm_handler(callback: CallbackQuery, state: FSMContext):
    """Yazı yazma etkinliği onay handler"""
    try:
        user_id = callback.from_user.id
        data = await state.get_data()
        
        title = data.get('title')
        description = data.get('description')
        duration_hours = data.get('duration_hours')
        multiplier = data.get('multiplier')
        
        # Etkinliği oluştur
        success, event_id = await create_writing_event(
            title=title,
            description=description,
            duration_hours=duration_hours,
            kp_multiplier=multiplier,
            created_by=user_id
        )
        
        if success:
            # Gruplara bildirim gönder
            await send_writing_event_notification(event_id, title, description, duration_hours, multiplier)
            
            await callback.message.edit_text(
                f"✅ **Yazı Yazma Etkinliği Oluşturuldu!**\n\n"
                f"**Başlık:** {title}\n"
                f"**Süre:** {duration_hours} saat\n"
                f"**KP Çarpanı:** x{multiplier}\n"
                f"**ID:** {event_id}\n\n"
                f"Etkinlik aktif! Artık tüm mesajlar {multiplier}x KP kazandıracak!",
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                "❌ Etkinlik oluşturulamadı! Zaten aktif bir etkinlik olabilir.",
                parse_mode="Markdown"
            )
        
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Writing event confirm hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.callback_query(F.data == "writing_event_cancel")
async def writing_event_cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Yazı yazma etkinliği iptal handler"""
    await state.clear()
    await callback.message.delete()
    await callback.answer("❌ İptal edildi")

# ============================================================================
# FSM HANDLERS - Mesaj Yarışı Etkinliği
# ============================================================================

@router.message(MessageRaceEventStates.waiting_for_title)
async def message_race_title_handler(message: Message, state: FSMContext):
    """Mesaj yarışı başlık handler"""
    try:
        title = message.text.strip()
        if len(title) < 3:
            await message.reply("❌ Başlık en az 3 karakter olmalı!")
            return
        
        await state.update_data(title=title)
        await message.reply(
            "✅ Başlık kaydedildi!\n\n"
            "Etkinlik açıklamasını yazın:",
            parse_mode="Markdown"
        )
        await state.set_state(MessageRaceEventStates.waiting_for_description)
        
    except Exception as e:
        logger.error(f"❌ Message race title handler hatası: {e}")

@router.message(MessageRaceEventStates.waiting_for_description)
async def message_race_description_handler(message: Message, state: FSMContext):
    """Mesaj yarışı açıklama handler"""
    try:
        description = message.text.strip()
        await state.update_data(description=description)
        await message.reply(
            "✅ Açıklama kaydedildi!\n\n"
            "Etkinlik süresini saat cinsinden yazın (örn: 2):",
            parse_mode="Markdown"
        )
        await state.set_state(MessageRaceEventStates.waiting_for_duration)
        
    except Exception as e:
        logger.error(f"❌ Message race description handler hatası: {e}")

@router.message(MessageRaceEventStates.waiting_for_duration)
async def message_race_duration_handler(message: Message, state: FSMContext):
    """Mesaj yarışı süre handler"""
    try:
        try:
            duration_hours = int(message.text.strip())
            if duration_hours < 1 or duration_hours > 168:
                await message.reply("❌ Süre 1-168 saat arasında olmalı!")
                return
        except ValueError:
            await message.reply("❌ Geçerli bir sayı girin!")
            return
        
        await state.update_data(duration_hours=duration_hours)
        await message.reply(
            "✅ Süre kaydedildi!\n\n"
            "Kaç kişi ödül alacak? (örn: 3, 5, 10):",
            parse_mode="Markdown"
        )
        await state.set_state(MessageRaceEventStates.waiting_for_winners)
        
    except Exception as e:
        logger.error(f"❌ Message race duration handler hatası: {e}")

@router.message(MessageRaceEventStates.waiting_for_winners)
async def message_race_winners_handler(message: Message, state: FSMContext):
    """Mesaj yarışı kazanan sayısı handler"""
    try:
        try:
            top_winners = int(message.text.strip())
            if top_winners < 1 or top_winners > 20:
                await message.reply("❌ Kazanan sayısı 1-20 arasında olmalı!")
                return
        except ValueError:
            await message.reply("❌ Geçerli bir sayı girin!")
            return
        
        await state.update_data(top_winners=top_winners)
        await message.reply(
            f"✅ Kazanan sayısı kaydedildi!\n\n"
            f"Ödülleri yazın (her satıra bir ödül, {top_winners} adet):\n"
            f"Örnek:\n"
            f"100\n"
            f"50\n"
            f"25",
            parse_mode="Markdown"
        )
        await state.set_state(MessageRaceEventStates.waiting_for_rewards)
        
    except Exception as e:
        logger.error(f"❌ Message race winners handler hatası: {e}")

@router.message(MessageRaceEventStates.waiting_for_rewards)
async def message_race_rewards_handler(message: Message, state: FSMContext):
    """Mesaj yarışı ödüller handler"""
    try:
        data = await state.get_data()
        top_winners = data.get('top_winners')
        
        # Ödülleri parse et
        rewards_text = message.text.strip()
        rewards_lines = [line.strip() for line in rewards_text.split('\n') if line.strip()]
        
        if len(rewards_lines) < top_winners:
            await message.reply(f"❌ En az {top_winners} ödül girmelisiniz!")
            return
        
        rewards = []
        for i, line in enumerate(rewards_lines[:top_winners]):
            try:
                reward = float(line)
                if reward < 0:
                    await message.reply(f"❌ Ödül negatif olamaz! (Satır {i+1})")
                    return
                rewards.append(reward)
            except ValueError:
                await message.reply(f"❌ Geçerli bir sayı girin! (Satır {i+1})")
                return
        
        title = data.get('title')
        description = data.get('description')
        duration_hours = data.get('duration_hours')
        
        # Onay mesajı
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Oluştur", callback_data="message_race_confirm")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="message_race_cancel")]
        ])
        
        rewards_text = "\n".join([f"{i+1}. → {r} KP" for i, r in enumerate(rewards)])
        
        await message.reply(
            f"📋 **Etkinlik Özeti**\n\n"
            f"**Başlık:** {title}\n"
            f"**Açıklama:** {description}\n"
            f"**Süre:** {duration_hours} saat\n"
            f"**Kazanan Sayısı:** {top_winners}\n"
            f"**Ödüller:**\n{rewards_text}\n\n"
            f"Etkinliği oluşturmak istiyor musunuz?",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        await state.update_data(rewards=rewards)
        await state.set_state(MessageRaceEventStates.waiting_for_confirmation)
        
    except Exception as e:
        logger.error(f"❌ Message race rewards handler hatası: {e}")

@router.callback_query(F.data == "message_race_confirm")
async def message_race_confirm_handler(callback: CallbackQuery, state: FSMContext):
    """Mesaj yarışı onay handler"""
    try:
        user_id = callback.from_user.id
        data = await state.get_data()
        
        title = data.get('title')
        description = data.get('description')
        duration_hours = data.get('duration_hours')
        top_winners = data.get('top_winners')
        rewards = data.get('rewards')
        
        # Etkinliği oluştur
        success, event_id = await create_message_race_event(
            title=title,
            description=description,
            duration_hours=duration_hours,
            top_winners=top_winners,
            rewards=rewards,
            created_by=user_id
        )
        
        if success:
            # Gruplara bildirim gönder
            await send_message_race_notification(event_id, title, description, duration_hours, top_winners, rewards)
            
            rewards_text = "\n".join([f"{i+1}. → {r} KP" for i, r in enumerate(rewards)])
            
            await callback.message.edit_text(
                f"✅ **Mesaj Yarışı Etkinliği Oluşturuldu!**\n\n"
                f"**Başlık:** {title}\n"
                f"**Süre:** {duration_hours} saat\n"
                f"**Kazanan Sayısı:** {top_winners}\n"
                f"**Ödüller:**\n{rewards_text}\n"
                f"**ID:** {event_id}\n\n"
                f"Etkinlik aktif! En çok mesaj atanlar ödül kazanacak!",
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                "❌ Etkinlik oluşturulamadı! Zaten aktif bir etkinlik olabilir.",
                parse_mode="Markdown"
            )
        
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Message race confirm hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

@router.callback_query(F.data == "message_race_cancel")
async def message_race_cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Mesaj yarışı iptal handler"""
    await state.clear()
    await callback.message.delete()
    await callback.answer("❌ İptal edildi")

# ============================================================================
# BİLDİRİM FONKSİYONLARI
# ============================================================================

async def send_event_notification_to_all_users(event_id: int, event_type: str, title: str, description: str, duration_hours: int, *args):
    """Tüm kayıtlı üyelere etkinlik bildirimi gönder"""
    try:
        if not _bot_instance:
            return
        
        pool = await get_db_pool()
        if not pool:
            return
        
        # Bitiş zamanını hesapla
        ends_at = datetime.now() + timedelta(hours=duration_hours)
        ends_at_str = ends_at.strftime("%d.%m.%Y %H:%M")
        
        async with pool.acquire() as conn:
            # Tüm kayıtlı kullanıcıları al
            users = await conn.fetch("""
                SELECT user_id FROM users 
                WHERE is_registered = TRUE
            """)
        
        if not users:
            logger.info("ℹ️ Kayıtlı kullanıcı bulunamadı, özel mesaj gönderilmedi")
            return
        
        # Etkinlik tipine göre mesaj hazırla
        if event_type == 'writing_event':
            multiplier = args[0] if args else 1.0
            notification_text = (
                f"🎉 **YENİ ETKİNLİK BAŞLADI!**\n\n"
                f"✍️ **{title}**\n\n"
                f"📝 **Açıklama:**\n{description}\n\n"
                f"🎯 **KP Çarpanı:** x{multiplier}\n"
                f"⏰ **Süre:** {duration_hours} saat\n"
                f"🕐 **Bitiş Zamanı:** {ends_at_str}\n\n"
                f"💎 **Nasıl Kazanırsınız?**\n"
                f"• Etkinlik süresince attığınız her mesaj **{multiplier}x** çarpanla KP kazandırır\n"
                f"• Ne kadar çok mesaj atarsanız, o kadar çok bonus KP kazanırsınız!\n"
                f"• Etkinlik bitene kadar mesajlaştıkça daha fazla KP kazanacaksınız\n\n"
                f"🚀 **Hemen grup sohbetlerine katılın ve bonus KP kazanın!**\n\n"
                f"💡 Gruplarda mesaj atarak etkinlikten yararlanabilirsiniz!"
            )
        elif event_type == 'message_race_event':
            top_winners = args[0] if args else 1
            rewards = args[1] if len(args) > 1 else []
            rewards_text = "\n".join([f"   {i+1}. 🥇 {r} KP" for i, r in enumerate(rewards)])
            
            notification_text = (
                f"🎉 **YENİ ETKİNLİK BAŞLADI!**\n\n"
                f"🏆 **{title}**\n\n"
                f"📝 **Açıklama:**\n{description}\n\n"
                f"⏰ **Süre:** {duration_hours} saat\n"
                f"🕐 **Bitiş Zamanı:** {ends_at_str}\n"
                f"🎯 **Kazanan Sayısı:** {top_winners} kişi\n\n"
                f"💰 **Ödüller:**\n{rewards_text}\n\n"
                f"📊 **Nasıl Kazanırsınız?**\n"
                f"• Etkinlik süresince attığınız her mesaj sayılır\n"
                f"• En çok mesaj atan {top_winners} kişi ödül kazanır\n"
                f"• Mesajlarınız otomatik olarak kaydedilir\n\n"
                f"🚀 **Hemen grup sohbetlerine katılın ve yarışta öne geçin!**\n\n"
                f"💡 Gruplarda mesaj atarak etkinlikten yararlanabilirsiniz!"
            )
        else:
            return
        
        # Tüm kullanıcılara gönder
        sent_count = 0
        failed_count = 0
        
        for user in users:
            try:
                await _bot_instance.send_message(
                    chat_id=user['user_id'],
                    text=notification_text,
                    parse_mode="Markdown"
                )
                sent_count += 1
                await asyncio.sleep(0.1)  # Rate limit (100ms)
            except Exception as e:
                failed_count += 1
                # Sadece önemli hataları logla (forbidden, blocked gibi)
                if "forbidden" not in str(e).lower() and "blocked" not in str(e).lower():
                    logger.warning(f"⚠️ Özel mesaj gönderilemedi (User: {user['user_id']}): {e}")
        
        logger.info(f"✅ Etkinlik özel mesajları gönderildi - Başarılı: {sent_count}, Başarısız: {failed_count}")
        
    except Exception as e:
        logger.error(f"❌ Send event notification to all users hatası: {e}")

async def send_writing_event_notification(event_id: int, title: str, description: str, duration_hours: int, multiplier: float):
    """Yazı yazma etkinliği bildirimi gönder ve sabitle"""
    try:
        if not _bot_instance:
            return
        
        pool = await get_db_pool()
        if not pool:
            return
        
        # Bitiş zamanını hesapla
        ends_at = datetime.now() + timedelta(hours=duration_hours)
        ends_at_str = ends_at.strftime("%d.%m.%Y %H:%M")
        
        async with pool.acquire() as conn:
            groups = await conn.fetch("""
                SELECT group_id FROM registered_groups WHERE is_active = TRUE
            """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Etkinlik Detayları", callback_data=f"event_detail_{event_id}")]
        ])
        
        # Daha açıklayıcı mesaj (net istatistik yok)
        message_text = (
            f"✍️ **YAZI YAZMA ETKİNLİĞİ BAŞLADI!**\n\n"
            f"**📌 {title}**\n\n"
            f"📝 **Açıklama:**\n{description}\n\n"
            f"🎯 **KP Çarpanı:** x{multiplier}\n"
            f"⏰ **Süre:** {duration_hours} saat\n"
            f"🕐 **Bitiş Zamanı:** {ends_at_str}\n\n"
            f"💎 **Nasıl Kazanırsınız?**\n"
            f"• Etkinlik süresince attığınız her mesaj **{multiplier}x** çarpanla KP kazandırır\n"
            f"• Ne kadar çok mesaj atarsanız, o kadar çok bonus KP kazanırsınız!\n"
            f"• Etkinlik bitene kadar mesajlaştıkça daha fazla KP kazanacaksınız\n\n"
            f"🚀 **Hemen yazmaya başlayın ve bonus KP kazanın!**"
        )
        
        # Her grup için mesaj gönder ve sabitle
        group_message_ids = {}  # {group_id: message_id}
        
        for group in groups:
            try:
                sent_message = await _bot_instance.send_message(
                    chat_id=group['group_id'],
                    text=message_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                
                # Mesajı sabitle
                try:
                    await _bot_instance.pin_chat_message(
                        chat_id=group['group_id'],
                        message_id=sent_message.message_id,
                        disable_notification=False  # Bildirim göster
                    )
                    group_message_ids[group['group_id']] = sent_message.message_id
                    logger.info(f"✅ Etkinlik mesajı sabitlendi - Grup: {group['group_id']}, Message ID: {sent_message.message_id}")
                except Exception as pin_error:
                    logger.warning(f"⚠️ Mesaj sabitleme hatası (Grup: {group['group_id']}): {pin_error}")
                
                await asyncio.sleep(0.5)  # Rate limit
            except Exception as e:
                logger.error(f"❌ Grup {group['group_id']} bildirim hatası: {e}")
        
        # İlk grubun message_id'sini database'e kaydet (ana mesaj olarak)
        if group_message_ids:
            first_group_id = list(group_message_ids.keys())[0]
            first_message_id = group_message_ids[first_group_id]
            
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE events 
                    SET message_id = $1 
                    WHERE id = $2
                """, first_message_id, event_id)
                logger.info(f"✅ Etkinlik message_id kaydedildi: {event_id} -> {first_message_id}")
        
        logger.info(f"✅ Yazı yazma etkinliği bildirimi gönderildi ve sabitlendi: {event_id}")
        
        # Tüm kayıtlı üyelere özel mesaj gönder
        await send_event_notification_to_all_users(event_id, 'writing_event', title, description, duration_hours, multiplier)
        
    except Exception as e:
        logger.error(f"❌ Send writing event notification hatası: {e}")

async def send_message_race_notification(event_id: int, title: str, description: str, duration_hours: int, top_winners: int, rewards: List[float]):
    """Mesaj yarışı etkinliği bildirimi gönder ve sabitle"""
    try:
        if not _bot_instance:
            return
        
        pool = await get_db_pool()
        if not pool:
            return
        
        # Bitiş zamanını hesapla
        ends_at = datetime.now() + timedelta(hours=duration_hours)
        ends_at_str = ends_at.strftime("%d.%m.%Y %H:%M")
        
        async with pool.acquire() as conn:
            groups = await conn.fetch("""
                SELECT group_id FROM registered_groups WHERE is_active = TRUE
            """)
        
        rewards_text = "\n".join([f"   {i+1}. 🥇 {r} KP" for i, r in enumerate(rewards)])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Liderlik Tablosu", callback_data=f"race_leaderboard_{event_id}")],
            [InlineKeyboardButton(text="📋 Etkinlik Detayları", callback_data=f"event_detail_{event_id}")]
        ])
        
        # Daha açıklayıcı mesaj
        message_text = (
            f"🏆 **MESAJ YARIŞI ETKİNLİĞİ BAŞLADI!**\n\n"
            f"**📌 {title}**\n\n"
            f"📝 **Açıklama:**\n{description}\n\n"
            f"⏰ **Süre:** {duration_hours} saat\n"
            f"🕐 **Bitiş Zamanı:** {ends_at_str}\n"
            f"🎯 **Kazanan Sayısı:** {top_winners} kişi\n\n"
            f"💰 **Ödüller:**\n{rewards_text}\n\n"
            f"📊 **Nasıl Kazanırsınız?**\n"
            f"• Etkinlik süresince attığınız her mesaj sayılır\n"
            f"• En çok mesaj atan {top_winners} kişi ödül kazanır\n"
            f"• Mesajlarınız otomatik olarak kaydedilir\n"
            f"• Liderlik tablosunu butona tıklayarak görebilirsiniz\n\n"
            f"🚀 **Hemen yazmaya başlayın ve yarışta öne geçin!**"
        )
        
        # Her grup için mesaj gönder ve sabitle
        group_message_ids = {}  # {group_id: message_id}
        
        for group in groups:
            try:
                sent_message = await _bot_instance.send_message(
                    chat_id=group['group_id'],
                    text=message_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                
                # Mesajı sabitle
                try:
                    await _bot_instance.pin_chat_message(
                        chat_id=group['group_id'],
                        message_id=sent_message.message_id,
                        disable_notification=False  # Bildirim göster
                    )
                    group_message_ids[group['group_id']] = sent_message.message_id
                    logger.info(f"✅ Etkinlik mesajı sabitlendi - Grup: {group['group_id']}, Message ID: {sent_message.message_id}")
                except Exception as pin_error:
                    logger.warning(f"⚠️ Mesaj sabitleme hatası (Grup: {group['group_id']}): {pin_error}")
                
                await asyncio.sleep(0.5)  # Rate limit
            except Exception as e:
                logger.error(f"❌ Grup {group['group_id']} bildirim hatası: {e}")
        
        # İlk grubun message_id'sini database'e kaydet (ana mesaj olarak)
        if group_message_ids:
            first_group_id = list(group_message_ids.keys())[0]
            first_message_id = group_message_ids[first_group_id]
            
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE events 
                    SET message_id = $1 
                    WHERE id = $2
                """, first_message_id, event_id)
                logger.info(f"✅ Etkinlik message_id kaydedildi: {event_id} -> {first_message_id}")
        
        logger.info(f"✅ Mesaj yarışı etkinliği bildirimi gönderildi ve sabitlendi: {event_id}")
        
        # Tüm kayıtlı üyelere özel mesaj gönder
        await send_event_notification_to_all_users(event_id, 'message_race_event', title, description, duration_hours, top_winners, rewards)
        
    except Exception as e:
        logger.error(f"❌ Send message race notification hatası: {e}")

# ============================================================================
# OTOMATIK BİTİRME TASK
# ============================================================================

async def check_and_end_expired_events():
    """Süresi dolan etkinlikleri otomatik bitir"""
    try:
        pool = await get_db_pool()
        if not pool:
            return
        
        async with pool.acquire() as conn:
            # Süresi dolan etkinlikleri bul
            expired_events = await conn.fetch("""
                SELECT id, event_type, title
                FROM events
                WHERE status = 'active'
                  AND event_type IN ('writing_event', 'message_race_event')
                  AND ends_at < NOW()
            """)
            
            for event in expired_events:
                event_id = event['id']
                event_type = event['event_type']
                
                if event_type == 'writing_event':
                    await end_writing_event(event_id)
                    logger.info(f"✅ Süresi dolan yazı yazma etkinliği bitirildi: {event_id}")
                elif event_type == 'message_race_event':
                    await end_message_race_event(event_id)
                    logger.info(f"✅ Süresi dolan mesaj yarışı etkinliği bitirildi: {event_id}")
                    
    except Exception as e:
        logger.error(f"❌ Check expired events hatası: {e}")

async def send_event_reminder(event_id: int, event_type: str, group_id: int, message_id: int):
    """Aktif etkinlik için hatırlatma mesajı gönder (ana mesajı reply yaparak)"""
    try:
        if not _bot_instance:
            return
        
        pool = await get_db_pool()
        if not pool:
            return
        
        async with pool.acquire() as conn:
            event = await conn.fetchrow("""
                SELECT id, title, description, duration_minutes, bonus_multiplier, 
                       ends_at, event_config, event_type
                FROM events
                WHERE id = $1 AND status = 'active'
            """, event_id)
            
            if not event:
                return  # Etkinlik artık aktif değil
        
        # Kalan süreyi hesapla
        ends_at = event['ends_at']
        now = datetime.now()
        remaining = ends_at - now
        
        if remaining.total_seconds() <= 0:
            return  # Süre dolmuş
        
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        
        if hours > 0:
            remaining_str = f"{hours} saat {minutes} dakika"
        else:
            remaining_str = f"{minutes} dakika"
        
        ends_at_str = ends_at.strftime("%d.%m.%Y %H:%M")
        
        # Etkinlik tipine göre hatırlatma mesajı
        if event_type == 'writing_event':
            multiplier = float(event.get('bonus_multiplier', 1.0))
            reminder_text = (
                f"⏰ **ETKİNLİK HATIRLATMASI**\n\n"
                f"✍️ **{event['title']}** hala devam ediyor!\n\n"
                f"🎯 KP Çarpanı: **x{multiplier}**\n"
                f"⏳ Kalan Süre: **{remaining_str}**\n"
                f"🕐 Bitiş: **{ends_at_str}**\n\n"
                f"💎 Mesajlaştıkça daha fazla bonus KP kazanıyorsunuz!\n"
                f"🚀 Hemen yazmaya devam edin!"
            )
        elif event_type == 'message_race_event':
            event_config = event.get('event_config', {})
            top_winners = event_config.get('top_winners', 1)
            reminder_text = (
                f"⏰ **ETKİNLİK HATIRLATMASI**\n\n"
                f"🏆 **{event['title']}** hala devam ediyor!\n\n"
                f"⏳ Kalan Süre: **{remaining_str}**\n"
                f"🕐 Bitiş: **{ends_at_str}**\n"
                f"🎯 Kazanan: **{top_winners}** kişi\n\n"
                f"📊 En çok mesaj atanlar ödül kazanacak!\n"
                f"🚀 Liderlik tablosunu kontrol edin ve yarışta öne geçin!"
            )
        else:
            return
        
        try:
            # Ana mesajı reply yaparak hatırlatma gönder
            await _bot_instance.send_message(
                chat_id=group_id,
                text=reminder_text,
                parse_mode="Markdown",
                reply_to_message_id=message_id
            )
            logger.info(f"✅ Etkinlik hatırlatması gönderildi - Event: {event_id}, Group: {group_id}")
        except Exception as e:
            logger.error(f"❌ Hatırlatma mesajı gönderilemedi (Grup: {group_id}): {e}")
            
    except Exception as e:
        logger.error(f"❌ Send event reminder hatası: {e}")

async def check_and_send_reminders():
    """Aktif etkinlikler için hatırlatma gönder"""
    try:
        pool = await get_db_pool()
        if not pool:
            return
        
        async with pool.acquire() as conn:
            # Aktif etkinlikleri ve message_id'lerini al
            active_events = await conn.fetch("""
                SELECT id, event_type, title, message_id, group_id, ends_at
                FROM events
                WHERE status = 'active'
                  AND event_type IN ('writing_event', 'message_race_event')
                  AND message_id IS NOT NULL
                  AND ends_at > NOW()
            """)
        
        for event in active_events:
            event_id = event['id']
            event_type = event['event_type']
            message_id = event['message_id']
            group_id = event.get('group_id', 0)
            
            # Eğer group_id 0 ise, tüm aktif gruplara gönder
            if group_id == 0:
                async with pool.acquire() as conn2:
                    groups = await conn2.fetch("""
                        SELECT group_id FROM registered_groups WHERE is_active = TRUE
                    """)
                
                for group in groups:
                    await send_event_reminder(event_id, event_type, group['group_id'], message_id)
                    await asyncio.sleep(0.3)  # Rate limit
            else:
                await send_event_reminder(event_id, event_type, group_id, message_id)
                
    except Exception as e:
        logger.error(f"❌ Check and send reminders hatası: {e}")

async def start_event_checker_task():
    """Etkinlik kontrol task'ını başlat"""
    while True:
        try:
            await check_and_end_expired_events()
            await asyncio.sleep(60)  # Her 1 dakikada bir kontrol et
        except Exception as e:
            logger.error(f"❌ Event checker task hatası: {e}")
            await asyncio.sleep(60)

async def start_event_reminder_task():
    """Etkinlik hatırlatma task'ını başlat (her 30 dakikada bir)"""
    while True:
        try:
            await check_and_send_reminders()
            await asyncio.sleep(1800)  # Her 30 dakikada bir hatırlat (30 * 60 = 1800 saniye)
        except Exception as e:
            logger.error(f"❌ Event reminder task hatası: {e}")
            await asyncio.sleep(1800)


