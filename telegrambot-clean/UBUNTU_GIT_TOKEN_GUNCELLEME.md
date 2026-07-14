# Ubuntu Git Token Güncelleme

## Yeni Token ile Remote URL Güncelle

### 1. Mevcut remote'u kaldır
```bash
git remote remove origin
```

### 2. Yeni token ile remote ekle
```bash
git remote add origin https://[REDACTED]@github.com/aston599/telegrambot.git
```

### 3. Remote'u kontrol et
```bash
git remote -v
```

### 4. Şimdi git pull yap
```bash
git pull origin main
```

---

## Alternatif: Git Credential Helper Kullan (Daha Güvenli)

### 1. Credential helper'ı ayarla
```bash
git config --global credential.helper store
```

### 2. Remote URL'yi güncelle (token olmadan)
```bash
git remote set-url origin https://github.com/aston599/telegrambot.git
```

### 3. İlk pull'da token'ı gireceksiniz (sadece bir kez)
```bash
git pull origin main
# Username: aston599 (veya token)
# Password: [REDACTED]
```

### 4. Sonraki pull'larda otomatik çalışacak

---

## Tek Komutla Tüm İşlemler (Yeni Token ile)
```bash
git remote remove origin && \
git remote add origin https://[REDACTED]@github.com/aston599/telegrambot.git && \
git pull origin main && \
pip install -r requirements.txt && \
sudo systemctl restart kirvehub-bot-clean && \
sudo systemctl status kirvehub-bot-clean
```

---

## Notlar

- Token URL'de görünecek (history'de kalabilir)
- Daha güvenli: SSH key kullanmak
- Token'ı `.git/config` dosyasında saklamak yerine credential helper kullanın

