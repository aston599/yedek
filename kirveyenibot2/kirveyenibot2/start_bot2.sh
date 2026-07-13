#!/bin/bash

# KirveBot2 başlatma scripti

echo "🚀 KirveBot2 başlatılıyor..."

# Önceki bot2 süreçlerini durdur
pkill -f "python.*bot.py.*kirveyenibot2"

# Bot2'yi başlat
cd /root/kirveyenibot2
python3 bot.py &

echo "✅ KirveBot2 başlatıldı!"
echo "📱 Bot2 Token: 8432099283:AAHUa2AiYE2IXoAmL7rZ4IzbWgR0UCKf7X8"
echo "🔗 Yeni linkler:"
echo "   - Merso: https://t2m.io/tg58"
echo "   - AMG: https://t2m.io/tgg58"
