#!/usr/bin/env python3
"""
Sistem Hata Kontrolü Script
"""

import asyncio
import sys
import os

# Workspace path'i ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def check_system_errors():
    """Sistemde hata kontrolü yap"""
    errors = []
    warnings = []
    
    print("🔍 Sistem Hata Kontrolü Başlatılıyor...\n")
    
    # 1. Import kontrolü
    print("1️⃣ Import kontrolü yapılıyor...")
    try:
        from handlers.scheduled_messages import (
            send_auto_commands,
            scheduled_message_task,
            get_active_groups
        )
        from handlers.group_activity_monitor import check_group_activity
        print("   ✅ scheduled_messages.py import başarılı")
    except Exception as e:
        errors.append(f"❌ scheduled_messages.py import hatası: {e}")
        print(f"   ❌ scheduled_messages.py import hatası: {e}")
    
    try:
        from handlers.group_activity_monitor import check_group_activity
        print("   ✅ group_activity_monitor.py import başarılı")
    except Exception as e:
        errors.append(f"❌ group_activity_monitor.py import hatası: {e}")
        print(f"   ❌ group_activity_monitor.py import hatası: {e}")
    
    try:
        from handlers.market_callbacks import show_market_menu_universal
        print("   ✅ market_callbacks.py import başarılı")
    except Exception as e:
        errors.append(f"❌ market_callbacks.py import hatası: {e}")
        print(f"   ❌ market_callbacks.py import hatası: {e}")
    
    try:
        from handlers.site_manager import site_command
        print("   ✅ site_manager.py import başarılı")
    except Exception as e:
        errors.append(f"❌ site_manager.py import hatası: {e}")
        print(f"   ❌ site_manager.py import hatası: {e}")
    
    # 2. Database bağlantı kontrolü
    print("\n2️⃣ Database bağlantı kontrolü yapılıyor...")
    try:
        from database import init_database, get_db_pool
        await init_database()
        pool = await get_db_pool()
        if pool:
            print("   ✅ Database bağlantısı başarılı")
        else:
            warnings.append("⚠️ Database pool None döndü")
            print("   ⚠️ Database pool None döndü")
    except Exception as e:
        errors.append(f"❌ Database bağlantı hatası: {e}")
        print(f"   ❌ Database bağlantı hatası: {e}")
    
    # 3. Scheduled messages settings kontrolü
    print("\n3️⃣ Scheduled messages settings kontrolü yapılıyor...")
    try:
        from handlers.scheduled_messages import get_scheduled_settings
        settings = await get_scheduled_settings()
        if settings:
            print("   ✅ Scheduled settings alındı")
            
            # Otomatik komutlar kontrolü
            auto_commands = settings.get('auto_commands', {})
            if auto_commands:
                print(f"   ✅ {len(auto_commands)} otomatik komut bulundu")
                for cmd_name, cmd_data in auto_commands.items():
                    is_active = cmd_data.get('is_active', False)
                    interval = cmd_data.get('interval_minutes', 'N/A')
                    status = "✅ Aktif" if is_active else "❌ Pasif"
                    print(f"      • {cmd_name}: {status} (Interval: {interval} dakika)")
            else:
                warnings.append("⚠️ Otomatik komut bulunamadı")
                print("   ⚠️ Otomatik komut bulunamadı")
            
            # Bot profilleri kontrolü
            bot_profiles = settings.get('bot_profiles', {})
            if bot_profiles:
                print(f"   ✅ {len(bot_profiles)} bot profili bulundu")
                for bot_id, profile in bot_profiles.items():
                    link = profile.get('link', 'N/A')
                    if 'kirve1.com' in link:
                        print(f"      • {bot_id}: ✅ URL güncel ({link})")
                    elif 'kumarlayasiyorum' in link:
                        warnings.append(f"⚠️ {bot_id} eski URL kullanıyor: {link}")
                        print(f"      • {bot_id}: ⚠️ Eski URL ({link})")
        else:
            warnings.append("⚠️ Scheduled settings boş")
            print("   ⚠️ Scheduled settings boş")
    except Exception as e:
        errors.append(f"❌ Scheduled settings kontrolü hatası: {e}")
        print(f"   ❌ Scheduled settings kontrolü hatası: {e}")
    
    # 4. Fonksiyon imzaları kontrolü
    print("\n4️⃣ Fonksiyon imzaları kontrolü yapılıyor...")
    try:
        import inspect
        from handlers.scheduled_messages import send_auto_commands
        
        sig = inspect.signature(send_auto_commands)
        params = list(sig.parameters.keys())
        if 'bot' in params and 'settings' in params:
            print("   ✅ send_auto_commands() imza doğru")
        else:
            errors.append(f"❌ send_auto_commands() imza hatası: {params}")
            print(f"   ❌ send_auto_commands() imza hatası: {params}")
    except Exception as e:
        errors.append(f"❌ Fonksiyon imza kontrolü hatası: {e}")
        print(f"   ❌ Fonksiyon imza kontrolü hatası: {e}")
    
    # 5. Syntax kontrolü (basit)
    print("\n5️⃣ Syntax kontrolü yapılıyor...")
    try:
        import py_compile
        files_to_check = [
            'handlers/scheduled_messages.py',
            'handlers/market_callbacks.py',
            'handlers/site_manager.py',
            'main.py'
        ]
        
        for file_path in files_to_check:
            if os.path.exists(file_path):
                try:
                    py_compile.compile(file_path, doraise=True)
                    print(f"   ✅ {file_path} syntax doğru")
                except py_compile.PyCompileError as e:
                    errors.append(f"❌ {file_path} syntax hatası: {e}")
                    print(f"   ❌ {file_path} syntax hatası: {e}")
            else:
                warnings.append(f"⚠️ {file_path} bulunamadı")
                print(f"   ⚠️ {file_path} bulunamadı")
    except Exception as e:
        errors.append(f"❌ Syntax kontrolü hatası: {e}")
        print(f"   ❌ Syntax kontrolü hatası: {e}")
    
    # Özet
    print("\n" + "="*80)
    print("📊 KONTROL ÖZETİ")
    print("="*80)
    
    if errors:
        print(f"\n❌ {len(errors)} HATA BULUNDU:")
        for error in errors:
            print(f"   {error}")
    else:
        print("\n✅ HATA BULUNMADI!")
    
    if warnings:
        print(f"\n⚠️ {len(warnings)} UYARI:")
        for warning in warnings:
            print(f"   {warning}")
    else:
        print("\n✅ UYARI YOK!")
    
    print("\n" + "="*80)
    
    if errors:
        print("❌ Sistemde hatalar var! Lütfen düzeltin.")
        return False
    else:
        print("✅ Sistem kontrolü başarılı! Hata yok.")
        return True

if __name__ == "__main__":
    try:
        result = asyncio.run(check_system_errors())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Kontrol kullanıcı tarafından durduruldu!")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Kontrol hatası: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

