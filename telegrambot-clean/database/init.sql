-- 🔧 Database Initialization Script
-- Tüm tabloları ve constraint'leri oluştur

-- Users tablosu
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    rank_level INTEGER DEFAULT 0,
    total_points DECIMAL(10,2) DEFAULT 0.00,
    weekly_points DECIMAL(10,2) DEFAULT 0.00,
    daily_points DECIMAL(10,2) DEFAULT 0.00,
    last_message_date TIMESTAMP,
    message_count INTEGER DEFAULT 0
);

-- Groups tablosu
CREATE TABLE IF NOT EXISTS groups (
    group_id BIGINT PRIMARY KEY,
    group_name VARCHAR(255),
    group_username VARCHAR(255),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Daily stats tablosu
CREATE TABLE IF NOT EXISTS daily_stats (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    group_id BIGINT NOT NULL,
    message_date DATE NOT NULL,
    message_count INTEGER DEFAULT 0,
    points_earned DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
    UNIQUE(user_id, group_id, message_date)
);

-- Recruitment logs tablosu
CREATE TABLE IF NOT EXISTS recruitment_logs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    recruitment_date DATE NOT NULL,
    recruitment_type VARCHAR(50) DEFAULT 'auto',
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, recruitment_date)
);

-- Events tablosu
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    event_name VARCHAR(255) NOT NULL,
    description TEXT,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    max_participants INTEGER,
    entry_fee DECIMAL(10,2) DEFAULT 0.00,
    prize_pool DECIMAL(10,2) DEFAULT 0.00,
    group_id BIGINT NOT NULL,
    created_by BIGINT NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Event participations tablosu
CREATE TABLE IF NOT EXISTS event_participations (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    user_id BIGINT NOT NULL,
    payment_amount DECIMAL(10,2) DEFAULT 0.00,
    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(event_id, user_id)
);

-- Event forced winners tablosu (Hileli kazanan atama sistemi)
CREATE TABLE IF NOT EXISTS event_forced_winners (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    user_id BIGINT NOT NULL,
    rank_order INTEGER NOT NULL,
    added_by BIGINT NOT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (added_by) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(event_id, user_id),
    INDEX(event_id, rank_order)
);

-- Market products tablosu
CREATE TABLE IF NOT EXISTS market_products (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    category VARCHAR(100),
    image_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Market orders tablosu
CREATE TABLE IF NOT EXISTS market_orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    admin_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES market_products(id) ON DELETE CASCADE
);

-- Custom commands tablosu
CREATE TABLE IF NOT EXISTS custom_commands (
    id SERIAL PRIMARY KEY,
    command_name VARCHAR(100) NOT NULL,
    scope SMALLINT DEFAULT 3,
    response_message TEXT NOT NULL,
    button_text VARCHAR(128),
    button_url VARCHAR(256),
    created_by BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    reply_text TEXT
);

-- System settings tablosu
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Point settings tablosu
CREATE TABLE IF NOT EXISTS point_settings (
    id SERIAL PRIMARY KEY,
    setting_name VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User ranks tablosu
CREATE TABLE IF NOT EXISTS user_ranks (
    id SERIAL PRIMARY KEY,
    rank_name VARCHAR(100) UNIQUE NOT NULL,
    min_points DECIMAL(10,2) NOT NULL,
    max_points DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System logs tablosu
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    log_level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index'leri oluştur
CREATE INDEX IF NOT EXISTS idx_users_rank_level ON users(rank_level);
CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats(user_id, message_date);
CREATE INDEX IF NOT EXISTS idx_daily_stats_group_date ON daily_stats(group_id, message_date);
CREATE INDEX IF NOT EXISTS idx_recruitment_logs_user_date ON recruitment_logs(user_id, recruitment_date);
CREATE INDEX IF NOT EXISTS idx_events_group_id ON events(group_id);
CREATE INDEX IF NOT EXISTS idx_events_created_by ON events(created_by);
CREATE INDEX IF NOT EXISTS idx_event_participations_event_id ON event_participations(event_id);
CREATE INDEX IF NOT EXISTS idx_event_participations_user_id ON event_participations(user_id);
CREATE INDEX IF NOT EXISTS idx_market_orders_user_id ON market_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_market_orders_status ON market_orders(status);
CREATE INDEX IF NOT EXISTS idx_custom_commands_scope ON custom_commands(scope);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);

-- Varsayılan rank'ları ekle
INSERT INTO user_ranks (rank_name, min_points, max_points) 
VALUES 
    ('Yeni Üye', 0.00, 1.00),
    ('Bronze', 1.00, 10.00),
    ('Silver', 10.00, 50.00),
    ('Gold', 50.00, 100.00),
    ('Platinum', 100.00, 500.00),
    ('Diamond', 500.00, NULL)
ON CONFLICT (rank_name) DO NOTHING;

-- Sistem ayarlarını ekle
INSERT INTO system_settings (setting_key, setting_value, description) 
VALUES 
    ('points_per_message', '0.04', 'Her mesaj için point miktarı'),
    ('daily_limit', '5.0', 'Günlük point limiti'),
    ('weekly_limit', '20.0', 'Haftalık point limiti'),
    ('messages_for_point', '5', 'Point için gereken mesaj sayısı')
ON CONFLICT (setting_key) DO NOTHING;

-- Point settings'i ekle
INSERT INTO point_settings (setting_name, setting_value, description) 
VALUES 
    ('points_per_message', '0.04', 'Her mesaj için point miktarı'),
    ('daily_limit', '5.0', 'Günlük point limiti'),
    ('weekly_limit', '20.0', 'Haftalık point limiti'),
    ('messages_for_point', '5', 'Point için gereken mesaj sayısı')
ON CONFLICT (setting_name) DO NOTHING; 