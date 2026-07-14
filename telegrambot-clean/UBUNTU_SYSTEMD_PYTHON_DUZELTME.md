# 🔧 Systemd Service Python Yolu Düzeltme

## Sorun
Systemd service'i `/usr/bin/python3` (sistem Python'u) kullanıyor, bu yüzden venv'deki paketler görünmüyor.

## Çözüm

### Systemd Service Dosyasını Düzelt

```bash
sudo nano /etc/systemd/system/kirvehub-bot-clean.service
```

**ExecStart satırını değiştir:**
```ini
# Eski (YANLIŞ):
ExecStart=/usr/bin/python3 /home/kirvehub/telegrambot-clean/main.py

# Yeni (DOĞRU):
ExecStart=/home/kirvehub/telegrambot-clean/venv/bin/python /home/kirvehub/telegrambot-clean/main.py
```

### Veya Tek Komutla Düzelt

```bash
sudo sed -i 's|ExecStart=/usr/bin/python3|ExecStart=/home/kirvehub/telegrambot-clean/venv/bin/python|g' /etc/systemd/system/kirvehub-bot-clean.service && \
sudo systemctl daemon-reload && \
sudo systemctl restart kirvehub-bot-clean && \
sudo systemctl status kirvehub-bot-clean
```

### Manuel Düzenleme

```bash
# Service dosyasını düzenle
sudo nano /etc/systemd/system/kirvehub-bot-clean.service
```

**İçeriği şöyle olmalı:**
```ini
[Unit]
Description=KirveHub Telegram Bot (Clean)
Documentation=https://github.com/aston599/telegrambot
After=network.target

[Service]
Type=simple
User=kirvehub
Group=kirvehub
WorkingDirectory=/home/kirvehub/telegrambot-clean
Environment=PATH=/home/kirvehub/telegrambot-clean/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/home/kirvehub/telegrambot-clean
ExecStart=/home/kirvehub/telegrambot-clean/venv/bin/python /home/kirvehub/telegrambot-clean/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
ReadWritePaths=/home/kirvehub/telegrambot-clean/logs /home/kirvehub/telegrambot-clean/data /home/kirvehub/telegrambot-clean

[Install]
WantedBy=multi-user.target
```

**ÖNEMLİ:** `ExecStart` satırı `/home/kirvehub/telegrambot-clean/venv/bin/python` olmalı!

### Sonra

```bash
sudo systemctl daemon-reload
sudo systemctl restart kirvehub-bot-clean
sudo systemctl status kirvehub-bot-clean
```


