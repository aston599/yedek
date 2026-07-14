-- =============================================
-- SİTELER LİSTESİ GÜNCELLEME
-- !siteler komutu için site listesi
-- Görseldeki siteler ve bonuslar eşleştirildi
-- =============================================

-- Mevcut siteleri güncelle veya ekle
-- ON CONFLICT ile mevcut siteler güncellenir, yeni olanlar eklenir

-- 1. MERS BAHİS - %100 HOŞ GELDİN BONUSU
INSERT INTO sites (name, url, description, icon, priority, is_active) VALUES
('Mersobahis', 'https://t2m.io/mersokirvehub', '%100 Hoş Geldin Bonusu', '🎰', 100, true)
ON CONFLICT (name) DO UPDATE SET
    url = EXCLUDED.url,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    priority = EXCLUDED.priority,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 2. AMG BAHİS - 333 FS DENEME BONUSU
INSERT INTO sites (name, url, description, icon, priority, is_active) VALUES
('AMG Bahis', 'https://t2m.io/amgkirve', '333 FS Deneme Bonusu', '🎲', 95, true)
ON CONFLICT (name) DO UPDATE SET
    url = EXCLUDED.url,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    priority = EXCLUDED.priority,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 3. GalaBet - 500 FS VEYA 500 FB DENEME BONUSU
INSERT INTO sites (name, url, description, icon, priority, is_active) VALUES
('GalaBet', 'https://g.t2m.io/galakirve', '500 FS veya 500 FB Deneme Bonusu', '🃏', 90, true)
ON CONFLICT (name) DO UPDATE SET
    url = EXCLUDED.url,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    priority = EXCLUDED.priority,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 4. Padişahbet - 1.000 TL NAKİT DENEME BONUSU
INSERT INTO sites (name, url, description, icon, priority, is_active) VALUES
('Padişahbet', 'https://p.t2m.io/EfQMjRJ', '1.000 TL Nakit Deneme Bonusu', '👑', 85, true)
ON CONFLICT (name) DO UPDATE SET
    url = EXCLUDED.url,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    priority = EXCLUDED.priority,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 5. GRANDPASHABET - 500 TL DENEME BONUSU
INSERT INTO sites (name, url, description, icon, priority, is_active) VALUES
('Grandpashabet', 'https://shorttwelve.online/denizaksoy', '500 TL Deneme Bonusu', '⭐', 80, true)
ON CONFLICT (name) DO UPDATE SET
    url = EXCLUDED.url,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    priority = EXCLUDED.priority,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 6. BetPuan - 200 FS VEYA 100 FB DENEME BONUSU
INSERT INTO sites (name, url, description, icon, priority, is_active) VALUES
('BetPuan', 'https://www.betpuanpartner.com/links/?btag=2098924', '200 FS veya 100 FB Deneme Bonusu', '💎', 75, true)
ON CONFLICT (name) DO UPDATE SET
    url = EXCLUDED.url,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    priority = EXCLUDED.priority,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- 7. Dodobet - (görselde yok ama link var)
INSERT INTO sites (name, url, description, icon, priority, is_active) VALUES
('Dodobet', 'https://cutt.ly/2r7JwG3d', 'Güvenilir bahis sitesi', '🎯', 70, true)
ON CONFLICT (name) DO UPDATE SET
    url = EXCLUDED.url,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    priority = EXCLUDED.priority,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- Görseldeki diğer siteler (link yok, opsiyonel):
-- BETCI BETCI - 200 FS DENEME BONUSU (link yok, eklenmedi)
-- betorspin. - 500 TL DENEME BONUSU (link yok, eklenmedi)

-- Başarı mesajı
SELECT 'Siteler başarıyla güncellendi!' as status;
SELECT name, url, description, priority FROM sites WHERE is_active = true ORDER BY priority DESC, id;

