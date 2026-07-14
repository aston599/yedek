# 🛡️ Mod Komutları Dokümantasyonu

## Yeni Eklenen Mod Komutları

### 1. **Mesaj Silme - `!sil`**

**Kullanım:**
- Bir mesaja yanıt vererek `!sil` yazın
- Mesaj silinir ve komut mesajı da silinir

**Yetki:** Mod veya Admin

**Örnek:**
```
[Kullanıcı mesajına reply]
!sil
```

**Özellikler:**
- Reply ile çalışır
- Komut mesajı otomatik silinir
- Hata durumunda bilgilendirme mesajı gösterilir

---

### 2. **Mute Kaldırma - `!mkaldir` veya `!mkaldır`**

**Kullanım:**
- Bir mesaja yanıt vererek `!mkaldir` yazın
- Veya kullanıcıyı etiketleyerek `!mkaldir` yazın

**Yetki:** Mod veya Admin

**Örnek:**
```
[Kullanıcı mesajına reply]
!mkaldir
```

**Özellikler:**
- Reply veya mention ile çalışır
- Kullanıcının tüm izinleri geri verilir
- Bildirim mesajı gösterilir
- Komut mesajı otomatik silinir

---

### 3. **Susturma - `!sustur süre`**

**Kullanım:**
- Bir mesaja yanıt vererek `!sustur SÜRE` yazın
- Veya kullanıcıyı etiketleyerek `!sustur SÜRE @kullanıcı` yazın

**Parametreler:**
- `SÜRE`: Dakika cinsinden (pozitif sayı)

**Yetki:** Mod veya Admin

**Örnekler:**
```
[Kullanıcı mesajına reply]
!sustur 10

!sustur 30 @username
```

**Özellikler:**
- Reply veya mention ile çalışır
- Süre dakika cinsinden belirtilir
- Kullanıcı belirtilen süre boyunca susturulur
- Bildirim mesajı gösterilir
- Komut mesajı otomatik silinir
- Kendini susturamaz

---

## Teknik Detaylar

### Database Yapısı

Moderatorlar `moderators` tablosunda saklanır:

```sql
CREATE TABLE moderators (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    added_by BIGINT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT
)
```

### Yetki Kontrolü

Tüm mod komutları `is_moderator()` fonksiyonu ile kontrol edilir:

```python
async def is_moderator(user_id: int) -> bool:
    """Kullanıcı mod mu kontrol et"""
    moderators = await get_moderators_from_db()
    return any(mod['user_id'] == user_id for mod in moderators)
```

### Yeni Fonksiyonlar

**`unmute_user()`** - `handlers/punishment_system.py`:
- Kullanıcının mute'unu kaldırır
- Tüm izinleri geri verir
- Mod veya Owner yetkisi gerekir

---

## Komut Özeti

| Komut | Kullanım | Yetki | Açıklama |
|-------|----------|-------|----------|
| `!sil` | Reply ile | Mod/Admin | Mesaj silme |
| `!mkaldir` | Reply/Mention | Mod/Admin | Mute kaldırma |
| `!sustur SÜRE` | Reply/Mention | Mod/Admin | Susturma (dakika) |

---

## Güvenlik Özellikleri

1. **Yetki Kontrolü:** Tüm komutlar mod/admin kontrolü yapar
2. **Rate Limiting:** Mute işlemleri için rate limiting var (1 dakikada 5'ten fazla mute → kötü niyetli kullanıcı)
3. **Hata Yönetimi:** Tüm komutlarda try-except blokları var
4. **Loglama:** Tüm işlemler loglanır

---

## Örnek Senaryolar

### Senaryo 1: Mesaj Silme
1. Mod → Bir mesaja reply yapar
2. Mod → `!sil` yazar
3. Sistem → Mesajı siler
4. Sistem → Komut mesajını siler

### Senaryo 2: Mute Kaldırma
1. Mod → Bir mesaja reply yapar
2. Mod → `!mkaldir` yazar
3. Sistem → Kullanıcının mute'unu kaldırır
4. Sistem → Bildirim gösterir

### Senaryo 3: Susturma
1. Mod → Bir mesaja reply yapar
2. Mod → `!sustur 10` yazar
3. Sistem → Kullanıcıyı 10 dakika susturur
4. Sistem → Bildirim gösterir

---

## İlgili Dosyalar

- **`handlers/mod_handler.py`**: Mod komutları
- **`handlers/punishment_system.py`**: Mute/unmute fonksiyonları
- **`database.py`**: Moderators tablosu

---

**Hazırlayan:** AI Assistant  
**Tarih:** 2025-11-15

