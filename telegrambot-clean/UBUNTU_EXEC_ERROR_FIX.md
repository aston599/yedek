# 🔧 Ubuntu Systemd EXEC Error (203) Çözümü

## Sorun
```
Process: 1947067 ExecStart=/home/kirvehub/telegrambot/venv/bin/python main.py (code=exited, status=203/EXEC)
```

## Olası Nedenler
1. Python executable bulunamıyor
2. Dosya izinleri yanlış
3. Systemd service dosyasındaki path yanlış
4. User/Group ayarları yanlış

## Çözüm Komutları

### 1. Python Path Kontrolü
```bash
cd ~/telegrambot
ls -la venv/bin/python*
which python3
python3 --version
```

### 2. Service Dosyası Kontrolü
```bash
cat /etc/systemd/system/kirvehub-bot.service | grep ExecStart
```

### 3. Manuel Test
```bash
cd ~/telegrambot
source venv/bin/activate
/home/kirvehub/telegrambot/venv/bin/python main.py
```

### 4. Dosya İzinlerini Düzelt
```bash
cd ~/telegrambot
chown -R kirvehub:kirvehub /home/kirvehub/telegrambot
chmod +x /home/kirvehub/telegrambot/venv/bin/python
chmod +x /home/kirvehub/telegrambot/main.py
```

### 5. Systemd Service Dosyasını Düzelt
```bash
sudo nano /etc/systemd/system/kirvehub-bot.service
# ExecStart satırını kontrol et
```

### 6. Alternatif: Python3 Kullan
Eğer venv/bin/python çalışmıyorsa:
```bash
# Service dosyasında:
ExecStart=/usr/bin/python3 /home/kirvehub/telegrambot/main.py
```

## Hızlı Çözüm
```bash
cd ~/telegrambot
chown -R kirvehub:kirvehub /home/kirvehub/telegrambot
chmod +x venv/bin/python*
sudo systemctl daemon-reload
sudo systemctl restart kirvehub-bot
sudo systemctl status kirvehub-bot
```


