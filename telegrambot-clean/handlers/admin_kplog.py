"""
Admin KP Log Handler
Son KP islemlerini gosterir (mesaj, admin islemleri, vs.)
"""
import logging
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_db_pool
from config import is_admin
from datetime import datetime, timedelta

router = Router()
logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 10

async def get_kp_logs(page: int = 1) -> dict:
    """
    Tum KP loglarini al (daily_stats + balance_logs)
    Returns: {
        'logs': [(user_id, username, amount, reason, date), ...],
        'total_pages': int,
        'current_page': int,
        'total_logs': int
    }
    """
    try:
        pool = await get_db_pool()
        if not pool:
            return {'logs': [], 'total_pages': 0, 'current_page': 1, 'total_logs': 0}
        
        offset = (page - 1) * ITEMS_PER_PAGE
        
        async with pool.acquire() as conn:
            # Son 7 gunun loglarini birlestir
            query = """
            WITH combined_logs AS (
                -- Daily stats'tan mesaj puanlari
                SELECT 
                    ds.user_id,
                    u.username,
                    ds.points_earned::numeric as amount,
                    'Mesaj (' || ds.message_count || ' mesaj)' as reason,
                    ds.message_date::timestamp as log_date,
                    'message' as log_type
                FROM daily_stats ds
                LEFT JOIN users u ON ds.user_id = u.user_id
                WHERE ds.points_earned > 0 
                  AND ds.message_date >= CURRENT_DATE - INTERVAL '7 days'
                
                UNION ALL
                
                -- Balance logs'tan admin islemleri
                SELECT 
                    bl.user_id,
                    u.username,
                    bl.amount,
                    bl.reason || ' (Admin ID: ' || bl.admin_id || ')' as reason,
                    bl.created_at as log_date,
                    'admin_' || bl.action as log_type
                FROM balance_logs bl
                LEFT JOIN users u ON bl.user_id = u.user_id
                WHERE bl.created_at >= NOW() - INTERVAL '7 days'
            )
            SELECT 
                user_id,
                COALESCE(username, 'Anonim') as username,
                amount,
                reason,
                log_date,
                log_type
            FROM combined_logs
            ORDER BY log_date DESC
            LIMIT $1 OFFSET $2
            """
            
            logs = await conn.fetch(query, ITEMS_PER_PAGE, offset)
            
            # Toplam kayit sayisi
            count_query = """
            SELECT COUNT(*) as total FROM (
                SELECT 1 FROM daily_stats 
                WHERE points_earned > 0 AND message_date >= CURRENT_DATE - INTERVAL '7 days'
                UNION ALL
                SELECT 1 FROM balance_logs
                WHERE created_at >= NOW() - INTERVAL '7 days'
            ) combined
            """
            total_count = await conn.fetchval(count_query)
            
            total_pages = (total_count + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total_count > 0 else 1
            
            return {
                'logs': [dict(log) for log in logs],
                'total_pages': total_pages,
                'current_page': page,
                'total_logs': total_count
            }
            
    except Exception as e:
        logger.error(f"get_kp_logs hatasi: {e}", exc_info=True)
        return {'logs': [], 'total_pages': 0, 'current_page': 1, 'total_logs': 0}


def format_kp_log_message(data: dict) -> str:
    """KP log mesajini formatla"""
    logs = data['logs']
    page = data['current_page']
    total_pages = data['total_pages']
    total_logs = data['total_logs']
    
    if not logs:
        return """
╔═══════════════════════════════════╗
║        📊 KP LOG SİSTEMİ          ║
╚═══════════════════════════════════╝

❌ Son 7 günde KP hareketi yok!

💡 Kullanıcılar mesaj atarak veya
   admin işlemleriyle puan kazanabilir.
"""
    
    message = f"""
╔═══════════════════════════════════╗
║        📊 KP LOG SİSTEMİ          ║
╚═══════════════════════════════════╝

📅 **Son 7 Günün KP Hareketleri**
📦 **Toplam Kayıt:** {total_logs}
📄 **Sayfa:** {page}/{total_pages}

"""
    
    for idx, log in enumerate(logs, 1):
        # Log type emoji
        if log['log_type'] == 'message':
            emoji = "💬"
        elif log['log_type'] == 'admin_add':
            emoji = "➕"
        elif log['log_type'] == 'admin_remove':
            emoji = "➖"
        else:
            emoji = "🔄"
        
        # Tarih formatlama
        log_date = log['log_date']
        if isinstance(log_date, datetime):
            date_str = log_date.strftime("%d.%m.%Y %H:%M")
        else:
            date_str = str(log_date)
        
        # Miktar formatlama
        amount = float(log['amount'])
        amount_str = f"+{amount:.2f}" if amount > 0 else f"{amount:.2f}"
        
        message += f"""
{emoji} **{idx + (page-1)*ITEMS_PER_PAGE}.** {log['username']} ({log['user_id']})
   💰 **{amount_str} KP** - {log['reason']}
   🕐 {date_str}
"""
    
    message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 Sayfa {page}/{total_pages}
"""
    
    return message


def create_pagination_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Sayfalama butonlari"""
    buttons = []
    
    # Onceki sayfa
    if current_page > 1:
        buttons.append(InlineKeyboardButton(
            text="◀️ Onceki",
            callback_data=f"kplog_page_{current_page - 1}"
        ))
    
    # Sayfa bilgisi
    buttons.append(InlineKeyboardButton(
        text=f"📄 {current_page}/{total_pages}",
        callback_data="kplog_current"
    ))
    
    # Sonraki sayfa
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(
            text="Sonraki ▶️",
            callback_data=f"kplog_page_{current_page + 1}"
        ))
    
    # Kapat butonu
    keyboard = [
        buttons,
        [InlineKeyboardButton(text="🔄 Yenile", callback_data=f"kplog_page_{current_page}")],
        [InlineKeyboardButton(text="❌ Kapat", callback_data="kplog_close")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(F.text.startswith("!kplog"))
async def handle_kplog_command(message: types.Message):
    """
    !kplog veya !kplog 2 komutu
    """
    user_id = message.from_user.id
    
    # Komut kontrolü - !kplog veya !kplog <sayı> olmalı
    if not message.text:
        return
    
    import re
    match = re.match(r'^!kplog\s*(\d*)$', message.text.strip())
    if not match:
        return  # Geçersiz komut formatı
    
    # Admin kontrolu
    if not is_admin(user_id):
        await message.reply("❌ Bu komut sadece adminler için!")
        return
    
    # Sayfa numarasini al
    page_str = match.group(1) if match else "1"
    page = int(page_str) if page_str else 1
    
    if page < 1:
        page = 1
    
    logger.info(f"!kplog komutu - User: {user_id}, Page: {page}")
    
    # Loglari al
    data = await get_kp_logs(page)
    
    # Mesaji formatla
    log_message = format_kp_log_message(data)
    
    # Keyboard olustur
    keyboard = create_pagination_keyboard(data['current_page'], data['total_pages'])
    
    try:
        await message.reply(
            log_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"kplog mesaj gonderme hatasi: {e}")
        await message.reply(f"❌ Log goruntulenirken hata olustu: {e}")


@router.callback_query(F.data.startswith("kplog_page_"))
async def handle_kplog_pagination(callback: types.CallbackQuery):
    """Sayfa degistirme"""
    user_id = callback.from_user.id
    
    # Admin kontrolu
    if not is_admin(user_id):
        await callback.answer("❌ Yetkiniz yok!", show_alert=True)
        return
    
    # Sayfa numarasini al
    page = int(callback.data.split("_")[-1])
    
    # Loglari al
    data = await get_kp_logs(page)
    
    # Mesaji formatla
    log_message = format_kp_log_message(data)
    
    # Keyboard olustur
    keyboard = create_pagination_keyboard(data['current_page'], data['total_pages'])
    
    try:
        await callback.message.edit_text(
            log_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await callback.answer(f"📄 Sayfa {page}")
    except Exception as e:
        logger.error(f"kplog sayfa degistirme hatasi: {e}")
        await callback.answer("❌ Hata olustu!", show_alert=True)


@router.callback_query(F.data == "kplog_current")
async def handle_kplog_current_page(callback: types.CallbackQuery):
    """Mevcut sayfa - hicbir sey yapma"""
    await callback.answer()


@router.callback_query(F.data == "kplog_close")
async def handle_kplog_close(callback: types.CallbackQuery):
    """Kapat"""
    try:
        await callback.message.delete()
        await callback.answer("✅ Kapandi")
    except Exception as e:
        logger.error(f"kplog kapatma hatasi: {e}")
        await callback.answer()

