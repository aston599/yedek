-- 🔧 KRİTİK DATABASE HATALARINI DÜZELT
-- En kritik hataları tek seferde çöz

-- 1. Events foreign key constraint'ini düzelt
DO $$
BEGIN
    -- Eğer events tablosu varsa
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'events'
    ) THEN
        -- Foreign key constraint'i kaldır (eğer varsa)
        BEGIN
            ALTER TABLE events DROP CONSTRAINT IF EXISTS events_created_by_fkey;
        EXCEPTION
            WHEN OTHERS THEN
                NULL;
        END;
        
        -- Yeni foreign key constraint ekle (CASCADE ile)
        ALTER TABLE events ADD CONSTRAINT events_created_by_fkey 
        FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Events foreign key constraint düzeltildi';
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
    
    -- Duplicate kayıtları temizle
    DELETE FROM daily_stats 
    WHERE id NOT IN (
        SELECT MIN(id) 
        FROM daily_stats 
        GROUP BY user_id, group_id, message_date
    );
    
    -- Yeni constraint ekle
    ALTER TABLE daily_stats ADD CONSTRAINT daily_stats_unique 
    UNIQUE(user_id, group_id, message_date);
    
    RAISE NOTICE 'Daily stats unique constraint düzeltildi';
END $$;

-- 3. Recruitment logs tablosunu ekle (eğer yoksa)
CREATE TABLE IF NOT EXISTS recruitment_logs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    recruitment_date DATE NOT NULL,
    recruitment_type VARCHAR(50) DEFAULT 'auto',
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, recruitment_date)
);

-- 4. Rank level kolonunu ekle (eğer yoksa)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'rank_level'
    ) THEN
        ALTER TABLE users ADD COLUMN rank_level INTEGER DEFAULT 0;
        RAISE NOTICE 'Rank level kolonu eklendi';
    END IF;
END $$;

-- 5. Varsayılan değerleri güncelle
UPDATE users SET rank_level = 0 WHERE rank_level IS NULL;

-- 6. Index'leri ekle
CREATE INDEX IF NOT EXISTS idx_recruitment_logs_user_date ON recruitment_logs(user_id, recruitment_date);
CREATE INDEX IF NOT EXISTS idx_users_rank_level ON users(rank_level);
CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats(user_id, message_date);
CREATE INDEX IF NOT EXISTS idx_daily_stats_group_date ON daily_stats(group_id, message_date);

-- 7. Sistem ayarlarını ekle
INSERT INTO system_settings (setting_key, setting_value, description) 
VALUES 
    ('points_per_message', '0.04', 'Her mesaj için point miktarı'),
    ('daily_limit', '5.0', 'Günlük point limiti'),
    ('weekly_limit', '20.0', 'Haftalık point limiti'),
    ('messages_for_point', '5', 'Point için gereken mesaj sayısı')
ON CONFLICT (setting_key) DO NOTHING;

-- 8. Point settings'i ekle
INSERT INTO point_settings (setting_name, setting_value, description) 
VALUES 
    ('points_per_message', '0.04', 'Her mesaj için point miktarı'),
    ('daily_limit', '5.0', 'Günlük point limiti'),
    ('weekly_limit', '20.0', 'Haftalık point limiti'),
    ('messages_for_point', '5', 'Point için gereken mesaj sayısı')
ON CONFLICT (setting_name) DO NOTHING;

-- 9. Varsayılan rank'ları ekle
INSERT INTO user_ranks (rank_name, min_points, max_points) 
VALUES 
    ('Yeni Üye', 0.00, 1.00),
    ('Bronze', 1.00, 10.00),
    ('Silver', 10.00, 50.00),
    ('Gold', 50.00, 100.00),
    ('Platinum', 100.00, 500.00),
    ('Diamond', 500.00, NULL)
ON CONFLICT (rank_name) DO NOTHING;

-- 10. VACUUM ve ANALYZE
VACUUM ANALYZE daily_stats;
VACUUM ANALYZE events;
VACUUM ANALYZE users;
VACUUM ANALYZE recruitment_logs;

-- 11. Migration tamamlandı log'u
INSERT INTO system_logs (log_level, message, details) 
VALUES ('INFO', 'Critical database errors fixed', 'Foreign key and unique constraints updated successfully'); 