"""
⏱️ Rate Limiting Sistemi - Performance Optimization
"""

import asyncio
import time
from collections import defaultdict
from typing import Dict, List, Tuple

class RateLimiter:
    """Rate limiting sistemi"""
    
    def __init__(self):
        self.user_limits: Dict[int, List[float]] = defaultdict(list)
        self.global_limits: List[float] = []
        
        # Limit ayarları
        self.user_message_limit = 0.5  # Kullanıcı başına 0.5 saniye (hızlandırıldı)
        self.user_callback_limit = 0.2  # Callback başına 0.2 saniye (hızlandırıldı)
        self.global_limit = 0.05  # Global 0.05 saniye (hızlandırıldı)
        
    async def check_user_message_limit(self, user_id: int) -> bool:
        """Kullanıcı mesaj limitini kontrol et"""
        current_time = time.time()
        user_times = self.user_limits[user_id]
        
        # Eski kayıtları temizle (5 saniyeden eski)
        user_times = [t for t in user_times if current_time - t < 5.0]
        self.user_limits[user_id] = user_times
        
        # Limit kontrolü
        if len(user_times) >= 10:  # 5 saniyede maksimum 10 mesaj (artırıldı)
            return False
            
        # Yeni kayıt ekle
        user_times.append(current_time)
        return True
        
    async def check_user_callback_limit(self, user_id: int) -> bool:
        """Kullanıcı callback limitini kontrol et"""
        current_time = time.time()
        user_times = self.user_limits[f"{user_id}_callback"]
        
        # Eski kayıtları temizle (2 saniyeden eski)
        user_times = [t for t in user_times if current_time - t < 2.0]
        self.user_limits[f"{user_id}_callback"] = user_times
        
        # Limit kontrolü
        if len(user_times) >= 20:  # 2 saniyede maksimum 20 callback (artırıldı)
            return False
            
        # Yeni kayıt ekle
        user_times.append(current_time)
        return True
        
    async def check_global_limit(self) -> bool:
        """Global limit kontrolü"""
        current_time = time.time()
        
        # Eski kayıtları temizle (1 saniyeden eski)
        self.global_limits = [t for t in self.global_limits if current_time - t < 1.0]
        
        # Limit kontrolü
        if len(self.global_limits) >= 200:  # 1 saniyede maksimum 200 işlem (artırıldı)
            return False
            
        # Yeni kayıt ekle
        self.global_limits.append(current_time)
        return True
        
    async def wait_if_needed(self, user_id: int, operation_type: str = "message"):
        """Gerekirse bekle"""
        if operation_type == "message":
            while not await self.check_user_message_limit(user_id):
                await asyncio.sleep(0.1)
        elif operation_type == "callback":
            while not await self.check_user_callback_limit(user_id):
                await asyncio.sleep(0.05)
                
        # Global limit kontrolü
        while not await self.check_global_limit():
            await asyncio.sleep(0.01)

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(operation_type: str = "message"):
    """Rate limiting decorator"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # User ID'yi bul
            user_id = None
            for arg in args:
                if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                    user_id = arg.from_user.id
                    break
                    
            if user_id:
                await rate_limiter.wait_if_needed(user_id, operation_type)
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator 