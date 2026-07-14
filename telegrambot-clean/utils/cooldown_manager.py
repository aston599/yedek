"""
⏱️ Cooldown Manager - Bot Mesaj Kısıtlamaları
"""

import asyncio
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class CooldownManager:
    """Bot mesaj cooldown yöneticisi"""
    
    def __init__(self):
        # Kullanıcı bazlı cooldown'lar
        self.user_last_message: Dict[int, datetime] = {}
        self.user_message_count: Dict[int, int] = defaultdict(int)
        
        # Global cooldown - SPAM KORUMASI: Artırıldı (arka arkaya mesaj engelleme)
        self.last_bot_message: Optional[datetime] = None
        self.global_cooldown = 120  # 120 saniye (2 dakika - arka arkaya mesaj engelleme - artırıldı)
        
        # Ayarlar - SPAM KORUMASI: Daha sıkı ayarlar
        self.min_cooldown = 1800   # 30 dakika (1800 saniye) - kullanıcı bazlı minimum (artırıldı)
        self.max_cooldown = 1800   # 30 dakika (1800 saniye) - kullanıcı bazlı maksimum (artırıldı)
        self.group_cooldown = 1200  # 20 dakika (1200 saniye) - grup bazlı cooldown (artırıldı)
        self.response_probability = 0.002  # %0.2 ihtimalle cevap ver (çok nadir - daha da azaltıldı)
        self.max_consecutive_messages = 1  # Aynı kişiye maksimum 1 mesaj (sıkı)
        
        # Grup bazlı cooldown takibi (yeni)
        self.group_last_message: Dict[int, datetime] = {}
        
    async def can_respond_to_user(self, user_id: int, group_id: Optional[int] = None, is_private: bool = False) -> bool:
        """Kullanıcıya cevap verilebilir mi kontrol et (iyileştirilmiş)"""
        try:
            # ÖNEMLİ: Özel mesajlarda cooldown yok - Her zaman cevap verilebilir
            if is_private:
                return True
            
            now = datetime.now()
            
            # 1. Kullanıcı bazlı cooldown kontrolü (15 dakika)
            if user_id in self.user_last_message:
                time_diff = (now - self.user_last_message[user_id]).total_seconds()
                if time_diff < self.min_cooldown:
                    return False
            
            # 2. Grup bazlı cooldown kontrolü (10 dakika) - YENİ
            if group_id and group_id in self.group_last_message:
                group_time_diff = (now - self.group_last_message[group_id]).total_seconds()
                if group_time_diff < self.group_cooldown:
                    return False
            
            # 3. Global cooldown kontrolü
            if self.last_bot_message:
                global_time_diff = (now - self.last_bot_message).total_seconds()
                if global_time_diff < self.global_cooldown:
                    return False
            
            # 4. Response probability kontrolü (çok nadir - %2)
            if random.random() > self.response_probability:
                return False
                
            # 5. Kullanıcının mesaj sayısı kontrolü (daha sıkı - max 1)
            if self.user_message_count[user_id] >= self.max_consecutive_messages:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Cooldown kontrol hatası: {e}")
            return False
    
    async def record_user_message(self, user_id: int, group_id: Optional[int] = None):
        """Kullanıcı mesajını kaydet (iyileştirilmiş - grup takibi eklendi)"""
        try:
            now = datetime.now()
            self.user_last_message[user_id] = now
            self.user_message_count[user_id] += 1
            self.last_bot_message = now
            
            # Grup bazlı cooldown kaydı (yeni)
            if group_id:
                self.group_last_message[group_id] = now
            
            # 15 dakika sonra mesaj sayısını sıfırla (cooldown ile uyumlu)
            asyncio.create_task(self._reset_user_count(user_id))
            
        except Exception as e:
            logger.error(f"❌ Mesaj kayıt hatası: {e}")
    
    async def _reset_user_count(self, user_id: int):
        """Kullanıcı mesaj sayısını sıfırla (cooldown ile uyumlu - SPAM KORUMASI)"""
        try:
            await asyncio.sleep(1200)  # 20 dakika bekle (cooldown ile uyumlu - artırıldı)
            self.user_message_count[user_id] = 0
        except Exception as e:
            logger.error(f"❌ Mesaj sayısı sıfırlama hatası: {e}")
    
    async def check_user_registration(self, user_id: int) -> bool:
        """Kullanıcı kayıt durumunu kontrol et"""
        try:
            from database import is_user_registered
            return await is_user_registered(user_id)
        except Exception as e:
            logger.error(f"❌ Kayıt kontrol hatası: {e}")
            return False
    
    async def should_redirect_to_registration(self, user_id: int) -> bool:
        """Kullanıcıyı kayıta yönlendir mi kontrol et"""
        try:
            is_registered = await self.check_user_registration(user_id)
            return not is_registered
        except Exception as e:
            logger.error(f"❌ Kayıt yönlendirme hatası: {e}")
            return True
    
    def get_cooldown_status(self, user_id: int) -> Dict:
        """Cooldown durumunu getir"""
        try:
            now = datetime.now()
            last_message = self.user_last_message.get(user_id)
            
            if last_message:
                time_diff = (now - last_message).total_seconds()
                remaining = max(0, self.min_cooldown - time_diff)
            else:
                remaining = 0
                
            return {
                "can_respond": remaining <= 0,
                "remaining_seconds": remaining,
                "message_count": self.user_message_count[user_id],
                "is_registered": True  # Bu değer ayrıca kontrol edilmeli
            }
        except Exception as e:
            logger.error(f"❌ Cooldown durum hatası: {e}")
            return {"can_respond": False, "remaining_seconds": 0, "message_count": 0, "is_registered": False}

# Global cooldown manager instance
cooldown_manager = CooldownManager()