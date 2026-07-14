-- Eksik kolonları ekle (eğer yoksa)

-- external_link kolonunu ekle
ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS external_link VARCHAR(500);

-- site_requirement kolonunu ekle
ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS site_requirement VARCHAR(100);

-- sold_count kolonunu ekle (eğer yoksa)
ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS sold_count INTEGER DEFAULT 0;

-- Kolonların eklendiğini kontrol et
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'market_products' 
AND column_name IN ('external_link', 'site_requirement', 'sold_count')
ORDER BY column_name;


