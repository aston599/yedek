-- 🗑️ TÜM MARKET VERİLERİNİ TEMİZLE
-- Bu script tüm ürünleri ve kategorileri siler

-- 1. Tüm siparişleri sil (foreign key)
DELETE FROM market_orders;

-- 2. Tüm ürünleri sil
DELETE FROM market_products;

-- 3. Tüm kategorileri sil
DELETE FROM market_categories;

-- 4. Sequence'leri sıfırla
ALTER SEQUENCE IF EXISTS market_categories_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS market_products_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS market_orders_id_seq RESTART WITH 1;

-- ✅ Market tamamen temizlendi!





