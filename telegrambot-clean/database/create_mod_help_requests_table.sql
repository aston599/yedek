-- Mod yardım istekleri tablosu - !mod komutunun kullanımını loglamak için (opsiyonel)
-- Bu tablo, !mod komutunun ne zaman, kim tarafından, hangi grupta kullanıldığını kaydeder
-- İstatistik ve analiz için kullanılabilir

CREATE TABLE IF NOT EXISTS mod_help_requests (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    group_id BIGINT,
    chat_type VARCHAR(20) NOT NULL, -- 'group', 'supergroup', 'private'
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_moderator BOOLEAN DEFAULT FALSE, -- İsteği yapan kişi mod mu?
    notification_sent BOOLEAN DEFAULT FALSE, -- Modlara bildirim gönderildi mi?
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexler
CREATE INDEX IF NOT EXISTS idx_mod_help_requests_user_id ON mod_help_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_mod_help_requests_group_id ON mod_help_requests(group_id);
CREATE INDEX IF NOT EXISTS idx_mod_help_requests_requested_at ON mod_help_requests(requested_at);
CREATE INDEX IF NOT EXISTS idx_mod_help_requests_chat_type ON mod_help_requests(chat_type);

-- Açıklamalar
COMMENT ON TABLE mod_help_requests IS 'Mod yardım istekleri log tablosu - !mod komutunun kullanımını kaydeder';
COMMENT ON COLUMN mod_help_requests.user_id IS 'İsteği yapan kullanıcının ID''si';
COMMENT ON COLUMN mod_help_requests.group_id IS 'İsteğin yapıldığı grup ID''si (özel mesajda NULL)';
COMMENT ON COLUMN mod_help_requests.chat_type IS 'Chat tipi: group, supergroup, private';
COMMENT ON COLUMN mod_help_requests.is_moderator IS 'İsteği yapan kişi mod mu?';
COMMENT ON COLUMN mod_help_requests.notification_sent IS 'Modlara bildirim gönderildi mi?';

