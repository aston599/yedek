#!/bin/bash

# KirveBot2 Sunucu Kurulum Scripti
echo "🚀 KirveBot2 sunucu kurulumu başlatılıyor..."

# Klasör oluştur
cd /root/kirveyenibot
mkdir -p bot2
cd bot2

# Dosyaları kopyala
cp ../bot.py .
cp ../database.py .
cp ../requirements.txt .
cp ../.gitignore .

# Config dosyasını oluştur
cp ../kirveyenibot2/config_bot2.py ./config.py

echo "✅ KirveBot2 dosyaları hazırlandı!"

# Bot'u başlat
echo "🤖 KirveBot2 başlatılıyor..."
python3 bot.py &

echo "🎉 KirveBot2 kurulumu tamamlandı!"
echo "📱 Bot Token: 8432099283:AAHUa2AiYE2IXoAmL7rZ4IzbWgR0UCKf7X8"
echo "🔗 Yeni linkler:"
echo "   - Merso: https://t2m.io/tg58"
echo "   - AMG: https://t2m.io/tgg58"
echo ""
echo "📊 Bot durumunu kontrol etmek için:"
echo "ps aux | grep python"
