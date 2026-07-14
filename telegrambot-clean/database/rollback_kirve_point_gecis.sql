-- ============================================================================
-- KIRVE POINT GEÇİŞ ROLLBACK SCRIPT
-- ============================================================================
-- Bu script migration'ı geri alır (hata durumunda)
-- ÖNEMLİ: Bu script'i sadece hata durumunda kullanın!
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. KULLANICI BAKİYELERİNİ GERİ YÜKLE
-- ============================================================================

UPDATE users u
SET 
    kirve_points = b.kirve_points,
    daily_points = b.daily_points,
    updated_at = b.backup_date
FROM users_backup_kirve_point_migration b
WHERE u.user_id = b.user_id;

-- ============================================================================
-- 2. SİSTEM AYARLARINI GERİ YÜKLE
-- ============================================================================

UPDATE system_settings s
SET 
    points_per_message = b.points_per_message,
    daily_limit = b.daily_limit,
    weekly_limit = b.weekly_limit,
    updated_at = b.updated_at
FROM system_settings_backup_kirve_point_migration b
WHERE s.id = b.id;

-- Eğer system_settings tablosunda kayıt yoksa yedekten ekle
INSERT INTO system_settings (
    id, points_per_message, daily_limit, weekly_limit, created_at, updated_at
)
SELECT 
    id, points_per_message, daily_limit, weekly_limit, created_at, updated_at
FROM system_settings_backup_kirve_point_migration
ON CONFLICT (id) DO UPDATE SET
    points_per_message = EXCLUDED.points_per_message,
    daily_limit = EXCLUDED.daily_limit,
    weekly_limit = EXCLUDED.weekly_limit,
    updated_at = EXCLUDED.updated_at;

-- ============================================================================
-- 3. ROLLBACK LOG
-- ============================================================================

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
    'kirve_point_migration_v1_rollback',
    COUNT(*),
    SUM(kirve_points) FILTER (WHERE kirve_points > 0),
    (SELECT SUM(kirve_points) FROM users WHERE kirve_points > 0),
    jsonb_build_object(
        'rollback_date', NOW(),
        'rollback_reason', 'Migration hatası - Geri alındı'
    ),
    'rolled_back',
    'Migration geri alındı - Yedeklerden restore edildi'
FROM users_backup_kirve_point_migration
WHERE kirve_points > 0;

-- ============================================================================
-- 4. ENDEKSELEME FONKSİYONUNU KALDIR (Opsiyonel)
-- ============================================================================

DROP FUNCTION IF EXISTS calculate_migration_multiplier(
    DECIMAL, INTEGER, TIMESTAMP, INTEGER
);

COMMIT;

-- ============================================================================
-- ROLLBACK TAMAMLANDI
-- ============================================================================
-- Sistem eski haline döndürüldü
-- Yedek tablolar silinmedi (güvenlik için)
-- ============================================================================

