# 📅 Zamanlanmış ve Otomatik Mesajlar Analizi

## 🔍 Mevcut Durum

### Database Tablosu: `scheduled_messages_settings`

**Yapı:**
```sql
CREATE TABLE scheduled_messages_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**JSON Yapısı:**
```json
{
    "active_bots": {
        "bot_id_1": true,
        "bot_id_2": false
    },
    "groups": [123456789, -1001234567890],
    "last_message_time": {
        "bot_id_1": "2025-01-14T10:00:00",
        "bot_id_2": "2025-01-14T09:00:00"
    },
    "bot_profiles": {
        "bot_id_1": {
            "message": "Mesaj metni",
            "link": "https://example.com",
            "link_text": "Linke Git",
            "image": "https://example.com/image.jpg",
            "interval": 30,
            "groups": [123456789]
        }
    },
    "auto_commands": {
        "command_name": {
            "enabled": true,
            "interval": 60,
            "groups": [123456789]
        }
    },
    "auto_commands_last_sent": {
        "command_name": "2025-01-14T10:00:00"
    }
}
```

---

## 📊 Analiz Script'i

**Dosya:** `database/show_scheduled_messages.sql`

Bu script ile:
1. ✅ Tablo yapısını görebilirsiniz
2. ✅ Mevcut ayarları görebilirsiniz
3. ✅ Aktif botları listeleyebilirsiniz
4. ✅ Bot profillerini görebilirsiniz
5. ✅ Otomatik komutları görebilirsiniz
6. ✅ Grupları listeleyebilirsiniz
7. ✅ Son mesaj zamanlarını görebilirsiniz
8. ✅ Tüm JSON yapısını güzel formatta görebilirsiniz

---

## 🚀 Kullanım

### 1. SQL Script'ini Çalıştır

```sql
\i database/show_scheduled_messages.sql
```

### 2. Veya Manuel Sorgu

```sql
-- Basit görüntüleme
SELECT jsonb_pretty(settings) 
FROM scheduled_messages_settings 
WHERE id = 1;
```

---

## 📋 Sonraki Adımlar

1. ✅ SQL'deki mevcut verileri analiz et
2. ⏳ Zamanlanmış mesaj sistemini baştan düzenle
3. ⏳ Otomatik mesaj sistemini iyileştir
4. ⏳ Chat sistemi ile entegrasyon kontrolü

---

**Hazırlayan:** AI Assistant  
**Tarih:** 2025-01-14

