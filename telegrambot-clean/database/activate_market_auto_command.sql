-- =============================================
-- MARKET OTOMATIK KOMUTUNU AKTİF ET
-- Özelden site yönlendirmesi yapacak
-- =============================================

DO $$
DECLARE
    current_settings JSONB;
    updated_settings JSONB;
BEGIN
    -- Mevcut ayarları al
    SELECT settings INTO current_settings
    FROM scheduled_messages_settings
    WHERE id = 1;
    
    IF current_settings IS NULL THEN
        RAISE EXCEPTION 'scheduled_messages_settings tablosunda ayar bulunamadı!';
    END IF;
    
    updated_settings := current_settings;
    
    -- Market komutunu aktif et ve özelden gönderecek şekilde güncelle
    updated_settings := jsonb_set(
        updated_settings,
        ARRAY['auto_commands', 'market'],
        '{
            "is_active": true,
            "message_text": "🛍️ **KIRVE MARKET**\n\nMarket sistemimiz web sitesinde!\n\n🌐 **Web Market:**\nhttps://kirve1.com/market\n\n💡 Hesabınız otomatik olarak senkronize edilecektir.",
            "interval_minutes": 90,
            "send_privately": true
        }'::JSONB
    );
    
    -- Ayarları kaydet
    UPDATE scheduled_messages_settings
    SET settings = updated_settings,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = 1;
    
    RAISE NOTICE '✅ Market otomatik komutu aktif edildi!';
    RAISE NOTICE '   - is_active: true';
    RAISE NOTICE '   - interval_minutes: 90';
    RAISE NOTICE '   - send_privately: true (özelden gönderilecek)';
    
END $$;

-- Güncellenmiş ayarları göster
SELECT 
    jsonb_pretty(settings->'auto_commands'->'market') as market_command
FROM scheduled_messages_settings
WHERE id = 1;

