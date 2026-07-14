-- =============================================
-- MARKET KAPSAMLI DÜZENLEME
-- =============================================
-- 1. Gereksiz kategorileri kaldır (2 kategori)
-- 2. Merso ve AMG'ye freespin ekle
-- 3. Ürün açıklamalarını düzenle
-- 4. Ekonomik düzenlemeler
-- =============================================

BEGIN;

-- =============================================
-- 1. GEREKSİZ KATEGORİLERİ KALDIR (2 KATEGORİ)
-- =============================================

-- En az ürünü olan veya gereksiz kategorileri bul ve kaldır
-- Önce hangi kategorilerin en az ürünü olduğunu görelim
-- Sonra en az ürünlü 2 kategoriyi kaldıracağız

-- Kategorileri kontrol et
DO $$
DECLARE
    cat_record RECORD;
    cat_count INT;
    removed_count INT := 0;
BEGIN
    -- En az ürünü olan aktif kategorileri bul
    FOR cat_record IN 
        SELECT 
            c.id, 
            c.name,
            COUNT(p.id) as product_count
        FROM market_categories c
        LEFT JOIN market_products p ON p.category_id = c.id
        WHERE c.is_active = true
        GROUP BY c.id, c.name
        HAVING COUNT(p.id) <= 2  -- 2 veya daha az ürünü olanlar
        ORDER BY product_count ASC, c.id ASC
        LIMIT 2
    LOOP
        -- Bu kategorideki ürünleri başka kategoriye taşı veya pasif yap
        UPDATE market_products 
        SET is_active = false
        WHERE category_id = cat_record.id;
        
        -- Kategoriyi pasif yap
        UPDATE market_categories 
        SET is_active = false
        WHERE id = cat_record.id;
        
        removed_count := removed_count + 1;
        RAISE NOTICE 'Kategori kaldırıldı: % (ID: %, Ürün: %)', cat_record.name, cat_record.id, cat_record.product_count;
    END LOOP;
    
    RAISE NOTICE 'Toplam % kategori kaldırıldı', removed_count;
END $$;

-- =============================================
-- 2. Freespin KATEGORİSİNİ OLUŞTUR/KONTROL ET
-- =============================================

-- Freespin kategorisi yoksa oluştur
INSERT INTO market_categories (name, description, emoji, display_order, is_active)
SELECT 'Freespinler', 'Site freespin paketleri', '🎰', 2, true
WHERE NOT EXISTS (
    SELECT 1 FROM market_categories WHERE name ILIKE '%freespin%'
);

-- Freespin kategori ID'sini al
DO $$
DECLARE
    freespin_cat_id INT;
BEGIN
    SELECT id INTO freespin_cat_id 
    FROM market_categories 
    WHERE name ILIKE '%freespin%' 
    LIMIT 1;
    
    -- =============================================
    -- 3. MERSO VE AMG'YE FREESPIN EKLE
    -- =============================================
    
    -- Merso Freespin paketleri ekle (eğer yoksa)
    INSERT INTO market_products (
        name, 
        description, 
        category_id, 
        price, 
        stock, 
        site_name, 
        site_link,
        company_name,
        is_active,
        is_featured,
        delivery_content
    )
    SELECT 
        'Mersobahis 50 Freespin',
        'Mersobahis sitesinde kullanabileceğiniz 50 freespin paketi. Çevrim şartı yoktur.',
        freespin_cat_id,
        500.00,
        100,
        'Mersobahis',
        'https://t2m.io/mersokirvehub',
        'Mersobahis',
        true,
        false,
        'Freespinler hesabınıza otomatik olarak yüklenir.'
    WHERE NOT EXISTS (
        SELECT 1 FROM market_products 
        WHERE name ILIKE '%merso%50%freespin%' AND is_active = true
    );
    
    INSERT INTO market_products (
        name, 
        description, 
        category_id, 
        price, 
        stock, 
        site_name, 
        site_link,
        company_name,
        is_active,
        is_featured,
        delivery_content
    )
    SELECT 
        'Mersobahis 100 Freespin',
        'Mersobahis sitesinde kullanabileceğiniz 100 freespin paketi. Çevrim şartı yoktur.',
        freespin_cat_id,
        900.00,
        100,
        'Mersobahis',
        'https://t2m.io/mersokirvehub',
        'Mersobahis',
        true,
        false,
        'Freespinler hesabınıza otomatik olarak yüklenir.'
    WHERE NOT EXISTS (
        SELECT 1 FROM market_products 
        WHERE name ILIKE '%merso%100%freespin%' AND is_active = true
    );
    
    INSERT INTO market_products (
        name, 
        description, 
        category_id, 
        price, 
        stock, 
        site_name, 
        site_link,
        company_name,
        is_active,
        is_featured,
        delivery_content
    )
    SELECT 
        'Mersobahis 200 Freespin',
        'Mersobahis sitesinde kullanabileceğiniz 200 freespin paketi. Çevrim şartı yoktur.',
        freespin_cat_id,
        1700.00,
        100,
        'Mersobahis',
        'https://t2m.io/mersokirvehub',
        'Mersobahis',
        true,
        true,
        'Freespinler hesabınıza otomatik olarak yüklenir.'
    WHERE NOT EXISTS (
        SELECT 1 FROM market_products 
        WHERE name ILIKE '%merso%200%freespin%' AND is_active = true
    );
    
    -- AMG Freespin paketleri ekle (eğer yoksa)
    INSERT INTO market_products (
        name, 
        description, 
        category_id, 
        price, 
        stock, 
        site_name, 
        site_link,
        company_name,
        is_active,
        is_featured,
        delivery_content
    )
    SELECT 
        'AMG Bahis 50 Freespin',
        'AMG Bahis sitesinde kullanabileceğiniz 50 freespin paketi. Çevrim şartı yoktur.',
        freespin_cat_id,
        500.00,
        100,
        'AMG Bahis',
        'https://t2m.io/amgkirve',
        'AMG Bahis',
        true,
        false,
        'Freespinler hesabınıza otomatik olarak yüklenir.'
    WHERE NOT EXISTS (
        SELECT 1 FROM market_products 
        WHERE name ILIKE '%amg%50%freespin%' AND is_active = true
    );
    
    INSERT INTO market_products (
        name, 
        description, 
        category_id, 
        price, 
        stock, 
        site_name, 
        site_link,
        company_name,
        is_active,
        is_featured,
        delivery_content
    )
    SELECT 
        'AMG Bahis 100 Freespin',
        'AMG Bahis sitesinde kullanabileceğiniz 100 freespin paketi. Çevrim şartı yoktur.',
        freespin_cat_id,
        900.00,
        100,
        'AMG Bahis',
        'https://t2m.io/amgkirve',
        'AMG Bahis',
        true,
        false,
        'Freespinler hesabınıza otomatik olarak yüklenir.'
    WHERE NOT EXISTS (
        SELECT 1 FROM market_products 
        WHERE name ILIKE '%amg%100%freespin%' AND is_active = true
    );
    
    INSERT INTO market_products (
        name, 
        description, 
        category_id, 
        price, 
        stock, 
        site_name, 
        site_link,
        company_name,
        is_active,
        is_featured,
        delivery_content
    )
    SELECT 
        'AMG Bahis 200 Freespin',
        'AMG Bahis sitesinde kullanabileceğiniz 200 freespin paketi. Çevrim şartı yoktur.',
        freespin_cat_id,
        1700.00,
        100,
        'AMG Bahis',
        'https://t2m.io/amgkirve',
        'AMG Bahis',
        true,
        true,
        'Freespinler hesabınıza otomatik olarak yüklenir.'
    WHERE NOT EXISTS (
        SELECT 1 FROM market_products 
        WHERE name ILIKE '%amg%200%freespin%' AND is_active = true
    );
    
    RAISE NOTICE 'Freespin ürünleri eklendi (Merso ve AMG)';
END $$;

-- =============================================
-- 4. ÜRÜN AÇIKLAMALARINI DÜZENLE
-- =============================================

-- Merso ürünlerinin açıklamalarını düzenle
UPDATE market_products 
SET 
    description = CASE 
        WHEN name ILIKE '%500%' THEN 'Mersobahis sitesinde geçerli 500 TL bakiyedir. Çevrim şartı yoktur. Hesabınıza otomatik olarak yüklenir.'
        WHEN name ILIKE '%1000%' OR name ILIKE '%1.000%' THEN 'Mersobahis sitesinde geçerli 1.000 TL bakiyedir. Çevrim şartı yoktur. Hesabınıza otomatik olarak yüklenir.'
        WHEN name ILIKE '%2500%' OR name ILIKE '%2.500%' THEN 'Mersobahis sitesinde geçerli 2.500 TL bakiyedir. Çevrim şartı yoktur. Hesabınıza otomatik olarak yüklenir.'
        WHEN name ILIKE '%5000%' OR name ILIKE '%5.000%' THEN 'Mersobahis sitesinde geçerli 5.000 TL bakiyedir. Çevrim şartı yoktur. Hesabınıza otomatik olarak yüklenir.'
        ELSE description
    END,
    delivery_content = 'Bakiyeniz hesabınıza otomatik olarak yüklenir. Site: https://t2m.io/mersokirvehub'
WHERE site_name ILIKE '%merso%' 
  AND (name ILIKE '%bakiye%' OR name ILIKE '%tl%')
  AND is_active = true;

-- AMG ürünlerinin açıklamalarını düzenle
UPDATE market_products 
SET 
    description = CASE 
        WHEN name ILIKE '%500%' THEN 'AMG Bahis sitesinde geçerli 500 TL bakiyedir. Çevrim şartı yoktur. Hesabınıza otomatik olarak yüklenir.'
        WHEN name ILIKE '%1000%' OR name ILIKE '%1.000%' THEN 'AMG Bahis sitesinde geçerli 1.000 TL bakiyedir. Çevrim şartı yoktur. Hesabınıza otomatik olarak yüklenir.'
        WHEN name ILIKE '%2500%' OR name ILIKE '%2.500%' THEN 'AMG Bahis sitesinde geçerli 2.500 TL bakiyedir. Çevrim şartı yoktur. Hesabınıza otomatik olarak yüklenir.'
        WHEN name ILIKE '%5000%' OR name ILIKE '%5.000%' THEN 'AMG Bahis sitesinde geçerli 5.000 TL bakiyedir. Çevrim şartı yoktur. Hesabınıza otomatik olarak yüklenir.'
        ELSE description
    END,
    delivery_content = 'Bakiyeniz hesabınıza otomatik olarak yüklenir. Site: https://t2m.io/amgkirve'
WHERE site_name ILIKE '%amg%' 
  AND (name ILIKE '%bakiye%' OR name ILIKE '%tl%')
  AND is_active = true;

-- Genel açıklama düzenlemeleri
UPDATE market_products 
SET 
    description = TRIM(description),
    description = REPLACE(description, '', ''),
    description = REPLACE(description, 'çevrim', 'çevrim'),
    description = REPLACE(description, 'ücretsiz', 'ücretsiz'),
    description = REPLACE(description, 'orjinal', 'orijinal')
WHERE description IS NOT NULL;

-- =============================================
-- 5. EKONOMİK DÜZENLEMELER
-- =============================================

-- Fiyatları mantıklı hale getir
-- Freespin fiyatları: 50 FS = 500 KP, 100 FS = 900 KP, 200 FS = 1700 KP (indirimli)
UPDATE market_products 
SET price = CASE 
    WHEN name ILIKE '%50%freespin%' THEN 500.00
    WHEN name ILIKE '%100%freespin%' THEN 900.00
    WHEN name ILIKE '%200%freespin%' THEN 1700.00
    ELSE price
END
WHERE name ILIKE '%freespin%' AND is_active = true;

-- Bakiye fiyatlarını kontrol et ve düzenle (1 TL = 10 KP mantığı)
-- 500 TL = 5000 KP, 1000 TL = 10000 KP, vb.
UPDATE market_products 
SET price = CASE 
    WHEN name ILIKE '%500%' AND (name ILIKE '%bakiye%' OR name ILIKE '%tl%') THEN 5000.00
    WHEN name ILIKE '%1000%' AND (name ILIKE '%bakiye%' OR name ILIKE '%tl%') THEN 10000.00
    WHEN name ILIKE '%2500%' AND (name ILIKE '%bakiye%' OR name ILIKE '%tl%') THEN 25000.00
    WHEN name ILIKE '%5000%' AND (name ILIKE '%bakiye%' OR name ILIKE '%tl%') THEN 50000.00
    ELSE price
END
WHERE (site_name ILIKE '%merso%' OR site_name ILIKE '%amg%')
  AND (name ILIKE '%bakiye%' OR name ILIKE '%tl%')
  AND is_active = true
  AND price < 1000;  -- Sadece düşük fiyatlı olanları düzelt

-- Site linklerini düzenle
UPDATE market_products 
SET 
    site_link = CASE 
        WHEN site_name ILIKE '%merso%' THEN 'https://t2m.io/mersokirvehub'
        WHEN site_name ILIKE '%amg%' THEN 'https://t2m.io/amgkirve'
        ELSE site_link
    END
WHERE (site_name ILIKE '%merso%' OR site_name ILIKE '%amg%')
  AND is_active = true;

-- =============================================
-- 6. KATEGORİ SIRALAMASINI DÜZENLE
-- =============================================

UPDATE market_categories 
SET display_order = CASE 
    WHEN name ILIKE '%bakiye%' OR name ILIKE '%site%' THEN 1
    WHEN name ILIKE '%freespin%' THEN 2
    WHEN name ILIKE '%nakit%' OR name ILIKE '%çekim%' THEN 3
    WHEN name ILIKE '%ödül%' OR name ILIKE '%premium%' THEN 4
    ELSE display_order
END
WHERE is_active = true;

COMMIT;

-- =============================================
-- SONUÇ RAPORU
-- =============================================

SELECT 
    '✅ Market düzenlemesi tamamlandı!' as message,
    (SELECT COUNT(*) FROM market_categories WHERE is_active = true) as aktif_kategori,
    (SELECT COUNT(*) FROM market_products WHERE is_active = true) as aktif_urun,
    (SELECT COUNT(*) FROM market_products WHERE name ILIKE '%freespin%' AND is_active = true) as freespin_urun;


