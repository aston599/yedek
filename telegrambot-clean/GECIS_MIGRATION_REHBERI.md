# 🔄 Kirve Point Geçiş Migration Rehberi

## 📋 Genel Bakış

Bu rehber, Kirve Point geçiş migration'ının nasıl yapılacağını adım adım açıklar.

---

## 🎯 Migration Hedefleri

1. **Mevcut Bakiyeleri Endeksleme:**
   - Hibrit sistem (3.0x - 5.0x multiplier)
   - Aktivite bazlı bonus
   - Mesaj bazlı bonus

2. **Yeni Puan Ayarları:**
   - Mesaj başına: 0.04 → 0.20 (5x artış)
   - Günlük limit: 5.00 → 200.00 (40x artış)
   - Haftalık limit: 20.00 → 1000.00 (50x artış)

---

## 📁 Dosyalar

1. **`database/migration_kirve_point_gecis.sql`** - Ana migration script
2. **`database/rollback_kirve_point_gecis.sql`** - Rollback script (hata durumunda)
3. **`database/verify_migration.sql`** - Doğrulama script

---

## 🚀 Migration Adımları

### Adım 1: Hazırlık

```bash
# 1. Database yedeği al
pg_dump -h YOUR_HOST -U YOUR_USER -d YOUR_DB > backup_before_migration.sql

# 2. Test ortamında migration'ı test et (ÖNEMLİ!)
# 3. Migration script'lerini gözden geçir
```

### Adım 2: Migration Çalıştırma

```sql
-- PostgreSQL'de çalıştır
\i database/migration_kirve_point_gecis.sql
```

**Migration Yapacaklar:**
1. ✅ Backup tabloları oluşturur
2. ✅ Sistem ayarlarını günceller
3. ✅ Kullanıcı bakiyelerini endeksler
4. ✅ Migration logları oluşturur

### Adım 3: Doğrulama

```sql
-- Doğrulama script'ini çalıştır
\i database/verify_migration.sql
```

**Kontrol Edilecekler:**
- ✅ Toplam puan artışı
- ✅ Multiplier dağılımı
- ✅ Aktivite bazlı analiz
- ✅ Hata kontrolü (negatif bakiye, anormal multiplier)

### Adım 4: Rollback (Gerekirse)

```sql
-- Hata durumunda rollback
\i database/rollback_kirve_point_gecis.sql
```

---

## 📊 Endeksleme Mantığı

### Hibrit Sistem Formülü

```
Base Multiplier: 3.0x (herkes için minimum)

Aktivite Bonusu:
- 1000+ mesaj: +50%
- 500-1000 mesaj: +30%
- 100-500 mesaj: +10%
- Son 30 gün aktif: +30%
- Son 60 gün aktif: +10%
- Rank 5+: +20%
- Rank 3-4: +10%

Mesaj Bonusu:
- Mesaj sayısı / 10000 (max 1.0)
- 1000 mesaj = 0.1, 5000 mesaj = 0.5, 10000+ mesaj = 1.0

Toplam Multiplier:
- Minimum: 3.0x
- Maksimum: 5.0x
- Formül: 3.0 + Aktivite Bonusu + Mesaj Bonusu
```

### Örnek Senaryolar

**Senaryo 1: Çok Aktif Kullanıcı**
- Mevcut: 200 KP
- Mesaj: 5000
- Son aktivite: 2 gün önce
- Rank: 5
- Hesaplama:
  - Base: 3.0x
  - Aktivite: +50% (1000+ mesaj) + 30% (aktif) + 20% (rank) = +100%
  - Mesaj: 5000/10000 = 0.5 = +50%
  - Toplam: 3.0 + 1.0 + 0.5 = 4.5x
  - **Yeni: 200 * 4.5 = 900 KP**

**Senaryo 2: Orta Aktif Kullanıcı**
- Mevcut: 50 KP
- Mesaj: 1000
- Son aktivite: 15 gün önce
- Rank: 2
- Hesaplama:
  - Base: 3.0x
  - Aktivite: +50% (1000+ mesaj) + 10% (60 gün içi) = +60%
  - Mesaj: 1000/10000 = 0.1 = +10%
  - Toplam: 3.0 + 0.6 + 0.1 = 3.7x
  - **Yeni: 50 * 3.7 = 185 KP**

**Senaryo 3: Pasif Kullanıcı**
- Mevcut: 10 KP
- Mesaj: 100
- Son aktivite: 90 gün önce
- Rank: 1
- Hesaplama:
  - Base: 3.0x
  - Aktivite: 0
  - Mesaj: 100/10000 = 0.01 = +1%
  - Toplam: 3.0 + 0.0 + 0.01 = 3.01x
  - **Yeni: 10 * 3.01 = 30.1 KP**

---

## ⚠️ Önemli Notlar

### 1. Güvenlik

- ✅ **Mutlaka yedek alın** migration öncesi
- ✅ **Test ortamında test edin** production'a geçmeden önce
- ✅ **Rollback planı hazır olsun** hata durumunda

### 2. Performans

- Migration büyük tablolarda uzun sürebilir
- Production'da maintenance window planlayın
- İndex'lerin mevcut olduğundan emin olun

### 3. Doğrulama

- Migration sonrası mutlaka doğrulama yapın
- Test kullanıcıları ile kontrol edin
- İstatistikleri karşılaştırın

---

## 🔧 Ayarlama (İsteğe Bağlı)

### Multiplier Değiştirme

Eğer multiplier'ları değiştirmek isterseniz:

```sql
-- database/migration_kirve_point_gecis.sql içinde
-- calculate_migration_multiplier fonksiyonunu düzenleyin

-- Örnek: Base multiplier'ı 5.0x yapmak için
base_multiplier DECIMAL := 5.0;  -- 3.0 yerine 5.0

-- Maksimum multiplier'ı 7.0x yapmak için
total_multiplier := GREATEST(LEAST(total_multiplier, 7.0), 5.0);
```

### Puan Ayarları Değiştirme

```sql
-- Seçenek B: Yüksek Seviye
UPDATE system_settings 
SET 
    points_per_message = 0.50,      -- 0.20 yerine 0.50
    daily_limit = 500.00,            -- 200.00 yerine 500.00
    weekly_limit = 2500.00,          -- 1000.00 yerine 2500.00
    updated_at = NOW()
WHERE id = 1;
```

---

## 📈 Beklenen Sonuçlar

### İstatistikler (1000 Kullanıcı Varsayımı)

| Kullanıcı Tipi | Sayı | Mevcut Toplam | Yeni Toplam | Artış |
|----------------|------|---------------|-------------|-------|
| Çok Aktif | 100 | 20,000 KP | 90,000 KP | +350% |
| Aktif | 300 | 30,000 KP | 105,000 KP | +250% |
| Orta | 400 | 20,000 KP | 62,000 KP | +210% |
| Pasif | 200 | 2,000 KP | 6,000 KP | +200% |
| **TOPLAM** | **1000** | **72,000 KP** | **263,000 KP** | **+265%** |

---

## ✅ Migration Checklist

- [ ] Database yedeği alındı
- [ ] Test ortamında test edildi
- [ ] Migration script'i gözden geçirildi
- [ ] Maintenance window planlandı
- [ ] Rollback planı hazır
- [ ] Migration çalıştırıldı
- [ ] Doğrulama yapıldı
- [ ] Test kullanıcıları kontrol edildi
- [ ] İstatistikler karşılaştırıldı
- [ ] Production'a deploy edildi

---

## 🆘 Sorun Giderme

### Problem: Migration çok uzun sürüyor

**Çözüm:**
- İndex'leri kontrol edin
- Batch processing kullanın
- Maintenance mode açın

### Problem: Negatif bakiye oluştu

**Çözüm:**
```sql
-- Negatif bakiyeleri sıfırla
UPDATE users SET kirve_points = 0 WHERE kirve_points < 0;
```

### Problem: Multiplier anormal

**Çözüm:**
```sql
-- Anormal multiplier'ları düzelt
UPDATE users u
SET kirve_points = b.kirve_points * 3.0
FROM users_backup_kirve_point_migration b
WHERE u.user_id = b.user_id
  AND b.kirve_points > 0
  AND (u.kirve_points / NULLIF(b.kirve_points, 0)) NOT BETWEEN 3.0 AND 5.0;
```

---

## 📞 Destek

Migration sırasında sorun yaşarsanız:
1. Rollback script'ini çalıştırın
2. Yedekten restore edin
3. Hata loglarını kontrol edin
4. Migration loglarını inceleyin

---

**Son Güncelleme:** 2025-01-14
**Versiyon:** 1.0

