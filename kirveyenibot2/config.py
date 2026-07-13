import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8391790953:AAHBpJ3gfc-ugO9LE3iSoX2OOl0JKIcQ9-c"

# Yönetici kullanıcı ID'si - botun sahibi
ADMIN_USER_ID = 8154732274

# Yetkili grup ID'si - SABİT - sadece bu grup
AUTHORIZED_GROUP_ID = -1003124612051  # KirveHub +18 grubu - DEĞİŞTİRİLMEZ!

DATABASE_PATH = "bot_database.db"

# Site bilgileri
SITES = {
    "merso": {
        "name": "Merso Bahis",
        "url": "https://t2m.io/tg58"  # YENİ MERSO LİNKİ
    },
    "amg": {
        "name": "AMG Bahis", 
        "url": "https://t2m.io/tgg58"  # YENİ AMG LİNKİ
    }
}

# Grup linkleri
TARGET_GROUP_LINK = "https://t.me/+oGnKw4heUchhNzY0"  # Ana geçiş kanalı
APPROVED_GROUP_LINK = "https://t.me/+R9NbjDBDgdIyODcy"  # Onaylanınca gidilecek özel +18 kanal
CHAT_GROUP_LINK = "https://t.me/+mLf71wrQD-Y3ZjUy"  # Sohbet grubu linki (KirveHub Sohbet)

# Bot bilgileri
BOT_VERSION = "v2.1.0"
LAST_UPDATE = "2025-01-17"

