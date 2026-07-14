-- 🛍️ MARKET ÜRÜNLERİ GÜNCELLEME SQL
-- Tarih: 2025-01-XX
-- Güncellenmiş ürünler, kategoriler ve fiyatlandırma

-- Önce mevcut ürünleri temizle (opsiyonel - dikkatli kullan!)
-- DELETE FROM market_products WHERE category_id IN (SELECT id FROM market_categories WHERE name LIKE '%Gamer%' OR name LIKE '%Site%');

-- ============================================
-- 0. GEREKLİ KOLONLARI EKLE
-- ============================================

-- site_requirement kolonunu ekle (çevrim şartı için)
ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS site_requirement VARCHAR(100);

-- external_link kolonunu ekle
ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS external_link VARCHAR(500);

-- site_username kolonunu market_orders'a ekle (zaten varsa hata vermez)
ALTER TABLE market_orders 
ADD COLUMN IF NOT EXISTS site_username VARCHAR(255) DEFAULT NULL;

-- ============================================
-- 1. KATEGORİLERİ GÜNCELLE/OLUŞTUR
-- ============================================

-- Site Bakiyeleri kategorisi
INSERT INTO market_categories (name, description, icon, display_order, is_active, emoji)
VALUES ('Site Bakiyeleri', 'Bahis siteleri bakiye yüklemeleri (Çevrimli)', '💰', 1, TRUE, '💰')
ON CONFLICT (name) DO UPDATE SET 
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    display_order = EXCLUDED.display_order,
    emoji = EXCLUDED.emoji;

-- Freespinler kategorisi
INSERT INTO market_categories (name, description, icon, display_order, is_active, emoji)
VALUES ('Freespinler', 'Bahis siteleri freespin paketleri', '🎰', 2, TRUE, '🎰')
ON CONFLICT (name) DO UPDATE SET 
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    display_order = EXCLUDED.display_order,
    emoji = EXCLUDED.emoji;

-- Oyun Hediye Kartları
INSERT INTO market_categories (name, description, icon, display_order, is_active, emoji)
VALUES ('Oyun Hediye Kartları', 'Xbox, PlayStation, ByNoGame hediye kartları', '🎮', 3, TRUE, '🎮')
ON CONFLICT (name) DO UPDATE SET 
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    display_order = EXCLUDED.display_order,
    emoji = EXCLUDED.emoji;

-- Oyun İçi Para
INSERT INTO market_categories (name, description, icon, display_order, is_active, emoji)
VALUES ('Oyun İçi Para', 'Valorant, LoL, PUBG, Wild Rift', '🎯', 4, TRUE, '🎯')
ON CONFLICT (name) DO UPDATE SET 
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    display_order = EXCLUDED.display_order,
    emoji = EXCLUDED.emoji;

-- Mobil Hediye Kartları
INSERT INTO market_categories (name, description, icon, display_order, is_active, emoji)
VALUES ('Mobil Hediye Kartları', 'Google Play hediye kartları', '📱', 5, TRUE, '📱')
ON CONFLICT (name) DO UPDATE SET 
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    display_order = EXCLUDED.display_order,
    emoji = EXCLUDED.emoji;

-- Dijital Ürünler
INSERT INTO market_categories (name, description, icon, display_order, is_active, emoji)
VALUES ('Dijital Ürünler', 'Elite Pass, Spotify vb.', '🎁', 6, TRUE, '🎁')
ON CONFLICT (name) DO UPDATE SET 
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    display_order = EXCLUDED.display_order,
    emoji = EXCLUDED.emoji;

-- Abonelikler
INSERT INTO market_categories (name, description, icon, display_order, is_active, emoji)
VALUES ('Abonelikler', 'Netflix, Amazon Prime, Disney+, YouTube Premium, NordVPN', '📺', 7, TRUE, '📺')
ON CONFLICT (name) DO UPDATE SET 
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    display_order = EXCLUDED.display_order,
    emoji = EXCLUDED.emoji;

-- Gamer Ekipmanları (Azaltılmış)
INSERT INTO market_categories (name, description, icon, display_order, is_active, emoji)
VALUES ('Gamer Ekipmanları', 'Gaming mouse, klavye, kulaklık, monitör, konsol, PC', '🎮', 8, TRUE, '🎮')
ON CONFLICT (name) DO UPDATE SET 
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    display_order = EXCLUDED.display_order,
    emoji = EXCLUDED.emoji;

-- Teknoloji Ürünleri
INSERT INTO market_categories (name, description, icon, display_order, is_active, emoji)
VALUES ('Teknoloji Ürünleri', 'iPhone, MacBook, Samsung, TV, AirPods, Apple Watch', '📱', 9, TRUE, '📱')
ON CONFLICT (name) DO UPDATE SET 
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    display_order = EXCLUDED.display_order,
    emoji = EXCLUDED.emoji;

-- ============================================
-- 2. SİTE BAKİYELERİ (Çevrimli)
-- ============================================

-- Merso ve AMG Bahis Bakiyeleri
DO $$
DECLARE
    cat_id INTEGER;
    product_id INTEGER;
BEGIN
    SELECT id INTO cat_id FROM market_categories WHERE name = 'Site Bakiyeleri';
    
    -- Merso Bakiyeleri
    FOR product_id IN SELECT id FROM market_products WHERE name IN ('Merso 50 TL', 'Merso 100 TL', 'Merso 250 TL', 'Merso 500 TL', 'Merso 1000 TL', 'Merso 2500 TL', 'Merso 5000 TL')
    LOOP
        UPDATE market_products SET
            description = CASE name
                WHEN 'Merso 50 TL' THEN 'Merso Bahis 50 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'Merso 100 TL' THEN 'Merso Bahis 100 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'Merso 250 TL' THEN 'Merso Bahis 250 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'Merso 500 TL' THEN 'Merso Bahis 500 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'Merso 1000 TL' THEN 'Merso Bahis 1000 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'Merso 2500 TL' THEN 'Merso Bahis 2500 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'Merso 5000 TL' THEN 'Merso Bahis 5000 TL bakiye yükleme. Çevrim şartı: 1x'
            END,
            price = CASE name
                WHEN 'Merso 50 TL' THEN 75
                WHEN 'Merso 100 TL' THEN 150
                WHEN 'Merso 250 TL' THEN 375
                WHEN 'Merso 500 TL' THEN 750
                WHEN 'Merso 1000 TL' THEN 1500
                WHEN 'Merso 2500 TL' THEN 3750
                WHEN 'Merso 5000 TL' THEN 7500
            END,
            site_requirement = '1x',
            category_id = cat_id,
            site_name = 'Merso Bahis',
            site_link = 'https://kumarlayasiyorum9.com'
        WHERE id = product_id;
    END LOOP;
    
    -- Merso Bakiyeleri INSERT (yoksa)
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, site_name, site_link, site_requirement, auto_delivery)
    SELECT * FROM (VALUES
        ('Merso 50 TL', 'Merso Bahis 50 TL bakiye yükleme. Çevrim şartı: 1x', 75, cat_id, 999, TRUE, 'Merso Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('Merso 100 TL', 'Merso Bahis 100 TL bakiye yükleme. Çevrim şartı: 1x', 150, cat_id, 999, TRUE, 'Merso Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('Merso 250 TL', 'Merso Bahis 250 TL bakiye yükleme. Çevrim şartı: 1x', 375, cat_id, 999, TRUE, 'Merso Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('Merso 500 TL', 'Merso Bahis 500 TL bakiye yükleme. Çevrim şartı: 1x', 750, cat_id, 999, TRUE, 'Merso Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('Merso 1000 TL', 'Merso Bahis 1000 TL bakiye yükleme. Çevrim şartı: 1x', 1500, cat_id, 999, TRUE, 'Merso Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('Merso 2500 TL', 'Merso Bahis 2500 TL bakiye yükleme. Çevrim şartı: 1x', 3750, cat_id, 999, TRUE, 'Merso Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('Merso 5000 TL', 'Merso Bahis 5000 TL bakiye yükleme. Çevrim şartı: 1x', 7500, cat_id, 999, TRUE, 'Merso Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE)
    ) AS v(name, description, price, category_id, stock, is_active, site_name, site_link, site_requirement, auto_delivery)
    WHERE NOT EXISTS (SELECT 1 FROM market_products WHERE market_products.name = v.name);
    
    -- AMG Bakiyeleri UPDATE
    FOR product_id IN SELECT id FROM market_products WHERE name IN ('AMG 50 TL', 'AMG 100 TL', 'AMG 250 TL', 'AMG 500 TL', 'AMG 1000 TL', 'AMG 2500 TL', 'AMG 5000 TL')
    LOOP
        UPDATE market_products SET
            description = CASE name
                WHEN 'AMG 50 TL' THEN 'AMG Bahis 50 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'AMG 100 TL' THEN 'AMG Bahis 100 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'AMG 250 TL' THEN 'AMG Bahis 250 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'AMG 500 TL' THEN 'AMG Bahis 500 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'AMG 1000 TL' THEN 'AMG Bahis 1000 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'AMG 2500 TL' THEN 'AMG Bahis 2500 TL bakiye yükleme. Çevrim şartı: 1x'
                WHEN 'AMG 5000 TL' THEN 'AMG Bahis 5000 TL bakiye yükleme. Çevrim şartı: 1x'
            END,
            price = CASE name
                WHEN 'AMG 50 TL' THEN 75
                WHEN 'AMG 100 TL' THEN 150
                WHEN 'AMG 250 TL' THEN 375
                WHEN 'AMG 500 TL' THEN 750
                WHEN 'AMG 1000 TL' THEN 1500
                WHEN 'AMG 2500 TL' THEN 3750
                WHEN 'AMG 5000 TL' THEN 7500
            END,
            site_requirement = '1x',
            category_id = cat_id,
            site_name = 'AMG Bahis',
            site_link = 'https://kumarlayasiyorum9.com'
        WHERE id = product_id;
    END LOOP;
    
    -- AMG Bakiyeleri INSERT (yoksa)
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, site_name, site_link, site_requirement, auto_delivery)
    SELECT * FROM (VALUES
        ('AMG 50 TL', 'AMG Bahis 50 TL bakiye yükleme. Çevrim şartı: 1x', 75, cat_id, 999, TRUE, 'AMG Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('AMG 100 TL', 'AMG Bahis 100 TL bakiye yükleme. Çevrim şartı: 1x', 150, cat_id, 999, TRUE, 'AMG Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('AMG 250 TL', 'AMG Bahis 250 TL bakiye yükleme. Çevrim şartı: 1x', 375, cat_id, 999, TRUE, 'AMG Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('AMG 500 TL', 'AMG Bahis 500 TL bakiye yükleme. Çevrim şartı: 1x', 750, cat_id, 999, TRUE, 'AMG Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('AMG 1000 TL', 'AMG Bahis 1000 TL bakiye yükleme. Çevrim şartı: 1x', 1500, cat_id, 999, TRUE, 'AMG Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('AMG 2500 TL', 'AMG Bahis 2500 TL bakiye yükleme. Çevrim şartı: 1x', 3750, cat_id, 999, TRUE, 'AMG Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE),
        ('AMG 5000 TL', 'AMG Bahis 5000 TL bakiye yükleme. Çevrim şartı: 1x', 7500, cat_id, 999, TRUE, 'AMG Bahis', 'https://kumarlayasiyorum9.com', '1x', FALSE)
    ) AS v(name, description, price, category_id, stock, is_active, site_name, site_link, site_requirement, auto_delivery)
    WHERE NOT EXISTS (SELECT 1 FROM market_products WHERE market_products.name = v.name);
END $$;

-- ============================================
-- 3. FREESPİNLER
-- ============================================

DO $$
DECLARE
    freespin_cat_id INTEGER;
BEGIN
    SELECT id INTO freespin_cat_id FROM market_categories WHERE name = 'Freespinler';
    
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, site_name, site_link, auto_delivery)
    VALUES 
    ('Merso 100 Freespin', 'Merso Bahis 100 freespin paketi', 150, freespin_cat_id, 999, TRUE, 'Merso Bahis', 'https://kumarlayasiyorum9.com', FALSE),
    ('Merso 200 Freespin', 'Merso Bahis 200 freespin paketi', 300, freespin_cat_id, 999, TRUE, 'Merso Bahis', 'https://kumarlayasiyorum9.com', FALSE),
    ('Merso 300 Freespin', 'Merso Bahis 300 freespin paketi', 450, freespin_cat_id, 999, TRUE, 'Merso Bahis', 'https://kumarlayasiyorum9.com', FALSE),
    ('AMG 100 Freespin', 'AMG Bahis 100 freespin paketi', 150, freespin_cat_id, 999, TRUE, 'AMG Bahis', 'https://kumarlayasiyorum9.com', FALSE),
    ('AMG 200 Freespin', 'AMG Bahis 200 freespin paketi', 300, freespin_cat_id, 999, TRUE, 'AMG Bahis', 'https://kumarlayasiyorum9.com', FALSE),
    ('AMG 300 Freespin', 'AMG Bahis 300 freespin paketi', 450, freespin_cat_id, 999, TRUE, 'AMG Bahis', 'https://kumarlayasiyorum9.com', FALSE)
    ON CONFLICT DO NOTHING;
END $$;

-- ============================================
-- 4. OYUN HEDİYE KARTLARI
-- ============================================

DO $$
DECLARE
    oyun_cat_id INTEGER;
BEGIN
    SELECT id INTO oyun_cat_id FROM market_categories WHERE name = 'Oyun Hediye Kartları';
    
    -- Xbox
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Xbox 25 TL', 'Xbox hediye kartı 25 TL', 50, oyun_cat_id, 999, TRUE, FALSE),
    ('Xbox 50 TL', 'Xbox hediye kartı 50 TL', 100, oyun_cat_id, 999, TRUE, FALSE),
    ('Xbox 100 TL', 'Xbox hediye kartı 100 TL', 200, oyun_cat_id, 999, TRUE, FALSE),
    ('Xbox 300 TL', 'Xbox hediye kartı 300 TL', 600, oyun_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- PlayStation
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('PS Store 250 TL', 'PlayStation Store hediye kartı 250 TL', 500, oyun_cat_id, 999, TRUE, FALSE),
    ('PS Store 500 TL', 'PlayStation Store hediye kartı 500 TL', 1000, oyun_cat_id, 999, TRUE, FALSE),
    ('PS Store 750 TL', 'PlayStation Store hediye kartı 750 TL', 1500, oyun_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- ByNoGame
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('ByNoGame 25 TL', 'ByNoGame hediye kartı 25 TL', 50, oyun_cat_id, 999, TRUE, FALSE),
    ('ByNoGame 50 TL', 'ByNoGame hediye kartı 50 TL', 100, oyun_cat_id, 999, TRUE, FALSE),
    ('ByNoGame 100 TL', 'ByNoGame hediye kartı 100 TL', 200, oyun_cat_id, 999, TRUE, FALSE),
    ('ByNoGame 250 TL', 'ByNoGame hediye kartı 250 TL', 500, oyun_cat_id, 999, TRUE, FALSE),
    ('ByNoGame 500 TL', 'ByNoGame hediye kartı 500 TL', 1000, oyun_cat_id, 999, TRUE, FALSE),
    ('ByNoGame 1000 TL', 'ByNoGame hediye kartı 1000 TL', 2000, oyun_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
END $$;

-- ============================================
-- 5. OYUN İÇİ PARA BİRİMLERİ
-- ============================================

DO $$
DECLARE
    oyun_para_cat_id INTEGER;
BEGIN
    SELECT id INTO oyun_para_cat_id FROM market_categories WHERE name = 'Oyun İçi Para';
    
    -- Valorant Points
    INSERT INTO market_products (name, description, price, original_price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Valorant 375 VP', 'Valorant Points 375 VP paketi', 216, 240, oyun_para_cat_id, 999, TRUE, FALSE),
    ('Valorant 825 VP', 'Valorant Points 825 VP paketi', 450, 500, oyun_para_cat_id, 999, TRUE, FALSE),
    ('Valorant 1700 VP', 'Valorant Points 1700 VP paketi', 900, 1000, oyun_para_cat_id, 999, TRUE, FALSE),
    ('Valorant 2925 VP', 'Valorant Points 2925 VP paketi', 1530, 1700, oyun_para_cat_id, 999, TRUE, FALSE),
    ('Valorant 4325 VP', 'Valorant Points 4325 VP paketi', 2214, 2460, oyun_para_cat_id, 999, TRUE, FALSE),
    ('Valorant 8900 VP', 'Valorant Points 8900 VP paketi', 4500, 4500, oyun_para_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- League of Legends RP
    INSERT INTO market_products (name, description, price, original_price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('LoL 460 RP', 'League of Legends 460 RP paketi', 216, 240, oyun_para_cat_id, 999, TRUE, FALSE),
    ('LoL 1005 RP', 'League of Legends 1005 RP paketi', 450, 500, oyun_para_cat_id, 999, TRUE, FALSE),
    ('LoL 2105 RP', 'League of Legends 2105 RP paketi', 900, 1000, oyun_para_cat_id, 999, TRUE, FALSE),
    ('LoL 3625 RP', 'League of Legends 3625 RP paketi', 1530, 1700, oyun_para_cat_id, 999, TRUE, FALSE),
    ('LoL 5295 RP', 'League of Legends 5295 RP paketi', 2214, 2460, oyun_para_cat_id, 999, TRUE, FALSE),
    ('LoL 10875 RP', 'League of Legends 10875 RP paketi', 4500, 4500, oyun_para_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- PUBG Mobile UC
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('PUBG 60 UC', 'PUBG Mobile 60 UC paketi', 72, oyun_para_cat_id, 999, TRUE, FALSE),
    ('PUBG 325 UC', 'PUBG Mobile 325 UC paketi', 360, oyun_para_cat_id, 999, TRUE, FALSE),
    ('PUBG 660 UC', 'PUBG Mobile 660 UC paketi', 720, oyun_para_cat_id, 999, TRUE, FALSE),
    ('PUBG 1800 UC', 'PUBG Mobile 1800 UC paketi', 1800, oyun_para_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- Wild Rift
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Wild Rift GP 25 TL', 'Wild Rift Google Play 25 TL paketi', 45, oyun_para_cat_id, 999, TRUE, FALSE),
    ('Wild Rift GP 50 TL', 'Wild Rift Google Play 50 TL paketi', 90, oyun_para_cat_id, 999, TRUE, FALSE),
    ('Wild Rift GP 100 TL', 'Wild Rift Google Play 100 TL paketi', 180, oyun_para_cat_id, 999, TRUE, FALSE),
    ('Wild Rift AS 25 TL', 'Wild Rift Apple Store 25 TL paketi', 45, oyun_para_cat_id, 999, TRUE, FALSE),
    ('Wild Rift AS 50 TL', 'Wild Rift Apple Store 50 TL paketi', 90, oyun_para_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
END $$;

-- ============================================
-- 6. MOBİL HEDİYE KARTLARI
-- ============================================

DO $$
DECLARE
    mobil_cat_id INTEGER;
BEGIN
    SELECT id INTO mobil_cat_id FROM market_categories WHERE name = 'Mobil Hediye Kartları';
    
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Google Play 25 TL', 'Google Play hediye kartı 25 TL', 50, mobil_cat_id, 999, TRUE, FALSE),
    ('Google Play 50 TL', 'Google Play hediye kartı 50 TL', 100, mobil_cat_id, 999, TRUE, FALSE),
    ('Google Play 100 TL', 'Google Play hediye kartı 100 TL', 200, mobil_cat_id, 999, TRUE, FALSE),
    ('Google Play 250 TL', 'Google Play hediye kartı 250 TL', 500, mobil_cat_id, 999, TRUE, FALSE),
    ('Google Play 500 TL', 'Google Play hediye kartı 500 TL', 1000, mobil_cat_id, 999, TRUE, FALSE),
    ('Google Play 1000 TL', 'Google Play hediye kartı 1000 TL', 2000, mobil_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
END $$;

-- ============================================
-- 7. DİJİTAL ÜRÜNLER
-- ============================================

DO $$
DECLARE
    dijital_cat_id INTEGER;
BEGIN
    SELECT id INTO dijital_cat_id FROM market_categories WHERE name = 'Dijital Ürünler';
    
    INSERT INTO market_products (name, description, price, original_price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Elite Pass', 'Elite Pass upgrade kartı', 1078, 1198, dijital_cat_id, 999, TRUE, FALSE),
    ('Elite Pass Plus', 'Elite Pass Plus upgrade kartı', 2698, 2698, dijital_cat_id, 999, TRUE, FALSE),
    ('Spotify 10 USD', 'Spotify hediye kartı 10 USD', 630, 700, dijital_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
END $$;

-- ============================================
-- 8. ABONELİKLER
-- ============================================

DO $$
DECLARE
    abonelik_cat_id INTEGER;
BEGIN
    SELECT id INTO abonelik_cat_id FROM market_categories WHERE name = 'Abonelikler';
    
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Netflix 1 Ekran 1 Ay', 'Netflix 1 ekran 1 aylık abonelik', 300, abonelik_cat_id, 999, TRUE, FALSE),
    ('Netflix 4 Ekran 1 Ay', 'Netflix 4 ekran 1 aylık abonelik', 450, abonelik_cat_id, 999, TRUE, FALSE),
    ('Netflix 12 Ay', 'Netflix 12 aylık abonelik', 3600, abonelik_cat_id, 999, TRUE, FALSE),
    ('Amazon Prime 1 Ay', 'Amazon Prime 1 aylık abonelik', 75, abonelik_cat_id, 999, TRUE, FALSE),
    ('Amazon Prime 12 Ay', 'Amazon Prime 12 aylık abonelik', 750, abonelik_cat_id, 999, TRUE, FALSE),
    ('Disney+ 1 Ay', 'Disney+ 1 aylık abonelik', 150, abonelik_cat_id, 999, TRUE, FALSE),
    ('Disney+ 12 Ay', 'Disney+ 12 aylık abonelik', 1500, abonelik_cat_id, 999, TRUE, FALSE),
    ('YouTube Premium 1 Ay', 'YouTube Premium 1 aylık abonelik', 120, abonelik_cat_id, 999, TRUE, FALSE),
    ('YouTube Premium 12 Ay', 'YouTube Premium 12 aylık abonelik', 1200, abonelik_cat_id, 999, TRUE, FALSE),
    ('NordVPN 1 Ay', 'NordVPN 1 aylık abonelik', 225, abonelik_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
END $$;

-- ============================================
-- 9. GAMER EKİPMANLARI (Azaltılmış)
-- ============================================

DO $$
DECLARE
    gamer_cat_id INTEGER;
BEGIN
    SELECT id INTO gamer_cat_id FROM market_categories WHERE name = 'Gamer Ekipmanları';
    
    -- Küçük Ekipmanlar
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Gaming Mouse', 'Gaming mouse 16000 DPI', 1000, gamer_cat_id, 999, TRUE, FALSE),
    ('Gaming Klavye', 'Gaming mekanik klavye', 1500, gamer_cat_id, 999, TRUE, FALSE),
    ('Gaming Kulaklık', 'Gaming 7.1 surround kulaklık', 2000, gamer_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- Orta Ekipmanlar
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Gaming Monitor 27"', 'Gaming monitör 27" 165Hz', 2000, gamer_cat_id, 999, TRUE, FALSE),
    ('Nintendo Switch', 'Nintendo Switch OLED', 3200, gamer_cat_id, 999, TRUE, FALSE),
    ('PlayStation 5', 'PlayStation 5 konsol', 7200, gamer_cat_id, 999, TRUE, FALSE),
    ('Xbox Series X', 'Xbox Series X konsol', 6800, gamer_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- Büyük Ekipmanlar
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Gaming PC Entry', 'Gaming PC Entry seviye', 5000, gamer_cat_id, 999, TRUE, FALSE),
    ('Gaming PC Mid', 'Gaming PC Mid seviye', 8000, gamer_cat_id, 999, TRUE, FALSE),
    ('Gaming PC Ultra', 'Gaming PC Ultra seviye', 15000, gamer_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
END $$;

-- ============================================
-- 10. TEKNOLOJİ ÜRÜNLERİ
-- ============================================

DO $$
DECLARE
    teknoloji_cat_id INTEGER;
BEGIN
    SELECT id INTO teknoloji_cat_id FROM market_categories WHERE name = 'Teknoloji Ürünleri';
    
    -- AirPods
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('AirPods Pro 2', 'Apple AirPods Pro 2', 5000, teknoloji_cat_id, 999, TRUE, FALSE),
    ('AirPods Max', 'Apple AirPods Max', 7000, teknoloji_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- Apple Watch
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Apple Watch Series 9', 'Apple Watch Series 9', 6500, teknoloji_cat_id, 999, TRUE, FALSE),
    ('Apple Watch Ultra 2', 'Apple Watch Ultra 2', 9000, teknoloji_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- Samsung
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Samsung Galaxy S24', 'Samsung Galaxy S24', 9000, teknoloji_cat_id, 999, TRUE, FALSE),
    ('Samsung Galaxy S24+', 'Samsung Galaxy S24+', 11000, teknoloji_cat_id, 999, TRUE, FALSE),
    ('Samsung Galaxy S24 Ultra', 'Samsung Galaxy S24 Ultra', 14000, teknoloji_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- TV'ler
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('Smart TV 55" 4K', 'Smart TV 55" 4K', 7500, teknoloji_cat_id, 999, TRUE, FALSE),
    ('Smart TV 65" 4K', 'Smart TV 65" 4K', 10000, teknoloji_cat_id, 999, TRUE, FALSE),
    ('Smart TV 75" 4K', 'Smart TV 75" 4K', 14000, teknoloji_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- iPhone 17
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('iPhone 17 128GB', 'Apple iPhone 17 128GB', 12000, teknoloji_cat_id, 999, TRUE, FALSE),
    ('iPhone 17 256GB', 'Apple iPhone 17 256GB', 13000, teknoloji_cat_id, 999, TRUE, FALSE),
    ('iPhone 17 512GB', 'Apple iPhone 17 512GB', 14500, teknoloji_cat_id, 999, TRUE, FALSE),
    ('iPhone 17 Pro 256GB', 'Apple iPhone 17 Pro 256GB', 15000, teknoloji_cat_id, 999, TRUE, FALSE),
    ('iPhone 17 Pro 512GB', 'Apple iPhone 17 Pro 512GB', 15000, teknoloji_cat_id, 999, TRUE, FALSE),
    ('iPhone 17 Pro Max 256GB', 'Apple iPhone 17 Pro Max 256GB', 15000, teknoloji_cat_id, 999, TRUE, FALSE),
    ('iPhone 17 Pro Max 512GB', 'Apple iPhone 17 Pro Max 512GB', 15000, teknoloji_cat_id, 999, TRUE, FALSE),
    ('iPhone 17 Pro Max 1TB', 'Apple iPhone 17 Pro Max 1TB', 15000, teknoloji_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
    
    -- MacBook
    INSERT INTO market_products (name, description, price, category_id, stock, is_active, auto_delivery)
    VALUES 
    ('MacBook Air M3', 'Apple MacBook Air M3', 11000, teknoloji_cat_id, 999, TRUE, FALSE),
    ('MacBook Air M3 15"', 'Apple MacBook Air M3 15"', 12500, teknoloji_cat_id, 999, TRUE, FALSE),
    ('MacBook Pro M3', 'Apple MacBook Pro M3', 13500, teknoloji_cat_id, 999, TRUE, FALSE),
    ('MacBook Pro M3 Max', 'Apple MacBook Pro M3 Max', 15000, teknoloji_cat_id, 999, TRUE, FALSE)
    ON CONFLICT DO NOTHING;
END $$;

-- ============================================
-- SON KONTROL
-- ============================================

-- Toplam ürün sayısını kontrol et
SELECT 
    c.name as kategori,
    COUNT(p.id) as urun_sayisi
FROM market_categories c
LEFT JOIN market_products p ON p.category_id = c.id AND p.is_active = TRUE
WHERE c.is_active = TRUE
GROUP BY c.name
ORDER BY c.display_order;

-- Toplam aktif ürün sayısı
SELECT COUNT(*) as toplam_aktif_urun FROM market_products WHERE is_active = TRUE;

