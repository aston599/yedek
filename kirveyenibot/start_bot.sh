#!/bin/bash

echo "🚀 Bot başlatılıyor..."

# Önce durdur
./stop_bot.sh

# Kısa bekle
sleep 2

# Systemd servisini başlat
systemctl start kirvebot

# Durumu kontrol et
sleep 3
systemctl status kirvebot --no-pager

echo "✅ Bot başlatıldı!"
echo "📊 Logları görmek için: journalctl -u kirvebot -f"
