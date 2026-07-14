"""
Admin Kategori Yönetimi - !kategoriekle, !kategorisil komutları
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_db_pool
from config import is_admin

logger = logging.getLogger(__name__)
router = Router()

# FSM States
class CategoryCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_icon = State()

# Temporary storage
category_data = {}

@router.message(F.text == "!kategoriekle")
async def start_category_creation(message: Message, state: FSMContext):
    """Kategori ekleme sürecini başlat"""
    try:
        if not is_admin(message.from_user.id):
            return
        
        user_id = message.from_user.id
        category_data[user_id] = {}
        
        await message.reply(
            "📂 **YENİ KATEGORİ OLUŞTURMA**\n\n"
            "1️⃣ **Kategori adını girin** (emoji ile birlikte)\n\n"
            "Örnek: `🎮 Dijital Ürünler`\n"
            "Örnek: `💰 Site Bakiyesi`\n\n"
            "İptal için: /cancel",
            parse_mode="Markdown"
        )
        
        await state.set_state(CategoryCreation.waiting_for_name)
        logger.info(f"✅ Kategori oluşturma başlatıldı - Admin: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Kategori oluşturma başlatma hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")


@router.message(CategoryCreation.waiting_for_name)
async def process_category_name(message: Message, state: FSMContext):
    """Kategori adını al"""
    try:
        user_id = message.from_user.id
        
        if message.text == "/cancel":
            await state.clear()
            category_data.pop(user_id, None)
            await message.reply("❌ Kategori oluşturma iptal edildi.")
            return
        
        category_name = message.text.strip()
        
        if not category_name:
            await message.reply("❌ Kategori adı boş olamaz! Tekrar girin:")
            return
        
        if len(category_name) > 100:
            await message.reply("❌ Kategori adı çok uzun! (Max 100 karakter)")
            return
        
        category_data[user_id]['name'] = category_name
        
        await message.reply(
            f"✅ **Kategori Adı:** {category_name}\n\n"
            f"2️⃣ **Icon (emoji) girin:**\n\n"
            f"Örnek: `🎮`\n"
            f"Örnek: `💰`\n\n"
            f"İptal için: /cancel",
            parse_mode="Markdown"
        )
        
        await state.set_state(CategoryCreation.waiting_for_icon)
        logger.info(f"✅ Kategori adı alındı: {category_name}")
        
    except Exception as e:
        logger.error(f"❌ Kategori adı işleme hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")


@router.message(CategoryCreation.waiting_for_icon)
async def process_category_icon(message: Message, state: FSMContext):
    """Kategori icon'unu al ve kaydet"""
    try:
        user_id = message.from_user.id
        
        if message.text == "/cancel":
            await state.clear()
            category_data.pop(user_id, None)
            await message.reply("❌ Kategori oluşturma iptal edildi.")
            return
        
        icon = message.text.strip()
        
        if not icon:
            await message.reply("❌ Icon boş olamaz! Tekrar girin:")
            return
        
        if len(icon) > 50:
            await message.reply("❌ Icon çok uzun! Tek emoji girin:")
            return
        
        category_data[user_id]['icon'] = icon
        
        # Database'e kaydet
        pool = await get_db_pool()
        if not pool:
            await message.reply("❌ Database bağlantısı yok!")
            await state.clear()
            return
        
        name = category_data[user_id]['name']
        
        async with pool.acquire() as conn:
            category_id = await conn.fetchval("""
                INSERT INTO market_categories (name, icon, is_active)
                VALUES ($1, $2, true)
                RETURNING id
            """, name, icon)
        
        # Başarı mesajı
        await message.reply(
            f"✅ **KATEGORİ OLUŞTURULDU!**\n\n"
            f"🆔 **ID:** {category_id}\n"
            f"📂 **Ad:** {name}\n"
            f"🎨 **Icon:** {icon}\n\n"
            f"Artık bu kategoriye ürün ekleyebilirsin!\n"
            f"Komut: `!marketurun`",
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Kategori oluşturuldu - ID: {category_id}, Name: {name}, Admin: {user_id}")
        
        # Cleanup
        await state.clear()
        category_data.pop(user_id, None)
        
    except Exception as e:
        logger.error(f"❌ Kategori kaydetme hatası: {e}", exc_info=True)
        await message.reply(f"❌ Kaydetme hatası: {e}")
        await state.clear()


@router.message(F.text == "!kategoriliste")
async def list_categories(message: Message):
    """Tüm kategorileri listele"""
    try:
        if not is_admin(message.from_user.id):
            return
        
        pool = await get_db_pool()
        if not pool:
            await message.reply("❌ Database bağlantısı yok!")
            return
        
        async with pool.acquire() as conn:
            categories = await conn.fetch("""
                SELECT id, name, icon, is_active,
                       (SELECT COUNT(*) FROM market_products 
                        WHERE category_id = market_categories.id AND is_active = true) as product_count
                FROM market_categories
                ORDER BY id
            """)
        
        if not categories:
            await message.reply("❌ Hiç kategori yok!\n\nEklemek için: `!kategoriekle`", parse_mode="Markdown")
            return
        
        text = "📂 **TÜM KATEGORİLER**\n\n"
        
        for cat in categories:
            status = "✅ Aktif" if cat['is_active'] else "❌ Pasif"
            icon = cat['icon'] or "📦"
            text += f"**ID {cat['id']}:** {icon} {cat['name']}\n"
            text += f"   • Durum: {status}\n"
            text += f"   • Ürün Sayısı: {cat['product_count']}\n\n"
        
        text += "\n💡 Kategori silmek için: `!kategorisil <ID>`"
        
        await message.reply(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Kategori listeleme hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")


@router.message(F.text.startswith("!kategorisil "))
async def delete_category(message: Message):
    """Kategori sil/deaktive et"""
    try:
        if not is_admin(message.from_user.id):
            return
        
        try:
            category_id = int(message.text.split()[1])
        except (IndexError, ValueError):
            await message.reply("❌ Kullanım: `!kategorisil <ID>`\n\nÖrnek: `!kategorisil 5`", parse_mode="Markdown")
            return
        
        pool = await get_db_pool()
        if not pool:
            await message.reply("❌ Database bağlantısı yok!")
            return
        
        async with pool.acquire() as conn:
            # Kategoriyi kontrol et
            category = await conn.fetchrow("""
                SELECT id, name, 
                       (SELECT COUNT(*) FROM market_products 
                        WHERE category_id = $1 AND is_active = true) as product_count
                FROM market_categories
                WHERE id = $1
            """, category_id)
            
            if not category:
                await message.reply(f"❌ ID {category_id} kategorisi bulunamadı!")
                return
            
            # Deaktive et (silme)
            await conn.execute("""
                UPDATE market_categories
                SET is_active = false
                WHERE id = $1
            """, category_id)
        
        await message.reply(
            f"✅ **KATEGORİ DEAKTİVE EDİLDİ**\n\n"
            f"🆔 **ID:** {category_id}\n"
            f"📂 **Ad:** {category['name']}\n"
            f"📦 **Etkilenen Ürün:** {category['product_count']}\n\n"
            f"⚠️ Kategori markette artık görünmeyecek.",
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Kategori deaktive edildi - ID: {category_id}, Admin: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Kategori silme hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")





