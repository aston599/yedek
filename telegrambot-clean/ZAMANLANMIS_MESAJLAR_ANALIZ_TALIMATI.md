# 📅 Zamanlanmış Mesajlar Analiz Talimatı

## 🚀 Script Çalıştırma

### Windows'ta Çalıştırma:

**Yöntem 1: main.py ile (Önerilen)**
```bash
python main.py --analyze
```

**Yöntem 2: Direkt Script**
```bash
python show_scheduled_messages.py
```

**Yöntem 3: Python Launcher ile**
```bash
py show_scheduled_messages.py
```

---

## 📊 Script Çıktısı

Script şunları gösterecek:

1. **Tablo Yapısı** - `scheduled_messages_settings` tablosunun yapısı
2. **Mevcut Ayarlar** - Oluşturulma ve güncelleme tarihleri
3. **Aktif Botlar** - Hangi botların aktif olduğu
4. **Bot Profilleri** - Bot ID'leri, mesajlar, linkler, interval'ler, gruplar
5. **Otomatik Komutlar** - Mod, market, site komutları ve ayarları
6. **Gruplar** - Mesaj gönderilecek grup ID'leri
7. **Son Mesaj Zamanları** - Her bot için son mesaj gönderilme zamanı
8. **Otomatik Komutlar - Son Gönderilme** - Otomatik komutların son gönderilme zamanları
9. **Tüm JSON Yapısı** - Güzel formatta tüm ayarlar
10. **Özet İstatistikler** - Toplam sayılar ve özetler

---

## 🔍 Mevcut Sistem

### Database Tablosu:
- **Tablo:** `scheduled_messages_settings`
- **ID:** 1 (sabit)
- **Format:** JSONB

### JSON Yapısı:
```json
{
    "active_bots": {
        "bot_id": true/false
    },
    "groups": [group_id1, group_id2, ...],
    "last_message_time": {
        "bot_id": "2025-01-14T10:00:00"
    },
    "bot_profiles": {
        "bot_id": {
            "message": "Mesaj metni",
            "link": "https://example.com",
            "link_text": "Linke Git",
            "image": "https://example.com/image.jpg",
            "interval": 30,
            "groups": [group_id1, group_id2]
        }
    },
    "auto_commands": {
        "mod": {
            "message_text": "...",
            "interval_minutes": 120,
            "is_active": true
        },
        "market": {...},
        "site": {...}
    },
    "auto_commands_last_sent": {
        "mod": "2025-01-14T10:00:00",
        "market": "...",
        "site": "..."
    }
}
```

---

## 📝 Notlar

- Script sadece okuma yapar, hiçbir değişiklik yapmaz
- Database bağlantısı `config.py`'den alınır
- Hata durumunda detaylı traceback gösterilir

---

**Hazırlayan:** AI Assistant  
**Tarih:** 2025-01-14

