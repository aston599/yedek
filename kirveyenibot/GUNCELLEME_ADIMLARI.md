# 🔄 KirveBot Güncelleme Adımları

## 📋 Yapılan Değişiklikler

### ✅ 1. Config Güncellemeleri
- **ADMIN_USER_ID:** `8154732274` → `8521478746` (Mike)
- **APPROVED_GROUP_LINK:** Yeni +18 grup linki güncellendi
- **BOT_VERSION:** `v2.1.0` → `v2.2.0`
- **LAST_UPDATE:** `2025-12-01`

---

## 🚀 Sunucuda Çalıştırılacak Komutlar

### 📂 Adım 1: Ana dizine git
```bash
cd /root/kirveyenibot
```

### 📥 Adım 2: GitHub'dan güncellemeleri çek
```bash
git pull origin main
```

**VEYA** manuel olarak dosyaları güncelleyin (Git kullanmıyorsanız).

### 🛑 Adım 3: Botu durdur
```bash
systemctl stop kirvebot
```

### 🗄️ Adım 4: Veritabanına yeni admin ekle
```bash
python3 add_new_admin.py
```

Bu komut:
- ✅ Yeni admin'i (Mike - 8521478746) veritabanına ekler
- ✅ Mevcut adminleri listeler
- ✅ İşlem sonucunu gösterir

### 🔄 Adım 5: Botu başlat
```bash
systemctl start kirvebot
```

### ✅ Adım 6: Durumu kontrol et
```bash
systemctl status kirvebot
```

### 📊 Adım 7: Logları izle
```bash
journalctl -u kirvebot -f --lines=50
```

---

## 🧪 Test Adımları

### 1. Bot'a mesaj gönderin:
```
/start
```

### 2. Yeni admin ID'nizi kontrol edin:
```
/benkim
```

**Beklenen Çıktı:**
```
👤 Ad: Mike
📝 Kullanıcı Adı: @mikedahjenkoy
🆔 ID: 8521478746
```

### 3. Admin komutlarını test edin:
```
/adminyardim
/adminler
/bekleyenler
```

### 4. Yeni grup linkini test edin:
Bot'tan başvuru yapıp onaylandığında yeni linke yönlendirme olmalı.

---

## ⚠️ Sorun Giderme

### Bot başlamıyorsa:

**1. Log kontrol:**
```bash
journalctl -u kirvebot -n 100 --no-pager
```

**2. Manuel başlatma testi:**
```bash
cd /root/kirveyenibot
python3 bot.py
```

**3. Python process kontrol:**
```bash
ps aux | grep python
```

**4. Port kontrol:**
```bash
netstat -tulpn | grep 8001
```

### Veritabanı hatası alırsanız:

**Yedek geri yükleme:**
```bash
cp bot_database_backup.db bot_database.db
python3 add_new_admin.py
```

---

## 📝 Notlar

1. ✅ **Bot token değişmedi** - Aynı token kullanılıyor
2. ✅ **Bot2'ye dokunulmadı** - Sadece ana bot güncellendi
3. ✅ **Eski admin** veritabanında kalabilir (sorun yaratmaz)
4. ✅ **Yeni +18 grup linki** aktif durumda: https://t.me/+2lBm39eukKpiYmYy

---

## 🔗 Önemli Bilgiler

**Ana Bot Bilgileri:**
- Token: `8391790953:AAHBpJ3gfc-ugO9LE3iSoX2OOl0JKIcQ9-c`
- Port: `8001`
- Service: `kirvebot.service`
- Dizin: `/root/kirveyenibot`

**Yeni Admin:**
- Ad: Mike
- Username: @mikedahjenkoy
- ID: 8521478746

**Yeni Grup:**
- Link: https://t.me/+2lBm39eukKpiYmYy
- Tip: +18 Özel Kanal

---

## ✨ Güncelleme Sonrası

Başarılı güncelleme sonrası bot şunları yapmalı:

1. ✅ Yeni admin ID'yi tanımalı
2. ✅ Admin komutlarına erişim vermeli
3. ✅ Onaylanan kullanıcıları yeni grup linkine yönlendirmeli
4. ✅ Tüm özellikler çalışır durumda olmalı

---

**Son Güncelleme:** 2025-12-01  
**Güncelleme Türü:** Admin ve Grup Linki Değişikliği  
**Versiyon:** v2.2.0

