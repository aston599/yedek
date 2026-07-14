-- Özel Ödüller kategorisini ve ürünlerini kaldır
BEGIN;

-- 1. Özel Ödüller kategorisini bul ve pasif yap
UPDATE market_categories 
SET is_active = false
WHERE name ILIKE '%özel%ödül%' 
   OR name ILIKE '%ozel%odul%'
   OR name ILIKE '%special%reward%'
   OR name ILIKE '%özel ödül%'
   OR name ILIKE '%Ozel Odul%';

-- 2. Bu kategorilerdeki ürünleri pasif yap
UPDATE market_products 
SET is_active = false
WHERE category_id IN (
    SELECT id FROM market_categories 
    WHERE name ILIKE '%özel%ödül%' 
       OR name ILIKE '%ozel%odul%'
       OR name ILIKE '%special%reward%'
       OR name ILIKE '%özel ödül%'
       OR name ILIKE '%Ozel Odul%'
);

COMMIT;

-- Sonuçları göster
SELECT 
    '✅ Özel Ödüller kategorisi kaldırıldı!' as message,
    (SELECT COUNT(*) FROM market_categories WHERE is_active = true) as aktif_kategori,
    (SELECT COUNT(*) FROM market_products WHERE is_active = true) as aktif_urun;


