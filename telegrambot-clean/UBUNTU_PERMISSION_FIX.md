# 🔧 Ubuntu Permission Hatası Çözümü

## Sorun
```
PermissionError: [Errno 13] Permission denied: '/home/kirvehub/telegrambot/bot.log'
```

## Çözüm Komutları

### 1. Eski bot.log dosyasını sil ve izinleri düzelt
```bash
cd ~/telegrambot
rm -f bot.log
rm -f bot_running.lock
```

### 2. Logs klasörünü oluştur ve izinleri ayarla
```bash
cd ~/telegrambot
mkdir -p logs
chown -R kirvehub:kirvehub logs/
chmod 755 logs/
```

### 3. GitHub'dan güncellemeleri çek
```bash
cd ~/telegrambot
git pull origin main
```

### 4. Systemd service dosyasını güncelle
```bash
sudo cp systemd/kirvehub-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 5. Botu yeniden başlat
```bash
sudo systemctl restart kirvehub-bot
sudo systemctl status kirvehub-bot
```

## Tek Komut (Hızlı Çözüm)

```bash
cd ~/telegrambot && rm -f bot.log bot_running.lock && mkdir -p logs && chown -R kirvehub:kirvehub logs/ && chmod 755 logs/ && git pull origin main && sudo cp systemd/kirvehub-bot.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart kirvehub-bot && sudo systemctl status kirvehub-bot
```

## Alternatif: Log dosyasını tamamen devre dışı bırak

Eğer log dosyası gerekmiyorsa, main.py'de FileHandler'ı kaldırabilirsiniz (sadece console logging).


