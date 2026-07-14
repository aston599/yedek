# 📅 SQL'den Çıkartılan Zamanlanmış Mesajlar Özeti

## 📊 Genel Bilgiler

- **Oluşturulma:** 2025-07-31 03:41:34
- **Son Güncelleme:** 2025-11-13 11:14:40
- **Backup Dosyası:** `scheduled_messages_sql_backup.json`

---

## 🤖 Aktif Botlar (3 adet)

1. **bot_1753833578** - ✅ Aktif
2. **bot_1754124395** - ✅ Aktif (Kayıt botu)
3. **bot_1754193607** - ✅ Aktif (Kirve Site botu)

---

## 👤 Bot Profilleri (2 adet)

### 1. bot_1754124395 (Kayıt)
- **Mesaj:** "Kirvelerim artık sohbet ederek Kirve Point kazan, market üzerinden kullan! Detaylar için özel mesajdan bana ulaş."
- **Link:** `https://www.kumarlayasiyorum9.com` ⚠️ **ESKİ URL**
- **Link Text:** "GÜVENİLİR SİTELERİMİZ"
- **Interval:** 50 dakika
- **Grup:** `-1002231486317`
- **Durum:** `active: false` (ama `active_bots` içinde `true`)

### 2. bot_1754193607 (Kirve Site)
- **Mesaj:** "Kirvelerim güvenli sitelerimize erişmek için aşağıda olan bağlantıya girin."
- **Link:** `https://www.kumarlayasiyorum9.com` ⚠️ **ESKİ URL**
- **Link Text:** "GÜVENİLİR SİTELER"
- **Interval:** 70 dakika
- **Grup:** `-1002231486317`
- **Durum:** `active: false` (ama `active_bots` içinde `true`)

---

## ⚙️ Otomatik Komutlar (3 adet - Hepsi Aktif)

### 1. mod
- **Durum:** ✅ Aktif
- **Interval:** 120 dakika (2 saat)
- **Mesaj:** "🛡️ **Aktif Modları Görmek İçin:**\n\n`!mod` veya `!modlar` yazarak aktif modları görebilirsiniz."

### 2. site
- **Durum:** ✅ Aktif
- **Interval:** 60 dakika (1 saat)
- **Mesaj:** "🌐 **Siteleri Görmek İçin:**\n\n`!site` veya `!siteler` yazarak siteleri görebilirsiniz."

### 3. market
- **Durum:** ✅ Aktif ⚠️ **BAKIMDA OLMALI**
- **Interval:** 60 dakika (1 saat)
- **Mesaj:** "🛍️ **Market'e Ulaşmak İçin:**\n\n`!market` yazarak markete ulaşabilirsiniz."

---

## ⏰ Son Mesaj Zamanları

- **bot_1753833578:** 2025-08-02 08:46:20 (Eski - 3+ ay önce)
- **bot_1754124395:** 2025-11-14 17:35:33 (Yakın zamanda)
- **bot_1754193607:** 2025-11-14 16:42:06 (Yakın zamanda)

---

## 📨 Otomatik Komutlar - Son Gönderilme Zamanları

⚠️ **Kayıt yok** - Otomatik komutların son gönderilme zamanları takip edilmiyor.

---

## 🔍 Tespit Edilen Sorunlar

1. ❌ **URL'ler Eski:** `kumarlayasiyorum9.com` → `kirve1.com` olmalı
2. ❌ **Market Komutu Aktif:** Market bakımda ama komut hala aktif
3. ❌ **Bot Profil Tutarsızlığı:** `active: false` ama `active_bots` içinde `true`
4. ❌ **Gruplar Listesi Boş:** `groups` array'i boş ama bot profillerinde grup var
5. ❌ **Otomatik Komut Takibi Yok:** `auto_commands_last_sent` boş

---

## 📋 Yapılacaklar

1. ✅ SQL'den veriler çıkartıldı
2. ⏳ URL'leri güncelle (`kirve1.com`)
3. ⏳ Market komutunu devre dışı bırak
4. ⏳ Bot profillerini düzenle
5. ⏳ Otomatik komut sistemini iyileştir
6. ⏳ Chat sistemi ile entegrasyon kontrolü

---

**Hazırlayan:** AI Assistant  
**Tarih:** 2025-01-14

