-- ============================================================================
-- GERCEK FIYAT GUNCELLEME
-- Turkiye 2025 fiyatlari | Kazanma zorluguna optimize
-- ============================================================================

-- ADIM 1: Site bakiyelerini guncelle (1 KP = 2 TL)
-- ============================================================================

UPDATE market_products SET price = 25 WHERE product_name LIKE '%50 TL%Bakiye%';
UPDATE market_products SET price = 50 WHERE product_name LIKE '%100 TL%Bakiye%';
UPDATE market_products SET price = 125 WHERE product_name LIKE '%250 TL%Bakiye%';
UPDATE market_products SET price = 250 WHERE product_name LIKE '%500 TL%Bakiye%';
UPDATE market_products SET price = 500 WHERE product_name LIKE '%1000 TL%Bakiye%';
UPDATE market_products SET price = 1250 WHERE product_name LIKE '%2500 TL%Bakiye%';

-- ADIM 2: Nakit cekimleri guncelle (1 KP = 1.4 TL)
-- ============================================================================

UPDATE market_products SET price = 70 WHERE product_name LIKE '%50 TL%Nakit%';
UPDATE market_products SET price = 140 WHERE product_name LIKE '%100 TL%Nakit%';
UPDATE market_products SET price = 350 WHERE product_name LIKE '%250 TL%Nakit%';
UPDATE market_products SET price = 710 WHERE product_name LIKE '%500 TL%Nakit%';
UPDATE market_products SET price = 1400 WHERE product_name LIKE '%1000 TL%Nakit%';
UPDATE market_products SET price = 3500 WHERE product_name LIKE '%2500 TL%Nakit%';

-- ADIM 3: Gaming kodlarini guncelle (1 KP = 1.2 TL)
-- ============================================================================

-- Steam/PSN/Xbox kodlari
UPDATE market_products SET price = 85 
WHERE (product_name LIKE '%Steam%' OR product_name LIKE '%PSN%' OR product_name LIKE '%Xbox%' OR product_name LIKE '%PlayStation Store%')
  AND product_name LIKE '%50 TL%';

UPDATE market_products SET price = 170 
WHERE (product_name LIKE '%Steam%' OR product_name LIKE '%PSN%' OR product_name LIKE '%Xbox%' OR product_name LIKE '%PlayStation Store%')
  AND product_name LIKE '%100 TL%';

UPDATE market_products SET price = 420 
WHERE (product_name LIKE '%Steam%' OR product_name LIKE '%PSN%' OR product_name LIKE '%Xbox%' OR product_name LIKE '%PlayStation Store%')
  AND product_name LIKE '%250 TL%';

UPDATE market_products SET price = 850 
WHERE (product_name LIKE '%Steam%' OR product_name LIKE '%PSN%' OR product_name LIKE '%Xbox%' OR product_name LIKE '%PlayStation Store%')
  AND product_name LIKE '%500 TL%';

-- Abonelikler
UPDATE market_products SET price = 1200 WHERE product_name LIKE '%PlayStation Plus%12%';
UPDATE market_products SET price = 1300 WHERE product_name LIKE '%Xbox Game Pass%12%';

-- ADIM 4: Hediye kartlarini guncelle (1 KP = 1.2 TL)
-- ============================================================================

UPDATE market_products SET price = 85 
WHERE (product_name LIKE '%Amazon%' OR product_name LIKE '%Google Play%' OR product_name LIKE '%App Store%')
  AND product_name LIKE '%50 TL%';

UPDATE market_products SET price = 170 
WHERE (product_name LIKE '%Amazon%' OR product_name LIKE '%Google Play%' OR product_name LIKE '%App Store%')
  AND product_name LIKE '%100 TL%';

UPDATE market_products SET price = 420 
WHERE (product_name LIKE '%Amazon%' OR product_name LIKE '%Google Play%' OR product_name LIKE '%App Store%')
  AND product_name LIKE '%250 TL%';

UPDATE market_products SET price = 850 
WHERE (product_name LIKE '%Amazon%' OR product_name LIKE '%Google Play%' OR product_name LIKE '%App Store%')
  AND product_name LIKE '%500 TL%';

UPDATE market_products SET price = 1700 
WHERE (product_name LIKE '%Amazon%' OR product_name LIKE '%Google Play%' OR product_name LIKE '%App Store%')
  AND product_name LIKE '%1000 TL%';

-- ADIM 5: Streaming aylik (1 KP = 0.8 TL)
-- ============================================================================

UPDATE market_products SET price = 125 WHERE product_name LIKE '%Netflix%1 Ekran%' AND product_name LIKE '%1 ay%';
UPDATE market_products SET price = 210 WHERE product_name LIKE '%Netflix%4 Ekran%' AND product_name LIKE '%1 ay%';
UPDATE market_products SET price = 70 WHERE product_name LIKE '%Spotify%' AND product_name LIKE '%1 ay%';
UPDATE market_products SET price = 60 WHERE product_name LIKE '%YouTube%' AND product_name LIKE '%1 ay%';

-- ADIM 6: Streaming yillik (1 KP = 1.0 TL)
-- ============================================================================

UPDATE market_products SET price = 2000 WHERE product_name LIKE '%Netflix%12 ay%';
UPDATE market_products SET price = 650 WHERE product_name LIKE '%Spotify%12 ay%';
UPDATE market_products SET price = 560 WHERE product_name LIKE '%YouTube%12 ay%';
UPDATE market_products SET price = 1400 WHERE product_name LIKE '%Disney%12 ay%';

-- ADIM 7: Yuksek degerli urunler (1 KP = 12 TL)
-- ============================================================================

-- Apple
UPDATE market_products SET price = 1050 WHERE product_name LIKE '%AirPods Pro 2%';
UPDATE market_products SET price = 1350 WHERE product_name LIKE '%Apple Watch%Series 9%';
UPDATE market_products SET price = 4000 WHERE product_name LIKE '%iPhone 16%' AND product_name LIKE '%128GB%';
UPDATE market_products SET price = 6000 WHERE product_name LIKE '%iPhone 16 Pro%' AND product_name LIKE '%256GB%';
UPDATE market_products SET price = 7900 WHERE product_name LIKE '%iPhone 16 Pro Max%' AND product_name LIKE '%512GB%';
UPDATE market_products SET price = 4350 WHERE product_name LIKE '%MacBook Air M3%';

-- Gaming Konsollar
UPDATE market_products SET price = 1150 WHERE product_name LIKE '%Nintendo Switch%OLED%';
UPDATE market_products SET price = 1500 WHERE product_name LIKE '%PlayStation 5 Digital%';
UPDATE market_products SET price = 1750 WHERE product_name LIKE '%PlayStation 5%Disk%';
UPDATE market_products SET price = 1750 WHERE product_name LIKE '%PlayStation 5%' AND product_name NOT LIKE '%Digital%';
UPDATE market_products SET price = 1600 WHERE product_name LIKE '%Xbox Series X%';

-- Gaming Ekipman
UPDATE market_products SET price = 1350 WHERE product_name LIKE '%Gaming Monitor%27%';
UPDATE market_products SET price = 3750 WHERE product_name LIKE '%Gaming Laptop%RTX 4060%';
UPDATE market_products SET price = 5400 WHERE product_name LIKE '%Gaming Laptop%RTX 4070%';
UPDATE market_products SET price = 4200 WHERE product_name LIKE '%Gaming PC%Mid%';
UPDATE market_products SET price = 6700 WHERE product_name LIKE '%Gaming PC%High%';

-- TV & Ekran
UPDATE market_products SET price = 1900 WHERE product_name LIKE '%55%4K%Smart TV%';
UPDATE market_products SET price = 2900 WHERE product_name LIKE '%65%4K%Smart TV%';

-- ADIM 8: Canli yayin bonus
-- ============================================================================

UPDATE market_products SET price = 500 WHERE product_name LIKE '%Bonus Buy%1000 TL%';
UPDATE market_products SET price = 1250 WHERE product_name LIKE '%Bonus Buy%2500 TL%';
UPDATE market_products SET price = 2500 WHERE product_name LIKE '%Bonus Buy%5000 TL%';

-- ADIM 9: Tum urunleri aktif yap
-- ============================================================================

UPDATE market_products 
SET is_active = true, 
    is_available = true
WHERE stock > 0;

-- ============================================================================
-- KONTROL
-- ============================================================================

-- Kategori bazli fiyat dagilimi
SELECT 
    c.name as kategori,
    COUNT(p.id) as urun_sayisi,
    MIN(p.price) as en_ucuz,
    MAX(p.price) as en_pahali,
    AVG(p.price)::INTEGER as ortalama_fiyat
FROM market_categories c
LEFT JOIN market_products p ON p.category_id = c.id AND p.is_active = true
WHERE p.id IS NOT NULL
GROUP BY c.id, c.name
ORDER BY AVG(p.price);

-- Fiyat segmentleri
SELECT 
    CASE 
        WHEN price BETWEEN 0 AND 200 THEN 'Hizli (0-200 KP)'
        WHEN price BETWEEN 200 AND 500 THEN 'Populer (200-500 KP)'
        WHEN price BETWEEN 500 AND 1500 THEN 'Orta (500-1500 KP)'
        WHEN price BETWEEN 1500 AND 4000 THEN 'Yuksek (1500-4000 KP)'
        ELSE 'Ultra (4000+ KP)'
    END as segment,
    COUNT(*) as urun_sayisi,
    MIN(price) as min_kp,
    MAX(price) as max_kp
FROM market_products
WHERE is_active = true
GROUP BY segment
ORDER BY MIN(price);

-- Toplam urun
SELECT COUNT(*) as toplam_aktif_urun FROM market_products WHERE is_active = true;

-- En populer urunler (ucuz ve stoklu)
SELECT 
    product_name,
    price,
    stock,
    site_name
FROM market_products
WHERE is_active = true AND stock > 0
ORDER BY price, stock DESC
LIMIT 15;






