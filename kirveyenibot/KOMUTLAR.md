# 🤖 KirveKing Bot - Komut Listesi

## 👤 KULLANICI KOMUTLARI

### `/start`
Üyelik başvurusunu başlatır
- Site seçimi (Merso Bahis / AMG Bahis)
- Ekran görüntüsü yükleme
- Kullanıcı adı girişi

### `/durumum`
Başvuru durumunuzu gösterir
- Bekliyor / Onaylandı / Reddedildi

### `/benkim`
Telegram User ID'nizi öğrenin

### `/yardim` veya `/help`
Kullanıcı komutlarını gösterir

---

## 👨‍💼 ADMIN KOMUTLARI

### 📋 BAŞVURU YÖNETİMİ

#### `/bekleyenler [sayfa/arama]`
Bekleyen başvuruları listele
- `/bekleyenler` → İlk 10 başvuru
- `/bekleyenler 2` → 2. sayfa
- `/bekleyenler kirve` → Arama

#### `/onayla [id]`
Başvuruyu onayla
- Örnek: `/onayla 1`
- Kullanıcıya bildirim gönderilir

#### `/reddet [id]`
Başvuruyu reddet
- Örnek: `/reddet 1`
- Red nedeni seçimi

#### `/gecmis [sayfa/arama]`
Onaylanan başvuruları göster

#### `/topluonayla [id1,id2,id3...]`
Birden fazla başvuruyu onayla (max 20)
- Örnek: `/topluonayla 1,2,3,4,5`

#### `/toplureddet [id1,id2,id3...]`
Birden fazla başvuruyu reddet (max 20)
- Örnek: `/toplureddet 1,2,3`

---

### 📝 NOT SİSTEMİ

#### `/not [başvuru_id] [not]`
Başvuruya not ekle
- Örnek: `/not 1 Kullanıcı doğrulandı`

#### `/notlar [başvuru_id]`
Başvuru notlarını göster

---

### 📊 İSTATİSTİK VE RAPORLAR

#### `/istatistikler`
Detaylı bot istatistikleri
- Toplam/Bekleyen/Onaylı/Reddedilen
- Site bazında dağılım
- Günlük/Haftalık başvurular

#### `/exportexcel`
Tüm başvuruları Excel olarak indir

#### `/profil [user_id]`
Kullanıcı profili ve geçmişi
- Tüm başvurular
- İstatistikler
- Engel durumu

---

### 👥 ADMIN YÖNETİMİ

#### `/adminekle [user_id]`
Yeni admin ekle
- Örnek: `/adminekle 123456789`

#### `/admincikar [user_id]`
Admin yetkisini kaldır

#### `/adminler`
Tüm adminleri listele

---

### 🚫 KULLANICI YÖNETİMİ

#### `/banla [user_id] [sebep]`
Kullanıcıyı engelle
- Örnek: `/banla 123456 Sahte bilgi`

#### `/unban [user_id]`
Engeli kaldır

#### `/banliste`
Engellenmiş kullanıcıları göster

---

### ⚙️ DİĞER

#### `/kirvebasla`
Yetkili gruba hoş geldin mesajı gönder

#### `/adminyardim`
Admin komutlarının detaylı listesi

#### `!cc [sayı]` (Grup içinde)
Mesaj silme (Şu an çalışmıyor - Telegram API sınırlaması)

---

## 🔒 GÜVENLİK ÖZELLİKLERİ

### ✅ Otomatik Kontroller
- **24 Saat Spam Koruması**: Kullanıcılar 24 saat içinde sadece 1 başvuru yapabilir
- **Screenshot Doğrulama**:
  - Dosya boyutu: 10KB - 20MB
  - Format: JPEG, PNG, WEBP
  - Minimum boyut: 200x200 pixel
- **Engel Sistemi**: Engellenmiş kullanıcılar bot kullanamaz
- **Admin Kontrolü**: Sadece yetkili kişiler admin komutlarını kullanabilir

### 🔔 Bildirimler
- Yeni başvuru geldiğinde tüm adminlere otomatik bildirim
- Onay/Red durumunda kullanıcıya otomatik bildirim

---

## 📚 KULLANIM ÖRNEKLERİ

### Kullanıcı İçin:
```
1. /start → Bot ile başvuruyu başlat
2. Site seç (Merso Bahis / AMG Bahis)
3. Ekran görüntüsü yükle
4. Kullanıcı adını yaz
5. /durumum → Başvuru durumunu kontrol et
```

### Admin İçin:
```
1. /bekleyenler → Bekleyen başvuruları gör
2. /onayla 1 → 1 numaralı başvuruyu onayla
   VEYA
   /reddet 1 → 1 numaralı başvuruyu reddet
3. /not 1 Kontrol edildi → Başvuruya not ekle
4. /istatistikler → Genel durumu gör
```

### Toplu İşlem Örneği:
```
/topluonayla 1,2,3,4,5 → 5 başvuruyu birden onayla
/toplureddet 6,7,8 → 3 başvuruyu birden reddet
```

---

## 🎯 ÖNEMLİ NOTLAR

1. **Tüm admin komutları** bot özelinden çalışır
2. **Sayfalama**: Her sayfada 10 başvuru gösterilir
3. **Arama**: ID, username veya site username ile arama yapılabilir
4. **Toplu İşlemler**: Tek seferde en fazla 20 başvuru işlenebilir
5. **Excel Export**: Tüm başvuru verilerini içerir

---

## 💡 İPUCU

Hangi komutları kullanabileceğinizi görmek için:
- Kullanıcıysanız: `/yardim`
- Adminseniz: `/adminyardim`

