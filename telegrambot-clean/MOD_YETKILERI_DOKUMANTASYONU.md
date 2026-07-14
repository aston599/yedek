# 🛡️ Mod Yetkileri Dokümantasyonu

## Mod Yetkileri Özeti

### ✅ Modların Yapabildikleri:

1. **Mesaj Silme** (`!sil`)
   - Reply ile mesaj silme
   - Sadece grup/supergroup'da çalışır

2. **Susturma** (`!sustur SÜRE`)
   - Kullanıcıyı belirtilen süre boyunca susturma
   - Reply veya mention ile çalışır
   - Rate limiting: 1 dakikada 5'ten fazla mute → kötü niyetli kullanıcı

3. **Mute Kaldırma** (`!mkaldir` veya `!mkaldır`)
   - Kullanıcının mute'unu kaldırma
   - Reply veya mention ile çalışır

4. **Uyarı Verme** (`!uyarı` veya `/uyarı`)
   - Kullanıcıya uyarı verme
   - Uyarı sistemi:
     - 1. uyarı: 5 dakika mute (sadece owner yapabilir)
     - 2. uyarı: 30 dakika mute (sadece owner yapabilir)
     - 3. uyarı: Kalıcı ban (sadece owner yapabilir)
   - Rate limiting: 1 dakikada 10'dan fazla uyarı → kötü niyetli kullanıcı

5. **Uyarıları Görüntüleme** (`!uyarılar` veya `/uyarılar`)
   - Kullanıcının uyarı sayısını görüntüleme

6. **Uyarıları Sıfırlama** (`!uyarısıfırla` veya `/resetwarn`)
   - Kullanıcının uyarılarını sıfırlama

7. **Mod Listesi** (`!mod` veya `!modlar`)
   - Aktif modları listeleme
   - Mod değilse 10 dakika cooldown

8. **Mod Durumu Yönetimi**
   - `!modaktif` - Mod'u aktif yap (listede görünür)
   - `!modpasif` - Mod'u pasif yap (listede görünmez, ama yetkileri aktif)

### ❌ Modların Yapamadıkları:

1. **Ban İşlemi**
   - Sadece owner (bot sahibi) ban yapabilir
   - Modlar ban yapamaz

2. **Admin Yetkileri**
   - Admin komutlarını kullanamazlar
   - Admin seviyesi yok

3. **Diğer Modları Cezalandırma**
   - Modlar, diğer modları cezalandıramaz
   - Sadece normal kullanıcıları cezalandırabilirler

4. **Mute/Ban İşlemlerinde Owner Onayı**
   - Uyarı sistemi ile mute/ban işlemleri için owner onayı gerekir
   - Modlar uyarı ekleyebilir ama mute/ban işlemi için owner onayı gerekir

## 🔇 Muteleme Sistemi

### Nasıl Çalışır?

1. **Susturma Komutu** (`!sustur SÜRE`)
   - Mod veya owner kullanabilir
   - Süre dakika cinsinden belirtilir
   - Kullanıcının tüm izinleri kapatılır (mesaj gönderme, medya, vb.)
   - Belirtilen süre sonunda otomatik olarak kalkar

2. **Mute Kaldırma** (`!mkaldir`)
   - Mod veya owner kullanabilir
   - Kullanıcının tüm izinleri geri verilir
   - Süre dolmadan önce kaldırılabilir

3. **Uyarı Sistemi ile Mute**
   - 1. uyarı: 5 dakika mute (sadece owner yapabilir)
   - 2. uyarı: 30 dakika mute (sadece owner yapabilir)
   - 3. uyarı: Kalıcı ban (sadece owner yapabilir)

### Rate Limiting (Güvenlik)

- **Mute işlemleri**: 1 dakikada 5'ten fazla mute → kötü niyetli kullanıcı
- **Uyarı işlemleri**: 1 dakikada 10'dan fazla uyarı → kötü niyetli kullanıcı
- **Ban işlemleri**: 1 dakikada 3'ten fazla ban → kötü niyetli kullanıcı (sadece owner için)

### Kötü Niyetli Kullanıcı Tespiti

Eğer bir mod arka arkaya çok hızlı mute/uyarı yaparsa:
1. Mod yetkisi alınır
2. Kalıcı mute uygulanır
3. Owner'a bildirim gönderilir

## 📊 Mod Durumu Sistemi

### Aktif Mod
- `is_active = TRUE` (varsayılan)
- Mod listesinde görünür (`!mod` komutu)
- Mod yetkileri aktif
- Yardım isteklerinde bildirim alır

### Pasif Mod
- `is_active = FALSE`
- Mod listesinde görünmez
- Mod yetkileri hala aktif (sadece listede görünmez)
- Yardım isteklerinde bildirim almaz

### Komutlar
- `!modaktif` - Mod'u aktif yap
- `!modpasif` - Mod'u pasif yap

## 🆘 Yardım İsteği Bildirimi

Grupta birisi `!mod` yazdığında:
- Tüm aktif modlara özelden bildirim gönderilir
- Bildirim içeriği:
  - Kullanıcı bilgileri (ad, username, ID)
  - Grup bilgileri (ad, ID)
  - Zaman damgası

## 📝 SQL Yapısı

### moderators Tablosu
```sql
CREATE TABLE moderators (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    added_by BIGINT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,  -- Aktif/Pasif durumu
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### Indexler
- `idx_moderators_user_id` - user_id için index
- `idx_moderators_is_active` - is_active için index
- `idx_moderators_added_by` - added_by için index

### mod_codes Tablosu
```sql
CREATE TABLE mod_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    is_used BOOLEAN DEFAULT FALSE,
    used_by BIGINT,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    notes TEXT
);
```

## 🔍 SQL Kontrolü

### ✅ Kontrol Edilenler:
1. ✅ `moderators` tablosu mevcut ve doğru yapıda
2. ✅ `is_active` kolonu mevcut (BOOLEAN DEFAULT TRUE)
3. ✅ Indexler mevcut
4. ✅ Foreign key constraint mevcut
5. ✅ `mod_codes` tablosu mevcut ve doğru yapıda

### ⚠️ Potansiyel İyileştirmeler:
1. `moderators` tablosunda `last_activity` kolonu eklenebilir (mod aktivite takibi için)
2. `moderators` tablosunda `status` kolonu eklenebilir (aktif/pasif/izinli vb.)
3. `mod_codes` tablosunda `expires_at` kolonu eklenebilir (kod süresi için)

## 📋 Komut Özeti

| Komut | Yetki | Açıklama |
|-------|-------|----------|
| `!sil` | Mod/Admin | Mesaj silme |
| `!sustur SÜRE` | Mod/Admin | Susturma |
| `!mkaldir` | Mod/Admin | Mute kaldırma |
| `!uyarı` | Mod/Admin | Uyarı verme |
| `!uyarılar` | Herkes | Uyarıları görüntüleme |
| `!uyarısıfırla` | Mod/Admin | Uyarıları sıfırlama |
| `!mod` / `!modlar` | Herkes | Mod listesi |
| `!modaktif` | Mod | Mod'u aktif yap |
| `!modpasif` | Mod | Mod'u pasif yap |
| `!modol KOD` | Herkes | Mod kodunu kullan |
| `!modkoduret [sayı]` | Admin | Mod kodları üret |
| `!modkodlar` | Admin | Mod kodlarını listele |

