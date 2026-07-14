# 🔧 Systemd Klasörü ve Dosya Düzeltme

## Sorun
`systemd/kirvehub-bot.service` dosyası bulunamıyor çünkü `systemd` klasörü eksik.

## Çözüm

### 1. Systemd Klasörünü Oluştur ve Dosyayı Kopyala

```bash
cd /home/kirvehub/telegrambot-clean

# Systemd klasörünü oluştur
mkdir -p systemd

# Dosyayı mevcut bot'tan kopyala
cp ../telegrambot/systemd/kirvehub-bot.service systemd/

# VEYA dosyayı sıfırdan oluştur
nano systemd/kirvehub-bot.service
```

### 2. Systemd Service Dosyası İçeriği

Aşağıdaki içeriği `nano systemd/kirvehub-bot.service` ile oluştur:

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
ExecStart=/usr/bin/python3 /home/kirvehub/telegrambot-clean/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
ReadWritePaths=/home/kirvehub/telegrambot-clean/logs /home/kirvehub/telegrambot-clean/data /home/kirvehub/telegrambot-clean

[Install]
WantedBy=multi-user.target
```

### 3. Tek Komutla Çözüm

```bash
cd /home/kirvehub/telegrambot-clean && \
mkdir -p systemd && \
cat > systemd/kirvehub-bot.service << 'EOF'
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
ExecStart=/usr/bin/python3 /home/kirvehub/telegrambot-clean/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
ReadWritePaths=/home/kirvehub/telegrambot-clean/logs /home/kirvehub/telegrambot-clean/data /home/kirvehub/telegrambot-clean

[Install]
WantedBy=multi-user.target
EOF
```

### 4. Dosyayı Kontrol Et

```bash
cat systemd/kirvehub-bot.service
```

### 5. Systemd Service'i Kur

```bash
sudo cp /home/kirvehub/telegrambot-clean/systemd/kirvehub-bot.service /etc/systemd/system/kirvehub-bot-clean.service
sudo systemctl daemon-reload
sudo systemctl enable kirvehub-bot-clean
sudo systemctl start kirvehub-bot-clean
sudo systemctl status kirvehub-bot-clean
```


