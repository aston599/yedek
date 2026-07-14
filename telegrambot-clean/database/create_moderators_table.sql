-- Moderators tablosu - Manuel mod yönetimi
CREATE TABLE IF NOT EXISTS moderators (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    added_by BIGINT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexler
CREATE INDEX IF NOT EXISTS idx_moderators_user_id ON moderators(user_id);
CREATE INDEX IF NOT EXISTS idx_moderators_is_active ON moderators(is_active);
CREATE INDEX IF NOT EXISTS idx_moderators_added_by ON moderators(added_by);


