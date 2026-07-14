-- =============================================
-- OTOMATIK KOMUT MESAJLARI - scheduled_messages_settings'e EKLEME
-- =============================================

-- scheduled_messages_settings tablosuna otomatik komut mesajlarını ekle
DO $$
DECLARE
    current_settings JSONB;
    auto_commands JSONB;
BEGIN
    -- Mevcut ayarları al
    SELECT settings INTO current_settings
    FROM scheduled_messages_settings
    WHERE id = 1;
    
    -- Eğer tablo boşsa oluştur
    IF current_settings IS NULL THEN
        INSERT INTO scheduled_messages_settings (id, settings)
        VALUES (1, '{"active_bots": {}, "groups": [], "last_message_time": {}, "bot_profiles": {}, "auto_commands": {}, "auto_commands_last_sent": {}}'::JSONB)
        ON CONFLICT (id) DO NOTHING;
        
        SELECT settings INTO current_settings
        FROM scheduled_messages_settings
        WHERE id = 1;
    END IF;
    
    -- Otomatik komut mesajlarını oluştur
    auto_commands := '{
        "mod": {
            "message_text": "🛡️ <b>Aktif Modları Görmek İçin:</b>\n\n<code>!mod</code> veya <code>!modlar</code> yazarak aktif modları görebilirsiniz.",
            "interval_minutes": 120,
            "is_active": true
        },
        "market": {
            "message_text": "🛍️ <b>Market''e Ulaşmak İçin:</b>\n\n<code>!market</code> yazarak markete ulaşabilirsiniz.",
            "interval_minutes": 60,
            "is_active": true
        },
        "site": {
            "message_text": "🌐 <b>Siteleri Görmek İçin:</b>\n\n<code>!site</code> veya <code>!siteler</code> yazarak siteleri görebilirsiniz.",
            "interval_minutes": 60,
            "is_active": true
        }
    }'::JSONB;
    
    -- Mevcut ayarları güncelle (auto_commands yoksa ekle, varsa güncelle)
    IF current_settings->'auto_commands' IS NULL OR jsonb_typeof(current_settings->'auto_commands') = 'null' THEN
        current_settings := current_settings || jsonb_build_object('auto_commands', auto_commands);
        current_settings := current_settings || jsonb_build_object('auto_commands_last_sent', '{}'::JSONB);
    ELSE
        -- Mevcut komutları koru, yeni olanları ekle
        current_settings := jsonb_set(
            current_settings,
            '{auto_commands}',
            (current_settings->'auto_commands') || auto_commands
        );
    END IF;
    
    -- Ayarları kaydet
    UPDATE scheduled_messages_settings
    SET settings = current_settings,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = 1;
    
    RAISE NOTICE '✅ Otomatik komut mesajları scheduled_messages_settings''e eklendi!';
END $$;

-- Başarı mesajı
SELECT 'Otomatik komut mesajları başarıyla eklendi!' as status;
SELECT jsonb_object_keys(settings->'auto_commands') as aktif_komutlar 
FROM scheduled_messages_settings 
WHERE id = 1;

