# 📅 Zamanlanmış Mesajlar Yeniden Düzenleme Planı

## 🎯 Hedefler

1. ✅ Otomatik komut sistemi oluştur
2. ✅ !market → Site yönlendirmesi (https://kirve1.com/market)
3. ✅ !site → !siteler, siteye ve sıralamaya yönlendir
4. ✅ URL'leri güncelle (kirve1.com)
5. ✅ Interval'ları düzenle
6. ✅ Algoritma: Son mesaj bot ise, birisi yazana kadar bekle

---

## 📋 Yapılacaklar

### 1. Otomatik Komut Sistemi
- `auto_commands` için gönderme mekanizması ekle
- `auto_commands_last_sent` takibi
- Interval kontrolü

### 2. Komut Güncellemeleri
- **!market**: Site yönlendirmesi (https://kirve1.com/market)
- **!siteler**: Site listesi + sıralama yönlendirmesi
- **!mod**: Değişmeden kalacak

### 3. URL Güncellemeleri
- `kumarlayasiyorum9.com` → `kirve1.com`
- Bot profillerindeki linkler
- Otomatik komut mesajlarındaki linkler

### 4. Interval Düzenlemeleri
- Market: 60 → 90 dakika (bakımda olduğu için daha nadir)
- Site: 60 → 90 dakika
- Mod: 120 dakika (değişmeden)

### 5. Algoritma İyileştirmesi
- `group_activity_monitor.py`'deki `check_group_activity()` kullan
- Son mesaj bot ise, birisi yazana kadar zamanlanmış mesaj göndermesin
- Hem bot profilleri hem de otomatik komutlar için geçerli

---

## 🔧 Teknik Detaylar

### Son Mesaj Kontrolü
```python
from handlers.group_activity_monitor import check_group_activity, get_group_last_message_info

# Grup aktivitesini kontrol et
should_send, reason = await check_group_activity(group_id)
if not should_send:
    logger.debug(f"⏸️ Mesaj gönderilmedi - {reason}")
    continue
```

### Otomatik Komut Gönderme
```python
async def send_auto_command(command_name: str, group_id: int):
    """Otomatik komut mesajını gönder"""
    settings = await get_scheduled_settings()
    auto_commands = settings.get('auto_commands', {})
    
    if command_name not in auto_commands:
        return False
    
    cmd_data = auto_commands[command_name]
    if not cmd_data.get('is_active', False):
        return False
    
    # Interval kontrolü
    last_sent = settings.get('auto_commands_last_sent', {}).get(command_name)
    if last_sent:
        # ... interval kontrolü
    
    # Son mesaj kontrolü
    should_send, reason = await check_group_activity(group_id)
    if not should_send:
        return False
    
    # Mesajı gönder
    # ...
```

---

## 📊 Yeni Yapı

### Otomatik Komutlar
```json
{
  "market": {
    "is_active": false,  // Bakımda
    "message_text": "🛍️ **Market'e Ulaşmak İçin:**\n\n🌐 [Web Market'e Git](https://kirve1.com/market)",
    "interval_minutes": 90
  },
  "siteler": {
    "is_active": true,
    "message_text": "🌐 **Siteleri Görmek İçin:**\n\n`!siteler` yazarak siteleri görebilirsiniz.",
    "interval_minutes": 90
  },
  "mod": {
    "is_active": true,
    "message_text": "🛡️ **Aktif Modları Görmek İçin:**\n\n`!mod` veya `!modlar` yazarak aktif modları görebilirsiniz.",
    "interval_minutes": 120
  }
}
```

### Bot Profilleri
```json
{
  "bot_1754124395": {
    "link": "https://kirve1.com",
    "message": "...",
    "interval": 50
  }
}
```

---

**Hazırlayan:** AI Assistant  
**Tarih:** 2025-01-14

