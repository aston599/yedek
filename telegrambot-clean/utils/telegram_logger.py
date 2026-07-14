"""
📱 Telegram Logger - Tüm logları Telegram grubuna gönderir
"""

import logging
import asyncio
import time
from datetime import datetime
from aiogram import Bot
from collections import defaultdict, deque

class TelegramLogHandler(logging.Handler):
    """Telegram'a log gönderen handler"""
    
    def __init__(self, bot: Bot, chat_id: int, level=logging.INFO):
        super().__init__(level)
        self.bot = bot
        self.chat_id = chat_id
        self.log_queue = deque(maxlen=50)  # Maksimum 50 log
        self.last_send_time = 0
        self.rate_limit_delay = 45  # 30 -> 45 saniye bekle (daha güvenli)
        self.min_logs_to_send = 6   # 5 -> 6 log varsa gönder
        self.max_logs_per_message = 2  # 3 -> 2 (daha küçük paket)
        # Eşzamanlı gönderimi engellemek için lock
        import asyncio as _asyncio
        self._send_lock = _asyncio.Lock()
        
    def emit(self, record):
        """Log kaydını işle"""
        try:
            # Log seviyesini kontrol et
            if record.levelno < self.level:
                return
                
            # Log mesajını formatla
            message = self.format(record)
            
            # Severity hesapla
            severity = self._calculate_severity(record.levelname)
            
            # Log'u queue'ya ekle
            log_entry = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'level': record.levelname,
                'message': message,
                'severity': severity
            }
            
            self.log_queue.append(log_entry)
            
            # Queue'yu kontrol et ve gönder
            asyncio.create_task(self._check_and_send_logs())
            
        except Exception as e:
            print(f"Log emit hatası: {e}")
    
    def _calculate_severity(self, level: str) -> int:
        """Log seviyesine göre severity hesapla"""
        severity_map = {
            'DEBUG': 1,
            'INFO': 3,
            'WARNING': 5,
            'ERROR': 7,
            'CRITICAL': 9,
            'SYSTEM': 2
        }
        return severity_map.get(level, 3)
    
    async def _check_and_send_logs(self):
        """Log'ları kontrol et ve gönder"""
        current_time = time.time()
        
        # Rate limit kontrolü
        if current_time - self.last_send_time < self.rate_limit_delay:
            return
            
        # Yeterli log var mı kontrol et
        if len(self.log_queue) < self.min_logs_to_send:
            return
        
        # Aynı anda birden fazla gönderimi engelle
        if self._send_lock.locked():
            return
        async with self._send_lock:
            await self.send_logs()
    
    async def send_logs(self):
        """Log'ları gönder"""
        if not self.log_queue:
            return
            
        try:
            current_time = time.time()
            # Hata anında dahi sık tekrar denemeyi önlemek için baştan zaman damgası koy
            self.last_send_time = current_time
            
            # Log'ları grupla (level'e göre)
            logs_by_level = defaultdict(list)
            sent_count = 0
            
            while self.log_queue and sent_count < 1:  # Maksimum 1 mesaj gönder (daha az risk)
                # En yüksek severity'li log'u al
                logs = list(self.log_queue)
                if not logs:
                    break
                    
                # En yüksek severity'li log'u bul
                max_severity_log = max(logs, key=lambda x: x['severity'])
                
                # Aynı seviyedeki log'ları grupla
                level = max_severity_log['level']
                level_logs = [log for log in logs if log['level'] == level][:self.max_logs_per_message]
                
                # Log'ları queue'dan çıkar
                for log in level_logs:
                    if log in self.log_queue:
                        self.log_queue.remove(log)
                
                # Log'ları gönder
                await self.send_level_logs(level, level_logs)
                sent_count += 1
                
                # Rate limit için bekle
                await asyncio.sleep(5)  # 5 saniye bekle
                
            self.last_send_time = current_time
            
        except Exception as e:
            print(f"Log gönderme hatası: {e}")
            # Hata durumunda bekleme süresini uzat ve zaman damgasını güncelle
            self.rate_limit_delay = max(self.rate_limit_delay, 120)
            self.last_send_time = time.time()
            
    async def send_level_logs(self, level: str, logs: list):
        """Seviye loglarını gönder - Minimalize emoji versiyon (kopyala-yapıştır için)"""
        if not logs:
            return
            
        try:
            # Minimalize prefix'ler (kopyala-yapıştır için)
            level_prefix = {
                'DEBUG': '[DEBUG]',
                'INFO': '[INFO]',
                'WARNING': '[WARN]',
                'ERROR': '[ERROR]',
                'CRITICAL': '[CRITICAL]',
                'SYSTEM': '[SYSTEM]'
            }.get(level, '[LOG]')
            
            # En yüksek severity'li log'u bul
            max_severity = max(log['severity'] for log in logs)
            health_status = "OK" if max_severity <= 5 else "WARN" if max_severity <= 7 else "CRITICAL"
            
            # Minimalize başlık
            message = f"<b>{level_prefix} {level} Raporu</b>\n"
            message += f"────────────────────────────────────\n\n"
            
            # Özet bilgiler (minimalize)
            message += f"<b>Ozet:</b>\n"
            message += f"• Toplam Log: <code>{len(logs)}</code>\n"
            message += f"• Zaman: <code>{datetime.now().strftime('%H:%M:%S')}</code>\n"
            message += f"• Severity: <code>{max_severity}/10</code>\n"
            message += f"• Durum: <code>{health_status}</code>\n\n"
            
            # Log detayları - Minimalize format (daha fazla log göster)
            message += f"<b>Detaylar:</b>\n"
            message += f"────────────────────────────────────\n"
            
            for i, log in enumerate(logs[:5]):  # 3'ten 5'e çıkarıldı (daha fazla log görmek için)
                # HTML karakterlerini escape et
                safe_message = log['message'].replace('<', '&lt;').replace('>', '&gt;')
                # Timestamp formatı
                clean_timestamp = log['timestamp']
                # Severity göster (kritik loglar için işaret)
                severity_mark = "!" if log['severity'] >= 8 else "?" if log['severity'] >= 5 else ""
                message += f"<code>{clean_timestamp}</code> {severity_mark} {safe_message}\n\n"
                
            if len(logs) > 5:
                message += f"<i>... ve {len(logs) - 5} log daha</i>\n"
            
            message += f"────────────────────────────────────\n"
            message += f"<i>KirveBot Log Sistemi</i>"
                
            # Mesajı gönder
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML"
            )
            
        except Exception as e:
            print(f"Seviye log gönderme hatası: {e}")
            # Flood control hatası varsa daha uzun bekle
            if "Flood control exceeded" in str(e) or "Too Many Requests" in str(e):
                self.rate_limit_delay = max(self.rate_limit_delay, 120)  # 120 saniye
                self.last_send_time = time.time()
                print(f"⚠️ Flood control tespit edildi! Rate limit {self.rate_limit_delay} saniyeye çıkarıldı.")

# Global telegram logger
_telegram_logger = None

def setup_telegram_logger(bot: Bot, chat_id: int):
    """Telegram logger'ı kur"""
    global _telegram_logger
    
    if _telegram_logger:
        return _telegram_logger
        
    # Telegram handler oluştur
    telegram_handler = TelegramLogHandler(bot, chat_id)
    telegram_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    telegram_handler.setFormatter(formatter)
    
    # Root logger'a ekle
    root_logger = logging.getLogger()
    root_logger.addHandler(telegram_handler)
    
    _telegram_logger = telegram_handler
    return _telegram_logger

def get_telegram_logger():
    """Telegram logger'ı al"""
    return _telegram_logger 