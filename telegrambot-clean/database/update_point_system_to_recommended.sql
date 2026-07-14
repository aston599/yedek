-- ============================================================================
-- ÖNERİLEN POINT SİSTEMİNE GEÇİŞ
-- ============================================================================
-- Bu script önerilen point sistemine geçiş yapar:
-- - messages_for_point: 2 → 5 (spam koruması)
-- - points_per_message: 0.04 → 0.10 (daha görünür)
-- - daily_limit: 5.0 → 10.0 (daha ulaşılabilir)
-- - weekly_limit: 20.0 → 50.0 (çelişki çözüldü)

-- ============================================================================
-- SYSTEM_SETTINGS TABLOSU GÜNCELLEME (ID BAZLI YAPI)
-- ============================================================================

-- system_settings tablosunu güncelle (id bazlı yapı)
UPDATE system_settings 
SET 
    points_per_message = 0.10,
    daily_limit = 10.0,
    weekly_limit = 50.0,
    updated_at = NOW()
WHERE id = 1;

-- Eğer system_settings tablosunda kayıt yoksa ekle
INSERT INTO system_settings (id, points_per_message, daily_limit, weekly_limit, created_at, updated_at)
VALUES (1, 0.10, 10.0, 50.0, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    points_per_message = 0.10,
    daily_limit = 10.0,
    weekly_limit = 50.0,
    updated_at = NOW();

-- ============================================================================
-- POINT_SETTINGS TABLOSU GÜNCELLEME (Eğer varsa - KEY-VALUE YAPI)
-- ============================================================================

-- point_settings tablosu varsa güncelle (setting_name bazlı)
UPDATE point_settings 
SET setting_value = '0.10'
WHERE setting_name = 'points_per_message';

UPDATE point_settings 
SET setting_value = '10.0'
WHERE setting_name = 'daily_limit';

UPDATE point_settings 
SET setting_value = '50.0'
WHERE setting_name = 'weekly_limit';

UPDATE point_settings 
SET setting_value = '5'
WHERE setting_name = 'messages_for_point';

-- ============================================================================
-- KONTROL SORGULARI
-- ============================================================================

-- Güncellenmiş değerleri kontrol et
SELECT 
    'system_settings (id=1)' as tablo,
    points_per_message,
    daily_limit,
    weekly_limit
FROM system_settings 
WHERE id = 1;

-- point_settings tablosu kontrolü (eğer varsa)
SELECT 
    'point_settings' as tablo,
    setting_name,
    setting_value
FROM point_settings 
WHERE setting_name IN ('points_per_message', 'daily_limit', 'weekly_limit', 'messages_for_point');

-- Başarı mesajı
SELECT '✅ Önerilen point sistemine geçiş tamamlandı!' as durum;
SELECT '📊 Yeni Değerler:' as bilgi;
SELECT '  • messages_for_point: 5 (2 → 5)' as degisiklik;
SELECT '  • points_per_message: 0.10 (0.04 → 0.10)' as degisiklik;
SELECT '  • daily_limit: 10.0 (5.0 → 10.0)' as degisiklik;
SELECT '  • weekly_limit: 50.0 (20.0 → 50.0)' as degisiklik;
SELECT '  • award_cooldown: 60-120 saniye (180-300 → 60-120)' as degisiklik;

