-- sold_count kolonunu ekle (eğer yoksa)
ALTER TABLE market_products 
ADD COLUMN IF NOT EXISTS sold_count INTEGER DEFAULT 0;

-- Kolonun eklendiğini kontrol et
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'market_products' 
AND column_name = 'sold_count';


