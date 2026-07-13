# Bot yapılandırması
import os
from dotenv import load_dotenv

load_dotenv()

# Bot Token (YENİ BOT)
BOT_TOKEN = "8432099283:AAHUa2AiYE2IXoAmL7rZ4IzbWgR0UCKf7X8"

# Bot Source (hangi bot'tan geldiği için)
BOT_SOURCE = "bot2"

# Bot Port (Bot2 için farklı port)
BOT_PORT = 8002

# Bot sahibi (ana bot ile aynı)
ADMIN_USER_ID = 8154732274  # Senin User ID'ni buraya yaz

# Yetkili grup ID (ana bot ile aynı)
AUTHORIZED_GROUP_ID = -1003124612051  # Senin grup ID'ni buraya yaz

# Database yolu (paylaşımlı - ana bot ile aynı database)
DATABASE_PATH = "../bot_database.db"

# Linkler - YENİ BOT İÇİN
APPROVED_GROUP_LINK = "https://t.me/+R9NbjDBDgdIyODcy"  # +18 kanal
CHAT_GROUP_LINK = "https://t.me/kirvehub18"  # Sohbet grubu

# Affiliate linkler - BOT2 LİNKLERİ
SITES = {
    "merso": {
        "name": "Merso Bahis",
        "url": "https://t2m.io/tg58",  # BOT2 MERSO LİNKİ
        "username_field": "merso_username",
        "screenshot_field": "merso_screenshot"
    },
    "amg": {
        "name": "AMG Bahis", 
        "url": "https://t2m.io/tgg58",  # BOT2 AMG LİNKİ
        "username_field": "amg_username",
        "screenshot_field": "amg_screenshot"
    }
}

# Bot versiyonu
BOT_VERSION = "2.0.0"
LAST_UPDATE = "2025-01-20"

# Ana bot token (cross-bot bildirimler için)
MAIN_BOT_TOKEN = "1234567890:ABC..."  # Ana bot token'ını buraya yaz

# Bot türü (hangi site için)
BOT_TYPE = "dual"  # "dual" (Merso+AMG), "amg_only", "merso_only"

# Screenshot klasörü
SCREENSHOTS_DIR = "screenshots"

# Bot başlangıç mesajı
STARTUP_MESSAGE = "KirveBot 2.0 başlatıldı! 🚀"

# Başvuru türü seçenekleri
APPLICATION_TYPES = {
    "dual": {
        "name": "Tam Başvuru (Merso + AMG)",
        "sites": ["merso", "amg"],
        "description": "Her iki site için başvuru yapın"
    },
    "amg_only": {
        "name": "Sadece AMG Başvuru",
        "sites": ["amg"],
        "description": "Sadece AMG Bahis için başvuru yapın"
    },
    "merso_only": {
        "name": "Sadece Merso Başvuru", 
        "sites": ["merso"],
        "description": "Sadece Merso Bahis için başvuru yapın"
    }
}
