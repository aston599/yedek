"""
🧠 Memory Manager - Cache ve Performance Optimizasyonu
"""

import asyncio
import logging
import gc
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheManager:
    """Cache yöneticisi - Database query'lerini cache'ler"""
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.cache_ttl: Dict[str, int] = {}  # Time to live (saniye)
        
    def set_cache(self, key: str, value: Any, ttl: int = 60) -> None:
        """Cache'e değer ekle"""
        self.cache[key] = value
        self.cache_timestamps[key] = datetime.now()
        self.cache_ttl[key] = ttl
        
    def get_cache(self, key: str) -> Optional[Any]:
        """Cache'den değer al"""
        if key not in self.cache:
            return None
            
        # TTL kontrolü
        timestamp = self.cache_timestamps.get(key)
        ttl = self.cache_ttl.get(key, 60)
        
        if timestamp and datetime.now() - timestamp > timedelta(seconds=ttl):
            # Cache süresi dolmuş
            del self.cache[key]
            del self.cache_timestamps[key]
            del self.cache_ttl[key]
            return None
            
        return self.cache[key]
        
    def clear_cache(self, key: str = None) -> None:
        """Cache temizle"""
        if key:
            self.cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
            self.cache_ttl.pop(key, None)
        else:
            self.cache.clear()
            self.cache_timestamps.clear()
            self.cache_ttl.clear()
            
    def cleanup_expired(self) -> None:
        """Süresi dolmuş cache'leri temizle"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, timestamp in self.cache_timestamps.items():
            ttl = self.cache_ttl.get(key, 60)
            if current_time - timestamp > timedelta(seconds=ttl):
                expired_keys.append(key)
                
        for key in expired_keys:
            self.cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
            self.cache_ttl.pop(key, None)

class MemoryManager:
    """Memory yöneticisi - Performance optimization"""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.cleanup_task = None
        
    def start_cleanup_task(self):
        """Cleanup task'ını başlat"""
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    async def _cleanup_loop(self):
        """Periyodik cleanup loop"""
        while True:
            try:
                # Cache temizliği
                self.cache_manager.cleanup_expired()
                
                # Garbage collection
                collected = gc.collect()
                if collected > 0:
                    logger.debug(f"🧹 Garbage collection: {collected} objects")
                    
                # 5 dakikada bir temizlik
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"❌ Cleanup loop hatası: {e}")
                await asyncio.sleep(60)
                
    def force_garbage_collection(self):
        """Zorla garbage collection"""
        try:
            collected = gc.collect()
            logger.info(f"🧹 Force garbage collection: {collected} objects")
        except Exception as e:
            logger.error(f"❌ Force garbage collection hatası: {e}")
            
    def get_cache_manager(self) -> CacheManager:
        """Cache manager'ı döndür"""
        return self.cache_manager
        
    def set_input_state(self, user_id: int, state: str) -> None:
        """Kullanıcının input state'ini ayarla"""
        key = f"input_state_{user_id}"
        self.cache_manager.set_cache(key, state, ttl=300)  # 5 dakika
        logger.info(f"🎯 INPUT STATE SET - User: {user_id}, State: {state}")
        
    def get_input_state(self, user_id: int) -> Optional[str]:
        """Kullanıcının input state'ini al"""
        key = f"input_state_{user_id}"
        state = self.cache_manager.get_cache(key)
        logger.info(f"🎯 INPUT STATE GET - User: {user_id}, State: {state}")
        return state
        
    def clear_input_state(self, user_id: int) -> None:
        """Kullanıcının input state'ini temizle"""
        key = f"input_state_{user_id}"
        self.cache_manager.clear_cache(key)
        
    def set_lottery_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """Çekiliş verilerini kaydet"""
        key = f"lottery_data_{user_id}"
        self.cache_manager.set_cache(key, data, ttl=3600)  # 1 saat
        
    def get_lottery_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Çekiliş verilerini al"""
        key = f"lottery_data_{user_id}"
        return self.cache_manager.get_cache(key)
        
    def clear_lottery_data(self, user_id: int) -> None:
        """Çekiliş verilerini temizle"""
        key = f"lottery_data_{user_id}"
        self.cache_manager.clear_cache(key)

# Global instance
memory_manager = MemoryManager()

def cleanup_all_resources():
    """Tüm kaynakları temizle"""
    try:
        # Cache temizliği
        memory_manager.cache_manager.clear_cache()
        
        # Garbage collection
        memory_manager.force_garbage_collection()
        
        logger.info("🧹 Tüm memory kaynakları temizlendi!")
        
    except Exception as e:
        logger.error(f"❌ Memory cleanup hatası: {e}")

async def start_memory_cleanup():
    """Memory cleanup task'ını başlat"""
    try:
        memory_manager.start_cleanup_task()
        logger.info("🧹 Memory cleanup task başlatıldı!")
        return memory_manager.cleanup_task
    except Exception as e:
        logger.error(f"❌ Memory cleanup task başlatma hatası: {e}")
        return None 