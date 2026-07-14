#!/usr/bin/env python3
"""
📅 SQL'deki Zamanlanmış Mesajları Çıkart
"""

import asyncio
import json
from database import get_db_pool, init_database

async def extract_scheduled_messages():
    """SQL'deki zamanlanmış mesajları çıkart"""
    try:
        print("🔌 Database'e bağlanılıyor...")
        await init_database()
        pool = await get_db_pool()
        
        if not pool:
            print("❌ Database pool oluşturulamadı!")
            return
        
        conn = await pool.acquire()
        
        try:
            # scheduled_messages_settings tablosundan veriyi çek
            result = await conn.fetchrow("""
                SELECT id, settings, created_at, updated_at
                FROM scheduled_messages_settings
                WHERE id = 1
            """)
            
            if not result:
                print("❌ scheduled_messages_settings tablosunda veri yok!")
                return
            
            settings = result['settings']
            created_at = result['created_at']
            updated_at = result['updated_at']
            
            # JSON parse et
            if isinstance(settings, str):
                settings = json.loads(settings)
            
            print("\n" + "="*80)
            print("📋 SQL'DEN ÇIKARTILAN VERİLER")
            print("="*80)
            print(f"\n📅 Oluşturulma: {created_at}")
            print(f"📅 Son Güncelleme: {updated_at}")
            
            print("\n" + "="*80)
            print("📄 TÜM JSON YAPISI (SQL'den)")
            print("="*80)
            print(json.dumps(settings, indent=2, ensure_ascii=False, default=str))
            
            # Dosyaya kaydet
            output_file = "scheduled_messages_backup.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'id': result['id'],
                    'created_at': str(created_at),
                    'updated_at': str(updated_at),
                    'settings': settings
                }, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\n💾 Veriler '{output_file}' dosyasına kaydedildi!")
            
            # Detaylı analiz
            print("\n" + "="*80)
            print("📊 DETAYLI ANALİZ")
            print("="*80)
            
            # Aktif botlar
            active_bots = settings.get('active_bots', {})
            print(f"\n🤖 Aktif Botlar: {len(active_bots)}")
            for bot_id, is_active in active_bots.items():
                print(f"   • {bot_id}: {'✅ Aktif' if is_active else '❌ Pasif'}")
            
            # Bot profilleri
            bot_profiles = settings.get('bot_profiles', {})
            print(f"\n👤 Bot Profilleri: {len(bot_profiles)}")
            for bot_id, profile in bot_profiles.items():
                print(f"\n   🤖 {bot_id}:")
                print(f"      Mesaj: {profile.get('message', 'N/A')[:60]}...")
                print(f"      Link: {profile.get('link', 'N/A')}")
                print(f"      Interval: {profile.get('interval', 'N/A')} dakika")
                print(f"      Gruplar: {len(profile.get('groups', []))} grup")
            
            # Otomatik komutlar
            auto_commands = settings.get('auto_commands', {})
            print(f"\n⚙️ Otomatik Komutlar: {len(auto_commands)}")
            for cmd_name, cmd_data in auto_commands.items():
                enabled = "✅ Aktif" if cmd_data.get('is_active', False) else "❌ Pasif"
                interval = cmd_data.get('interval_minutes', 'N/A')
                print(f"   • {cmd_name}: {enabled} (Interval: {interval} dakika)")
            
            # Gruplar
            groups = settings.get('groups', [])
            print(f"\n👥 Gruplar: {len(groups)}")
            if groups:
                for group_id in groups:
                    print(f"   • Group ID: {group_id}")
            
            # Son mesaj zamanları
            last_message_time = settings.get('last_message_time', {})
            print(f"\n⏰ Son Mesaj Zamanları: {len(last_message_time)} bot")
            for bot_id, last_time in last_message_time.items():
                print(f"   • {bot_id}: {last_time}")
            
        finally:
            await pool.release(conn)
            print("\n✅ Veriler çıkartıldı!")
            
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 SQL'den Zamanlanmış Mesajlar Çıkartılıyor...\n")
    try:
        asyncio.run(extract_scheduled_messages())
    except KeyboardInterrupt:
        print("\n⏹️ Script kullanıcı tarafından durduruldu!")
    except Exception as e:
        print(f"\n❌ Script hatası: {e}")
        import traceback
        traceback.print_exc()

