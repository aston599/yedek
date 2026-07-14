-- 1. Gereksiz kategorileri deaktive et
UPDATE market_categories 
SET is_active = false 
WHERE id IN (19, 20); -- Canlı Yayın Bonus, Özel Ödüller

-- 2. market_products tablosuna external_link kolonu ekle
ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS external_link VARCHAR(500);

-- 3. market_products tablosuna site_requirement kolonu ekle (hangi siteye üyelik gerekli)
ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS site_requirement VARCHAR(100);

-- 4. "None" olan ürün isimlerini düzelt
UPDATE market_products 
SET product_name = COALESCE(site_name, 'Ürün') || ' ' || COALESCE(description, 'Kod')
WHERE product_name IS NULL OR product_name = 'None' OR TRIM(product_name) = '';

-- 5. Site bakiyesi ürünlerine link ve requirement ekle
UPDATE market_products 
SET 
    external_link = 'https://t2m.io/mersokirvehub',
    site_requirement = 'Mersobahis'
WHERE category_id = 18 AND (site_name ILIKE '%merso%' OR description ILIKE '%merso%');

UPDATE market_products 
SET 
    external_link = 'https://t2m.io/amgkirve',
    site_requirement = 'AMG Bahis'
WHERE category_id = 18 AND (site_name ILIKE '%amg%' OR description ILIKE '%amg%');

-- 6. Discord ürünlerini kaldır (gereksiz)
UPDATE market_products 
SET is_active = false 
WHERE product_name ILIKE '%discord%';





