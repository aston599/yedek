# 🌸 Kirve Rebekka Karakter Güncellemesi

## Yapılan Değişiklikler

### 1. **Bot İsimleri ve Referanslar**

**Güncellenen Dosya:** `handlers/chat_system.py`

- Bot mention'larına "rebekka" ve "rebekah" eklendi
- Bot artık "Kirve Rebekka" olarak tanınıyor
- Dokümantasyon güncellendi

### 2. **Flörtleşme Özelliği (Nadir, Abartmadan)**

**Eklenen Özellikler:**
- Flörtleşme cevapları eklendi (nadir kullanılacak)
- Sadece bot'a hitap edildiğinde ve belirli tetikleyiciler varsa çalışır
- %15 ihtimalle aktif olur (nadir)

**Flörtleşme Tetikleyicileri:**
- "güzel", "tatlı", "seksi", "harika", "mükemmel"
- "aşkım", "bebeğim", "canım", "tatlım", "güzelim", "sevgilim"

**Flörtleşme Cevapları:**
- "Haha, şakacı seni 😊"
- "Ay, ne tatlısın 😉"
- "Vay be, iltifat mı bu? 😄"
- "Teşekkürler, sen de çok naziksin 😊"
- "Haha, güzel konuşuyorsun 😉"
- "Ay, böyle konuşma beni utandırıyorsun 😊"
- "Teşekkürler, sen de harikasın 😄"
- "Haha, ne kadar tatlısın 😉"

### 3. **Karakter Özellikleri**

**Emoji Güncellemeleri:**
- Daha kadınsı emojiler eklendi: 💕, 🌸
- Mevcut emojiler korundu: 🙂, 😊, 😉, ✨

**Selamlaşma Güncellemeleri:**
- "nasılsın" cevaplarına daha samimi versiyonlar eklendi:
  - "İyiyim canım, sen nasılsın? 😊"
  - "Çok iyiyim, teşekkürler! Sen? 💎"

## Teknik Detaylar

### Flörtleşme Sistemi

```python
# Flörtleşme cevapları (nadir, abartmadan)
FLIRT_RESPONSES = [
    "Haha, şakacı seni 😊",
    "Ay, ne tatlısın 😉",
    # ... (8 cevap)
]

# Flörtleşme tetikleyicileri
FLIRT_TRIGGERS = [
    "güzel", "tatlı", "seksi", "harika", "mükemmel",
    "aşkım", "bebeğim", "canım", "tatlım", "güzelim", "sevgilim"
]

# Kullanım: Sadece bot'a hitap edildiğinde ve %15 ihtimalle
if is_addressed_to_bot and random.random() < 0.15:
    if any(trigger in text_lower for trigger in FLIRT_TRIGGERS):
        response = choose_diverse_response(message.chat.id, FLIRT_RESPONSES)
```

### Bot Mention Güncellemesi

```python
bot_mentions = [
    "bot", "kirve", "kirvehub", 
    "rebekka", "rebekah",  # YENİ
    "@kirvehub_bot", "@kirvelastbot"
]
```

## Özellikler

✅ **Nadir Flörtleşme:** Sadece %15 ihtimalle ve bot'a hitap edildiğinde
✅ **Abartısız:** Nazik ve samimi cevaplar
✅ **Karakter Uyumu:** Kadın karakteri yansıtan emojiler ve ifadeler
✅ **Doğal:** Mevcut sohbet akışını bozmadan

## Örnek Senaryolar

### Senaryo 1: Normal Selamlaşma
**Kullanıcı:** "Merhaba Rebekka!"
**Bot:** "Merhaba! 😊 Nasılsın?"

### Senaryo 2: Flörtleşme (Nadir)
**Kullanıcı:** "Rebekka çok güzelsin"
**Bot:** "Haha, şakacı seni 😊" (veya diğer flörtleşme cevaplarından biri)

### Senaryo 3: Samimi Selamlaşma
**Kullanıcı:** "Nasılsın Rebekka?"
**Bot:** "İyiyim canım, sen nasılsın? 😊"

## Notlar

- Flörtleşme özelliği **nadir** kullanılır (%15 ihtimalle)
- Sadece bot'a **hitap edildiğinde** çalışır
- **Abartısız** ve **nazik** cevaplar
- Mevcut sohbet sistemi korunur

---

**Hazırlayan:** AI Assistant  
**Tarih:** 2025-11-15  
**Karakter:** Kirve Rebekka 🌸

