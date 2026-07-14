-- 🗑️ GEREKSIZ KATEGORILERI KALDIR
-- Canlı Yayın Ödülleri ve Özel Ödüller kategorilerini kaldır

-- 1. Kategorileri deaktive et (ID'lere göre)
UPDATE market_categories 
SET is_active = false 
WHERE name ILIKE '%canlı yayın%' 
   OR name ILIKE '%özel ödül%'
   OR name ILIKE '%live stream%'
   OR name ILIKE '%special reward%';

-- 2. Bu kategorilerdeki ürünleri de deaktive et
UPDATE market_products 
SET is_active = false 
WHERE category_id IN (
    SELECT id FROM market_categories 
    WHERE is_active = false
);

-- ✅ Gereksiz kategoriler kaldırıldı!
SELECT 'Gereksiz kategoriler başarıyla kaldırıldı!' as message;


