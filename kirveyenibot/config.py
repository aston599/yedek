import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8391790953:AAHBpJ3gfc-ugO9LE3iSoX2OOl0JKIcQ9-c"

# Bot Source (hangi bot'tan geldiği için)
BOT_SOURCE = "main"

# Bot Port (Ana Bot için port)
BOT_PORT = 8001

# Yönetici kullanıcı ID'si - botun sahibi
ADMIN_USER_ID = 8521478746  # Mike (@mikedahjenkoy)

# Yetkili grup ID'si - SABİT - sadece bu grup
AUTHORIZED_GROUP_ID = -1003124612051  # KirveHub +18 grubu - DEĞİŞTİRİLMEZ!

DATABASE_PATH = "bot_database.db"

# Site bilgileri
SITES = {
    "gameofbet": {
        "name": "Game of Bet",
        "url": "https://t2m.io/kirvegob"  # ANA BOT GAME OF BET LİNKİ (10.000 TL çekim imkanlı deneme bonuslu)
    },
    "amg": {
        "name": "AMG Bahis", 
        "url": "https://t2m.io/kirveamg18"  # ANA BOT AMG LİNKİ
    }
}

# Grup linkleri
TARGET_GROUP_LINK = "https://t.me/+oGnKw4heUchhNzY0"  # Ana geçiş kanalı
APPROVED_GROUP_LINK = "https://t.me/+2lBm39eukKpiYmYy"  # Onaylanınca gidilecek özel +18 kanal (Kirvehub +18)
CHAT_GROUP_LINK = "https://t.me/+mLf71wrQD-Y3ZjUy"  # Sohbet grubu linki (KirveHub Sohbet)

# Bot bilgileri
BOT_VERSION = "v2.3.0"
LAST_UPDATE = "2025-01-20"

