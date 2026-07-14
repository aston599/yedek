-- 🔧 Database Constraint Düzeltme Script'i
-- Foreign key ve unique constraint hatalarını düzelt

-- 1. Events tablosundaki foreign key constraint'ini düzelt
DO $$
BEGIN
    -- Eğer events tablosu varsa ve created_by kolonu varsa
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'events'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'events' AND column_name = 'created_by'
    ) THEN
        -- Foreign key constraint'i kaldır (eğer varsa)
        BEGIN
            ALTER TABLE events DROP CONSTRAINT IF EXISTS events_created_by_fkey;
        EXCEPTION
            WHEN OTHERS THEN
                -- Constraint yoksa hata verme
                NULL;
        END;
        
        -- Yeni foreign key constraint ekle (CASCADE ile)
        ALTER TABLE events ADD CONSTRAINT events_created_by_fkey 
        FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE CASCADE;
    END IF;
END $$;

-- 2. Daily stats unique constraint'ini düzelt
DO $$
BEGIN
    -- Eğer constraint varsa kaldır
    BEGIN
        ALTER TABLE daily_stats DROP CONSTRAINT IF EXISTS daily_stats_unique;
    EXCEPTION
        WHEN OTHERS THEN
            NULL;
    END;
    
    -- Yeni constraint ekle (ON CONFLICT DO NOTHING ile)
    ALTER TABLE daily_stats ADD CONSTRAINT daily_stats_unique 
    UNIQUE(user_id, group_id, message_date);
END $$;

-- 3. Duplicate kayıtları temizle
DELETE FROM daily_stats 
WHERE id NOT IN (
    SELECT MIN(id) 
    FROM daily_stats 
    GROUP BY user_id, group_id, message_date
);

-- 4. Index'leri yeniden oluştur
REINDEX INDEX CONCURRENTLY IF EXISTS idx_daily_stats_user_date;
REINDEX INDEX CONCURRENTLY IF EXISTS idx_daily_stats_group_date;

-- 5. VACUUM ve ANALYZE
VACUUM ANALYZE daily_stats;
VACUUM ANALYZE events;

-- 6. Migration tamamlandı log'u
INSERT INTO system_logs (log_level, message, details) 
VALUES ('INFO', 'Database constraints fixed', 'Foreign key and unique constraints updated successfully'); 