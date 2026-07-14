"""
Admin Kategori Düzeltme - !kategoriduzenle komutu
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from database import get_db_pool
from config import is_admin

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "!kategoriduzenle")
async def category_fix_command(message: Message):
    """Kategorileri düzenle ve gereksizleri kaldır"""
    try:
        # Sadece admin
        if not is_admin(message.from_user.id):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        status_msg = await message.reply("🔧 Kategori temizliği başlıyor...")
        
        pool = await get_db_pool()
        if not pool:
            await status_msg.edit_text("❌ Database bağlantısı yok!")
            return
        
        async with pool.acquire() as conn:
            # 1. Kolonları ekle
            await status_msg.edit_text("🔧 1/9 - Kolonlar kontrol ediliyor...")
            try:
                await conn.execute("ALTER TABLE market_products ADD COLUMN IF NOT EXISTS external_link VARCHAR(500)")
                await conn.execute("ALTER TABLE market_products ADD COLUMN IF NOT EXISTS site_requirement VARCHAR(100)")
                await conn.execute("ALTER TABLE market_products ADD COLUMN IF NOT EXISTS delivery_info TEXT")
            except Exception as e:
                logger.warning(f"Kolon ekleme uyarısı: {e}")
            
            # 2. Gereksiz kategorileri bul ve deaktive et
            await status_msg.edit_text("🗑️ 2/9 - Gereksiz kategoriler kaldırılıyor...")
            result = await conn.execute("""
                UPDATE market_categories 
                SET is_active = false 
                WHERE 
                    name ILIKE '%canlı yayın%' 
                    OR name ILIKE '%özel ödül%'
                    OR name ILIKE '%live stream%'
                    OR name ILIKE '%special reward%'
                    OR name ILIKE '%discord%'
                    OR id IN (19, 20, 21)
            """)
            logger.info(f"Deaktive edilen kategoriler: {result}")
            
            # 3. Bu kategorilerdeki ürünleri deaktive et
            await status_msg.edit_text("🗑️ 3/9 - İlgili ürünler kaldırılıyor...")
            await conn.execute("""
                UPDATE market_products 
                SET is_active = false 
                WHERE category_id IN (
                    SELECT id FROM market_categories 
                    WHERE is_active = false
                )
            """)
            
            # 4. Gerekli kategorileri aktif et
            await status_msg.edit_text("✅ 4/9 - Gerekli kategoriler aktif ediliyor...")
            await conn.execute("""
                UPDATE market_categories 
                SET is_active = true 
                WHERE 
                    name ILIKE '%dijital%'
                    OR name ILIKE '%site bakiye%'
                    OR name ILIKE '%site bakiyeleri%'
                    OR name ILIKE '%nakit%'
                    OR name ILIKE '%fiziksel%'
                    OR name ILIKE '%çekim%'
            """)
            
            # 5. Merso linkleri
            await status_msg.edit_text("🔗 5/9 - Mersobahis linkleri ekleniyor...")
            await conn.execute("""
                UPDATE market_products 
                SET 
                    external_link = 'https://t2m.io/mersokirvehub', 
                    site_requirement = 'Mersobahis'
                WHERE 
                    (site_name ILIKE '%merso%' OR description ILIKE '%merso%' OR name ILIKE '%merso%')
                    AND is_active = true
            """)
            
            # 6. AMG linkleri
            await status_msg.edit_text("🔗 6/9 - AMG Bahis linkleri ekleniyor...")
            await conn.execute("""
                UPDATE market_products 
                SET 
                    external_link = 'https://t2m.io/amgkirve', 
                    site_requirement = 'AMG Bahis'
                WHERE 
                    (site_name ILIKE '%amg%' OR description ILIKE '%amg%' OR name ILIKE '%amg%')
                    AND is_active = true
            """)
            
            # 7. Discord ürünleri
            await status_msg.edit_text("🗑️ 7/9 - Discord ürünleri kaldırılıyor...")
            await conn.execute("UPDATE market_products SET is_active = false WHERE name ILIKE '%discord%'")
            
            # 8. None isimleri düzelt
            await status_msg.edit_text("🔧 8/9 - İsimler düzeltiliyor...")
            await conn.execute("""
                UPDATE market_products 
                SET name = COALESCE(site_name, 'Ürün') || ' ' || COALESCE(description, 'Kod')
                WHERE 
                    name IS NULL 
                    OR name = 'None' 
                    OR TRIM(name) = ''
            """)
            
            # 9. Sonuçları al
            await status_msg.edit_text("📊 9/9 - Sonuçlar alınıyor...")
            
            # Aktif kategoriler
            active_cats = await conn.fetch("""
                SELECT 
                    id,
                    name,
                    (SELECT COUNT(*) FROM market_products WHERE category_id = market_categories.id AND is_active = true) as urun_sayisi
                FROM market_categories 
                WHERE is_active = true
                ORDER BY id
            """)
            
            # İstatistikler
            total_products = await conn.fetchval("SELECT COUNT(*) FROM market_products WHERE is_active = true")
            merso_count = await conn.fetchval("SELECT COUNT(*) FROM market_products WHERE site_requirement = 'Mersobahis' AND is_active = true")
            amg_count = await conn.fetchval("SELECT COUNT(*) FROM market_products WHERE site_requirement = 'AMG Bahis' AND is_active = true")
        
        # Sonuç mesajı oluştur
        result_text = "✅ **KATEGORİ TEMİZLİĞİ TAMAMLANDI!**\n\n"
        result_text += f"📂 **Aktif Kategoriler:** {len(active_cats)}\n"
        
        for cat in active_cats:
            result_text += f"  • {cat['name']} ({cat['urun_sayisi']} ürün)\n"
        
        result_text += f"\n📦 **Toplam Aktif Ürün:** {total_products}\n"
        result_text += f"🔗 **Mersobahis:** {merso_count or 0} ürün\n"
        result_text += f"🔗 **AMG Bahis:** {amg_count or 0} ürün\n"
        result_text += f"\n❌ **Kaldırılanlar:**\n"
        result_text += "  • 🍿 Canlı Yayın Bonus\n"
        result_text += "  • 🎁 Özel Ödüller\n"
        result_text += "  • 💬 Discord Ürünleri\n"
        result_text += f"\n💡 **Market'te artık sadece {len(active_cats)} kategori görünecek!**"
        
        await status_msg.edit_text(result_text, parse_mode="Markdown")
        logger.info(f"✅ Kategori temizliği tamamlandı - Admin: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Kategori düzenleme hatası: {e}", exc_info=True)
        try:
            await message.reply(f"❌ Hata oluştu:\n{str(e)[:200]}")
        except:
            pass

