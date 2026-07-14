# 🔧 Ubuntu Bot Başlatma Hatası Çözümü

## Sorun
```
Active: activating (auto-restart) (Result: exit-code)
Process: 1946748 ExecStart=/home/kirvehub/telegrambot/venv/bin/python main.py (code=exited, status=1/FAILURE)
```

## Hata Loglarını Kontrol Et

### 1. Son 50 satır log
```bash
sudo journalctl -u kirvehub-bot -n 50 --no-pager
```

### 2. Son 5 dakika log
```bash
sudo journalctl -u kirvehub-bot --since "5 minutes ago" --no-pager
```

### 3. Canlı log takibi
```bash
sudo journalctl -u kirvehub-bot -f
```

### 4. Tüm hata mesajları
```bash
sudo journalctl -u kirvehub-bot --no-pager | grep -i error
```

## Manuel Test (Hata Mesajını Görmek İçin)

```bash
cd ~/telegrambot
source venv/bin/activate
python main.py
```

## Olası Sorunlar ve Çözümler

### 1. Import Hatası
```bash
# Python path kontrolü
cd ~/telegrambot
source venv/bin/activate
python -c "import main"
```

### 2. Config/Database Hatası
```bash
# Config dosyasını kontrol et
cat config.py | grep -i "BOT_TOKEN\|DATABASE_URL"
```

### 3. Lock File Sorunu
```bash
# Lock file'ı sil
rm -f ~/telegrambot/bot_running.lock
sudo systemctl restart kirvehub-bot
```

### 4. Permission Sorunu
```bash
# Dosya izinlerini kontrol et
ls -la ~/telegrambot/main.py
chmod +x ~/telegrambot/main.py
```

### 5. Python Version Sorunu
```bash
# Python version kontrolü
python --version
which python
```

## Hızlı Çözüm Komutları

```bash
# 1. Lock file temizle
rm -f ~/telegrambot/bot_running.lock

# 2. Log kontrolü
sudo journalctl -u kirvehub-bot -n 100 --no-pager

# 3. Manuel test
cd ~/telegrambot
source venv/bin/activate
python main.py
```


