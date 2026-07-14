#!/bin/bash
# Systemd servis dosyasını düzelt

echo "🔧 Systemd servis dosyası düzeltiliyor..."

# Mevcut dizini al
CURRENT_DIR=$(pwd)
echo "📁 Mevcut dizin: $CURRENT_DIR"

# Python executable yolunu kontrol et
PYTHON_PATH="$CURRENT_DIR/venv/bin/python"
if [ ! -f "$PYTHON_PATH" ]; then
    echo "❌ Python executable bulunamadı: $PYTHON_PATH"
    exit 1
fi
echo "✅ Python executable bulundu: $PYTHON_PATH"

# Systemd servis dosyasını düzelt
sudo tee /etc/systemd/system/kirvebot.service > /dev/null <<EOF
[Unit]
Description=KirveHub Telegram Bot
Documentation=https://github.com/aston599/telegrambot
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=$CURRENT_DIR
ExecStart=$PYTHON_PATH $CURRENT_DIR/main.py
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd servis dosyası güncellendi"

# Daemon reload
sudo systemctl daemon-reload
echo "✅ Systemd daemon reload edildi"

# Syntax kontrolü
sudo systemctl status kirvebot --no-pager || true





