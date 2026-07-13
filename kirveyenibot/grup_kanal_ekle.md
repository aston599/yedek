# Grup ve Kanal ID'lerini Alma Rehberi

## 1️⃣ **GRUP ID'sini Öğrenme:**

### Yöntem 1: Bot ile
1. Botu gruba ekle (admin yap)
2. Grupta `/grupid` komutunu yaz
3. Bot sana grup ID'sini gönderecek

### Yöntem 2: Manuel
1. Telegram Web'de grubu aç: https://web.telegram.org
2. URL'deki sayıya bak: `/#/im?p=g1234567890`
3. `g` harfinden sonraki sayı grup ID'si
4. Başına `-100` ekle: `-1001234567890`

## 2️⃣ **KANAL ID'sini Öğrenme:**

### Yöntem 1: Bot ile
1. Botu kanala admin olarak ekle
2. Kanalda herhangi bir mesajı bota forward et
3. Bot sana kanal ID'sini söyleyecek

### Yöntem 2: @username_to_id_bot
1. Telegram'da bu botu bul
2. Kanal linkini gönder
3. Bot sana ID'yi verecek

## 3️⃣ **CONFIG'e Ekleme:**

### `config.py` dosyasını aç:

```python
# Yetkili grup ID'si - SABİT - sadece bu grup
AUTHORIZED_GROUP_ID = -1003124612051  # KirveHub +18 grubu

# İstersenn birden fazla grup ekleyebilirsiniz
AUTHORIZED_GROUPS = [
    -1003124612051,  # Ana grup
    -1001234567890,  # İkinci grup
    -1009876543210,  # Üçüncü grup
]

# Kanal ID'leri
NOTIFICATION_CHANNEL = -1001111111111  # Bildirim kanalı
BACKUP_CHANNEL = -1002222222222  # Yedek kanal
```

## 4️⃣ **Bot'u Gruba/Kanala Ekleme:**

1. Bot sahibi olarak botu ekle
2. Botu **ADMIN** yap (önemli!)
3. Gerekli izinleri ver:
   - ✅ Mesaj gönderme
   - ✅ Mesaj silme (gruplarda)
   - ✅ Üyeleri davet etme (kanalda)

## 5️⃣ **Test Etme:**

Grupta:
```
/grupid
/kirvebaslat
```

Kanalda:
```
Bot otomatik çalışacak
```

---

**NOT:** Bot sadece eklendiği grup/kanalların ID'lerini görür. 
Privacy ayarları nedeniyle bazı bilgileri alamayabilir.

