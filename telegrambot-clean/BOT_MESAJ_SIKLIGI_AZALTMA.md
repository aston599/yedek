# 🤐 Bot Mesaj Sıklığı Azaltma

## Yapılan Değişiklikler

Botun çok fazla mesaj vermesini önlemek için tüm olasılıklar ve cooldown süreleri azaltıldı.

### 1. **Genel Rastgele Cevap Olasılığı**

**Önceki:** `chat_probability = 0.02` (%2)
**Yeni:** `chat_probability = 0.005` (%0.5)

**Değişiklik:** %75 azalma (4 kat daha nadir)

### 2. **Grup Soruları Olasılığı**

**Önceki:** `GROUP_QUESTION_PROBABILITY = 0.25` (%25)
**Yeni:** `GROUP_QUESTION_PROBABILITY = 0.10` (%10)

**Değişiklik:** %60 azalma (2.5 kat daha nadir)

### 3. **Kirve Mention Olasılığı**

**Önceki:** `KIRVE_MENTION_PROBABILITY = 0.2` (%20)
**Yeni:** `KIRVE_MENTION_PROBABILITY = 0.15` (%15)

**Önceki Cooldown:** 180 saniye (3 dakika)
**Yeni Cooldown:** 300 saniye (5 dakika)

**Değişiklik:** %25 azalma + cooldown artışı

### 4. **Flörtleşme Olasılığı**

**Önceki:** %15 ihtimalle
**Yeni:** %8 ihtimalle

**Değişiklik:** %47 azalma (neredeyse yarı yarıya)

### 5. **Pozitif Mesaj Cevapları**

**Önceki:** %0.5 ihtimalle
**Yeni:** %0.2 ihtimalle

**Değişiklik:** %60 azalma (2.5 kat daha nadir)

### 6. **Genel Mesaj Cooldown**

**Önceki:** 300 saniye (5 dakika)
**Yeni:** 600 saniye (10 dakika)

**Değişiklik:** 2 kat daha uzun cooldown

## Yeni Olasılık Tablosu

| Özellik | Önceki | Yeni | Değişiklik |
|---------|--------|------|------------|
| Genel rastgele cevap | %2 | %0.5 | ↓ %75 |
| Grup soruları | %25 | %10 | ↓ %60 |
| Kirve mention | %20 | %15 | ↓ %25 |
| Flörtleşme | %15 | %8 | ↓ %47 |
| Pozitif mesajlar | %0.5 | %0.2 | ↓ %60 |
| Genel cooldown | 5 dk | 10 dk | ↑ 2x |
| Kirve mention cooldown | 3 dk | 5 dk | ↑ 1.67x |

## Sonuç

Bot artık **çok daha nadir** mesaj gönderecek:
- ✅ Genel rastgele cevaplar 4 kat daha nadir
- ✅ Grup soruları 2.5 kat daha nadir
- ✅ Flörtleşme cevapları neredeyse yarı yarıya azaldı
- ✅ Cooldown süreleri artırıldı
- ✅ Sadece bot'a hitap edildiğinde daha aktif olacak

## Notlar

- Bot hala bot'a hitap edildiğinde (selamlaşma, sorular) normal şekilde cevap verecek
- Rastgele mesajlar çok nadir olacak
- Cooldown sistemi botun spam yapmasını engelliyor

---

**Hazırlayan:** AI Assistant  
**Tarih:** 2025-11-15

