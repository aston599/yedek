-- =============================================
-- SİTE YÖNETİM SİSTEMİ - DATABASE TABLO
-- =============================================

-- Sites tablosu oluştur
CREATE TABLE IF NOT EXISTS sites (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    url VARCHAR(500) NOT NULL,
    description TEXT,
    icon VARCHAR(10) DEFAULT '🌐',
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Öncelik indexi (hızlı sıralama için)
CREATE INDEX IF NOT EXISTS idx_sites_priority ON sites(priority DESC, id);
CREATE INDEX IF NOT EXISTS idx_sites_active ON sites(is_active);

-- Örnek siteler ekle (isteğe bağlı)
INSERT INTO sites (name, url, description, icon, priority, is_active) VALUES
('Mersobahis', 'https://t2m.io/mersokirvehub', 'Güvenilir bahis sitesi', '🎰', 100, true),
('AMG Bahis', 'https://t2m.io/amgkirve', 'Premium bahis deneyimi', '🎲', 90, true),
('Site 3', 'https://example3.com', 'Üçüncü site', '🎯', 80, true)
ON CONFLICT (name) DO NOTHING;

-- Trigger: updated_at otomatik güncelleme
CREATE OR REPLACE FUNCTION update_sites_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sites_updated_at_trigger
    BEFORE UPDATE ON sites
    FOR EACH ROW
    EXECUTE FUNCTION update_sites_updated_at();

-- Başarı mesajı
SELECT 'Sites tablosu başarıyla oluşturuldu!' as status;
SELECT COUNT(*) as toplam_site FROM sites;


