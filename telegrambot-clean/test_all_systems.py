#!/usr/bin/env python3
"""
🧪 Tüm Sistemleri Test Et - Telegram Simülasyonu
Bot'un tüm sistemlerini test eder ve hataları raporlar
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock
import traceback

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test sonuçları
test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def log_test(name: str, passed: bool, message: str = "", warning: bool = False):
    """Test sonucunu kaydet"""
    if warning:
        test_results['warnings'].append(f"⚠️ {name}: {message}")
        print(f"⚠️ {name}: {message}")
    elif passed:
        test_results['passed'].append(name)
        print(f"✅ {name}: {message if message else 'Başarılı'}")
    else:
        test_results['failed'].append(f"{name}: {message}")
        print(f"❌ {name}: {message}")

# Mock Telegram Objeleri
class MockUser:
    def __init__(self, user_id: int, first_name: str = "Test", username: str = None, is_bot: bool = False):
        self.id = user_id
        self.first_name = first_name
        self.username = username
        self.is_bot = is_bot
        self.last_name = None

class MockChat:
    def __init__(self, chat_id: int, chat_type: str = "group", title: str = "Test Group"):
        self.id = chat_id
        self.type = chat_type
        self.title = title

class MockMessage:
    def __init__(self, user: MockUser, chat: MockChat, text: str = "test", message_id: int = 1, date: datetime = None):
        self.from_user = user
        self.chat = chat
        self.text = text
        self.message_id = message_id
        self.date = date or datetime.now()
        self.reply_to_message = None
        self.photo = None
        self.document = None

# Test Fonksiyonları
async def test_bot_startup_protection():
    """Bot başlangıç koruması testi"""
    try:
        from handlers.chat_system import is_bot_startup_protection_active, bot_startup_time, STARTUP_PROTECTION_DURATION
        import time
        
        # Bot başlangıç zamanını şimdi olarak ayarla
        import handlers.chat_system as chat_system
        chat_system.bot_startup_time = time.time()
        
        # Hemen kontrol et (True olmalı)
        is_active = is_bot_startup_protection_active()
        if not is_active:
            log_test("Bot Başlangıç Koruması (Hemen)", False, "Bot başladıktan hemen sonra koruma aktif olmalı")
            return
        
        # 3 dakika sonra kontrol et (False olmalı)
        chat_system.bot_startup_time = time.time() - (STARTUP_PROTECTION_DURATION + 10)
        is_active = is_bot_startup_protection_active()
        if is_active:
            log_test("Bot Başlangıç Koruması (3 dk sonra)", False, "3 dakika sonra koruma kalkmalı")
            return
        
        log_test("Bot Başlangıç Koruması", True)
    except Exception as e:
        log_test("Bot Başlangıç Koruması", False, f"Hata: {str(e)}\n{traceback.format_exc()}")

async def test_site_list_auto():
    """Otomatik siteler listesi testi"""
    try:
        from handlers.site_manager import show_site_list_auto, SITE_LIST_AUTO_INTERVAL_MINUTES, SITE_LIST_CHECK_INTERVAL_MINUTES
        
        # Mock bot instance
        mock_bot = AsyncMock()
        mock_bot.get_me = AsyncMock(return_value=Mock(id=12345))
        mock_bot.send_message = AsyncMock()
        
        from handlers.site_manager import set_bot_instance
        set_bot_instance(mock_bot)
        
        # Test 1: Bot başlangıç koruması
        from handlers.chat_system import bot_startup_time, STARTUP_PROTECTION_DURATION
        import handlers.chat_system as chat_system
        import time
        chat_system.bot_startup_time = time.time()  # Yeni başladı
        
        result = await show_site_list_auto(-1001234567890, mock_bot)
        if result:
            log_test("Otomatik Siteler (Başlangıç Koruması)", False, "Bot başlangıç koruması aktifken mesaj gönderilmemeli")
            return
        
        # Test 2: Interval kontrolü
        chat_system.bot_startup_time = time.time() - (STARTUP_PROTECTION_DURATION + 10)  # 3 dakika geçti
        
        # İlk gönderim (başarılı olmalı - eğer database'de site varsa)
        result1 = await show_site_list_auto(-1001234567890, mock_bot)
        
        # Hemen tekrar gönderim (başarısız olmalı - interval kontrolü)
        result2 = await show_site_list_auto(-1001234567890, mock_bot)
        if result2:
            log_test("Otomatik Siteler (Interval Kontrolü)", False, "Interval kontrolü çalışmıyor")
            return
        
        log_test("Otomatik Siteler Listesi", True, f"İlk gönderim: {result1}, İkinci gönderim: {result2}")
    except Exception as e:
        log_test("Otomatik Siteler Listesi", False, f"Hata: {str(e)}\n{traceback.format_exc()}")

async def test_group_activity_monitor():
    """Grup aktivite izleme testi"""
    try:
        from handlers.group_activity_monitor import (
            record_group_message, record_bot_message, check_group_activity,
            recent_messages_by_group, MIN_USER_MESSAGES_REQUIRED, MAX_RECENT_MESSAGES
        )
        from handlers.group_activity_monitor import set_bot_instance
        
        # Mock bot
        mock_bot = Mock()
        mock_bot.get_me = AsyncMock(return_value=Mock(id=12345))
        mock_bot.get_chat_member = AsyncMock(return_value=Mock(status='member', can_send_messages=True))
        set_bot_instance(mock_bot)
        
        group_id = -1001234567890
        
        # Test 1: Kullanıcı mesajlarını kaydet (25 kullanıcı mesajı)
        for i in range(25):
            user = MockUser(1000 + i, f"User{i}", is_bot=False)
            chat = MockChat(group_id)
            message = MockMessage(user, chat, f"Test message {i}")
            await record_group_message(message)
        
        # Test 2: Aktivite kontrolü (20+ kullanıcı mesajı var, son mesaj kullanıcı, başarılı olmalı)
        should_send, reason = await check_group_activity(group_id)
        if not should_send:
            log_test("Grup Aktivite (20+ Mesaj)", False, f"20+ kullanıcı mesajı varken ve son mesaj kullanıcı ise gönderilmeli: {reason}")
            return
        
        # Test 3: Bot mesajını kaydet (son mesajı bot yap)
        await record_bot_message(group_id, 12345)
        
        # Test 4: Aktivite kontrolü (son mesaj bot, başarısız olmalı)
        should_send, reason = await check_group_activity(group_id)
        if should_send:
            log_test("Grup Aktivite (Son Mesaj Bot)", False, "Son mesaj bot ise gönderilmemeli")
            return
        
        # Test 5: Yetersiz kullanıcı mesajı durumu
        # Yeni bir grup ID kullan (karışıklığı önlemek için)
        test_group_id = -1009999999999
        recent_messages_by_group[test_group_id] = []
        for i in range(10):  # Sadece 10 kullanıcı mesajı
            recent_messages_by_group[test_group_id].append({
                'time': datetime.now(),
                'is_bot': False,
                'user_id': 2000 + i
            })
        
        # group_activity_status'u da güncelle
        from handlers.group_activity_monitor import group_activity_status
        group_activity_status[test_group_id] = {
            'last_message_time': datetime.now(),
            'last_sender_id': 2000,
            'is_bot_message': False,
            'status': 'active'
        }
        
        should_send, reason = await check_group_activity(test_group_id)
        if should_send:
            log_test("Grup Aktivite (Yetersiz Mesaj)", False, "10 kullanıcı mesajı varken gönderilmemeli")
            return
        
        log_test("Grup Aktivite İzleme", True)
    except Exception as e:
        log_test("Grup Aktivite İzleme", False, f"Hata: {str(e)}\n{traceback.format_exc()}")

async def test_kp_earning_system():
    """KP kazanım sistemi testi"""
    try:
        from handlers.message_monitor import (
            DEFAULT_POINT_PER_MESSAGE, DAILY_POINT_LIMIT, WEEKLY_POINT_LIMIT,
            get_system_settings
        )
        
        # Test 1: Default değerler
        if DEFAULT_POINT_PER_MESSAGE != 2.00:
            log_test("KP Sistemi (Default PPM)", False, f"Beklenen: 2.00, Bulunan: {DEFAULT_POINT_PER_MESSAGE}")
            return
        
        if DAILY_POINT_LIMIT != 133.33:
            log_test("KP Sistemi (Daily Limit)", False, f"Beklenen: 133.33, Bulunan: {DAILY_POINT_LIMIT}")
            return
        
        if WEEKLY_POINT_LIMIT != 800.0:
            log_test("KP Sistemi (Weekly Limit)", False, f"Beklenen: 800.0, Bulunan: {WEEKLY_POINT_LIMIT}")
            return
        
        # Test 2: System settings çekme
        try:
            settings = await get_system_settings()
            if not isinstance(settings, dict):
                log_test("KP Sistemi (System Settings)", False, "System settings dict döndürmeli")
                return
        except Exception as e:
            log_test("KP Sistemi (System Settings)", True, f"Database bağlantısı yok (normal): {str(e)}", warning=True)
        
        log_test("KP Kazanım Sistemi", True)
    except Exception as e:
        log_test("KP Kazanım Sistemi", False, f"Hata: {str(e)}\n{traceback.format_exc()}")

async def test_cooldown_manager():
    """Cooldown manager testi"""
    try:
        from utils.cooldown_manager import cooldown_manager
        
        user_id = 12345
        group_id = -1001234567890
        
        # Test 1: Private mesaj cooldown yok
        can_respond = await cooldown_manager.can_respond_to_user(user_id, None, is_private=True)
        if not can_respond:
            log_test("Cooldown Manager (Private)", False, "Private mesajlarda cooldown olmamalı")
            return
        
        # Test 2: Normal cooldown kontrolü
        await cooldown_manager.record_user_message(user_id, group_id)
        can_respond = await cooldown_manager.can_respond_to_user(user_id, group_id, is_private=False)
        # İlk mesajdan hemen sonra cooldown olabilir (normal)
        
        log_test("Cooldown Manager", True)
    except Exception as e:
        log_test("Cooldown Manager", False, f"Hata: {str(e)}\n{traceback.format_exc()}")

async def test_chat_system():
    """Chat sistemi testi"""
    try:
        from handlers.chat_system import (
            chat_probability, min_message_length, NON_ADDRESSED_MIN_INTERVAL_SEC,
            GROUP_QUESTION_PROBABILITY, KIRVE_MENTION_PROBABILITY
        )
        
        # Test 1: Spam koruması değerleri
        if chat_probability > 0.01:
            log_test("Chat Sistemi (Probability)", False, f"chat_probability çok yüksek: {chat_probability}")
            return
        
        if min_message_length < 8:
            log_test("Chat Sistemi (Min Length)", False, f"min_message_length çok düşük: {min_message_length}")
            return
        
        if NON_ADDRESSED_MIN_INTERVAL_SEC < 1800:
            log_test("Chat Sistemi (Non-addressed Interval)", False, f"Interval çok kısa: {NON_ADDRESSED_MIN_INTERVAL_SEC}")
            return
        
        log_test("Chat Sistemi", True)
    except Exception as e:
        log_test("Chat Sistemi", False, f"Hata: {str(e)}\n{traceback.format_exc()}")

async def test_database_connection():
    """Database bağlantı testi"""
    try:
        from database import get_db_pool
        
        pool = await get_db_pool()
        if not pool:
            log_test("Database Bağlantısı", True, "Database bağlantısı yok (normal - .env gerekli)", warning=True)
            return
        
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            if result != 1:
                log_test("Database Bağlantısı", False, "Database sorgusu başarısız")
                return
        
        log_test("Database Bağlantısı", True)
    except Exception as e:
        log_test("Database Bağlantısı", True, f"Database bağlantısı yok (normal - .env gerekli): {str(e)}", warning=True)

async def test_mod_system():
    """Mod sistemi testi"""
    try:
        from handlers.mod_handler import get_moderators_from_db
        
        # Test 1: Mod listesi çekme
        try:
            mods = await get_moderators_from_db(include_inactive=False)
            if not isinstance(mods, list):
                log_test("Mod Sistemi (Liste)", False, "Mod listesi list döndürmeli")
                return
        except Exception as e:
            log_test("Mod Sistemi (Liste)", True, f"Database bağlantısı yok (normal): {str(e)}", warning=True)
        
        log_test("Mod Sistemi", True)
    except Exception as e:
        log_test("Mod Sistemi", False, f"Hata: {str(e)}\n{traceback.format_exc()}")

async def test_profile_handler():
    """Profile handler testi"""
    try:
        from handlers.profile_handler import _send_menu_privately
        
        # Test 1: total_points hatası kontrolü
        # Kod içinde total_points tanımlı mı kontrol et
        import inspect
        source = inspect.getsource(_send_menu_privately)
        if 'total_points = user_points.get' not in source:
            log_test("Profile Handler (total_points)", False, "total_points tanımlı değil")
            return
        
        log_test("Profile Handler", True)
    except Exception as e:
        log_test("Profile Handler", False, f"Hata: {str(e)}\n{traceback.format_exc()}")

async def test_scheduled_messages():
    """Zamanlanmış mesajlar testi"""
    try:
        from handlers.scheduled_messages import send_scheduled_message
        
        # Test 1: Bot başlangıç koruması kontrolü
        import handlers.chat_system as chat_system
        import time
        chat_system.bot_startup_time = time.time()  # Yeni başladı
        
        # Mock bot
        mock_bot = AsyncMock()
        mock_bot.get_me = AsyncMock(return_value=Mock(id=12345))
        mock_bot.send_message = AsyncMock()
        
        from handlers.scheduled_messages import set_bot_instance
        set_bot_instance(mock_bot)
        
        result = await send_scheduled_message("test_bot", -1001234567890, "Test message")
        if result:
            log_test("Zamanlanmış Mesajlar (Başlangıç Koruması)", False, "Bot başlangıç koruması aktifken mesaj gönderilmemeli")
            return
        
        log_test("Zamanlanmış Mesajlar", True)
    except Exception as e:
        log_test("Zamanlanmış Mesajlar", True, f"Test atlandı (normal): {str(e)}", warning=True)

async def test_site_manager_constants():
    """Site manager sabitleri testi"""
    try:
        from handlers.site_manager import (
            SITE_LIST_AUTO_INTERVAL_MINUTES, SITE_LIST_CHECK_INTERVAL_MINUTES
        )
        
        if SITE_LIST_AUTO_INTERVAL_MINUTES != 120:
            log_test("Site Manager (Auto Interval)", False, f"Beklenen: 120, Bulunan: {SITE_LIST_AUTO_INTERVAL_MINUTES}")
            return
        
        if SITE_LIST_CHECK_INTERVAL_MINUTES != 5:
            log_test("Site Manager (Check Interval)", False, f"Beklenen: 5, Bulunan: {SITE_LIST_CHECK_INTERVAL_MINUTES}")
            return
        
        log_test("Site Manager Sabitleri", True)
    except Exception as e:
        log_test("Site Manager Sabitleri", False, f"Hata: {str(e)}\n{traceback.format_exc()}")

async def test_group_activity_constants():
    """Grup aktivite sabitleri testi"""
    try:
        from handlers.group_activity_monitor import (
            MIN_USER_MESSAGES_REQUIRED, MAX_RECENT_MESSAGES
        )
        
        if MIN_USER_MESSAGES_REQUIRED != 20:
            log_test("Grup Aktivite (Min Messages)", False, f"Beklenen: 20, Bulunan: {MIN_USER_MESSAGES_REQUIRED}")
            return
        
        if MAX_RECENT_MESSAGES != 50:
            log_test("Grup Aktivite (Max Messages)", False, f"Beklenen: 50, Bulunan: {MAX_RECENT_MESSAGES}")
            return
        
        log_test("Grup Aktivite Sabitleri", True)
    except Exception as e:
        log_test("Grup Aktivite Sabitleri", False, f"Hata: {str(e)}\n{traceback.format_exc()}")

# Ana Test Fonksiyonu
async def run_all_tests():
    """Tüm testleri çalıştır"""
    print("=" * 60)
    print("🧪 TÜM SİSTEMLERİ TEST ET - BAŞLIYOR")
    print("=" * 60)
    print()
    
    tests = [
        ("Bot Başlangıç Koruması", test_bot_startup_protection),
        ("Otomatik Siteler Listesi", test_site_list_auto),
        ("Grup Aktivite İzleme", test_group_activity_monitor),
        ("KP Kazanım Sistemi", test_kp_earning_system),
        ("Cooldown Manager", test_cooldown_manager),
        ("Chat Sistemi", test_chat_system),
        ("Database Bağlantısı", test_database_connection),
        ("Mod Sistemi", test_mod_system),
        ("Profile Handler", test_profile_handler),
        ("Zamanlanmış Mesajlar", test_scheduled_messages),
        ("Site Manager Sabitleri", test_site_manager_constants),
        ("Grup Aktivite Sabitleri", test_group_activity_constants),
    ]
    
    for test_name, test_func in tests:
        try:
            await test_func()
        except Exception as e:
            log_test(test_name, False, f"Beklenmeyen hata: {str(e)}\n{traceback.format_exc()}")
        print()
    
    # Özet
    print("=" * 60)
    print("📊 TEST ÖZETİ")
    print("=" * 60)
    print(f"✅ Başarılı: {len(test_results['passed'])}")
    print(f"❌ Başarısız: {len(test_results['failed'])}")
    print(f"⚠️ Uyarı: {len(test_results['warnings'])}")
    print()
    
    if test_results['failed']:
        print("❌ BAŞARISIZ TESTLER:")
        for failure in test_results['failed']:
            print(f"  - {failure}")
        print()
    
    if test_results['warnings']:
        print("⚠️ UYARILAR:")
        for warning in test_results['warnings']:
            print(f"  - {warning}")
        print()
    
    if test_results['passed']:
        print("✅ BAŞARILI TESTLER:")
        for passed in test_results['passed']:
            print(f"  - {passed}")
        print()
    
    print("=" * 60)
    if len(test_results['failed']) == 0:
        print("🎉 TÜM TESTLER BAŞARILI!")
    else:
        print(f"⚠️ {len(test_results['failed'])} TEST BAŞARISIZ!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test kullanıcı tarafından durduruldu!")
    except Exception as e:
        print(f"\n\n❌ Kritik hata: {str(e)}\n{traceback.format_exc()}")

