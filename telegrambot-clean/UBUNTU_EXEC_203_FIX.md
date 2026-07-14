# 🔧 Ubuntu Systemd EXEC 203 Error Çözümü

## Sorun
```
status=203/EXEC
Main process exited, code=exited, status=203/EXEC
```

Bu hata, systemd'in ExecStart komutunu çalıştıramadığı anlamına gelir.

## Çözüm Adımları

### 1. Python Path Kontrolü
```bash
ls -la /home/kirvehub/telegrambot/venv/bin/python*
file /home/kirvehub/telegrambot/venv/bin/python
```

### 2. kirvehub Kullanıcısı Kontrolü
```bash
id kirvehub
getent passwd kirvehub
```

### 3. Dosya İzinlerini Düzelt
```bash
chown -R kirvehub:kirvehub /home/kirvehub/telegrambot
chmod +x /home/kirvehub/telegrambot/venv/bin/python*
chmod +x /home/kirvehub/telegrambot/main.py
```

### 4. Systemd Service Dosyasını Düzelt
```bash
sudo nano /etc/systemd/system/kirvehub-bot.service
```

ExecStart satırını şu şekilde değiştir:
```ini
ExecStart=/usr/bin/python3 /home/kirvehub/telegrambot/main.py
```

VEYA

```ini
ExecStart=/bin/bash -c 'cd /home/kirvehub/telegrambot && source venv/bin/activate && python main.py'
```

### 5. Alternatif: Systemd Service Dosyasını Basitleştir
```bash
sudo tee /etc/systemd/system/kirvehub-bot.service > /dev/null <<EOF
[Unit]
Description=KirveHub Telegram Bot
After=network.target

[Service]
Type=simple
User=kirvehub
Group=kirvehub
WorkingDirectory=/home/kirvehub/telegrambot
Environment=PATH=/home/kirvehub/telegrambot/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/usr/bin/python3 /home/kirvehub/telegrambot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 6. Daemon Reload ve Restart
```bash
sudo systemctl daemon-reload
sudo systemctl restart kirvehub-bot
sudo systemctl status kirvehub-bot
```

## Hızlı Çözüm (Tek Komut)
```bash
chown -R kirvehub:kirvehub /home/kirvehub/telegrambot && chmod +x /home/kirvehub/telegrambot/venv/bin/python* && sudo systemctl daemon-reload && sudo systemctl restart kirvehub-bot
```


