"""
🤖 Gelişmiş AI Sohbet Sistemi - KirveHub Bot
Kullanıcı sorularını anlayıp ilgili panelleri/komutları açan akıllı sistem
"""
import re
import logging
from typing import Optional, Dict, List, Tuple
from aiogram import Router, Bot, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from database import is_user_registered, get_db_pool
from config import get_config, is_admin
from utils.logger import logger

router = Router()

# Bot instance
_bot_instance: Optional[Bot] = None

def set_bot_instance(bot_instance: Bot):
    """Bot instance'ını set et"""
    global _bot_instance
    _bot_instance = bot_instance

# ==============================================
# INTENT RECOGNITION (Niyet Tanıma)
# ==============================================

# Intent tanımları ve anahtar kelimeler
INTENT_KEYWORDS = {
    "market_access": {
        "keywords": ["market", "mağaza", "shop", "alışveriş", "satın al", "ürün", "sipariş ver"],
        "patterns": [
            r"market.*(?:nasıl|aç|gir|göster|getir|ulaş|eriş)",
            r"(?:nasıl|aç|gir|göster|getir|ulaş|eriş).*market",
            r"alışveriş.*(?:yap|et|gir|başla)",
            r"market.*(?:nedir|ne|hakkında)"
        ],
        "action": {
            "command": "/market",
            "handler": "market_management_command",
            "response": "🛍️ Market paneline yönlendiriyorum...",
            "description": "Market'e erişmek için"
        }
    },
    "profile_view": {
        "keywords": ["profil", "hesap", "bilgilerim", "hesabım", "kullanıcı bilgileri", "hesap bilgileri"],
        "patterns": [
            r"profil.*(?:göster|aç|getir|gör|bak)",
            r"hesap.*(?:göster|aç|getir|gör|bak)",
            r"bilgilerim",
            r"hesabım.*(?:göster|aç|getir|gör|bak)"
        ],
        "action": {
            "command": "/profil",
            "handler": "profil_command",
            "response": "👤 Profil bilgilerinizi gösteriyorum...",
            "description": "Profil bilgilerinizi görmek için"
        }
    },
    "order_list": {
        "keywords": ["sipariş", "siparişlerim", "siparişler", "sipariş listesi", "siparişlerimi göster"],
        "patterns": [
            r"sipariş.*(?:göster|listele|bak|gör|getir)",
            r"siparişlerim",
            r"(?:göster|listele|bak|gör|getir).*sipariş"
        ],
        "action": {
            "command": "/siparislerim",
            "handler": "siparislerim_command",
            "response": "📦 Siparişlerinizi listeliyorum...",
            "description": "Siparişlerinizi görmek için"
        }
    },
    "lottery_participate": {
        "keywords": ["çekiliş", "çekilişe", "katılmak", "çekiliş var mı", "çekilişlere bak", "çekilişlere katıl"],
        "patterns": [
            r"çekiliş.*(?:katıl|gir|bak|gör|göster|listele)",
            r"(?:katıl|gir|bak|gör|göster|listele).*çekiliş",
            r"çekiliş.*(?:var mı|nedir|ne)"
        ],
        "action": {
            "command": "/cekilisler",
            "handler": "list_active_lotteries",
            "response": "🎲 Aktif çekilişleri gösteriyorum...",
            "description": "Çekilişlere katılmak için"
        }
    },
    "site_list": {
        "keywords": ["site", "siteler", "bahis", "güvenli", "siteleri göster", "siteleri listele"],
        "patterns": [
            r"site.*(?:göster|listele|bak|gör|getir)",
            r"siteler.*(?:göster|listele|bak|gör|getir)",
            r"(?:göster|listele|bak|gör|getir).*site",
            r"güvenli.*site"
        ],
        "action": {
            "command": "/site",
            "handler": "site_command",
            "response": "🌐 Güvenli siteleri gösteriyorum...",
            "description": "Güvenli siteleri görmek için"
        }
    },
    "help_request": {
        "keywords": ["yardım", "komut", "ne yapabilirim", "nasıl", "yardım et", "komutlar neler"],
        "patterns": [
            r"(?:ne|neler).*(?:yapabilirim|yapabilir|yapabilirsin)",
            r"komut.*(?:nedir|neler|liste|göster)",
            r"yardım.*(?:et|ver|göster)",
            r"nasıl.*(?:kullanırım|yaparım|ederim)"
        ],
        "action": {
            "command": "/komutlar",
            "handler": "komutlar_command",
            "response": "📋 Size yardımcı olabileceğim komutları gösteriyorum...",
            "description": "Yardım ve komut listesi için"
        }
    },
    "ranking_view": {
        "keywords": ["sıralama", "ranking", "sıralamalar", "liderlik", "top", "en çok"],
        "patterns": [
            r"sıralama.*(?:göster|bak|gör|listele)",
            r"ranking.*(?:göster|bak|gör|listele)",
            r"(?:göster|bak|gör|listele).*sıralama",
            r"lider.*(?:göster|bak|gör|listele)"
        ],
        "action": {
            "command": "/siralama",
            "handler": "siralama_command",
            "response": "🏆 Sıralamaları gösteriyorum...",
            "description": "Sıralamaları görmek için"
        }
    },
    "menu_view": {
        "keywords": ["menü", "menu", "ana menü", "menüyü göster", "menüyü aç"],
        "patterns": [
            r"menü.*(?:göster|aç|getir|gör)",
            r"menu.*(?:göster|aç|getir|gör)",
            r"(?:göster|aç|getir|gör).*menü"
        ],
        "action": {
            "command": "/menu",
            "handler": "menu_command",
            "response": "📱 Ana menüyü gösteriyorum...",
            "description": "Ana menüyü görmek için"
        }
    },
    "point_info": {
        "keywords": ["point", "puan", "kirve point", "kp", "point nedir", "puan nasıl kazanılır"],
        "patterns": [
            r"point.*(?:nedir|nasıl|hakkında|kaç)",
            r"puan.*(?:nedir|nasıl|hakkında|kaç)",
            r"kirve.*point.*(?:nedir|nasıl|hakkında)",
            r"(?:nasıl|ne).*point.*(?:kazan|al)"
        ],
        "action": {
            "command": None,
            "handler": "show_point_info",
            "response": "💎 Kirve Point sistemi hakkında bilgi veriyorum...",
            "description": "Point sistemi hakkında bilgi"
        }
    },
    "registration_info": {
        "keywords": ["kayıt", "kayıt ol", "üye ol", "nasıl kayıt olurum", "kayıt nasıl"],
        "patterns": [
            r"kayıt.*(?:ol|nasıl|nedir|hakkında)",
            r"(?:nasıl|ne).*kayıt.*(?:ol|yap)",
            r"üye.*(?:ol|nasıl|nedir)"
        ],
        "action": {
            "command": "/kirvekayit",
            "handler": "kirvekayit_command",
            "response": "📝 Kayıt işlemini başlatıyorum...",
            "description": "Kayıt olmak için"
        }
    }
}

# ==============================================
# ENTITY EXTRACTION (Varlık Çıkarma)
# ==============================================

def extract_entities(text: str) -> Dict[str, List[str]]:
    """Mesajdan önemli varlıkları çıkar"""
    entities = {
        "commands": [],
        "panels": [],
        "features": [],
        "numbers": []
    }
    
    # Komut isimleri
    command_patterns = [
        r"/?(\w+)",  # /komut veya komut
    ]
    
    # Panel isimleri
    panel_keywords = ["market", "profil", "sipariş", "çekiliş", "site", "menü", "sıralama"]
    for keyword in panel_keywords:
        if keyword in text.lower():
            entities["panels"].append(keyword)
    
    # Özellik isimleri
    feature_keywords = ["point", "puan", "bakiye", "kirve point", "kp"]
    for keyword in feature_keywords:
        if keyword in text.lower():
            entities["features"].append(keyword)
    
    # Sayılar
    numbers = re.findall(r'\d+', text)
    entities["numbers"] = numbers
    
    return entities

# ==============================================
# INTENT RECOGNITION (Niyet Tanıma)
# ==============================================

def recognize_intent(text: str) -> Optional[Tuple[str, float, Dict]]:
    """
    Kullanıcı mesajından niyeti tanı
    
    Returns:
        (intent_name, confidence, action_dict) veya None
    """
    text_lower = text.lower().strip()
    
    # Her intent için skor hesapla
    intent_scores = {}
    
    for intent_name, intent_data in INTENT_KEYWORDS.items():
        score = 0.0
        
        # Keyword matching
        keywords = intent_data.get("keywords", [])
        for keyword in keywords:
            if keyword in text_lower:
                score += 0.3
        
        # Pattern matching
        patterns = intent_data.get("patterns", [])
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 0.5
        
        if score > 0:
            intent_scores[intent_name] = {
                "score": score,
                "action": intent_data.get("action", {})
            }
    
    # En yüksek skorlu intent'i bul
    if intent_scores:
        best_intent = max(intent_scores.items(), key=lambda x: x[1]["score"])
        intent_name, intent_data = best_intent
        
        # Confidence hesapla (0.0 - 1.0)
        confidence = min(intent_data["score"] / 2.0, 1.0)
        
        # Minimum confidence threshold
        if confidence >= 0.3:
            return (intent_name, confidence, intent_data["action"])
    
    return None

# ==============================================
# CONTEXT MANAGEMENT (Bağlam Yönetimi)
# ==============================================

# Kullanıcı bağlamı (RAM'de tutulur)
user_contexts: Dict[int, Dict] = {}

def get_user_context(user_id: int) -> Dict:
    """Kullanıcı bağlamını al"""
    if user_id not in user_contexts:
        user_contexts[user_id] = {
            "last_intent": None,
            "last_action": None,
            "last_panel": None,
            "conversation_count": 0
        }
    return user_contexts[user_id]

def update_user_context(user_id: int, intent: str = None, action: str = None, panel: str = None):
    """Kullanıcı bağlamını güncelle"""
    context = get_user_context(user_id)
    if intent:
        context["last_intent"] = intent
    if action:
        context["last_action"] = action
    if panel:
        context["last_panel"] = panel
    context["conversation_count"] += 1

# ==============================================
# ACTION EXECUTION (Aksiyon Çalıştırma)
# ==============================================

async def execute_action(message: Message, action: Dict) -> bool:
    """
    Anlaşılan niyete göre işlem yap
    
    Returns:
        True if action was executed, False otherwise
    """
    try:
        user_id = message.from_user.id
        
        # Komut varsa çalıştır
        command = action.get("command")
        handler_name = action.get("handler")
        
        if command:
            # Fake message oluştur
            from aiogram.types import Message as MessageType
            fake_message = MessageType(
                message_id=message.message_id,
                date=message.date,
                chat=message.chat,
                from_user=message.from_user,
                text=command,
                content_type="text"
            )
            
            # Handler'ı import et ve çalıştır
            try:
                if handler_name == "market_management_command":
                    from handlers.admin_market_management import market_management_command
                    await market_management_command(fake_message)
                elif handler_name == "profil_command":
                    from handlers.profile_handler import profil_command
                    await profil_command(fake_message)
                elif handler_name == "siparislerim_command":
                    from handlers.profile_handler import siparislerim_command
                    await siparislerim_command(fake_message)
                elif handler_name == "list_active_lotteries":
                    from handlers.events_list import list_active_lotteries
                    await list_active_lotteries(fake_message)
                elif handler_name == "site_command":
                    from handlers.site_manager import site_command
                    await site_command(fake_message)
                elif handler_name == "komutlar_command":
                    from handlers.profile_handler import komutlar_command
                    await komutlar_command(fake_message)
                elif handler_name == "siralama_command":
                    from handlers.profile_handler import siralama_command
                    await siralama_command(fake_message)
                elif handler_name == "menu_command":
                    from handlers.profile_handler import menu_command
                    await menu_command(fake_message)
                elif handler_name == "kirvekayit_command":
                    from handlers.register_handler import kirvekayit_command
                    await kirvekayit_command(fake_message)
                else:
                    logger.warning(f"⚠️ Handler bulunamadı: {handler_name}")
                    return False
                
                return True
            except Exception as e:
                logger.error(f"❌ Handler çalıştırma hatası: {e}")
                return False
        
        # Özel handler (komut yok)
        elif handler_name == "show_point_info":
            await show_point_info(message)
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Action execution hatası: {e}")
        return False

async def show_point_info(message: Message):
    """Point sistemi hakkında bilgi göster"""
    try:
        info_text = """
💎 **KİRVE POINT SİSTEMİ**

📊 **Point Nasıl Kazanılır?**
• Her 5 mesajda 0.10 KP kazanırsın
• Günlük limit: 5.00 KP
• Haftalık limit: 20.00 KP

🛍️ **Point Ne İşe Yarar?**
• Market'ten ürün satın alabilirsin
• Özel etkinliklere katılabilirsin
• Sıralamalarda yükselirsin

📈 **Point'lerini Görmek İçin:**
• `/profil` - Profil bilgilerin
• `/siralama` - Sıralamalar

💡 **Daha fazla bilgi için:** `/komutlar`
        """
        
        await message.reply(info_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Point info hatası: {e}")

# ==============================================
# MAIN AI CHAT HANDLER
# ==============================================

async def handle_ai_chat(message: Message) -> Optional[str]:
    """
    Ana AI sohbet handler'ı
    
    Returns:
        Response message veya None
    """
    try:
        user_id = message.from_user.id
        text = message.text
        
        if not text or len(text) < 3:
            return None
        
        # Sadece özel mesajda çalış
        if message.chat.type != "private":
            return None
        
        # Komut mesajlarını atla (zaten handler'lar var)
        if text.startswith("/") or text.startswith("!"):
            return None
        
        # Intent tanıma
        intent_result = recognize_intent(text)
        
        if not intent_result:
            # Anlaşılamadı, genel yanıt ver
            return None
        
        intent_name, confidence, action = intent_result
        
        logger.info(f"🤖 AI Intent: {intent_name} (confidence: {confidence:.2f}) - User: {user_id}")
        
        # Bağlamı güncelle
        update_user_context(user_id, intent=intent_name, action=action.get("command"))
        
        # Aksiyonu çalıştır
        action_executed = await execute_action(message, action)
        
        if action_executed:
            # Başarılı yanıt
            response = action.get("response", "✅ İşlem tamamlandı!")
            
            # Ek bilgi ekle
            if confidence < 0.7:
                response += "\n\n💡 İpucu: Daha spesifik sorular sorarsanız daha iyi yardımcı olabilirim!"
            
            return response
        else:
            # Aksiyon çalıştırılamadı
            return "⚠️ İşlem gerçekleştirilemedi. Lütfen komutu manuel olarak deneyin."
        
    except Exception as e:
        logger.error(f"❌ AI chat handler hatası: {e}")
        return None

# ==============================================
# ROUTER HANDLERS
# ==============================================

@router.message(lambda m: m.chat.type == "private" and m.text and not m.text.startswith("/") and not m.text.startswith("!"))
async def ai_chat_handler(message: Message):
    """AI sohbet handler - Sadece özel mesajlarda, komut olmayan mesajları dinle"""
    try:
        # AI chat'i çalıştır
        response = await handle_ai_chat(message)
        
        if response:
            await message.reply(response)
            logger.info(f"✅ AI yanıt gönderildi - User: {message.from_user.id}, Intent: {response[:50]}")
        
    except Exception as e:
        logger.error(f"❌ AI chat router hatası: {e}")

