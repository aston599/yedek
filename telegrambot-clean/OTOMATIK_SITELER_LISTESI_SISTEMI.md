# Otomatik Siteler Listesi Sistemi

## Özellik

Her 10 dakikada bir, birisi gruba mesaj yazdığında otomatik olarak siteler listesi grupta gösterilir.

## Nasıl Çalışır?

1. **Birisi gruba mesaj yazıyor** (komut değil, normal mesaj)
2. **Sistem kontrol ediyor:**
   - Son 10 dakikada bu grup için siteler listesi gösterilmiş mi?
   - Gösterilmemişse → Otomatik göster
   - Gösterilmişse → Gösterme (10 dakika bekle)

## Teknik Detaylar

### Dosyalar

**`handlers/site_manager.py`:**
- `show_site_list_auto()`: Otomatik siteler listesi gösterim fonksiyonu
- `_last_site_list_shown`: Son gösterilme zamanlarını tutan dictionary
- `SITE_LIST_AUTO_INTERVAL_MINUTES = 10`: Interval (10 dakika)

**`handlers/message_monitor.py`:**
- `monitor_group_message()`: Her grup mesajında otomatik kontrol yapıyor

### Çalışma Mantığı

```python
# Her grup mesajında:
1. monitor_group_message() çağrılır
2. show_site_list_auto(group_id) çağrılır
3. Son gösterilme zamanı kontrol edilir
4. 10 dakika geçmişse → Liste gösterilir
5. Zaman kaydedilir
```

### Zaman Takibi

- **Memory-based:** `_last_site_list_shown` dictionary'sinde tutuluyor
- **Grup bazlı:** Her grup için ayrı zaman takibi
- **10 dakika interval:** `SITE_LIST_AUTO_INTERVAL_MINUTES = 10`

### Özellikler

- ✅ Sadece grupta çalışır (özel mesajlarda çalışmaz)
- ✅ Bot mesajları yoksayılır
- ✅ Kayıtlı gruplarda çalışır
- ✅ 10 dakika interval kontrolü
- ✅ Aynı liste formatı (!siteler ile aynı)

## Örnek Senaryo

1. **15:00** - Kullanıcı gruba mesaj yazıyor → Liste gösteriliyor
2. **15:05** - Başka kullanıcı yazıyor → Liste gösterilmiyor (5 dakika geçti, 10 dakika bekleniyor)
3. **15:11** - Başka kullanıcı yazıyor → Liste gösteriliyor (11 dakika geçti, 10 dakikadan fazla)

## Ayarlar

**Interval değiştirmek için:**
```python
# handlers/site_manager.py
SITE_LIST_AUTO_INTERVAL_MINUTES = 10  # 10 dakika (değiştirilebilir)
```

## Notlar

- Liste formatı `!siteler` komutu ile aynı
- Tüm butonlar ve linkler çalışıyor
- Bot instance kontrolü yapılıyor
- Hata durumunda sessizce geçiliyor (log ile)

---

**Hazırlayan:** AI Assistant  
**Tarih:** 2025-11-15

