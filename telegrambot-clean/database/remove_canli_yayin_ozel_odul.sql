-- 🗑️ CANLI YAYIN BONUS VE ÖZEL ÖDÜLLER KATEGORİLERİNİ KALDIR
-- Tarih: 2025-11-11

-- 1. Canlı Yayın Bonus ve Özel Ödüller kategorilerini deaktive et
UPDATE market_categories 
SET is_active = false 
WHERE 
    name ILIKE '%canlı yayın%' 
    OR name ILIKE '%özel ödül%'
    OR name ILIKE '%live stream%'
    OR name ILIKE '%special reward%'
    OR name ILIKE '%canli yayin%'
    OR name ILIKE '%ozel odul%';

-- 2. Bu kategorilerdeki tüm ürünleri deaktive et
UPDATE market_products 
SET is_active = false 
WHERE category_id IN (
    SELECT id FROM market_categories 
    WHERE 
        name ILIKE '%canlı yayın%' 
        OR name ILIKE '%özel ödül%'
        OR name ILIKE '%live stream%'
        OR name ILIKE '%special reward%'
        OR name ILIKE '%canli yayin%'
        OR name ILIKE '%ozel odul%'
);

-- 3. Kontrol: Kaldırılan kategorileri göster
SELECT 
    id,
    name as "Kategori Adı",
    is_active as "Aktif mi",
    'KALDIRILDI' as "Durum"
FROM market_categories 
WHERE 
    name ILIKE '%canlı yayın%' 
    OR name ILIKE '%özel ödül%'
    OR name ILIKE '%live stream%'
    OR name ILIKE '%special reward%'
    OR name ILIKE '%canli yayin%'
    OR name ILIKE '%ozel odul%';

-- 4. Kontrol: Kaldırılan ürünleri göster
SELECT 
    p.id,
    p.name as "Ürün Adı",
    c.name as "Kategori",
    p.is_active as "Aktif mi",
    'KALDIRILDI' as "Durum"
FROM market_products p
LEFT JOIN market_categories c ON c.id = p.category_id
WHERE p.category_id IN (
    SELECT id FROM market_categories 
    WHERE 
        name ILIKE '%canlı yayın%' 
        OR name ILIKE '%özel ödül%'
        OR name ILIKE '%live stream%'
        OR name ILIKE '%special reward%'
        OR name ILIKE '%canli yayin%'
        OR name ILIKE '%ozel odul%'
);

-- ✅ Kategoriler ve ürünler başarıyla kaldırıldı!
SELECT '✅ Canlı Yayın Bonus ve Özel Ödüller kategorileri kaldırıldı!' as message;

