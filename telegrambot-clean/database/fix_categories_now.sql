-- =============================================
-- KATEGORİ VE ÜRÜN TEMİZLİĞİ
-- =============================================

-- 1. KOLONLARI EKLE (varsa hata vermesin)
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS external_link VARCHAR(500);
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS site_requirement VARCHAR(100);
ALTER TABLE market_products ADD COLUMN IF NOT EXISTS delivery_info TEXT;

-- 2. GEREKSİZ KATEGORİLERİ KALDIR
UPDATE market_categories 
SET is_active = false 
WHERE 
    name ILIKE '%canlı yayın%' 
    OR name ILIKE '%özel ödül%'
    OR name ILIKE '%live stream%'
    OR name ILIKE '%special reward%'
    OR name ILIKE '%discord%'
    OR id IN (19, 20, 21);  -- ID'lere göre de kaldır

-- 3. BU KATEGORİLERDEKİ ÜRÜNLERİ KALDIR
UPDATE market_products 
SET is_active = false 
WHERE category_id IN (
    SELECT id FROM market_categories 
    WHERE is_active = false
);

-- 4. GEREKLİ KATEGORİLERİ AKTİF ET (temiz liste)
UPDATE market_categories 
SET is_active = true 
WHERE 
    name ILIKE '%dijital%'
    OR name ILIKE '%site bakiye%'
    OR name ILIKE '%site bakiyeleri%'
    OR name ILIKE '%nakit%'
    OR name ILIKE '%fiziksel%'
    OR name ILIKE '%çekim%';

-- 5. MERSO LİNKLERİNİ EKLE
UPDATE market_products 
SET 
    external_link = 'https://t2m.io/mersokirvehub', 
    site_requirement = 'Mersobahis'
WHERE 
    (site_name ILIKE '%merso%' OR description ILIKE '%merso%' OR name ILIKE '%merso%')
    AND is_active = true;

-- 6. AMG LİNKLERİNİ EKLE
UPDATE market_products 
SET 
    external_link = 'https://t2m.io/amgkirve', 
    site_requirement = 'AMG Bahis'
WHERE 
    (site_name ILIKE '%amg%' OR description ILIKE '%amg%' OR name ILIKE '%amg%')
    AND is_active = true;

-- 7. DISCORD ÜRÜNLERİNİ KALDIR
UPDATE market_products 
SET is_active = false 
WHERE name ILIKE '%discord%';

-- 8. "NONE" İSİMLERİNİ DÜZELT
UPDATE market_products 
SET name = COALESCE(site_name, 'Ürün') || ' ' || COALESCE(description, 'Kod')
WHERE 
    name IS NULL 
    OR name = 'None' 
    OR TRIM(name) = '';

-- 9. SONUÇLARI GÖSTER
SELECT 
    '=== AKTİF KATEGORİLER ===' as info,
    COUNT(*) as toplam
FROM market_categories 
WHERE is_active = true;

SELECT 
    id,
    name,
    icon,
    (SELECT COUNT(*) FROM market_products WHERE category_id = market_categories.id AND is_active = true) as urun_sayisi
FROM market_categories 
WHERE is_active = true
ORDER BY id;

SELECT 
    '=== AKTİF ÜRÜNLER ===' as info,
    COUNT(*) as toplam
FROM market_products 
WHERE is_active = true;

SELECT 
    '=== MERSO ÜRÜNLER ===' as info,
    COUNT(*) as toplam
FROM market_products 
WHERE site_requirement = 'Mersobahis' AND is_active = true;

SELECT 
    '=== AMG ÜRÜNLER ===' as info,
    COUNT(*) as toplam
FROM market_products 
WHERE site_requirement = 'AMG Bahis' AND is_active = true;

