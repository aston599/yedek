# Ubuntu Git Token Authentication Çözümü

## Hata
```
remote: Invalid username or token. Password authentication is not supported for Git operations.
```

## Çözüm: Remote URL'yi Token ile Güncelle

### 1. Mevcut remote'u kaldır
```bash
git remote remove origin
```

### 2. Token ile remote ekle
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

### 5. Tüm işlemleri tamamla
```bash
pip install -r requirements.txt
sudo systemctl restart kirvehub-bot-clean
sudo systemctl status kirvehub-bot-clean
```

---

## Alternatif: Git Credential Helper Kullan

### 1. Credential helper'ı ayarla
```bash
git config --global credential.helper store
```

### 2. Remote URL'yi güncelle (token ile)
```bash
git remote set-url origin https://[REDACTED]@github.com/aston599/telegrambot.git
```

### 3. Pull yap
```bash
git pull origin main
```

---

## Tek Komutla Tüm İşlemler
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

- Token'ı URL'de kullanmak güvenli değildir (history'de görünebilir)
- Daha güvenli yöntem: SSH key kullanmak veya credential helper
- Token'ı `.git/config` dosyasında saklamak yerine credential helper kullanın

