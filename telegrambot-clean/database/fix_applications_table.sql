-- Fix applications table eksik kolonlar
-- Tarih: 2025-10-20

-- Önce tablo var mı kontrol et
DO $$
BEGIN
    -- applications tablosu yoksa oluştur
    IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'applications') THEN
        CREATE TABLE applications (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            username VARCHAR(100),
            full_name VARCHAR(200),
            phone_number VARCHAR(20),
            amg_username VARCHAR(100),
            merso_username VARCHAR(100),
            screenshot_path VARCHAR(500),
            status VARCHAR(20) DEFAULT 'pending',
            bot_source VARCHAR(50) DEFAULT 'main',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX idx_applications_user_id ON applications(user_id);
        CREATE INDEX idx_applications_status ON applications(status);
        CREATE INDEX idx_applications_bot_source ON applications(bot_source);
        
        RAISE NOTICE 'applications tablosu oluşturuldu';
    ELSE
        -- Tablo varsa sadece eksik kolonları ekle
        
        -- merso_username kolonu ekle
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'merso_username'
        ) THEN
            ALTER TABLE applications ADD COLUMN merso_username VARCHAR(100);
            RAISE NOTICE 'merso_username kolonu eklendi';
        END IF;
        
        -- bot_source kolonu ekle
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'bot_source'
        ) THEN
            ALTER TABLE applications ADD COLUMN bot_source VARCHAR(50) DEFAULT 'main';
            RAISE NOTICE 'bot_source kolonu eklendi';
        END IF;
        
        -- amg_username kolonu kontrol et
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'applications' AND column_name = 'amg_username'
        ) THEN
            ALTER TABLE applications ADD COLUMN amg_username VARCHAR(100);
            RAISE NOTICE 'amg_username kolonu eklendi';
        END IF;
        
        RAISE NOTICE 'applications tablosu güncellendi';
    END IF;
END $$;

-- Index'leri kontrol et ve ekle
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_indexes WHERE indexname = 'idx_applications_bot_source'
    ) THEN
        CREATE INDEX idx_applications_bot_source ON applications(bot_source);
    END IF;
END $$;





