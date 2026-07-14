"""
Boss Greeting System - Patron Karsilama Sistemi
@adanalidenise geldiginde bazen samimi selamlar
"""
import logging
import random
from aiogram import Router, types, F
from datetime import datetime, timedelta

router = Router()
logger = logging.getLogger(__name__)

# Patron bilgileri
BOSS_USERNAME = "adanalidenise"
BOSS_USER_ID = None  # İlk mesajda otomatik alınacak

# Son karsilama zamani (her mesajda karsilamayalim)
last_greeting_time = {}

# Karsilama mesajlari (samimi, abartisiz)
GREETING_MESSAGES = [
    "Hoş geldin patron! 👋",
    "Merhaba şefim! 😊",
    "Selam patron, nasılsın? ☕",
    "Hoş buldum patronum! 🎯",
    "İyi günler boss! ✨",
    "Nasılsın patron? 💼",
    "Selam şefim, gruba hoş geldin! 👔",
    "Hoş geldin, güzel günler! 🌟",
    "Merhaba patronum! 🔥",
    "Selam boss, her şey yolunda! ✅"
]

# Karsilama ihtimali (%30)
GREETING_CHANCE = 0.30

# Minimum bekleme suresi (dakika)
MIN_WAIT_MINUTES = 60  # 1 saat icinde tekrar karsilamaz


def should_greet_boss(user_id: int) -> bool:
    """
    Patronu karsilamali miyiz?
    
    Kosullar:
    1. %30 sans
    2. Son 1 saat icinde karsilanmamis olmali
    """
    # Rastgele sans
    if random.random() > GREETING_CHANCE:
        return False
    
    # Son karsilama zamani kontrolu
    if user_id in last_greeting_time:
        time_passed = datetime.now() - last_greeting_time[user_id]
        if time_passed < timedelta(minutes=MIN_WAIT_MINUTES):
            return False
    
    return True


def get_random_greeting() -> str:
    """Rastgele bir karsilama mesaji sec"""
    return random.choice(GREETING_MESSAGES)


@router.message(F.chat.type.in_(["group", "supergroup"]))
async def greet_boss(message: types.Message):
    """Patron geldiginde bazen karsilamak"""
    global BOSS_USER_ID
    
    # Mesaj var mi?
    if not message.text:
        return
    
    user = message.from_user
    if not user:
        return
    
    # Username kontrolu
    username = user.username
    if not username or username.lower() != BOSS_USERNAME.lower():
        return
    
    # Boss user ID'yi kaydet (ilk seferde)
    if BOSS_USER_ID is None:
        BOSS_USER_ID = user.id
        logger.info(f"👔 Boss user ID kaydedildi: {BOSS_USER_ID}")
    
    # Karsilamali miyiz?
    if not should_greet_boss(user.id):
        return
    
    # Karsilama mesaji gonder
    greeting = get_random_greeting()
    
    try:
        await message.reply(greeting)
        
        # Son karsilama zamanini kaydet
        last_greeting_time[user.id] = datetime.now()
        
        logger.info(f"👔 Boss karsilandi - User: {username}, Message: {greeting}")
        
    except Exception as e:
        logger.error(f"❌ Boss karsilama hatasi: {e}")

