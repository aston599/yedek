# 🚀 Bot Güncelleme Planı - Detaylı

## 📋 Genel Bakış

Bu plan, aşağıdaki ana güncellemeleri içerir:
1. Market sistemini kaldırma ve API entegrasyonu
2. Chat zamanlayıcı sorununu düzeltme
3. Rastgele mesaj sistemini iyileştirme
4. Site URL güncelleme (https://kirve1.com)
5. Puan kazanımlarını market fiyatlarına göre ayarlama

---

## 🎯 1. MARKET SİSTEMİNİ KALDIRMA VE API ENTEGRASYONU

### 1.1 Market Sistemini Kaldırma

**Kaldırılacak Dosyalar:**
- `handlers/market_system.py` (tamamen kaldırılacak)
- `handlers/market_callbacks.py` (tamamen kaldırılacak)
- `handlers/admin_market_management.py` (tamamen kaldırılacak)
- `handlers/admin_market_fix.py` (tamamen kaldırılacak)

**Kaldırılacak Komutlar:**
- `/market` komutu
- Market ile ilgili tüm callback handler'lar
- Market admin komutları

**Database Tabloları:**
- `market_products` (kaldırılmayacak, sadece kullanılmayacak)
- `market_orders` (kaldırılmayacak, sadece kullanılmayacak)
- `market_categories` (kaldırılmayacak, sadece kullanılmayacak)

**Not:** Database tabloları silinmeyecek, sadece bot tarafından kullanılmayacak.

### 1.2 API Entegrasyonu

**Yeni Dosya:** `handlers/api_integration.py`

**Özellikler:**
- HMAC-SHA256 imza sistemi
- Player ID alma (Telegram chat_id ile)
- Puan ekleme/çıkarma
- Bakiye sorgulama
- Transaction geçmişi

**API Endpoint'leri:**
- `POST /api/game/v1/telegram/get-player` - Player ID alma
- `POST /api/game/v1/points/add` - Puan ekleme
- `POST /api/game/v1/points/deduct` - Puan çıkarma
- `GET /api/game/v1/balance/{id}` - Bakiye sorgulama
- `GET /api/game/v1/transactions` - İşlem geçmişi

**Config Ayarları:**
```python
API_BASE_URL = "https://api.r9jrx7mfs12l6szvgqot5.net/api/game/v1"
API_KEY = "YOUR_API_KEY"  # .env'den
API_SECRET = "YOUR_API_SECRET"  # .env'den
```

**Market Butonu:**
- `/market` komutu → Site marketine yönlendirme butonu
- Hesap senkronizasyonu (Telegram chat_id → Player ID)
- Site URL: `https://kirve1.com/market`

### 1.3 Puan Sistemi Entegrasyonu

**Değişiklikler:**
- Tüm puan ekleme/çıkarma işlemleri API üzerinden yapılacak
- Database'deki `users.points` sadece cache olarak kullanılacak
- Her puan işleminde API'ye istek atılacak
- API başarısız olursa fallback mekanizması (database)

---

## 🕐 2. CHAT ZAMANLAYICI SORUNU

### 2.1 Sorun Analizi

**Mevcut Durum:**
- `handlers/scheduled_messages.py` içindeki `scheduled_message_task` fonksiyonu
- Chat sistemi kapalı olsa bile zamanlayıcı mesajlar gönderilmeye devam ediyor
- `chat_system_active` kontrolü zamanlayıcıda yok

### 2.2 Çözüm

**Değişiklikler:**
1. `scheduled_message_task` fonksiyonuna chat sistemi kontrolü ekle
2. Chat kapalıysa zamanlayıcı mesajları gönderme
3. Chat açıldığında zamanlayıcıyı otomatik başlat
4. Chat kapandığında zamanlayıcıyı durdur

**Kod Değişiklikleri:**
```python
# handlers/scheduled_messages.py içinde
async def scheduled_message_task(bot: Bot):
    while scheduled_messages_active:
        # Chat sistemi kontrolü ekle
        from handlers.chat_system import get_chat_status
        if not get_chat_status():
            logger.info("💬 Chat sistemi kapalı, zamanlayıcı mesajlar durduruldu")
            await asyncio.sleep(60)  # 1 dakika bekle
            continue
        # ... mevcut kod
```

---

## 💬 3. RASTGELE MESAJ SİSTEMİNİ İYİLEŞTİRME

### 3.1 Sorun Analizi

**Mevcut Durum:**
- Bot çok rastgele "merhaba" gibi mesajlar atıyor
- Mesaj tekrarı yapıyor
- Mantıklı cevaplar vermiyor

**Sorunlu Dosyalar:**
- `handlers/chat_system.py` - Rastgele cevap sistemi
- `handlers/interactive_features.py` - Komik cevaplar
- `handlers/boss_greeting_system.py` - Patron karşılama

### 3.2 Çözüm

**Değişiklikler:**

1. **Mesaj Tekrarı Önleme:**
   - Son gönderilen mesajları cache'le
   - Aynı mesajı 24 saat içinde tekrar gönderme
   - Kullanıcı bazlı mesaj geçmişi

2. **Mantıklı Cevap Sistemi:**
   - Sadece bot'a yönlendirilmiş mesajlara cevap ver
   - Rastgele cevap olasılığını düşür (%10 → %3)
   - Context-aware cevaplar (mesaj içeriğine göre)

3. **Cooldown Sistemi:**
   - Kullanıcı bazlı cooldown (zaten var, iyileştirilecek)
   - Grup bazlı cooldown (aynı gruba çok sık mesaj gönderme)

4. **Akıllı Filtreleme:**
   - Boş/tekrar mesajları filtrele
   - Spam mesajları yoksay
   - Sadece anlamlı mesajlara cevap ver

**Kod Değişiklikleri:**
- `handlers/chat_system.py` - Rastgele cevap olasılığını düşür
- `handlers/interactive_features.py` - Mesaj tekrarı kontrolü ekle
- Yeni: `handlers/message_history.py` - Mesaj geçmişi yönetimi

---

## 🔗 4. SİTE URL GÜNCELLEME

### 4.1 Değiştirilecek URL'ler

**Eski URL:** `kirvehub.com`, `kumarlayasiyorum9.com`
**Yeni URL:** `https://kirve1.com`

**Değiştirilecek Dosyalar:**
- `handlers/chat_system.py` - +18 kanal linki
- `handlers/site_manager.py` - Site linkleri
- `handlers/dynamic_command_creator.py` - Örnek URL'ler
- `main.py` - Bot linki
- Tüm dokümantasyon dosyaları

**Değişiklikler:**
- Tüm `kirvehub.com` → `kirve1.com`
- Tüm `kumarlayasiyorum9.com` → `kirve1.com`
- HTTP → HTTPS zorunlu

---

## 💰 5. PUAN KAZANIMLARINI AYARLAMA

### 5.1 Market Fiyatları Analizi

**Market Ürünleri (https://kirve1.com/market):**
1. **NAKİT (TRC20):**
   - 1000 TL → K 5000 (1 TL = 5 KP)
   - 2500 TL → K 10000 (1 TL = 4 KP)
   - 5000 TL → K 20000 (1 TL = 4 KP)
   - 10000 TL → K 40000 (1 TL = 4 KP)

2. **DİĞER (Ürünler):**
   - Dyson Airwrap → K 60000
   - MacBook Pro → K 140000
   - PlayStation 5 → K 80000
   - iPhone 17 Pro Max → K 200000

**Ortalama Katsayı:** 1 TL ≈ 4-5 KP

### 5.2 Mevcut Puan Sistemi

**Mevcut:** `points_per_message = 0.04` (mesaj başına 0.04 KP)

**Hesaplama:**
- 1000 mesaj = 40 KP
- 40 KP = 8 TL (1 TL = 5 KP varsayımıyla)
- 1000 mesaj = 8 TL → Çok düşük!

### 5.3 Yeni Puan Sistemi

**Önerilen Katsayılar:**
- **Mesaj başına:** 0.20 KP (0.04 → 0.20, 5x artış)
- **Günlük limit:** 200 KP (50 → 200, 4x artış)
- **Haftalık limit:** 1000 KP (250 → 1000, 4x artış)

**Hesaplama:**
- 1000 mesaj = 200 KP
- 200 KP = 40 TL (1 TL = 5 KP varsayımıyla)
- 1000 mesaj = 40 TL → Daha mantıklı!

**Alternatif (Daha Yüksek):**
- **Mesaj başına:** 0.50 KP
- **Günlük limit:** 500 KP
- **Haftalık limit:** 2500 KP

### 5.4 Mevcut Kullanıcı Bakiyelerini Güncelleme

**Sorun:** Mevcut kullanıcıların bakiyeleri düşük (0.04 KP/mesaj)

**Çözüm:**
1. **Katsayı Uygulama:**
   - Tüm mevcut bakiyeleri 5x ile çarp (0.04 → 0.20 için)
   - Veya 12.5x ile çarp (0.04 → 0.50 için)

2. **API Entegrasyonu:**
   - Mevcut bakiyeleri API'ye senkronize et
   - Her kullanıcı için `player_id` al
   - Bakiye transferi yap

**Örnek:**
```sql
-- Mevcut bakiyeleri 5x ile çarp
UPDATE users 
SET points = points * 5 
WHERE points > 0;
```

---

## 📝 6. YAPILACAKLAR LİSTESİ (TODO)

### Faz 1: Market Kaldırma ve API Entegrasyonu
- [ ] `handlers/api_integration.py` dosyasını oluştur
- [ ] API helper fonksiyonlarını yaz (HMAC-SHA256 imza)
- [ ] Market komutlarını kaldır
- [ ] Market butonunu site yönlendirmesine çevir
- [ ] Puan ekleme/çıkarma işlemlerini API'ye bağla
- [ ] Config'e API ayarlarını ekle

### Faz 2: Chat Zamanlayıcı Düzeltme
- [ ] `scheduled_message_task` fonksiyonuna chat kontrolü ekle
- [ ] Chat kapalıyken zamanlayıcıyı durdur
- [ ] Chat açıldığında zamanlayıcıyı başlat

### Faz 3: Rastgele Mesaj İyileştirme
- [ ] Mesaj tekrarı önleme sistemi ekle
- [ ] Rastgele cevap olasılığını düşür (%10 → %3)
- [ ] Context-aware cevap sistemi
- [ ] Mesaj geçmişi cache sistemi

### Faz 4: URL Güncelleme
- [ ] Tüm `kirvehub.com` → `kirve1.com`
- [ ] Tüm `kumarlayasiyorum9.com` → `kirve1.com`
- [ ] HTTP → HTTPS zorunlu

### Faz 5: Puan Sistemi Güncelleme
- [ ] `points_per_message` değerini güncelle (0.04 → 0.20 veya 0.50)
- [ ] Günlük/haftalık limitleri güncelle
- [ ] Mevcut bakiyeleri katsayı ile çarp
- [ ] API'ye bakiye senkronizasyonu

### Faz 6: Test ve Doğrulama
- [ ] API entegrasyonunu test et
- [ ] Puan ekleme/çıkarma testleri
- [ ] Chat zamanlayıcı testleri
- [ ] Rastgele mesaj testleri
- [ ] URL yönlendirme testleri

---

## ⚠️ ÖNEMLİ NOTLAR

1. **API Güvenliği:**
   - API Secret'ı asla kod içine yazma
   - `.env` dosyasına ekle
   - HMAC-SHA256 imza sistemi zorunlu

2. **Database Uyumluluğu:**
   - Market tabloları silinmeyecek
   - Sadece kullanılmayacak
   - Gelecekte geri dönüş için saklanacak

3. **Geri Dönüş Planı:**
   - Tüm değişiklikler commit'lenmeli
   - Her faz ayrı commit olmalı
   - Rollback için branch oluştur

4. **Kullanıcı Deneyimi:**
   - Market kaldırılırken kullanıcılara bilgi ver
   - Yeni puan sistemi hakkında duyuru yap
   - Site marketine yönlendirme açık olmalı

---

## 🚀 BAŞLANGIÇ ONAYI

Bu planı onaylıyor musunuz? Onayladıktan sonra Faz 1'den başlayacağım.

**Önerilen Başlangıç Sırası:**
1. Faz 1: Market Kaldırma ve API Entegrasyonu
2. Faz 2: Chat Zamanlayıcı Düzeltme
3. Faz 3: Rastgele Mesaj İyileştirme
4. Faz 4: URL Güncelleme
5. Faz 5: Puan Sistemi Güncelleme
6. Faz 6: Test ve Doğrulama

**Soru:**
- Puan katsayısı için hangi değeri tercih edersiniz?
  - **Seçenek A:** 0.20 KP/mesaj (5x artış, orta seviye)
  - **Seçenek B:** 0.50 KP/mesaj (12.5x artış, yüksek seviye)

