-- 🔧 YENİ KOLONLARI EKLE
-- Market tablolarına eksik kolonları ekler

-- market_products tablosuna yeni kolonlar
ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS external_link VARCHAR(500);

ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS site_requirement VARCHAR(100);

ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS delivery_info TEXT;

ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);

-- market_categories tablosuna icon kolonu (emoji için)
ALTER TABLE market_categories 
ADD COLUMN IF NOT EXISTS icon VARCHAR(50);

-- ✅ Kolonlar eklendi!





