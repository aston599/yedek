-- =============================================
-- SİTE BAKİYELERİ İÇİN KULLANICI ADI ALANI
-- =============================================
-- Tarih: 2025-01-XX
-- Amaç: Site bakiyeleri siparişlerinde kullanıcı adı belirtme özelliği

-- 1. market_orders tablosuna site_username kolonu ekle
ALTER TABLE market_orders 
ADD COLUMN IF NOT EXISTS site_username VARCHAR(255) DEFAULT NULL;

-- 2. Kolon açıklaması (PostgreSQL comment)
COMMENT ON COLUMN market_orders.site_username IS 'Site bakiyeleri için kullanıcı adı (opsiyonel)';

-- 3. Index ekle (sipariş sorgularında performans için)
CREATE INDEX IF NOT EXISTS idx_market_orders_site_username 
ON market_orders(site_username) 
WHERE site_username IS NOT NULL;

-- ✅ Kolon başarıyla eklendi!






