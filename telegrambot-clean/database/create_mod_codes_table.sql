-- Mod kodları tablosu - Tek kullanımlık mod aktivasyon kodları
CREATE TABLE IF NOT EXISTS mod_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    is_used BOOLEAN DEFAULT FALSE,
    used_by BIGINT,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    notes TEXT
);

-- Indexler
CREATE INDEX IF NOT EXISTS idx_mod_codes_code ON mod_codes(code);
CREATE INDEX IF NOT EXISTS idx_mod_codes_is_used ON mod_codes(is_used);
CREATE INDEX IF NOT EXISTS idx_mod_codes_used_by ON mod_codes(used_by);

