-- Eksik kolonları ekle
-- message_count kolonu
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'message_count') THEN
        ALTER TABLE users ADD COLUMN message_count INTEGER DEFAULT 0;
        RAISE NOTICE 'message_count kolonu eklendi';
    ELSE
        RAISE NOTICE 'message_count kolonu zaten var';
    END IF;
END $$;

-- details kolonu
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'details') THEN
        ALTER TABLE users ADD COLUMN details TEXT DEFAULT '';
        RAISE NOTICE 'details kolonu eklendi';
    ELSE
        RAISE NOTICE 'details kolonu zaten var';
    END IF;
END $$;

-- rank_level kolonu
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'rank_level') THEN
        ALTER TABLE users ADD COLUMN rank_level INTEGER DEFAULT 1;
        RAISE NOTICE 'rank_level kolonu eklendi';
    ELSE
        RAISE NOTICE 'rank_level kolonu zaten var';
    END IF;
END $$;

-- Mevcut kullanıcıların message_count değerlerini güncelle
UPDATE users SET message_count = COALESCE(total_messages, 0) WHERE message_count IS NULL OR message_count = 0;

-- update_user_rank fonksiyonunu yeniden oluştur
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
    WHERE rank_id = old_rank_id;
    
    -- Mesaj sayısına göre rank belirle
    SELECT rank_id, rank_name INTO new_rank_id, new_rank_name
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
    
END;
$$ LANGUAGE plpgsql; 