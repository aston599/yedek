-- 🛍️ ÜRÜN EKLEME ŞABLONU
-- Bu dosyayı kopyala-düzenle ve ürünlerini ekle

-- ⚠️ ÖNEMLİ: Önce kategorileri ekle ve ID'lerini öğren!
-- SELECT id, name FROM market_categories;

-- ÖRNEK ÜRÜN EKLEMELERİ:

-- 1. Dijital Ürünler (category_id = 1)
INSERT INTO market_products (
    name, 
    description, 
    price, 
    stock, 
    category_id, 
    site_name,
    site_requirement,
    external_link,
    delivery_info,
    is_active
) VALUES
('Discord Nitro (1 ay)', 'Discord Nitro 1 aylık premium abonelik', 40, 10, 1, 'Discord', NULL, 'https://discord.com', 'Kod özel mesajdan gönderilecek', true),
('Spotify Premium (1 ay)', 'Spotify Premium 1 aylık üyelik', 70, 5, 1, 'Spotify', NULL, 'https://spotify.com', 'Hesap bilgileri özel mesajdan', true);

-- 2. Site Bakiyesi (category_id = 2)
INSERT INTO market_products (
    name, 
    description, 
    price, 
    stock, 
    category_id, 
    site_name,
    site_requirement,
    external_link,
    delivery_info,
    is_active
) VALUES
('Mersobahis 50 TL Bakiye', 'Mersobahis sitesine 50 TL bakiye yüklemesi', 25, 100, 2, 'Mersobahis', 'Mersobahis', 'https://t2m.io/mersokirvehub', 'Mersobahis kullanıcı adınızı belirtin', true),
('AMG Bahis 50 TL Bakiye', 'AMG Bahis sitesine 50 TL bakiye yüklemesi', 25, 100, 2, 'AMG Bahis', 'AMG Bahis', 'https://t2m.io/amgkirve', 'AMG Bahis kullanıcı adınızı belirtin', true);

-- 3. Nakit Çekim (category_id = 3)
INSERT INTO market_products (
    name, 
    description, 
    price, 
    stock, 
    category_id, 
    site_name,
    site_requirement,
    external_link,
    delivery_info,
    is_active
) VALUES
('50 TL Papara', 'Papara hesabınıza 50 TL gönderim', 250, 20, 3, 'Papara', NULL, NULL, 'Papara hesap numaranızı belirtin', true),
('100 TL Papara', 'Papara hesabınıza 100 TL gönderim', 500, 15, 3, 'Papara', NULL, NULL, 'Papara hesap numaranızı belirtin', true);

-- ✅ Eklenen ürünleri görmek için:
SELECT id, name, price, stock, category_id FROM market_products ORDER BY category_id, price;





