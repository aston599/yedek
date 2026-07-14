-- =============================================
-- SİTE TABLOSU GÜNCELLEMESİ - DETAYLI BİLGİLER
-- =============================================

-- Yeni kolonlar ekle
ALTER TABLE sites ADD COLUMN IF NOT EXISTS welcome_bonus TEXT;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS features TEXT;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS payment_methods TEXT;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS min_deposit VARCHAR(50);
ALTER TABLE sites ADD COLUMN IF NOT EXISTS support_info TEXT;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS promo_code VARCHAR(100);

-- Örnek veri güncelle
UPDATE sites 
SET 
    welcome_bonus = '🎁 %100 Hoş Geldin Bonusu\n💰 İlk Yatırım Bonusu\n🎰 50 Free Spin',
    features = '✅ 7/24 Canlı Destek\n✅ Hızlı Para Çekme\n✅ Türkçe Arayüz\n✅ Mobil Uygulama',
    payment_methods = '💳 Papara\n💳 Kredi Kartı\n💳 Havale\n💳 Cepbank',
    min_deposit = '50 TL',
    support_info = '📞 7/24 Canlı Destek\n📧 destek@site.com\n💬 Telegram: @destek',
    promo_code = 'KIRVEHUB100'
WHERE name = 'Mersobahis';

UPDATE sites 
SET 
    welcome_bonus = '🎁 %150 İlk Yatırım Bonusu\n💰 Kayıp Bonusu %10\n🎰 100 Free Spin',
    features = '✅ Premium Destek\n✅ Anlık Para Çekme\n✅ Türkçe Arayüz\n✅ Mobil Uyumlu',
    payment_methods = '💳 Papara\n💳 Kredi Kartı\n💳 Havale\n💳 Crypto',
    min_deposit = '100 TL',
    support_info = '📞 7/24 Premium Destek\n📧 support@amg.com\n💬 Telegram: @amgdestek',
    promo_code = 'AMGKIRVE150'
WHERE name = 'AMG Bahis';

-- Başarı mesajı
SELECT 'Sites tablosu güncellendi! Yeni kolonlar eklendi.' as status;
SELECT COUNT(*) as toplam_site FROM sites;


