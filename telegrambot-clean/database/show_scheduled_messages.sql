-- ============================================================================
-- ZAMANLANMIŞ VE OTOMATİK MESAJLAR ANALİZ SCRIPT
-- ============================================================================
-- Bu script scheduled_messages_settings tablosundaki tüm verileri gösterir
-- ============================================================================

-- 1. Tablo yapısını göster
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'scheduled_messages_settings'
ORDER BY ordinal_position;

-- 2. Mevcut ayarları göster (JSON formatında)
SELECT 
    id,
    settings,
    created_at,
    updated_at
FROM scheduled_messages_settings
WHERE id = 1;

-- 3. JSON içeriğini detaylı analiz et
SELECT 
    id,
    settings->'active_bots' as active_bots,
    settings->'groups' as groups,
    settings->'last_message_time' as last_message_time,
    settings->'bot_profiles' as bot_profiles,
    settings->'auto_commands' as auto_commands,
    settings->'auto_commands_last_sent' as auto_commands_last_sent,
    created_at,
    updated_at
FROM scheduled_messages_settings
WHERE id = 1;

-- 4. Aktif botları listele
SELECT 
    jsonb_object_keys(settings->'active_bots') as bot_id,
    settings->'active_bots'->jsonb_object_keys(settings->'active_bots') as is_active
FROM scheduled_messages_settings
WHERE id = 1;

-- 5. Bot profillerini listele
SELECT 
    jsonb_object_keys(settings->'bot_profiles') as bot_id,
    settings->'bot_profiles'->jsonb_object_keys(settings->'bot_profiles') as profile_data
FROM scheduled_messages_settings
WHERE id = 1;

-- 6. Otomatik komutları listele
SELECT 
    jsonb_object_keys(settings->'auto_commands') as command_name,
    settings->'auto_commands'->jsonb_object_keys(settings->'auto_commands') as command_data
FROM scheduled_messages_settings
WHERE id = 1;

-- 7. Grupları listele
SELECT 
    jsonb_array_elements_text(settings->'groups') as group_id
FROM scheduled_messages_settings
WHERE id = 1;

-- 8. Son mesaj zamanlarını listele
SELECT 
    jsonb_object_keys(settings->'last_message_time') as bot_id,
    settings->'last_message_time'->jsonb_object_keys(settings->'last_message_time') as last_time
FROM scheduled_messages_settings
WHERE id = 1;

-- 9. Tüm JSON yapısını güzel formatta göster
SELECT 
    jsonb_pretty(settings) as formatted_settings
FROM scheduled_messages_settings
WHERE id = 1;

-- ============================================================================
-- NOT: Bu script sadece okuma yapar, hiçbir değişiklik yapmaz
-- ============================================================================

