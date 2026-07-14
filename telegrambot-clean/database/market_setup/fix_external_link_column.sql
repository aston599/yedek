-- 🔧 MARKET ÜRÜNLER TABLOSUNA EXTERNAL_LINK EKLE
-- Bu script market_products tablosuna external_link kolonunu ekler

ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS external_link VARCHAR(500);

ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS site_requirement VARCHAR(100);

ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS delivery_info TEXT;

-- ✅ Kolonlar eklendi!
SELECT 'Kolonlar başarıyla eklendi!' as message;


