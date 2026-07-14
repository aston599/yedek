-- 🛍️ AKTİF MARKET ÜRÜNLERİ LİSTESİ

-- Tüm aktif ürünlerin detaylı listesi
SELECT 
    p.id,
    p.name as "Ürün Adı",
    c.name as "Kategori",
    p.company_name as "Şirket",
    p.site_name as "Site",
    p.price as "Fiyat (KP)",
    p.stock as "Stok",
    p.site_link as "Site Linki",
    p.description as "Açıklama",
    p.created_at as "Oluşturulma Tarihi"
FROM market_products p
LEFT JOIN market_categories c ON c.id = p.category_id
WHERE p.is_active = TRUE
ORDER BY c.name, p.name;

-- Özet bilgiler
SELECT 
    '=== ÖZET ===' as bilgi,
    COUNT(*) as "Toplam Aktif Ürün"
FROM market_products
WHERE is_active = TRUE;

-- Kategorilere göre dağılım
SELECT 
    c.name as "Kategori",
    COUNT(p.id) as "Ürün Sayısı",
    SUM(p.stock) as "Toplam Stok"
FROM market_categories c
LEFT JOIN market_products p ON p.category_id = c.id AND p.is_active = TRUE
WHERE c.is_active = TRUE
GROUP BY c.id, c.name
ORDER BY c.name;

-- Stok durumu
SELECT 
    CASE 
        WHEN stock = 0 THEN 'Stokta Yok'
        WHEN stock < 5 THEN 'Düşük Stok'
        ELSE 'Normal Stok'
    END as "Stok Durumu",
    COUNT(*) as "Ürün Sayısı"
FROM market_products
WHERE is_active = TRUE
GROUP BY 
    CASE 
        WHEN stock = 0 THEN 'Stokta Yok'
        WHEN stock < 5 THEN 'Düşük Stok'
        ELSE 'Normal Stok'
    END;

