# Ubuntu DigitalOcean - Git Pull ve Güncelleme Komutları

## 1. Sunucuya Bağlan
```bash
ssh root@your-server-ip
```

## 2. Bot Dizinine Git
```bash
cd /home/kirvehub/telegrambot-clean
```

## 3. Git Pull (Değişiklikleri Çek)
```bash
git pull origin main
```

## 4. Virtual Environment'i Aktif Et
```bash
source venv/bin/activate
```

## 5. Gerekirse Bağımlılıkları Güncelle
```bash
pip install -r requirements.txt
```

## 6. Bot'u Yeniden Başlat
```bash
sudo systemctl restart kirvehub-bot-clean
```

## 7. Bot Durumunu Kontrol Et
```bash
sudo systemctl status kirvehub-bot-clean
```

## 8. Logları İzle (İsteğe Bağlı)
```bash
sudo journalctl -u kirvehub-bot-clean -f
```

---

## Tek Komutla Tüm İşlemler
```bash
cd /home/kirvehub/telegrambot-clean && \
source venv/bin/activate && \
git pull origin main && \
pip install -r requirements.txt && \
sudo systemctl restart kirvehub-bot-clean && \
sudo systemctl status kirvehub-bot-clean
```

---

## Hata Durumunda

### Git Pull Çakışması
```bash
git stash
git pull origin main
git stash pop
```

### Veya Hard Reset (DİKKAT: Yerel değişiklikleri siler)
```bash
git fetch origin
git reset --hard origin/main
```

### Bot Başlamıyorsa
```bash
# Logları kontrol et
sudo journalctl -u kirvehub-bot-clean -n 50 --no-pager

# Python path kontrolü
which python
which python3

# Virtual environment kontrolü
ls -la venv/bin/python
```

---

**Not:** Tüm komutları root kullanıcısı olarak çalıştırın veya `sudo` kullanın.

