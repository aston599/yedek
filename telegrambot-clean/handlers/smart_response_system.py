"""
🤖 Akıllı Yanıt Sistemi
Bot'un daha akıllı ve samimi yanıtlar vermesi için geliştirilmiş sistem
"""

import re
import random
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from aiogram.types import Message
from database import get_user_info, get_user_points
from utils.logger import setup_logger

logger = setup_logger()

class SmartResponseSystem:
    def __init__(self):
        # Duygu analizi için anahtar kelimeler
        self.emotion_keywords = {
            "mutlu": ["güzel", "harika", "süper", "mükemmel", "sevindim", "güldüm", "😊", "😄", "🎉"],
            "üzgün": ["kötü", "üzgün", "sıkıldım", "yoruldum", "bıktım", "😔", "😢", "😭"],
            "kızgın": ["sinir", "kızdım", "öfke", "kırgın", "😠", "😡", "💢"],
            "şaşkın": ["vay", "wow", "inanılmaz", "şaşırdım", "😲", "😱", "🤯"],
            "yorgun": ["yorgun", "uyku", "uyuma", "uyumak", "tembel", "😴", "😪", "💤"],
            "enerjik": ["enerji", "güç", "motivasyon", "hazırım", "💪", "🔥", "⚡"],
            "aç": ["aç", "yemek", "karın", "acıktım", "🍕", "🍔", "🍜"],
            "susuz": ["susadım", "su", "içecek", "🥤", "💧", "☕"]
        }
        
        # Durum analizi için anahtar kelimeler
        self.context_keywords = {
            "iş": ["iş", "çalışma", "ofis", "patron", "mesai", "💼", "👔"],
            "okul": ["okul", "ders", "sınav", "ödev", "üniversite", "📚", "🎓"],
            "spor": ["spor", "fitness", "gym", "koşu", "egzersiz", "🏃", "💪"],
            "oyun": ["oyun", "game", "ps5", "xbox", "pc", "🎮", "🕹️"],
            "müzik": ["müzik", "şarkı", "konser", "festival", "🎵", "🎤", "🎧"],
            "film": ["film", "dizi", "netflix", "sinema", "🎬", "📺", "🍿"],
            "sosyal": ["arkadaş", "parti", "buluşma", "sohbet", "👥", "🎉", "🍻"],
            "aile": ["aile", "anne", "baba", "kardeş", "ev", "👨‍👩‍👧‍👦", "🏠"]
        }
        
        # Zaman analizi
        self.time_contexts = {
            "sabah": (time(6, 0), time(12, 0)),
            "öğlen": (time(12, 0), time(17, 0)),
            "akşam": (time(17, 0), time(22, 0)),
            "gece": (time(22, 0), time(6, 0))
        }
        
        # Akıllı yanıt şablonları
        self.response_templates = {
            "mutlu": {
                "morning": ["Güzel bir sabah! ☀️", "Sabah enerjisi harika! 🌅", "Güneş gibi parlıyorsun! ✨"],
                "afternoon": ["Öğlen keyfi yerinde! 🌞", "Gün ortası enerjisi! 💪", "Harika bir öğlen! 🎯"],
                "evening": ["Akşam keyfi güzel! 🌆", "Gün sonu rahatlaması! 😌", "Akşam huzuru! 🌙"],
                "night": ["Gece keyfi yerinde! 🌙", "Gece enerjisi! ⭐", "Gece huzuru! ✨"]
            },
            "üzgün": {
                "morning": ["Sabah hüznü geçer, güneş doğar! 🌅", "Yeni gün yeni umutlar! 🌟", "Sabah enerjisi seni kaldırır! 💪"],
                "afternoon": ["Öğlen molası iyi gelir! ☕", "Biraz dinlen, geçer! 😌", "Öğlen keyfi yerine gelir! 🌞"],
                "evening": ["Akşam rahatlaması! 🌆", "Gün sonu huzuru! 😊", "Akşam keyfi yerine gelir! 🌙"],
                "night": ["Gece huzuru! 🌙", "Uyku her şeyi düzeltir! 😴", "Gece rahatlaması! ✨"]
            },
            "yorgun": {
                "morning": ["Sabah uyanmak zor ama değerli! ⏰", "Kahve ile başla! ☕", "Sabah enerjisi gelir! 🌅"],
                "afternoon": ["Öğlen molası şart! 😴", "Biraz dinlen, devam ederiz! 💪", "Öğlen keyfi yerine gelir! 🌞"],
                "evening": ["Akşam rahatlaması! 🌆", "Gün sonu dinlenme! 😌", "Akşam huzuru! 🌙"],
                "night": ["Gece uykusu en iyisi! 😴", "Uyku vakti! 💤", "Gece huzuru! 🌙"]
            },
            "enerjik": {
                "morning": ["Sabah enerjisi harika! ⚡", "Güne başlama vakti! 💪", "Sabah motivasyonu! 🌅"],
                "afternoon": ["Öğlen enerjisi devam! 🔥", "Gün ortası gücü! 💪", "Öğlen motivasyonu! 🌞"],
                "evening": ["Akşam enerjisi! 🌆", "Gün sonu gücü! 💪", "Akşam motivasyonu! 🌙"],
                "night": ["Gece enerjisi! ⭐", "Gece gücü! 💪", "Gece motivasyonu! 🌙"]
            }
        }
        
        # Özel durum yanıtları
        self.special_responses = {
            "iş": {
                "positive": ["İş hayatı zorlu ama değerli! 💼", "Çalışmak güzeldir! 💪", "Başarı seninle! 🎯"],
                "negative": ["İş stresi geçer! 😌", "Biraz dinlen, devam ederiz! 💪", "Sabırla devam et! 🌟"],
                "neutral": ["İş hayatı böyle! 💼", "Çalışmaya devam! 💪", "Günlük rutin! 📅"]
            },
            "okul": {
                "positive": ["Eğitim en büyük yatırım! 📚", "Öğrenmek güzeldir! 🎓", "Başarı seninle! 🎯"],
                "negative": ["Ders stresi geçer! 😌", "Biraz dinlen, devam ederiz! 💪", "Sabırla devam et! 🌟"],
                "neutral": ["Eğitim hayatı böyle! 📚", "Öğrenmeye devam! 💪", "Günlük rutin! 📅"]
            },
            "spor": {
                "positive": ["Spor sağlık demek! 💪", "Egzersiz harika! 🏃", "Güç seninle! 🔥"],
                "negative": ["Yorgunluk geçer! 😌", "Biraz dinlen, devam ederiz! 💪", "Sabırla devam et! 🌟"],
                "neutral": ["Spor hayatı böyle! 💪", "Egzersize devam! 🏃", "Günlük rutin! 📅"]
            }
        }
        
        # Mizah anlayışı
        self.humor_patterns = {
            "şaka": ["😄", "😂", "🤣", "Hahaha!", "Güldürdün!", "Şaka güzeldi!"],
            "ironi": ["😏", "😉", "Anladım!", "Tabii tabii!", "Evet evet!"],
            "sarkazm": ["😏", "😉", "Tabii ki!", "Evet evet!", "Anladım!"]
        }
        
        # Emoji sistemi - Kullanıcı mesajlarına emoji ekleme
        self.emoji_responses = {
            "mutlu": ["😊", "😄", "🎉", "✨", "🌟", "💫"],
            "üzgün": ["😔", "😢", "💔", "🌧️", "☔", "🌈"],
            "kızgın": ["😠", "😡", "💢", "🔥", "⚡", "💥"],
            "şaşkın": ["😲", "😱", "🤯", "💫", "⭐", "🌟"],
            "yorgun": ["😴", "😪", "💤", "🌙", "⭐", "😌"],
            "enerjik": ["💪", "🔥", "⚡", "🚀", "🎯", "💎"],
            "aç": ["🍕", "🍔", "🍜", "🍖", "🍗", "🍟"],
            "susuz": ["🥤", "💧", "☕", "🍹", "🍷", "🧃"]
        }
        
        # Alakasız mesaj tespiti için kurallar
        self.irrelevant_patterns = {
            "random_chars": r'^[a-z]{8,}$',  # Sadece küçük harfler
            "numbers_only": r'^[0-9]{6,}$',  # Sadece sayılar
            "repeated_chars": r'^(.)\1{5,}$',  # Tekrar eden karakterler
            "special_chars_only": r'^[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]{3,}$',  # Sadece özel karakterler
            "spaces_only": r'^\s+$',  # Sadece boşluklar
            "emoji_only": r'^[😀-🙏🌀-🗿]+$',  # Sadece emoji
            "mixed_gibberish": r'^[a-zA-Z0-9!@#$%^&*()]{10,}$',  # Karışık anlamsız
            "single_char": r'^.$',  # Tek karakter
            "empty": r'^$',  # Boş mesaj
        }
        
        # Anlamlı mesaj tespiti için minimum gereksinimler
        self.meaningful_requirements = {
            "min_words": 1,  # En az 1 kelime (daha esnek)
            "min_turkish_chars": 2,  # En az 2 Türkçe karakter (daha esnek)
            "max_emoji_ratio": 0.8,  # Emoji oranı %80'i geçmemeli (daha esnek)
            "min_meaningful_score": 0.2  # Anlamlılık skoru (daha düşük)
        }
        
        # Bot'a hitap etme kalıpları
        self.bot_address_patterns = {
            "direct_address": [
                "bot", "kirve", "kirvehub", "kirve bot", "kirve hub",
                "hey bot", "hey kirve", "hey kirvehub",
                "bot bak", "kirve bak", "kirvehub bak",
                "bot dinle", "kirve dinle", "kirvehub dinle",
                "bot cevap", "kirve cevap", "kirvehub cevap"
            ],
            "question_patterns": [
                "ne düşünüyorsun", "ne diyorsun", "ne söylüyorsun",
                "nasıl buluyorsun", "ne yapıyorsun", "ne oluo",
                "ne haber", "naber", "nasılsın", "keyfin nasıl"
            ],
            "command_patterns": [
                "söyle", "anlat", "açıkla", "bilgi ver", "haber ver",
                "ne biliyorsun", "ne yapabilirsin", "ne yapıyorsun"
            ],
            "general_chat": [
                "günaydın", "merhaba", "selam", "sa", "iyi akşamlar", "iyi geceler",
                "nasılsın", "naber", "ne haber", "ne yapıyorsun", "keyfin nasıl"
            ]
        }
        
        # Bot'a hitap etmeyen kalıplar
        self.not_bot_address_patterns = [
            "arkadaş", "dost", "kardeş", "abi", "abla", "anne", "baba",
            "patron", "müdür", "hocam", "öğretmenim", "doktor",
            "seni", "sana", "senin", "senle", "seninle",
            "gel", "git", "gelir misin", "gider misin",
            "bana", "beni", "benim", "benle", "benimle"
        ]
    
    def is_irrelevant_message(self, text: str) -> bool:
        """Mesajın alakasız olup olmadığını kontrol et"""
        if not text or text is None:
            return True
            
        text_clean = text.strip()
        if not text_clean:
            return True
            
        # Çok kısa mesajlar (1 karakter) - SADECE gerçekten anlamsız olanlar
        if len(text_clean) == 1:
            # Tek karakter ama anlamlı olabilir (a, b, c, 1, 2, 3 gibi)
            if text_clean in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 
                             'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                             'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                             'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
                             '1', '2', '3', '4', '5', '6', '7', '8', '9', '0']:
                return True
            # Emoji veya özel karakterler anlamlı olabilir
            if ord(text_clean) > 127:
                return False  # Emoji ise alakasız değil
            return True
            
        # Çok uzun tekrar eden mesajlar
        if len(text_clean) > 100:
            # Tek karakter tekrarı kontrolü
            if len(set(text_clean)) <= 3:
                return True
            # Tek kelime tekrarı kontrolü
            words = text_clean.split()
            if len(words) > 1 and len(set(words)) == 1:
                return True
        
        # Sadece sayılar (ama kısa sayılar anlamlı olabilir)
        if text_clean.isdigit() and len(text_clean) > 3:
            return True
            
        # Sadece özel karakterler (ama kısa olanlar anlamlı olabilir)
        if all(char in '!@#$%^&*()_+-=[]{}|;:,.<>?' for char in text_clean) and len(text_clean) > 5:
            return True
            
        # Sadece boşluk
        if text_clean.isspace():
            return True
            
        # Sadece İngilizce harfler (qwerty, asdfgh vb.) - DAHA ESNEK
        if text_clean.isalpha() and len(text_clean) > 8:  # 8'den fazla karakter
            # Türkçe karakter kontrolü
            turkish_chars = 'çğıöşüÇĞIİÖŞÜ'
            if not any(char in turkish_chars for char in text_clean):
                return True
        
        # Sadece emoji kontrolü (daha esnek)
        emoji_count = sum(1 for char in text_clean if ord(char) > 127)
        if emoji_count > 0 and emoji_count >= len(text_clean) * 0.9:  # %90'dan fazlası emoji
            return True
        
        # Anlamsız tekrar eden karakterler
        if len(text_clean) > 15:  # Daha uzun mesajlar için
            # Tek karakter tekrarı
            for char in text_clean:
                if text_clean.count(char) > len(text_clean) * 0.8:  # %80'den fazla tekrar
                    return True
        
        return False
    
    def is_meaningful_message(self, text: str) -> bool:
        """Mesajın anlamlı olup olmadığını kontrol et"""
        if not text or text is None:
            return False
            
        text_lower = text.lower().strip()
        
        # Özel durumlar - Bazı kısa ama anlamlı mesajlar (ÖNCELİK)
        special_meaningful_words = [
            "evet", "hayır", "tamam", "anladım", "olur", "yok", "var", 
            "güzel", "kötü", "iyi", "süper", "harika", "mükemmel",
            "selam", "merhaba", "günaydın", "iyi akşamlar", "iyi geceler",
            "nasılsın", "naber", "ne haber", "ne yapıyorsun", "sa", "as",
            "hey", "hi", "hello", "bye", "görüşürüz", "hoşça kal"
        ]
        
        # Eğer mesaj sadece bu kelimelerden biriyse anlamlı kabul et
        if text_lower in special_meaningful_words:
            return True
        
        # Türkçe karakter sayısı (daha esnek)
        turkish_chars = len(re.findall(r'[çğıöşüÇĞIİÖŞÜa-zA-Z]', text))
        if turkish_chars < 2:  # En az 2 Türkçe karakter
            return False
        
        # Kelime sayısı (daha esnek)
        words = text_lower.split()
        if len(words) < 1:  # En az 1 kelime
            return False
        
        # Emoji oranı (daha esnek)
        emoji_count = len(re.findall(r'[😀-🙏🌀-🗿]', text))
        total_chars = len(text)
        if total_chars > 0 and emoji_count / total_chars > 0.7:  # %70'den fazlası emoji
            return False
        
        # Duygu veya bağlam tespiti
        emotion, emotion_score = self.analyze_emotion(text)
        contexts = self.analyze_context(text)
        humor = self.detect_humor(text)
        
        # Anlamlılık skoru hesapla (daha esnek)
        meaningful_score = 0
        
        # Duygu tespiti varsa +0.3
        if emotion_score > 0:
            meaningful_score += 0.3
        
        # Bağlam tespiti varsa +0.3
        if contexts:
            meaningful_score += 0.3
        
        # Mizah tespiti varsa +0.2
        if humor:
            meaningful_score += 0.2
        
        # Türkçe kelime oranı
        turkish_words = len([w for w in words if re.search(r'[çğıöşüÇĞIİÖŞÜa-zA-Z]', w)])
        if len(words) > 0:
            turkish_ratio = turkish_words / len(words)
            meaningful_score += turkish_ratio * 0.2
        
        # Daha düşük eşik değeri
        return meaningful_score >= 0.2  # %20 anlamlılık yeterli
    
    def is_addressed_to_bot(self, text: str) -> bool:
        """Mesajın bot'a hitap edip etmediğini kontrol et"""
        if not text or text is None:
            return False
            
        text_lower = text.lower().strip()
        
        # Bot'a hitap eden kelimeler (sohbet için)
        bot_mentions = [
            "bot", "kirve", "kirvehub", "@kirvehub_bot", "@kirvelastbot",
            "hey bot", "bot hey", "bot selam", "selam bot",
            "bot nasılsın", "bot ne haber", "bot naber", "kirve bot",
            "kirve", "kirvehub", "bot", "hey", "selam"
        ]
        
        # Direkt hitap kontrolü
        for mention in bot_mentions:
            if mention in text_lower:
                return True
        
        # Soru formatı kontrolü (bot'a soru soruluyor mu?)
        question_patterns = [
            r"bot\s+\w+",  # "bot nasılsın"
            r"\w+\s+bot",   # "selam bot"
            r"@kirvehub_bot\s+\w+",  # "@kirvehub_bot nasılsın"
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Genel selamlamalar bot'a hitap olarak kabul edilmez (daha sıkı)
        # Sadece bot'a direkt hitap eden mesajlar kabul edilir
        
        return False
    
    def analyze_emotion(self, text: str) -> Tuple[str, float]:
        """Mesajın duygusunu analiz et"""
        text_lower = text.lower()
        emotion_scores = {}
        
        for emotion, keywords in self.emotion_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score += 1
            emotion_scores[emotion] = score
        
        # En yüksek skorlu duyguyu bul
        if emotion_scores:
            max_emotion = max(emotion_scores, key=emotion_scores.get)
            max_score = emotion_scores[max_emotion]
            if max_score > 0:
                return max_emotion, max_score
        
        return "neutral", 0
    
    def analyze_context(self, text: str) -> List[str]:
        """Mesajın bağlamını analiz et"""
        text_lower = text.lower()
        contexts = []
        
        for context, keywords in self.context_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    contexts.append(context)
                    break
        
        return contexts
    
    def get_time_context(self) -> str:
        """Şu anki zamanı analiz et"""
        current_time = datetime.now().time()
        
        for time_name, (start_time, end_time) in self.time_contexts.items():
            if start_time <= current_time <= end_time:
                return time_name
        
        return "night"  # Varsayılan
    
    def detect_humor(self, text: str) -> Optional[str]:
        """Mizah türünü tespit et"""
        text_lower = text.lower()
        
        # Emoji analizi
        emoji_count = len(re.findall(r'[😀-🙏🌀-🗿]', text))
        if emoji_count >= 3:
            return "şaka"
        
        # Kelime analizi
        humor_words = ["haha", "lol", "😂", "😄", "🤣", "güldüm", "komik"]
        for word in humor_words:
            if word in text_lower:
                return "şaka"
        
        # Ironi tespiti
        irony_words = ["tabii", "evet evet", "anladım", "kesinlikle"]
        for word in irony_words:
            if word in text_lower:
                return "ironi"
        
        return None
    
    async def get_personalized_response(self, user_id: int, emotion: str, context: str, time_context: str) -> str:
        """Kişiselleştirilmiş yanıt oluştur"""
        try:
            # Kullanıcı bilgilerini al
            user_info = await get_user_info(user_id)
            user_points = await get_user_points(user_id)
            
            # Kullanıcı seviyesine göre yanıt
            if user_points and user_points.get('rank_level', 1) > 50:
                # Yüksek seviye kullanıcılar için daha samimi
                return self._get_advanced_response(emotion, context, time_context)
            else:
                # Normal kullanıcılar için standart yanıt
                return self._get_standard_response(emotion, context, time_context)
                
        except Exception as e:
            logger.error(f"Kişiselleştirilmiş yanıt hatası: {e}")
            return self._get_standard_response(emotion, context, time_context)
    
    def _get_standard_response(self, emotion: str, context: str, time_context: str) -> str:
        """Standart yanıt şablonlarından seç"""
        try:
            # Duygu bazlı yanıtlar
            if emotion in self.response_templates:
                time_responses = self.response_templates[emotion].get(time_context, [])
                if time_responses:
                    # Daha tutarlı seçim için hash kullan
                    import hashlib
                    hash_value = int(hashlib.md5(f"{emotion}{context}{time_context}".encode()).hexdigest()[:8], 16)
                    return time_responses[hash_value % len(time_responses)]
            
            # Bağlam bazlı yanıtlar
            if context in self.special_responses:
                if emotion in ["mutlu", "enerjik"]:
                    responses = self.special_responses[context].get("positive", [])
                elif emotion in ["üzgün", "kızgın", "yorgun"]:
                    responses = self.special_responses[context].get("negative", [])
                else:
                    responses = self.special_responses[context].get("neutral", [])
                
                if responses:
                    import hashlib
                    hash_value = int(hashlib.md5(f"{context}{emotion}".encode()).hexdigest()[:8], 16)
                    return responses[hash_value % len(responses)]
            
            # Varsayılan yanıtlar
            default_responses = {
                "morning": ["Günaydın! ☀️", "Sabah enerjisi! 🌅", "Güzel bir sabah! ✨"],
                "afternoon": ["Merhaba! 👋", "Öğlen keyfi! 🌞", "Gün ortası! 💪"],
                "evening": ["İyi akşamlar! 🌆", "Akşam huzuru! 🌙", "Gün sonu! 😌"],
                "night": ["İyi geceler! 🌙", "Gece huzuru! ✨", "Uyku vakti! 😴"]
            }
            
            time_responses = default_responses.get(time_context, ["Merhaba! 👋"])
            import hashlib
            hash_value = int(hashlib.md5(f"default{time_context}".encode()).hexdigest()[:8], 16)
            return time_responses[hash_value % len(time_responses)]
            
        except Exception as e:
            logger.error(f"Standart yanıt hatası: {e}")
            return "Merhaba! 👋"
    
    def _get_advanced_response(self, emotion: str, context: str, time_context: str) -> str:
        """Gelişmiş yanıt oluştur"""
        # Özel durum yanıtları
        if context in self.special_responses:
            if emotion in ["mutlu", "enerjik"]:
                return random.choice(self.special_responses[context]["positive"])
            elif emotion in ["üzgün", "yorgun"]:
                return random.choice(self.special_responses[context]["negative"])
            else:
                return random.choice(self.special_responses[context]["neutral"])
        
        # Gelişmiş duygu yanıtları
        advanced_responses = {
            "mutlu": ["Harika bir enerji! 🔥", "Pozitiflik bulaşıcı! ✨", "Güzel bir ruh hali! 🌟"],
            "üzgün": ["Her şey geçer! 🌈", "Yeni gün yeni umutlar! 🌅", "Güçlüsün! 💪"],
            "yorgun": ["Dinlenmeye ihtiyacın var! 😴", "Kendine iyi bak! 🌟", "Yorgunluk geçer! 💪"],
            "enerjik": ["Enerji bulaşıcı! ⚡", "Güç seninle! 💪", "Motivasyon harika! 🔥"]
        }
        
        return random.choice(advanced_responses.get(emotion, ["Merhaba! 👋"]))
    
    async def generate_smart_response(self, message: Message) -> Optional[str]:
        """Akıllı yanıt oluştur"""
        try:
            text = message.text
            if not text or text is None:
                logger.info("Mesaj metni boş veya None, yanıt verilmiyor")
                return None
                
            user_id = message.from_user.id
            text_lower = text.lower().strip()
            
            # Özel selamlama yanıtları (ÖNCELİK)
            greeting_responses = {
                "selam": ["Selam! 👋", "Selamlar! 😊", "Merhaba! 👋"],
                "merhaba": ["Merhaba! 👋", "Selamlar! 😊", "Merhaba! 👋"],
                "günaydın": ["Günaydın! ☀️", "Güzel bir sabah! 🌅", "Günaydın! 👋"],
                "iyi akşamlar": ["İyi akşamlar! 🌆", "Akşam huzuru! 🌙", "İyi akşamlar! 👋"],
                "iyi geceler": ["İyi geceler! 🌙", "Gece huzuru! ✨", "İyi geceler! 😴"],
                "sa": ["As! 👋", "Selam! 😊", "Merhaba! 👋"],
                "as": ["Sa! 👋", "Selam! 😊", "Merhaba! 👋"],
                "hey": ["Hey! 👋", "Selam! 😊", "Merhaba! 👋"],
                "hi": ["Hi! 👋", "Selam! 😊", "Merhaba! 👋"],
                "hello": ["Hello! 👋", "Selam! 😊", "Merhaba! 👋"]
            }
            
            # +18 sohbet algılama ve yönlendirme (ÖNCELİK)
            adult_keywords = [
                "+18", "18+", "artı 18", "artı18", "plus 18", "plus18",
                "yetiskin", "yetişkin", "erotik", "seks", "sex", "porno",
                "nsfw", "adult", "mature", "yasak", "yasaklı içerik"
            ]
            
            if any(keyword in text_lower for keyword in adult_keywords):
                logger.info(f"🔞 +18 sohbet algılandı - User: {user_id}, Text: '{text}'")
                return (
                    "🔞 **+18 İçerik**\n\n"
                    "Bu tür içerikler için özel kanalımızı kullanabilirsiniz:\n\n"
                    "👉 [Kirvehub +18](https://t.me/+fZZcRtudqpxjNDEy)\n\n"
                    "💡 Bu kanalda +18 içerikler paylaşılabilir."
                )
            
            # Eğer mesaj sadece selamlama ise direkt yanıt ver
            if text_lower in greeting_responses:
                return random.choice(greeting_responses[text_lower])
            
            # Bot'a hitap kontrolü (daha sıkı)
            if not self.is_addressed_to_bot(text):
                logger.info(f"Bot'a hitap etmeyen mesaj, yanıt verilmiyor: '{text}'")
                return None
            
            # Alakasız mesaj kontrolü (daha esnek)
            if self.is_irrelevant_message(text):
                logger.info(f"Alakasız mesaj tespit edildi, yanıt verilmiyor: '{text}'")
                return None
            
            # Duygu analizi
            emotion, emotion_score = self.analyze_emotion(text)
            
            # Bağlam analizi
            contexts = self.analyze_context(text)
            context = contexts[0] if contexts else "general"
            
            # Zaman analizi
            time_context = self.get_time_context()
            
            # Mizah tespiti
            humor_type = self.detect_humor(text)
            
            # Çok kısa mesajlar için özel yanıt (sadece anlamlı olanlar)
            if len(text) < 5 and self.is_meaningful_message(text):
                return random.choice(["Evet! 👍", "Tamam! 👌", "Anladım! 🤔", "Selam! 👋"])
            
            # Mizah varsa mizah yanıtı
            if humor_type:
                return random.choice(self.humor_patterns[humor_type])
            
            # Kişiselleştirilmiş yanıt
            response = await self.get_personalized_response(user_id, emotion, context, time_context)
            
            # Yanıt çok kısa ise emoji ekle
            if len(response) < 10:
                response += " " + random.choice(["😊", "👍", "👋", "✨"])
            
            # Kullanıcı mesajına uygun emoji ekle
            if emotion in self.emoji_responses:
                emoji = random.choice(self.emoji_responses[emotion])
                response += f" {emoji}"
            
            return response
            
        except Exception as e:
            logger.error(f"Akıllı yanıt hatası: {e}")
            return None  # Hata durumunda da yanıt verme

# Global instance
smart_response_system = SmartResponseSystem()

async def get_smart_response(message: Message) -> Optional[str]:
    """Akıllı yanıt al - Kontrollü çalışıyor"""
    return await smart_response_system.generate_smart_response(message) 