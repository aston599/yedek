-- ============================================================================
-- ZAMANLANMIŞ MESAJLAR GÜNCELLEME SCRIPT
-- ============================================================================
-- Bu script zamanlanmış mesajları yeni yapıya göre günceller:
-- 1. URL'leri güncelle (kirve1.com)
-- 2. Otomatik komutları güncelle (!market, !siteler, !mod)
-- 3. Interval'ları düzenle
-- ============================================================================

DO $$
DECLARE
    current_settings JSONB;
    updated_settings JSONB;
    bot_profile JSONB;
    bot_id TEXT;
    new_link TEXT;
BEGIN
    -- Mevcut ayarları al
    SELECT settings INTO current_settings
    FROM scheduled_messages_settings
    WHERE id = 1;
    
    IF current_settings IS NULL THEN
        RAISE EXCEPTION 'scheduled_messages_settings tablosunda veri yok!';
    END IF;
    
    updated_settings := current_settings;
    
    -- ============================================================================
    -- 1. BOT PROFİLLERİNDEKİ URL'LERİ GÜNCELLE
    -- ============================================================================
    IF updated_settings->'bot_profiles' IS NOT NULL THEN
        FOR bot_id IN SELECT jsonb_object_keys(updated_settings->'bot_profiles')
        LOOP
            bot_profile := updated_settings->'bot_profiles'->bot_id;
            
            -- Link'i güncelle
            IF bot_profile->'link' IS NOT NULL THEN
                new_link := bot_profile->>'link';
                
                -- Eski URL'leri yeni URL'e çevir
                IF new_link LIKE '%kumarlayasiyorum9.com%' OR new_link LIKE '%kumarlayasiyorum7.com%' THEN
                    new_link := REPLACE(new_link, 'kumarlayasiyorum9.com', 'kirve1.com');
                    new_link := REPLACE(new_link, 'kumarlayasiyorum7.com', 'kirve1.com');
                    
                    -- Profili güncelle
                    updated_settings := jsonb_set(
                        updated_settings,
                        ARRAY['bot_profiles', bot_id, 'link'],
                        to_jsonb(new_link)
                    );
                END IF;
            END IF;
        END LOOP;
    END IF;
    
    -- ============================================================================
    -- 2. OTOMATİK KOMUTLARI GÜNCELLE
    -- ============================================================================
    
    -- Market komutunu güncelle (site yönlendirmesi, bakımda - PASİF)
    updated_settings := jsonb_set(
        updated_settings,
        ARRAY['auto_commands', 'market'],
        '{
            "is_active": false,
            "message_text": "🛍️ <b>Market''e Ulaşmak İçin:</b>\n\n🌐 <a href=\"https://kirve1.com/market\">Web Market''e Git</a>",
            "interval_minutes": 90
        }'::JSONB
    );
    
    -- Eski 'site' komutunu kaldır (artık !siteler kullanılıyor)
    IF updated_settings->'auto_commands'->'site' IS NOT NULL THEN
        updated_settings := updated_settings - 'auto_commands' || 
            jsonb_build_object('auto_commands', 
                (updated_settings->'auto_commands') - 'site'
            );
    END IF;
    
    -- !siteler komutunu ekle/güncelle
    updated_settings := jsonb_set(
        updated_settings,
        ARRAY['auto_commands', 'siteler'],
        '{
            "is_active": true,
            "message_text": "🌐 <b>Siteleri Görmek İçin:</b>\n\n<code>!siteler</code> yazarak siteleri görebilirsiniz.",
            "interval_minutes": 90
        }'::JSONB
    );
    
    -- Mod komutunu güncelle (interval 120 dakika - değişmeden)
    updated_settings := jsonb_set(
        updated_settings,
        ARRAY['auto_commands', 'mod'],
        '{
            "is_active": true,
            "message_text": "🛡️ <b>Aktif Modları Görmek İçin:</b>\n\n<code>!mod</code> veya <code>!modlar</code> yazarak aktif modları görebilirsiniz.",
            "interval_minutes": 120
        }'::JSONB
    );
    
    -- ============================================================================
    -- 3. AYARLARI KAYDET
    -- ============================================================================
    UPDATE scheduled_messages_settings
    SET settings = updated_settings,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = 1;
    
    RAISE NOTICE '✅ Zamanlanmış mesajlar güncellendi!';
    RAISE NOTICE '   - Bot profillerindeki URL''ler güncellendi (kirve1.com)';
    RAISE NOTICE '   - Market komutu devre dışı bırakıldı (site yönlendirmesi)';
    RAISE NOTICE '   - Site komutu → !siteler olarak güncellendi';
    RAISE NOTICE '   - Interval''lar düzenlendi (90 dakika)';
    
END $$;

-- Güncellenmiş ayarları göster
SELECT 
    jsonb_pretty(settings->'bot_profiles') as bot_profiles,
    jsonb_pretty(settings->'auto_commands') as auto_commands
FROM scheduled_messages_settings
WHERE id = 1;

