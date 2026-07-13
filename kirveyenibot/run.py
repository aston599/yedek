import asyncio
import logging
from bot import main as bot_main
from database import init_db
import os

# Logging ayarlari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main_start():
    # Veritabanini baslat
    init_db()
    logger.info("Database initialized successfully")
    
    # Screenshots klasorunu olustur
    os.makedirs("screenshots", exist_ok=True)
    logger.info("Screenshots klasoru hazirlandi")
    
    # Botu baslat
    logger.info("Bot baslatiliyor...")
    bot_main()

if __name__ == '__main__':
    main_start()


