-- 🤖 KirveHub Bot - Güncellenmiş Database Initialization Script
-- Güncelleme Tarihi: 2025-07-31 04:52:46
-- Supabase'den export edilen schema ile birleştirildi
-- PostgreSQL için optimize edilmiş

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Supabase'den export edilen tablolar
-- 🤖 KirveHub Bot - Supabase Schema Export
-- Export Tarihi: 2025-07-31 04:33:46
-- PostgreSQL için optimize edilmiş
-- Supabase'den otomatik export

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- balance_logs tablosu
CREATE TABLE IF NOT EXISTS balance_logs (
    id integer NOT NULL DEFAULT nextval('balance_logs_id_seq'::regclass),
    user_id bigint NOT NULL,
    admin_id bigint NOT NULL,
    action character varying(10) NOT NULL,
    amount numeric NOT NULL,
    reason text,
    created_at timestamp without time zone DEFAULT now()
);
-- bot_status tablosu
CREATE TABLE IF NOT EXISTS bot_status (
    id integer NOT NULL DEFAULT nextval('bot_status_id_seq'::regclass),
    status text NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);
-- custom_commands tablosu
CREATE TABLE IF NOT EXISTS custom_commands (
    id integer NOT NULL DEFAULT nextval('custom_commands_id_seq'::regclass),
    command_name character varying(64) NOT NULL,
    scope smallint NOT NULL,
    reply_text text NOT NULL,
    button_text character varying(128),
    button_url character varying(256),
    created_by bigint NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);

-- Index: custom_commands_command_name_key
CREATE UNIQUE INDEX custom_commands_command_name_key ON public.custom_commands USING btree (command_name);
-- daily_stats tablosu
CREATE TABLE IF NOT EXISTS daily_stats (
    id integer NOT NULL DEFAULT nextval('daily_stats_id_seq'::regclass),
    user_id bigint,
    group_id bigint,
    message_date date,
    message_count integer DEFAULT 0,
    points_earned numeric DEFAULT 0.00,
    character_count integer DEFAULT 0
);

-- Index: daily_stats_user_id_group_id_message_date_key
CREATE UNIQUE INDEX daily_stats_user_id_group_id_message_date_key ON public.daily_stats USING btree (user_id, group_id, message_date);
-- event_participants tablosu
CREATE TABLE IF NOT EXISTS event_participants (
    id integer NOT NULL DEFAULT nextval('event_participants_id_seq'::regclass),
    event_id integer,
    user_id bigint NOT NULL,
    joined_at timestamp without time zone DEFAULT now(),
    withdrew_at timestamp without time zone,
    payment_amount numeric DEFAULT 0.00,
    status character varying(20) DEFAULT 'active'::character varying,
    is_winner boolean DEFAULT false
);

-- Index: event_participants_event_id_user_id_key
CREATE UNIQUE INDEX event_participants_event_id_user_id_key ON public.event_participants USING btree (event_id, user_id);
-- event_participations tablosu
CREATE TABLE IF NOT EXISTS event_participations (
    id integer NOT NULL DEFAULT nextval('event_participations_id_seq'::regclass),
    user_id bigint NOT NULL,
    event_id integer NOT NULL,
    joined_at timestamp without time zone DEFAULT now(),
    withdrew_at timestamp without time zone,
    can_withdraw boolean DEFAULT true,
    payment_amount numeric NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying,
    is_winner boolean DEFAULT false
);

-- Index: event_participations_user_id_event_id_key
CREATE UNIQUE INDEX event_participations_user_id_event_id_key ON public.event_participations USING btree (user_id, event_id);
-- events tablosu
CREATE TABLE IF NOT EXISTS events (
    id integer NOT NULL DEFAULT nextval('events_id_seq'::regclass),
    event_type character varying(50) NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    entry_cost numeric DEFAULT 0.00,
    max_winners integer DEFAULT 1,
    duration_minutes integer DEFAULT 0,
    bonus_multiplier numeric DEFAULT 1.00,
    status character varying(20) DEFAULT 'active'::character varying,
    created_by bigint NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    ended_at timestamp without time zone,
    participants jsonb DEFAULT '[]'::jsonb,
    winners jsonb DEFAULT '[]'::jsonb,
    group_id bigint DEFAULT 0,
    completed_at timestamp without time zone,
    completed_by bigint,
    message_id bigint
);
-- market_categories tablosu
CREATE TABLE IF NOT EXISTS market_categories (
    id integer NOT NULL DEFAULT nextval('market_categories_id_seq'::regclass),
    name character varying(100) NOT NULL,
    description text,
    icon character varying(50) DEFAULT '📦'::character varying,
    display_order integer DEFAULT 0,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    emoji character varying(10)
);

-- Index: market_categories_name_key
CREATE UNIQUE INDEX market_categories_name_key ON public.market_categories USING btree (name);
-- market_order_logs tablosu
CREATE TABLE IF NOT EXISTS market_order_logs (
    id integer NOT NULL DEFAULT nextval('market_order_logs_id_seq'::regclass),
    order_id integer,
    old_status character varying(20),
    new_status character varying(20),
    admin_id bigint,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
-- market_orders tablosu
CREATE TABLE IF NOT EXISTS market_orders (
    id integer NOT NULL DEFAULT nextval('market_orders_id_seq'::regclass),
    order_number character varying(20) NOT NULL,
    user_id bigint,
    product_id integer,
    quantity integer NOT NULL DEFAULT 1,
    total_price numeric NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    payment_status character varying(20) DEFAULT 'paid'::character varying,
    admin_notes text,
    delivery_content text,
    user_notes text,
    approved_by integer,
    approved_at timestamp without time zone,
    delivered_at timestamp without time zone,
    cancelled_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

-- Index: market_orders_order_number_key
CREATE UNIQUE INDEX market_orders_order_number_key ON public.market_orders USING btree (order_number);
-- market_products tablosu
CREATE TABLE IF NOT EXISTS market_products (
    id integer NOT NULL DEFAULT nextval('market_products_id_seq'::regclass),
    name character varying(200) NOT NULL,
    description text,
    company_name character varying(100),
    category_id integer,
    price numeric NOT NULL,
    original_price numeric,
    stock integer NOT NULL DEFAULT 0,
    sold_count integer DEFAULT 0,
    image_url text,
    is_active boolean DEFAULT true,
    is_featured boolean DEFAULT false,
    auto_delivery boolean DEFAULT false,
    delivery_content text,
    min_stock_alert integer DEFAULT 5,
    created_by bigint,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    site_link character varying(500) DEFAULT NULL::character varying,
    site_name character varying(255) DEFAULT NULL::character varying
);
-- point_settings tablosu
CREATE TABLE IF NOT EXISTS point_settings (
    setting_key character varying(50) NOT NULL,
    setting_value numeric,
    description text,
    updated_by bigint,
    updated_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
-- recruitment_daily_limits tablosu
CREATE TABLE IF NOT EXISTS recruitment_daily_limits (
    id integer NOT NULL DEFAULT nextval('recruitment_daily_limits_id_seq'::regclass),
    user_id bigint NOT NULL,
    recruitment_date date NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);

-- Index: recruitment_daily_limits_user_id_recruitment_date_key
CREATE UNIQUE INDEX recruitment_daily_limits_user_id_recruitment_date_key ON public.recruitment_daily_limits USING btree (user_id, recruitment_date);
-- recruitment_settings tablosu
CREATE TABLE IF NOT EXISTS recruitment_settings (
    setting_key character varying(50) NOT NULL,
    setting_value text,
    description text,
    updated_by bigint,
    updated_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
-- registered_groups tablosu
CREATE TABLE IF NOT EXISTS registered_groups (
    group_id bigint NOT NULL,
    group_name character varying(200),
    group_username character varying(100),
    registered_by bigint,
    registration_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_active boolean DEFAULT true,
    point_multiplier numeric DEFAULT 1.00
);
-- scheduled_messages_settings tablosu
CREATE TABLE IF NOT EXISTS scheduled_messages_settings (
    id integer NOT NULL DEFAULT 1,
    settings jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);
-- system_logs tablosu
CREATE TABLE IF NOT EXISTS system_logs (
    id integer NOT NULL DEFAULT nextval('system_logs_id_seq'::regclass),
    log_level character varying(10) NOT NULL,
    module character varying(50),
    message text NOT NULL,
    user_id bigint,
    created_at timestamp without time zone DEFAULT now()
);
-- system_settings tablosu
CREATE TABLE IF NOT EXISTS system_settings (
    id integer NOT NULL DEFAULT nextval('system_settings_id_seq'::regclass),
    points_per_message numeric DEFAULT 0.04,
    daily_limit numeric DEFAULT 5.00,
    weekly_limit numeric DEFAULT 20.00,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);
-- user_ranks tablosu
CREATE TABLE IF NOT EXISTS user_ranks (
    rank_id integer NOT NULL DEFAULT nextval('user_ranks_rank_id_seq'::regclass),
    rank_name character varying(50),
    rank_level integer,
    permissions ARRAY,
    created_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

-- Index: user_ranks_rank_name_key
CREATE UNIQUE INDEX user_ranks_rank_name_key ON public.user_ranks USING btree (rank_name);

-- Index: user_ranks_rank_level_key
CREATE UNIQUE INDEX user_ranks_rank_level_key ON public.user_ranks USING btree (rank_level);
-- users tablosu
CREATE TABLE IF NOT EXISTS users (
    user_id bigint NOT NULL,
    username character varying(255),
    first_name character varying(255),
    last_name character varying(255),
    created_at timestamp without time zone DEFAULT now(),
    last_activity timestamp without time zone DEFAULT now(),
    is_registered boolean DEFAULT false,
    registration_date timestamp without time zone,
    age integer,
    phone character varying(20),
    email character varying(255),
    interests ARRAY,
    status character varying(50) DEFAULT 'active'::character varying,
    notes text,
    kirve_points numeric DEFAULT 0.00,
    daily_points numeric DEFAULT 0.00,
    last_point_date date,
    total_messages integer DEFAULT 0,
    rank_id integer DEFAULT 1
);

-- Eksik tablolar (init.sql'den)

-- groups tablosu (eksik)
CREATE TABLE IF NOT EXISTS groups (
    group_id BIGINT PRIMARY KEY,
    group_name VARCHAR(255),
    group_type VARCHAR(50),
    member_count INTEGER DEFAULT 0,
    is_registered BOOLEAN DEFAULT FALSE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    admin_user_id BIGINT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

-- market_stats tablosu (eksik)
CREATE TABLE IF NOT EXISTS market_stats (
    id SERIAL PRIMARY KEY,
    stat_date DATE NOT NULL,
    total_orders INTEGER DEFAULT 0,
    total_revenue DECIMAL(10,2) DEFAULT 0.00,
    unique_customers INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stat_date)
);

-- market_items tablosu (eksik)
CREATE TABLE IF NOT EXISTS market_items (
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    stock_quantity INTEGER DEFAULT -1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- orders tablosu (eksik)
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    total_price DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES market_items(id) ON DELETE CASCADE
);

-- Indexler
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_is_registered ON users(is_registered);
CREATE INDEX IF NOT EXISTS idx_users_kirve_points ON users(kirve_points DESC);
CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity);
CREATE INDEX IF NOT EXISTS idx_groups_is_registered ON groups(is_registered);
CREATE INDEX IF NOT EXISTS idx_groups_admin_user_id ON groups(admin_user_id);
CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats(user_id, message_date);
CREATE INDEX IF NOT EXISTS idx_daily_stats_group_date ON daily_stats(group_id, message_date);
CREATE INDEX IF NOT EXISTS idx_events_active ON events(is_active);
CREATE INDEX IF NOT EXISTS idx_events_dates ON events(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_event_participants_event ON event_participants(event_id);
CREATE INDEX IF NOT EXISTS idx_event_participants_user ON event_participants(user_id);
CREATE INDEX IF NOT EXISTS idx_market_items_available ON market_items(is_available);
CREATE INDEX IF NOT EXISTS idx_market_items_type ON market_items(item_type);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);

-- Default point settings
INSERT INTO point_settings (setting_name, setting_value, description) VALUES
('point_per_message', '0.04', 'Her mesaj için kazanılan point miktarı'),
('daily_point_limit', '5.00', 'Günlük maksimum point limiti'),
('flood_protection_seconds', '10', 'Flood koruması için bekleme süresi'),
('min_message_length', '5', 'Point kazanmak için minimum mesaj uzunluğu'),
('max_concurrent_updates', '100', 'Maksimum eşzamanlı güncelleme'),
('rate_limit_delay', '0.1', 'Rate limiting için bekleme süresi')
ON CONFLICT (setting_name) DO NOTHING;

-- Default bot status
INSERT INTO bot_status (status, message) VALUES
('started', 'Bot başlatıldı'),
('running', 'Bot çalışıyor'),
('maintenance', 'Bot bakım modunda')
ON CONFLICT DO NOTHING;

-- Functions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_groups_updated_at ON groups;
CREATE TRIGGER update_groups_updated_at BEFORE UPDATE ON groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_events_updated_at ON events;
CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_market_items_updated_at ON market_items;
CREATE TRIGGER update_market_items_updated_at BEFORE UPDATE ON market_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_orders_updated_at ON orders;
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to reset daily points
CREATE OR REPLACE FUNCTION reset_daily_points()
RETURNS void AS $$
BEGIN
    UPDATE users 
    SET daily_points = 0.00, last_point_date = CURRENT_DATE
    WHERE last_point_date < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- Function to get user statistics
CREATE OR REPLACE FUNCTION get_user_stats(p_user_id BIGINT)
RETURNS TABLE(
    total_points DECIMAL(10,2),
    daily_points DECIMAL(10,2),
    total_messages INTEGER,
    rank_level INTEGER,
    registration_date TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.kirve_points,
        u.daily_points,
        u.total_messages,
        u.rank_level,
        u.registration_date
    FROM users u
    WHERE u.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;
