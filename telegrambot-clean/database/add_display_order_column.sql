-- display_order kolonunu ekle (eğer yoksa)
ALTER TABLE market_categories 
ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0;

-- Mevcut kategorilere sıra numarası ver
UPDATE market_categories 
SET display_order = id 
WHERE display_order IS NULL OR display_order = 0;


