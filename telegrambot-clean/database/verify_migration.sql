-- ============================================================================
-- MİGRATİON DOĞRULAMA SCRIPT
-- ============================================================================
-- Bu script migration'ın başarılı olup olmadığını kontrol eder
-- ============================================================================

-- ============================================================================
-- 1. GENEL İSTATİSTİKLER
-- ============================================================================

SELECT 
    'MİGRATİON ÖNCESİ' as durum,
    COUNT(*) as toplam_kullanici,
    COUNT(*) FILTER (WHERE kirve_points > 0) as aktif_kullanici,
    SUM(kirve_points) as toplam_puan,
    AVG(kirve_points) FILTER (WHERE kirve_points > 0) as ortalama_puan,
    MAX(kirve_points) as max_puan,
    MIN(kirve_points) FILTER (WHERE kirve_points > 0) as min_puan
FROM users_backup_kirve_point_migration
WHERE kirve_points > 0

UNION ALL

SELECT 
    'MİGRATİON SONRASI' as durum,
    COUNT(*) as toplam_kullanici,
    COUNT(*) FILTER (WHERE kirve_points > 0) as aktif_kullanici,
    SUM(kirve_points) as toplam_puan,
    AVG(kirve_points) FILTER (WHERE kirve_points > 0) as ortalama_puan,
    MAX(kirve_points) as max_puan,
    MIN(kirve_points) FILTER (WHERE kirve_points > 0) as min_puan
FROM users
WHERE kirve_points > 0;

-- ============================================================================
-- 2. MULTİPLİER DAĞILIMI
-- ============================================================================

SELECT 
    CASE 
        WHEN multiplier BETWEEN 3.0 AND 3.5 THEN '3.0x - 3.5x'
        WHEN multiplier BETWEEN 3.5 AND 4.0 THEN '3.5x - 4.0x'
        WHEN multiplier BETWEEN 4.0 AND 4.5 THEN '4.0x - 4.5x'
        WHEN multiplier BETWEEN 4.5 AND 5.0 THEN '4.5x - 5.0x'
        ELSE 'Diğer (' || multiplier::TEXT || 'x)'
    END as multiplier_range,
    COUNT(*) as kullanici_sayisi,
    ROUND(AVG(multiplier)::NUMERIC, 2) as ortalama_multiplier,
    ROUND(MIN(multiplier)::NUMERIC, 2) as min_multiplier,
    ROUND(MAX(multiplier)::NUMERIC, 2) as max_multiplier
FROM (
    SELECT 
        u.user_id,
        CASE 
            WHEN b.kirve_points > 0 THEN u.kirve_points / b.kirve_points
            ELSE 0
        END as multiplier
    FROM users u
    JOIN users_backup_kirve_point_migration b ON u.user_id = b.user_id
    WHERE b.kirve_points > 0
) as multipliers
GROUP BY multiplier_range
ORDER BY multiplier_range;

-- ============================================================================
-- 3. AKTİVİTE BAZLI ANALİZ
-- ============================================================================

SELECT 
    CASE 
        WHEN b.total_messages > 1000 THEN 'Çok Aktif (1000+ mesaj)'
        WHEN b.total_messages > 500 THEN 'Aktif (500-1000 mesaj)'
        WHEN b.total_messages > 100 THEN 'Orta (100-500 mesaj)'
        ELSE 'Pasif (<100 mesaj)'
    END as aktivite_seviyesi,
    COUNT(*) as kullanici_sayisi,
    ROUND(AVG(u.kirve_points / NULLIF(b.kirve_points, 0))::NUMERIC, 2) as ortalama_multiplier,
    ROUND(SUM(b.kirve_points)::NUMERIC, 2) as toplam_puan_once,
    ROUND(SUM(u.kirve_points)::NUMERIC, 2) as toplam_puan_sonra,
    ROUND((SUM(u.kirve_points) - SUM(b.kirve_points))::NUMERIC, 2) as artis_miktari
FROM users u
JOIN users_backup_kirve_point_migration b ON u.user_id = b.user_id
WHERE b.kirve_points > 0
GROUP BY aktivite_seviyesi
ORDER BY 
    CASE aktivite_seviyesi
        WHEN 'Çok Aktif (1000+ mesaj)' THEN 1
        WHEN 'Aktif (500-1000 mesaj)' THEN 2
        WHEN 'Orta (100-500 mesaj)' THEN 3
        ELSE 4
    END;

-- ============================================================================
-- 4. SİSTEM AYARLARI KONTROLÜ
-- ============================================================================

SELECT 
    'ÖNCESİ' as durum,
    points_per_message,
    daily_limit,
    weekly_limit,
    updated_at
FROM system_settings_backup_kirve_point_migration
WHERE id = 1

UNION ALL

SELECT 
    'SONRASI' as durum,
    points_per_message,
    daily_limit,
    weekly_limit,
    updated_at
FROM system_settings
WHERE id = 1;

-- ============================================================================
-- 5. HATA KONTROLÜ (Negatif bakiye, çok yüksek bakiye, vb.)
-- ============================================================================

-- Negatif bakiye kontrolü
SELECT 
    'NEGATİF BAKİYE' as hata_tipi,
    COUNT(*) as sayi,
    ARRAY_AGG(user_id) as kullanici_idleri
FROM users
WHERE kirve_points < 0;

-- Çok yüksek bakiye kontrolü (100K üzeri)
SELECT 
    'ÇOK YÜKSEK BAKİYE (>100K)' as hata_tipi,
    COUNT(*) as sayi,
    ARRAY_AGG(user_id) as kullanici_idleri
FROM users
WHERE kirve_points > 100000;

-- Multiplier anormallikleri (3.0-5.0 dışı)
SELECT 
    'ANORMAL MULTİPLİER' as hata_tipi,
    COUNT(*) as sayi,
    ARRAY_AGG(u.user_id) as kullanici_idleri
FROM users u
JOIN users_backup_kirve_point_migration b ON u.user_id = b.user_id
WHERE b.kirve_points > 0
  AND (u.kirve_points / NULLIF(b.kirve_points, 0)) NOT BETWEEN 3.0 AND 5.0;

-- ============================================================================
-- 6. MİGRATİON LOG KONTROLÜ
-- ============================================================================

SELECT 
    migration_name,
    migration_date,
    affected_users,
    total_points_before,
    total_points_after,
    ROUND(((total_points_after - total_points_before) / NULLIF(total_points_before, 0) * 100)::NUMERIC, 2) as yuzde_artis,
    status,
    notes
FROM migration_logs
WHERE migration_name LIKE 'kirve_point_migration%'
ORDER BY migration_date DESC
LIMIT 5;

-- ============================================================================
-- DOĞRULAMA TAMAMLANDI
-- ============================================================================
-- Tüm kontroller başarılıysa migration başarılıdır
-- Hata varsa rollback script'ini kullanın
-- ============================================================================

