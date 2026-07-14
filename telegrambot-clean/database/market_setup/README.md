# 🛍️ MARKET KURULUM KILAVUZU

Bu klasörde market sistemini sıfırdan kurmak için gereken tüm SQL dosyaları var.

## 📋 ADIM ADIM KURULUM

### 1️⃣ Market'i Temizle
```sql
-- database/market_setup/1_clean_all_market.sql
-- Tüm ürünleri, kategorileri ve siparişleri siler
```

**Nasıl Çalıştırılır:**
- Supabase Dashboard → SQL Editor
- Dosya içeriğini kopyala-yapıştır
- Run

---

### 2️⃣ Yeni Kolonları Ekle
```sql
-- database/market_setup/2_add_columns.sql
-- external_link, site_requirement, delivery_info, image_url kolonlarını ekler
```

**Nasıl Çalıştırılır:**
- Supabase Dashboard → SQL Editor
- Dosya içeriğini kopyala-yapıştır
- Run

---

### 3️⃣ Kategorileri Ekle
```sql
-- database/market_setup/3_category_template.sql
-- Kendi kategorilerini bu dosyayı düzenleyerek ekle
```

**Düzenleme Formatı:**
```sql
INSERT INTO market_categories (name, icon, is_active) VALUES
('🎮 Dijital Ürünler', '🎮', true),
('💰 Site Bakiyesi', '💰', true);
```

**Kategorilerin ID'sini Öğren:**
```sql
SELECT id, name, icon FROM market_categories;
```

---

### 4️⃣ Ürünleri Ekle
```sql
-- database/market_setup/4_product_template.sql
-- Kendi ürünlerini bu dosyayı düzenleyerek ekle
```

**Düzenleme Formatı:**
```sql
INSERT INTO market_products (
    name, 
    description, 
    price, 
    stock, 
    category_id,  -- Kategori ID'sini buraya yaz!
    site_name,
    site_requirement,
    external_link,
    delivery_info,
    is_active
) VALUES
('Ürün Adı', 'Açıklama', 100, 50, 1, 'Site', 'Gereksinim', 'https://link', 'Teslimat bilgisi', true);
```

---

## 🤖 BOT İÇİNDEN YÖNETİM

### Kategori Ekle
```
!kategoriekle
```
Bot sana adım adım soracak:
1. Kategori adı (emoji ile birlikte)
2. Icon (emoji)

### Ürün Ekle
```
!marketurun
```
Bot sana adım adım soracak:
1. Kategori seç
2. Ürün adı
3. Açıklama
4. Fiyat
5. Stok
6. Site linki (opsiyonel)
7. Site gereksinimi (opsiyonel)

---

## 💡 İPUÇLARI

### Emoji Kullanımı
- Kategori adı: `🎮 Dijital Ürünler`
- Icon: `🎮`
- Windows: `Win + .` ile emoji paneli

### Site Linkleri
- AMG Bahis: `https://t2m.io/amgkirve`
- Mersobahis: `https://t2m.io/mersokirvehub`

### Fiyatlandırma
- Kirve Point (KP) cinsinden
- Örnek: 50 TL ürün = 250 KP (kullanıcı 1 mesaj = 0.04 KP kazanıyor)

---

## ✅ KONTROL KOMUTLARI

### Kategorileri Görüntüle
```sql
SELECT id, name, icon, is_active FROM market_categories ORDER BY id;
```

### Ürünleri Görüntüle
```sql
SELECT id, name, price, stock, category_id, is_active 
FROM market_products 
ORDER BY category_id, price;
```

### Kategori Sil
```sql
UPDATE market_categories SET is_active = false WHERE id = <ID>;
-- veya tamamen sil:
DELETE FROM market_categories WHERE id = <ID>;
```

### Ürün Sil
```sql
UPDATE market_products SET is_active = false WHERE id = <ID>;
-- veya tamamen sil:
DELETE FROM market_products WHERE id = <ID>;
```

---

## 🔧 SORUN GİDERME

### "Ürün detayı yok" hatası
- `2_add_columns.sql` çalıştırıldı mı?
- Botu yeniden başlat

### "Kategori bulunamadı" hatası
- Kategoriler eklendi mi?
- `is_active = true` mi?

### Site linki çalışmıyor
- `external_link` kolonu eklendi mi?
- Link formatı doğru mu? (`https://` ile başlamalı)





