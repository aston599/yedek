-- Market Ürünleri Kontrol Sorgusu

-- Toplam ürün sayısı
SELECT 
    'Toplam Ürün' as bilgi,
    COUNT(*) as sayi
FROM market_products;

-- Aktif ürün sayısı
SELECT 
    'Aktif Ürün' as bilgi,
    COUNT(*) as sayi
FROM market_products
WHERE is_active = TRUE;

-- Pasif ürün sayısı
SELECT 
    'Pasif Ürün' as bilgi,
    COUNT(*) as sayi
FROM market_products
WHERE is_active = FALSE;

-- Kategorilere göre ürün dağılımı
SELECT 
    c.name as kategori,
    COUNT(p.id) as toplam_urun,
    COUNT(CASE WHEN p.is_active = TRUE THEN 1 END) as aktif_urun,
    SUM(p.stock) as toplam_stok
FROM market_categories c
LEFT JOIN market_products p ON p.category_id = c.id
WHERE c.is_active = TRUE
GROUP BY c.id, c.name
ORDER BY c.name;

-- Aktif ürünlerin detaylı listesi
SELECT 
    p.id,
    p.name as urun_adi,
    c.name as kategori,
    p.company_name as sirket,
    p.site_name as site,
    p.price as fiyat,
    p.stock as stok,
    p.sold_count as satilan,
    p.site_link as link,
    p.external_link as external_link,
    p.site_requirement as gereksinim
FROM market_products p
LEFT JOIN market_categories c ON c.id = p.category_id
WHERE p.is_active = TRUE
ORDER BY c.name, p.name;

-- Stok durumu
SELECT 
    'Düşük Stok (<5)' as durum,
    COUNT(*) as sayi
FROM market_products
WHERE is_active = TRUE AND stock < 5 AND stock >= 0;

SELECT 
    'Stokta Yok' as durum,
    COUNT(*) as sayi
FROM market_products
WHERE is_active = TRUE AND stock = 0;


