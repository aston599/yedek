#!/bin/bash

# KirveBot2 Kurulum Scripti
echo "🚀 KirveBot2 kurulumu başlatılıyor..."

# Klasör oluştur
cd /root/kirveyenibot
mkdir -p bot2
cd bot2

# Dosyaları kopyala
cp ../bot.py .
cp ../database.py .
cp ../requirements.txt .
cp ../.gitignore .

echo "✅ Dosyalar kopyalandı!"

# Config dosyasını oluştur
cat > config.py << 'EOF'
# Bot yapılandırması
BOT_TOKEN = "8432099283:AAHUa2AiYE2IXoAmL7rZ4IzbWgR0UCKf7X8"
ADMIN_USER_ID = 123456789
AUTHORIZED_GROUP_ID = -1003124612051
DATABASE_PATH = "../bot_database.db"

APPROVED_GROUP_LINK = "https://t.me/+R9NbjDBDgdIyODcy"
CHAT_GROUP_LINK = "https://t.me/kirvehub18"

SITES = {
    "merso": {
        "name": "Merso Bahis",
        "url": "https://t2m.io/tg58"
    },
    "amg": {
        "name": "AMG Bahis", 
        "url": "https://t2m.io/tgg58"
    }
}

BOT_VERSION = "2.0.0"
LAST_UPDATE = "2025-01-20"
EOF

echo "✅ Config dosyası oluşturuldu!"

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
