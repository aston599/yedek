#!/usr/bin/env python3
"""
SQL Güncelleme Script'ini Çalıştır
"""

import asyncio
import os
from database import get_db_pool, init_database

async def run_sql_update():
    """SQL güncelleme script'ini çalıştır"""
    try:
        print("🔌 Database'e bağlanılıyor...")
        await init_database()
        pool = await get_db_pool()
        
        if not pool:
            print("❌ Database pool oluşturulamadı!")
            return
        
        conn = await pool.acquire()
        
        try:
            # SQL script'ini oku
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "update_scheduled_messages.sql")
            if not os.path.exists(script_path):
                # Alternatif yol dene
                script_path = "database/update_scheduled_messages.sql"
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"SQL script bulunamadı: {script_path}")
            
            with open(script_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            print(f"📄 SQL script'i okundu: {script_path}")
            print("\n" + "="*80)
            print("🚀 SQL GÜNCELLEME BAŞLATILIYOR")
            print("="*80 + "\n")
            
            # SQL script'ini çalıştır
            # DO $$ bloğunu çalıştır
            await conn.execute(sql_script)
            
            print("\n" + "="*80)
            print("✅ SQL GÜNCELLEME TAMAMLANDI")
            print("="*80)
            
            # Güncellenmiş ayarları göster
            print("\n📊 Güncellenmiş Ayarlar:\n")
            result = await conn.fetchrow("""
                SELECT 
                    jsonb_pretty(settings->'bot_profiles') as bot_profiles,
                    jsonb_pretty(settings->'auto_commands') as auto_commands
                FROM scheduled_messages_settings
                WHERE id = 1
            """)
            
            if result:
                print("🤖 Bot Profilleri:")
                print(result['bot_profiles'] or "Yok")
                print("\n⚙️ Otomatik Komutlar:")
                print(result['auto_commands'] or "Yok")
            
        finally:
            await pool.release(conn)
            print("\n✅ İşlem tamamlandı!")
            
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 SQL Güncelleme Script'i Başlatılıyor...\n")
    try:
        asyncio.run(run_sql_update())
    except KeyboardInterrupt:
        print("\n⏹️ Script kullanıcı tarafından durduruldu!")
    except Exception as e:
        print(f"\n❌ Script hatası: {e}")
        import traceback
        traceback.print_exc()

