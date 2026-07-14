-- ============================================================================
-- KIRVE POINT GEÇİŞ MİGRATİON SCRIPT
-- ============================================================================
-- Bu script:
-- 1. Mevcut kullanıcı bakiyelerini endeksler (hibrit sistem)
-- 2. Yeni puan ayarlarını günceller
-- 3. Güvenli migration sağlar (backup, rollback)
--
-- ÖNEMLİ: Bu script'i çalıştırmadan önce database yedeği alın!
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. BACKUP TABLES (Güvenlik için)
-- ============================================================================

-- Mevcut bakiyeleri yedekle
CREATE TABLE IF NOT EXISTS users_backup_kirve_point_migration AS
SELECT 
    user_id,
    kirve_points,
    daily_points,
    total_messages,
    last_point_date,
    rank_id,
    last_activity,
    NOW() as backup_date
FROM users;

-- Sistem ayarlarını yedekle
CREATE TABLE IF NOT EXISTS system_settings_backup_kirve_point_migration AS
SELECT * FROM system_settings;

COMMENT ON TABLE users_backup_kirve_point_migration IS 'Kirve Point geçiş öncesi kullanıcı bakiyeleri yedeği';
COMMENT ON TABLE system_settings_backup_kirve_point_migration IS 'Kirve Point geçiş öncesi sistem ayarları yedeği';

-- ============================================================================
-- 2. YENİ PUAN AYARLARI (Sistem Ayarları)
-- ============================================================================
-- Seçenek A: Orta Seviye (ÖNERİLEN)
-- - Mesaj başına: 0.04 → 0.20 (5x artış)
-- - Günlük limit: 5.00 → 200.00 (40x artış)
-- - Haftalık limit: 20.00 → 1000.00 (50x artış)

-- Seçenek B: Yüksek Seviye
-- - Mesaj başına: 0.04 → 0.50 (12.5x artış)
-- - Günlük limit: 5.00 → 500.00 (100x artış)
-- - Haftalık limit: 20.00 → 2500.00 (125x artış)

-- ŞİMDİLİK SEÇENEK A KULLANILIYOR (İSTENİRSE DEĞİŞTİRİLEBİLİR)

UPDATE system_settings 
SET 
    points_per_message = 0.20,      -- 0.04 → 0.20 (5x)
    daily_limit = 200.00,            -- 5.00 → 200.00 (40x)
    weekly_limit = 1000.00,          -- 20.00 → 1000.00 (50x)
    updated_at = NOW()
WHERE id = 1;

-- Eğer system_settings tablosunda kayıt yoksa ekle
INSERT INTO system_settings (id, points_per_message, daily_limit, weekly_limit, created_at, updated_at)
VALUES (1, 0.20, 200.00, 1000.00, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    points_per_message = 0.20,
    daily_limit = 200.00,
    weekly_limit = 1000.00,
    updated_at = NOW();

-- ============================================================================
-- 3. ENDEKSELEME: KULLANICI BAKİYELERİNİ GÜNCELLE (Hibrit Sistem)
-- ============================================================================

-- Endeksleme fonksiyonu (PostgreSQL function)
CREATE OR REPLACE FUNCTION calculate_migration_multiplier(
    p_kirve_points DECIMAL,
    p_total_messages INTEGER,
    p_last_activity TIMESTAMP,
    p_rank_id INTEGER
) RETURNS DECIMAL AS $$
DECLARE
    base_multiplier DECIMAL := 3.0;  -- Minimum garantili artış
    activity_bonus DECIMAL := 0.0;
    message_bonus DECIMAL := 0.0;
    total_multiplier DECIMAL;
    days_since_activity INTEGER;
BEGIN
    -- 1. Aktivite bonusu hesapla
    -- Mesaj sayısı bonusu
    IF p_total_messages > 1000 THEN
        activity_bonus := activity_bonus + 0.5;  -- +50% (1000+ mesaj)
    ELSIF p_total_messages > 500 THEN
        activity_bonus := activity_bonus + 0.3;   -- +30% (500+ mesaj)
    ELSIF p_total_messages > 100 THEN
        activity_bonus := activity_bonus + 0.1;  -- +10% (100+ mesaj)
    END IF;
    
    -- Son aktivite bonusu (son 30 gün içinde aktif)
    IF p_last_activity IS NOT NULL THEN
        days_since_activity := EXTRACT(DAY FROM (NOW() - p_last_activity));
        IF days_since_activity <= 30 THEN
            activity_bonus := activity_bonus + 0.3;  -- +30% (son 30 gün aktif)
        ELSIF days_since_activity <= 60 THEN
            activity_bonus := activity_bonus + 0.1;   -- +10% (son 60 gün aktif)
        END IF;
    END IF;
    
    -- Rank bonusu
    IF p_rank_id >= 5 THEN
        activity_bonus := activity_bonus + 0.2;  -- +20% (yüksek rank)
    ELSIF p_rank_id >= 3 THEN
        activity_bonus := activity_bonus + 0.1;   -- +10% (orta rank)
    END IF;
    
    -- 2. Mesaj bazlı bonus (mesaj sayısına göre, max 1.0)
    message_bonus := LEAST(p_total_messages::DECIMAL / 10000.0, 1.0);
    -- 1000 mesaj = 0.1, 5000 mesaj = 0.5, 10000+ mesaj = 1.0
    
    -- 3. Toplam multiplier
    total_multiplier := base_multiplier + activity_bonus + message_bonus;
    
    -- 4. Güvenlik: Minimum 3.0, Maksimum 5.0
    total_multiplier := GREATEST(LEAST(total_multiplier, 5.0), 3.0);
    
    RETURN total_multiplier;
END;
$$ LANGUAGE plpgsql;

-- Endeksleme: Kullanıcı bakiyelerini güncelle
UPDATE users
SET 
    kirve_points = kirve_points * calculate_migration_multiplier(
        kirve_points,
        COALESCE(total_messages, 0),
        last_activity,
        COALESCE(rank_id, 1)
    ),
    -- Günlük puanları da sıfırla (yeni sistem başlayacak)
    daily_points = 0.00
    -- NOT: updated_at kolonu users tablosunda yok, kaldırıldı
WHERE kirve_points > 0 OR total_messages > 0;

-- Maksimum bakiye limiti (güvenlik)
UPDATE users
SET kirve_points = 100000.00
WHERE kirve_points > 100000.00;

-- ============================================================================
-- 4. MİGRATİON LOG TABLOSU (Takip için)
-- ============================================================================

CREATE TABLE IF NOT EXISTS migration_logs (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL,
    migration_date TIMESTAMP DEFAULT NOW(),
    affected_users INTEGER,
    total_points_before DECIMAL(15,2),
    total_points_after DECIMAL(15,2),
    multiplier_stats JSONB,
    status VARCHAR(50) DEFAULT 'completed',
    notes TEXT
);

-- Bu migration'ı logla
INSERT INTO migration_logs (
    migration_name,
    affected_users,
    total_points_before,
    total_points_after,
    multiplier_stats,
    status,
    notes
)
SELECT 
    'kirve_point_migration_v1',
    COUNT(*),
    SUM(kirve_points) FILTER (WHERE kirve_points > 0),
    NULL,  -- Migration sonrası hesaplanacak
    jsonb_build_object(
        'base_multiplier', 3.0,
        'max_multiplier', 5.0,
        'points_per_message_old', 0.04,
        'points_per_message_new', 0.20,
        'daily_limit_old', 5.00,
        'daily_limit_new', 200.00,
        'weekly_limit_old', 20.00,
        'weekly_limit_new', 1000.00
    ),
    'in_progress',
    'Hibrit endeksleme sistemi: Base 3.0x + Aktivite bonusu + Mesaj bonusu'
FROM users_backup_kirve_point_migration;

-- Migration sonrası istatistikleri güncelle
UPDATE migration_logs
SET 
    total_points_after = (SELECT SUM(kirve_points) FROM users WHERE kirve_points > 0),
    status = 'completed',
    notes = notes || ' | Migration tamamlandı: ' || NOW()::TEXT
WHERE migration_name = 'kirve_point_migration_v1' 
  AND status = 'in_progress';

-- ============================================================================
-- 5. DOĞRULAMA QUERY'LERİ (Migration sonrası kontrol)
-- ============================================================================

-- Migration öncesi/sonrası karşılaştırma
SELECT 
    'ÖNCESİ' as durum,
    COUNT(*) as kullanici_sayisi,
    SUM(kirve_points) as toplam_puan,
    AVG(kirve_points) as ortalama_puan,
    MAX(kirve_points) as max_puan,
    MIN(kirve_points) as min_puan
FROM users_backup_kirve_point_migration
WHERE kirve_points > 0

UNION ALL

SELECT 
    'SONRASI' as durum,
    COUNT(*) as kullanici_sayisi,
    SUM(kirve_points) as toplam_puan,
    AVG(kirve_points) as ortalama_puan,
    MAX(kirve_points) as max_puan,
    MIN(kirve_points) as min_puan
FROM users
WHERE kirve_points > 0;

-- Multiplier dağılımı (kaç kullanıcı hangi multiplier ile endekslendi)
SELECT 
    CASE 
        WHEN (u.kirve_points / NULLIF(b.kirve_points, 0)) BETWEEN 3.0 AND 3.5 THEN '3.0x - 3.5x'
        WHEN (u.kirve_points / NULLIF(b.kirve_points, 0)) BETWEEN 3.5 AND 4.0 THEN '3.5x - 4.0x'
        WHEN (u.kirve_points / NULLIF(b.kirve_points, 0)) BETWEEN 4.0 AND 4.5 THEN '4.0x - 4.5x'
        WHEN (u.kirve_points / NULLIF(b.kirve_points, 0)) BETWEEN 4.5 AND 5.0 THEN '4.5x - 5.0x'
        ELSE 'Diğer'
    END as multiplier_range,
    COUNT(*) as kullanici_sayisi,
    AVG(u.kirve_points / NULLIF(b.kirve_points, 0)) as ortalama_multiplier
FROM users u
JOIN users_backup_kirve_point_migration b ON u.user_id = b.user_id
WHERE b.kirve_points > 0
GROUP BY multiplier_range
ORDER BY multiplier_range;

-- ============================================================================
-- 6. ROLLBACK SCRIPT (Hata durumunda geri alma)
-- ============================================================================
-- NOT: Rollback için ayrı bir script hazırlanacak (rollback_kirve_point_gecis.sql)

-- ============================================================================
-- COMMIT (Migration tamamlandı)
-- ============================================================================

COMMIT;

-- ============================================================================
-- MİGRATİON TAMAMLANDI
-- ============================================================================
-- Sonraki adımlar:
-- 1. Doğrulama query'lerini çalıştır
-- 2. Migration loglarını kontrol et
-- 3. Test kullanıcıları ile doğrulama yap
-- 4. Production'a deploy et
-- ============================================================================

