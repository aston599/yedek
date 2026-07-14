-- 🔧 Varsayılan Komutlar Ekleme Script'i
-- Temel komutları database'e ekle

-- 1. !sitelerim komutu
INSERT INTO custom_commands (command_name, scope, response_message, button_text, button_url, created_by, is_active) 
VALUES 
    ('sitelerim', 1, '🌐 **KirveHub Siteleri**\n\n📱 **Ana Site:**\nhttps://kirvehub.com\n\n💬 **Telegram:**\n@kirvehubaff\n\n📺 **YouTube:**\nhttps://youtube.com/@kirvehub\n\n🎮 **Discord:**\nhttps://discord.gg/kirvehub\n\n📧 **İletişim:**\ninfo@kirvehub.com', '🌐 Siteyi Ziyaret Et', 'https://kirvehub.com', 8154732274, TRUE),
    ('site', 1, '🌐 **KirveHub Ana Sitesi**\n\n📱 **Resmi Web Sitesi:**\nhttps://kirvehub.com\n\n💡 **Özellikler:**\n• Güncel haberler\n• Ürün bilgileri\n• İletişim formu\n• Hakkımızda', '🌐 Siteyi Ziyaret Et', 'https://kirvehub.com', 8154732274, TRUE),
    ('kirvehub', 1, '🤖 **KirveHub Bot**\n\n📊 **Bot Bilgileri:**\n• Versiyon: 3.0\n• Durum: Aktif\n• Komutlar: /yardim\n\n💬 **Destek:**\n@kirvehubaff', '📊 Bot Durumu', 'https://t.me/kirvehubaff', 8154732274, TRUE),
    ('yardim', 1, '📚 **KirveHub Bot Yardım**\n\n🔧 **Temel Komutlar:**\n• /start - Bot başlat\n• /profil - Profil bilgileri\n• /market - Market sistemi\n• /etkinlikler - Etkinlikler\n• /siralama - Sıralama\n\n💡 **Özel Komutlar:**\n• !sitelerim - Sitelerim\n• !site - Ana site\n• !kirvehub - Bot bilgisi\n\n📞 **Destek:**\n@kirvehubaff', '📚 Yardım', 'https://t.me/kirvehubaff', 8154732274, TRUE),
    ('help', 1, '📚 **KirveHub Bot Help**\n\n🔧 **Basic Commands:**\n• /start - Start bot\n• /profile - Profile info\n• /market - Market system\n• /events - Events\n• /ranking - Rankings\n\n💡 **Custom Commands:**\n• !sitelerim - My sites\n• !site - Main site\n• !kirvehub - Bot info\n\n📞 **Support:**\n@kirvehubaff', '📚 Help', 'https://t.me/kirvehubaff', 8154732274, TRUE)
ON CONFLICT (command_name, scope) DO UPDATE SET
    response_message = EXCLUDED.response_message,
    button_text = EXCLUDED.button_text,
    button_url = EXCLUDED.button_url,
    is_active = TRUE;

-- 2. Global komutlar (scope 3)
INSERT INTO custom_commands (command_name, scope, response_message, button_text, button_url, created_by, is_active) 
VALUES 
    ('sitelerim', 3, '🌐 **KirveHub Siteleri**\n\n📱 **Ana Site:**\nhttps://kirvehub.com\n\n💬 **Telegram:**\n@kirvehubaff\n\n📺 **YouTube:**\nhttps://youtube.com/@kirvehub\n\n🎮 **Discord:**\nhttps://discord.gg/kirvehub\n\n📧 **İletişim:**\ninfo@kirvehub.com', '🌐 Siteyi Ziyaret Et', 'https://kirvehub.com', 8154732274, TRUE),
    ('site', 3, '🌐 **KirveHub Ana Sitesi**\n\n📱 **Resmi Web Sitesi:**\nhttps://kirvehub.com\n\n💡 **Özellikler:**\n• Güncel haberler\n• Ürün bilgileri\n• İletişim formu\n• Hakkımızda', '🌐 Siteyi Ziyaret Et', 'https://kirvehub.com', 8154732274, TRUE),
    ('kirvehub', 3, '🤖 **KirveHub Bot**\n\n📊 **Bot Bilgileri:**\n• Versiyon: 3.0\n• Durum: Aktif\n• Komutlar: /yardim\n\n💬 **Destek:**\n@kirvehubaff', '📊 Bot Durumu', 'https://t.me/kirvehubaff', 8154732274, TRUE),
    ('yardim', 3, '📚 **KirveHub Bot Yardım**\n\n🔧 **Temel Komutlar:**\n• /start - Bot başlat\n• /profil - Profil bilgileri\n• /market - Market sistemi\n• /etkinlikler - Etkinlikler\n• /siralama - Sıralama\n\n💡 **Özel Komutlar:**\n• !sitelerim - Sitelerim\n• !site - Ana site\n• !kirvehub - Bot bilgisi\n\n📞 **Destek:**\n@kirvehubaff', '📚 Yardım', 'https://t.me/kirvehubaff', 8154732274, TRUE),
    ('help', 3, '📚 **KirveHub Bot Help**\n\n🔧 **Basic Commands:**\n• /start - Start bot\n• /profile - Profile info\n• /market - Market system\n• /events - Events\n• /ranking - Rankings\n\n💡 **Custom Commands:**\n• !sitelerim - My sites\n• !site - Main site\n• !kirvehub - Bot info\n\n📞 **Support:**\n@kirvehubaff', '📚 Help', 'https://t.me/kirvehubaff', 8154732274, TRUE)
ON CONFLICT (command_name, scope) DO UPDATE SET
    response_message = EXCLUDED.response_message,
    button_text = EXCLUDED.button_text,
    button_url = EXCLUDED.button_url,
    is_active = TRUE;

-- 3. Migration tamamlandı log'u
INSERT INTO system_logs (log_level, message, details) 
VALUES ('INFO', 'Default commands added', 'sitelerim, site, kirvehub, yardim, help commands added successfully'); 