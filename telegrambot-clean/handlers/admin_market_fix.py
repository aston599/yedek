"""
Admin Market Fix Command - !marketfix komutu ile database'i düzelt
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from database import get_db_pool
from config import is_admin

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "!marketfix")
async def market_fix_command(message: Message):
    """Market düzeltmelerini uygula"""
    try:
        # Sadece admin
        if not is_admin(message.from_user.id):
            return
        
        status_msg = await message.reply("🔧 Market düzeltmeleri başlıyor...")
        
        pool = await get_db_pool()
        if not pool:
            await status_msg.edit_text("❌ Database bağlantısı yok!")
            return
        
        async with pool.acquire() as conn:
            # 1. Kolonları ekle
            await status_msg.edit_text("🔧 1/7 - Yeni kolonlar ekleniyor...")
            await conn.execute("ALTER TABLE market_products ADD COLUMN IF NOT EXISTS external_link VARCHAR(500)")
            await conn.execute("ALTER TABLE market_products ADD COLUMN IF NOT EXISTS site_requirement VARCHAR(100)")
            await conn.execute("ALTER TABLE market_products ADD COLUMN IF NOT EXISTS delivery_info TEXT")
            
            # 2. Gereksiz kategorileri deaktive et (Canlı Yayın Bonus ve Özel Ödüller)
            await status_msg.edit_text("🗑️ 2/7 - Canlı Yayın Bonus ve Özel Ödüller kaldırılıyor...")
            await conn.execute("""
                UPDATE market_categories 
                SET is_active = false 
                WHERE name ILIKE '%canlı yayın%' 
                   OR name ILIKE '%özel ödül%'
                   OR name ILIKE '%live stream%'
                   OR name ILIKE '%special reward%'
                   OR name ILIKE '%canli yayin%'
                   OR name ILIKE '%ozel odul%'
                   OR id IN (19, 20)
            """)
            
            # 3. Bu kategorilerdeki ürünleri de deaktive et
            await status_msg.edit_text("🗑️ 3/7 - İlgili ürünler kaldırılıyor...")
            await conn.execute("""
                UPDATE market_products 
                SET is_active = false 
                WHERE category_id IN (
                    SELECT id FROM market_categories 
                    WHERE is_active = false
                )
            """)
            
            # 4. None düzeltmeleri
            await status_msg.edit_text("🔧 4/7 - Ürün isimleri düzeltiliyor...")
            await conn.execute("""
                UPDATE market_products 
                SET name = COALESCE(site_name, 'Ürün') || ' ' || COALESCE(description, 'Kod')
                WHERE name IS NULL OR name = 'None' OR TRIM(name) = ''
            """)
            
            # 5. Merso linkleri
            await status_msg.edit_text("🔗 5/7 - Mersobahis linkleri ekleniyor...")
            merso_count = await conn.fetchval("""
                UPDATE market_products 
                SET external_link = 'https://t2m.io/mersokirvehub', site_requirement = 'Mersobahis'
                WHERE category_id = 18 AND (site_name ILIKE '%merso%' OR description ILIKE '%merso%' OR name ILIKE '%merso%')
                RETURNING (SELECT COUNT(*) FROM market_products WHERE site_requirement = 'Mersobahis')
            """)
            
            # 6. AMG linkleri
            await status_msg.edit_text("🔗 6/7 - AMG Bahis linkleri ekleniyor...")
            amg_count = await conn.fetchval("""
                UPDATE market_products 
                SET external_link = 'https://t2m.io/amgkirve', site_requirement = 'AMG Bahis'
                WHERE category_id = 18 AND (site_name ILIKE '%amg%' OR description ILIKE '%amg%' OR name ILIKE '%amg%')
                RETURNING (SELECT COUNT(*) FROM market_products WHERE site_requirement = 'AMG Bahis')
            """)
            
            # 7. Discord kaldır
            await status_msg.edit_text("🗑️ 7/7 - Discord ürünleri kaldırılıyor...")
            await conn.execute("UPDATE market_products SET is_active = false WHERE name ILIKE '%discord%'")
            
            # Sonuçları al
            await status_msg.edit_text("📊 Sonuçlar alınıyor...")
            active_cats = await conn.fetch("SELECT id, name FROM market_categories WHERE is_active = true ORDER BY id")
            active_products = await conn.fetchval("SELECT COUNT(*) FROM market_products WHERE is_active = true")
        
        # Sonuç mesajı
        result_text = "✅ **Market düzeltmeleri tamamlandı!**\n\n"
        result_text += f"📂 **Aktif Kategoriler:** {len(active_cats)}\n"
        for cat in active_cats:
            result_text += f"  • {cat['name']}\n"
        result_text += f"\n📦 **Aktif Ürünler:** {active_products}\n"
        result_text += f"🔗 **Merso linkleri:** {merso_count or 0} ürün\n"
        result_text += f"🔗 **AMG linkleri:** {amg_count or 0} ürün\n"
        result_text += f"\n❌ **Kaldırılan:**\n"
        result_text += "  • Canlı Yayın Bonus kategorisi\n"
        result_text += "  • Özel Ödüller kategorisi\n"
        result_text += "  • Discord ürünleri\n"
        
        await status_msg.edit_text(result_text, parse_mode="Markdown")
        logger.info(f"✅ Market düzeltmeleri tamamlandı - Admin: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Market fix hatası: {e}", exc_info=True)
        await message.reply(f"❌ Hata: {e}")

