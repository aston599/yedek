#!/bin/bash

echo "🛑 Bot durduruluyor..."

# Systemd servisini durdur
systemctl stop kirvebot

# Tüm python processlerini bul ve öldür
echo "🔍 Python processleri aranıyor..."
PYTHON_PIDS=$(ps aux | grep -E "python.*run\.py|python.*bot\.py" | grep -v grep | awk '{print $2}')

if [ ! -z "$PYTHON_PIDS" ]; then
    echo "⚡ Python processleri öldürülüyor: $PYTHON_PIDS"
    kill -TERM $PYTHON_PIDS
    sleep 3
    
    # Hala çalışıyorsa zorla öldür
    REMAINING=$(ps aux | grep -E "python.*run\.py|python.*bot\.py" | grep -v grep | awk '{print $2}')
    if [ ! -z "$REMAINING" ]; then
        echo "💀 Zorla öldürülüyor: $REMAINING"
        kill -9 $REMAINING
    fi
else
    echo "✅ Çalışan python processi bulunamadı"
fi

# Telegram webhook'u temizle
echo "🌐 Telegram webhook temizleniyor..."
curl -s -X POST "https://api.telegram.org/bot8391790953:AAHBpJ3gfc-ugO9LE3iSoX2OOl0JKIcQ9-c/deleteWebhook" > /dev/null

# Startup dosyasını sil
rm -f /tmp/kirvebot_startup_sent

echo "✅ Bot başarıyla durduruldu!"
