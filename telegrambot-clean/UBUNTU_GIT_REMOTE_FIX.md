# Ubuntu Git Remote Hatası Çözümü

## Hata
```
fatal: 'origin' does not appear to be a git repository
```

## Çözüm

### 1. Mevcut remote'ları kontrol et
```bash
git remote -v
```

### 2. Eğer remote yoksa, ekle
```bash
git remote add origin https://github.com/aston599/telegrambot.git
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

## Alternatif: Repository'yi Yeniden Clone Et

Eğer yukarıdaki çözüm işe yaramazsa:

```bash
# Mevcut dizini yedekle
cd /home/kirvehub
mv telegrambot-clean telegrambot-clean-backup

# Repository'yi yeniden clone et
git clone https://github.com/aston599/telegrambot.git telegrambot-clean

# Virtual environment'i yeniden kur
cd telegrambot-clean
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# .env dosyasını kopyala (yedekten)
cp ../telegrambot-clean-backup/.env .

# Bot'u başlat
sudo systemctl restart kirvehub-bot-clean
sudo systemctl status kirvehub-bot-clean
```

---

## Tek Komutla Remote Ekleme ve Pull
```bash
git remote add origin https://github.com/aston599/telegrambot.git && \
git pull origin main && \
pip install -r requirements.txt && \
sudo systemctl restart kirvehub-bot-clean && \
sudo systemctl status kirvehub-bot-clean
```

