-- 🔧 LEVEL SİSTEMİ DÜZELTME
-- Gerçekçi mesaj sayıları ve level grupları

-- 1. Users tablosuna rank_level kolonu ekle
ALTER TABLE users ADD COLUMN IF NOT EXISTS rank_level INTEGER DEFAULT 1;

-- 2. Users tablosuna rank_id kolonu ekle
ALTER TABLE users ADD COLUMN IF NOT EXISTS rank_id INTEGER DEFAULT 1;

-- 3. User_ranks tablosunu gerçekçi mesaj sayılarına göre güncelle
TRUNCATE TABLE user_ranks;

INSERT INTO user_ranks (rank_name, min_points, max_points) 
VALUES 
    -- Level 1-10: Bronze (100-1000 mesaj)
    ('Bronze', 100, 1000),
    
    -- Level 11-30: Silver (1000-3000 mesaj)
    ('Silver', 1000, 3000),
    
    -- Level 31-50: Gold (3000-6000 mesaj)
    ('Gold', 3000, 6000),
    
    -- Level 51-70: Platinum (6000-12000 mesaj)
    ('Platinum', 6000, 12000),
    
    -- Level 71-85: Diamond (12000-25000 mesaj)
    ('Diamond', 12000, 25000),
    
    -- Level 86-95: Master (25000-50000 mesaj)
    ('Master', 25000, 50000),
    
    -- Level 96-100: Legend (50000+ mesaj)
    ('Legend', 50000, NULL)
ON CONFLICT (rank_name) DO NOTHING;

-- 4. Rank güncelleme fonksiyonu (mesaj sayısına göre)
CREATE OR REPLACE FUNCTION update_user_rank(user_id BIGINT)
RETURNS VOID AS $$
DECLARE
    message_count INTEGER;
    new_rank_id INTEGER;
    new_rank_name VARCHAR(100);
    old_rank_id INTEGER;
    old_rank_name VARCHAR(100);
    current_level INTEGER;
BEGIN
    -- Kullanıcının toplam mesaj sayısını al
    SELECT message_count, rank_id INTO message_count, old_rank_id
    FROM users 
    WHERE user_id = $1;
    
    IF message_count IS NULL THEN
        message_count := 0;
    END IF;
    
    IF old_rank_id IS NULL THEN
        old_rank_id := 1;
    END IF;
    
    -- Eski rank adını al
    SELECT rank_name INTO old_rank_name
    FROM user_ranks 
    WHERE id = old_rank_id;
    
    -- Mesaj sayısına göre rank belirle
    SELECT id, rank_name INTO new_rank_id, new_rank_name
    FROM user_ranks 
    WHERE min_points <= message_count 
    AND (max_points IS NULL OR max_points > message_count)
    ORDER BY min_points DESC
    LIMIT 1;
    
    -- Rank bulunamadıysa varsayılan rank
    IF new_rank_id IS NULL THEN
        new_rank_id := 1;
        new_rank_name := 'Bronze';
    END IF;
    
    -- Level hesapla (1-100 arası)
    current_level := CASE 
        WHEN message_count < 1000 THEN 1 + (message_count / 100)  -- Bronze: 1-10
        WHEN message_count < 3000 THEN 10 + ((message_count - 1000) / 100)  -- Silver: 11-30
        WHEN message_count < 6000 THEN 30 + ((message_count - 3000) / 150)  -- Gold: 31-50
        WHEN message_count < 12000 THEN 50 + ((message_count - 6000) / 300)  -- Platinum: 51-70
        WHEN message_count < 25000 THEN 70 + ((message_count - 12000) / 650)  -- Diamond: 71-85
        WHEN message_count < 50000 THEN 85 + ((message_count - 25000) / 1250)  -- Master: 86-95
        ELSE 95 + ((message_count - 50000) / 5000)  -- Legend: 96-100
    END;
    
    -- Level'i 100'ü geçmemesi için sınırla
    IF current_level > 100 THEN
        current_level := 100;
    END IF;
    
    -- Kullanıcının rank'ını güncelle
    UPDATE users 
    SET rank_level = current_level,
        rank_id = new_rank_id
    WHERE user_id = $1;
    
    -- Level atladıysa log kaydı ve bildirim için flag
    IF new_rank_id > old_rank_id THEN
        INSERT INTO system_logs (log_level, message, details)
        VALUES ('INFO', 'User level up!', 
                format('User: %s, Messages: %s, Level: %s, Old Rank: %s, New Rank: %s (ID: %s)', 
                       user_id, message_count, current_level, old_rank_name, new_rank_name, new_rank_id));
        
        -- Level up bildirimi için özel log
        INSERT INTO system_logs (log_level, message, details)
        VALUES ('LEVEL_UP', 'User level up notification', 
                format('User: %s, Level: %s, Old Rank: %s, New Rank: %s, Messages: %s', 
                       user_id, current_level, old_rank_name, new_rank_name, message_count));
    END IF;
    
END;
$$ LANGUAGE plpgsql;

-- 5. Mesaj sayısı güncelleme fonksiyonu
CREATE OR REPLACE FUNCTION add_message_and_update_rank(
    p_user_id BIGINT
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Mesaj sayısını artır
    UPDATE users 
    SET message_count = message_count + 1,
        last_activity = NOW()
    WHERE user_id = p_user_id;
    
    -- Rank'ı güncelle
    PERFORM update_user_rank(p_user_id);
    
    RETURN TRUE;
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- 6. Tüm kullanıcıların rank'larını güncelle
SELECT update_user_rank(user_id) FROM users;

-- 7. Migration tamamlandı log'u
INSERT INTO system_logs (log_level, message, details) 
VALUES ('INFO', 'Level system updated to realistic message requirements', 'All rank functions updated with higher message requirements and level groups'); 