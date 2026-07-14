-- 📂 KATEGORİ EKLEME ŞABLONU
-- Bu dosyayı kopyala-düzenle ve kategorilerini ekle

-- Örnek Kategori Eklemeleri:
INSERT INTO market_categories (name, icon, is_active) VALUES
('🎮 Dijital Ürünler', '🎮', true),
('💰 Site Bakiyesi', '💰', true),
('💸 Nakit Çekim', '💸', true),
('📱 Fiziksel Ürünler', '📱', true);

-- ⚙️ KENDİ KATEGORİLERİNİ EKLE:
-- Formül: ('EMOJI İSİM', 'EMOJI', true)
-- 
-- INSERT INTO market_categories (name, icon, is_active) VALUES
-- ('🎁 Hediye Kartları', '🎁', true),
-- ('🎯 Özel Teklifler', '🎯', true),
-- ('🏆 VIP Ödüller', '🏆', true);

-- ✅ Kategorilerin ID'sini öğrenmek için:
SELECT id, name, icon FROM market_categories ORDER BY id;





