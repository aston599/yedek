# ⚠️ Uyarı Sistemi Dokümantasyonu

## Genel Bakış

Uyarı sistemi, moderatörler ve adminlerin kullanıcılara uyarı vermesini ve uyarı sayısına göre otomatik cezalar uygulamasını sağlar.

## 📋 Özellikler

### 1. **Uyarı Verme**
- **Komut:** `!uyarı` veya `/uyarı` veya `/warn`
- **Kullanım:** Bir mesaja yanıt vererek `!uyarı [sebep]` yazın
- **Yetki:** Mod veya Admin
- **Örnek:**
  ```
  !uyarı Spam yapıyor
  !uyarı Küfür kullanıyor
  ```

### 2. **Uyarı Sayısına Göre Otomatik Cezalar**

| Uyarı Sayısı | Cezalandırma | Süre | Yetki |
|-------------|--------------|------|-------|
| **1. Uyarı** | 🔇 Mute | 5 dakika | Owner (Mod uyarı ekleyebilir ama mute için owner onayı gerekir) |
| **2. Uyarı** | 🔇 Mute | 30 dakika | Owner (Mod uyarı ekleyebilir ama mute için owner onayı gerekir) |
| **3. Uyarı** | 🚫 Ban | Kalıcı | Owner (Mod uyarı ekleyebilir ama ban için owner onayı gerekir) |

### 3. **Uyarı Sıfırlama**
- **Komut:** `!uyarısıfırla` veya `/resetwarn`
- **Kullanım:** Bir mesaja yanıt vererek `!uyarısıfırla` yazın
- **Yetki:** Mod veya Admin
- **Sonuç:** Kullanıcının tüm uyarıları sıfırlanır (`is_active = FALSE`)

### 4. **Uyarıları Görüntüleme**
- **Komut:** `!uyarılar` veya `/warnings`
- **Kullanım:** Bir mesaja yanıt vererek `!uyarılar` yazın
- **Yetki:** Herkes (kendi uyarılarını görebilir)
- **Profil Menüsü:** Kullanıcılar profil menüsünden "⚠️ Uyarılarım" butonuna tıklayarak uyarılarını görebilir

## 🗄️ Database Yapısı

### `warnings` Tablosu

```sql
CREATE TABLE warnings (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,           -- Uyarı alan kullanıcı
    group_id BIGINT NOT NULL,          -- Grup ID (grup bazlı)
    warned_by BIGINT NOT NULL,         -- Uyarı veren kişi
    reason TEXT,                        -- Uyarı sebebi
    warning_number INTEGER NOT NULL,    -- Uyarı numarası (1, 2, 3...)
    is_active BOOLEAN DEFAULT TRUE,     -- Aktif mi? (sıfırlanınca FALSE olur)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Önemli Notlar:
- **Grup Bazlı:** Her grup için ayrı uyarı sayısı tutulur
- **Soft Delete:** Uyarılar silinmez, `is_active = FALSE` yapılır
- **Warning Number:** Her kullanıcı için grup bazında otomatik artar (1, 2, 3...)

## 🔧 Teknik Detaylar

### 1. **Uyarı Ekleme Fonksiyonu**

```python
async def add_warning(user_id: int, group_id: int, warned_by: int, reason: str = None) -> Dict:
    """
    - Uyarı ekler
    - Warning number'ı otomatik hesaplar (MAX + 1)
    - Toplam uyarı sayısını döndürür
    """
```

### 2. **Uyarı Sayısı Getirme**

```python
async def get_user_warnings(user_id: int, group_id: int) -> int:
    """
    - Sadece aktif uyarıları sayar (is_active = TRUE)
    - Grup bazlı çalışır
    """
```

### 3. **Uyarı Sıfırlama**

```python
async def reset_warnings(user_id: int, group_id: int) -> bool:
    """
    - Tüm aktif uyarıları pasif yapar (is_active = FALSE)
    - Uyarılar silinmez, sadece pasif olur
    """
```

## 🛡️ Güvenlik Özellikleri

### 1. **Rate Limiting (Modlar İçin)**
- Modlar 1 dakikada **10'dan fazla** uyarı veremez
- Aşarsa → Kötü niyetli kullanıcı olarak işaretlenir
- Mod yetkisi alınır
- Kalıcı mute uygulanır
- Owner'a bildirilir

### 2. **Yetki Kontrolü**
- **Mod:** Uyarı ekleyebilir, ama mute/ban için owner onayı gerekir
- **Owner:** Uyarı ekleyebilir ve otomatik mute/ban yapabilir
- **Normal Kullanıcı:** Uyarı veremez

### 3. **Kendini Uyaramaz**
- Kullanıcı kendine uyarı veremez

### 4. **Hedef Kullanıcı Yetki Kontrolü**
- Daha yüksek yetkili kullanıcıya uyarı verilemez
- Örnek: Mod, Admin'e uyarı veremez

## 📊 Uyarı İşlem Akışı

```
1. Mod/Owner → !uyarı komutu yazar
2. Sistem → Hedef kullanıcıyı belirler (reply veya mention)
3. Sistem → Yetki kontrolü yapar
4. Sistem → Rate limiting kontrolü yapar (modlar için)
5. Sistem → Uyarı ekler (database)
6. Sistem → Uyarı sayısını kontrol eder
7. Sistem → Otomatik ceza uygular (eğer owner ise):
   - 1. uyarı → 5 dakika mute
   - 2. uyarı → 30 dakika mute
   - 3. uyarı → Ban
8. Sistem → Grup bildirimi gönderir
9. Sistem → Kullanıcıya özel bildirim gönderir
10. Sistem → Son 10 mesajı siler
11. Sistem → Komut mesajını siler
```

## 📱 Bildirimler

### 1. **Grup Bildirimi**
- Uyarı verildiğinde grupta bildirim gösterilir
- Format:
  ```
  ⚠️ UYARI VERİLDİ
  
  👤 Kullanıcı: [İsim]
  📊 Uyarı Sayısı: X/3
  📋 Sebep: [Sebep]
  🔇 Süre: [Cezalandırma]
  👮 Moderatör: [Mod İsmi]
  ```

### 2. **Özel Bildirim**
- Uyarı alan kullanıcıya özel mesaj gönderilir
- Format:
  ```
  ⚠️ UYARI ALDINIZ
  
  📊 Uyarı Sayısı: X/3
  📋 Sebep: [Sebep]
  🔇 Süre: [Cezalandırma]
  ```

## 🔍 Uyarı Görüntüleme

### 1. **Komut ile**
```
!uyarılar (reply)
```

### 2. **Profil Menüsü**
- Profil menüsünde "⚠️ Uyarılarım" butonu
- Tüm gruplardaki uyarıları gösterir
- Format:
  ```
  ⚠️ UYARILARINIZ
  
  📊 Toplam Uyarı: X
  📋 Grup Bazlı:
  - Grup 1: X uyarı
  - Grup 2: Y uyarı
  ```

## 📝 Örnek Senaryolar

### Senaryo 1: İlk Uyarı
1. Mod → `!uyarı Spam yapıyor` (reply)
2. Sistem → Uyarı eklenir (1/3)
3. Sistem → Owner onayı beklenir (mute için)
4. Owner → Mute işlemini onaylar
5. Kullanıcı → 5 dakika mute edilir

### Senaryo 2: İkinci Uyarı
1. Mod → `!uyarı Küfür kullanıyor` (reply)
2. Sistem → Uyarı eklenir (2/3)
3. Sistem → Owner onayı beklenir (mute için)
4. Owner → Mute işlemini onaylar
5. Kullanıcı → 30 dakika mute edilir

### Senaryo 3: Üçüncü Uyarı
1. Owner → `!uyarı Kuralları ihlal ediyor` (reply)
2. Sistem → Uyarı eklenir (3/3)
3. Sistem → Otomatik ban uygulanır
4. Kullanıcı → Kalıcı olarak banlanır

### Senaryo 4: Uyarı Sıfırlama
1. Mod → `!uyarısıfırla` (reply)
2. Sistem → Tüm aktif uyarılar pasif yapılır
3. Sistem → Bildirim gönderilir

## ⚙️ Ayarlar

### Rate Limiting
```python
# handlers/punishment_system.py
_warn_actions: Dict[int, List[datetime]] = {}  # Rate limiting için
# 1 dakikada 10'dan fazla uyarı → Kötü niyetli kullanıcı
```

### Mute Süreleri
```python
# 1. uyarı: 5 dakika
# 2. uyarı: 30 dakika
# 3. uyarı: Ban (kalıcı)
```

## 🔗 İlgili Dosyalar

- **`handlers/punishment_system.py`**: Ana uyarı sistemi
- **`handlers/profile_handler.py`**: Profil menüsünde uyarı görüntüleme
- **`database.py`**: Database tablo oluşturma

## 📌 Notlar

1. **Grup Bazlı:** Her grup için ayrı uyarı sayısı tutulur
2. **Soft Delete:** Uyarılar silinmez, sadece pasif yapılır
3. **Owner Onayı:** Modlar uyarı ekleyebilir ama mute/ban için owner onayı gerekir
4. **Rate Limiting:** Modlar 1 dakikada 10'dan fazla uyarı veremez
5. **Otomatik Cezalar:** Sadece owner tarafından uygulanır
6. **Mesaj Silme:** Uyarı verildiğinde son 10 mesaj silinir

---

**Hazırlayan:** AI Assistant  
**Tarih:** 2025-11-15

