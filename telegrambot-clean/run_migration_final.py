#!/usr/bin/env python3
"""Final migration runner"""
import asyncio
import sys
import os
from pathlib import Path

# Find workspace
current = Path.cwd()
workspace = None
for p in [current] + list(current.parents)[:10]:
    if (p / "database.py").exists() and (p / "database" / "migration_kirve_point_gecis.sql").exists():
        workspace = p
        break

if not workspace:
    print("ERROR: Workspace bulunamadi!")
    sys.exit(1)

os.chdir(workspace)
sys.path.insert(0, str(workspace))

from database import get_db_pool, init_database
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    try:
        print("=" * 60)
        print("🔄 KIRVE POINT MIGRATION BAŞLATILIYOR...")
        print("=" * 60)
        print(f"📁 Workspace: {workspace}")
        
        await init_database()
        pool = await get_db_pool()
        if not pool:
            print("❌ Database pool oluşturulamadı!")
            return
        
        script_path = workspace / "database" / "migration_kirve_point_gecis.sql"
        print(f"📄 Script okunuyor: {script_path}")
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print("⚙️ Migration çalıştırılıyor...")
        print("⚠️  DİKKAT: Bu işlem kullanıcı bakiyelerini değiştirecek!")
        
        async with pool.acquire() as conn:
            await conn.execute(sql_script)
            print("✅ Migration tamamlandı!")
            
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            print(f"📊 Toplam kullanıcı: {user_count}")
            
            settings = await conn.fetchrow(
                "SELECT points_per_message, daily_limit, weekly_limit FROM system_settings WHERE id = 1"
            )
            if settings:
                print(f"⚙️ Sistem ayarları:")
                print(f"   - Mesaj başına: {settings['points_per_message']} KP")
                print(f"   - Günlük limit: {settings['daily_limit']} KP")
                print(f"   - Haftalık limit: {settings['weekly_limit']} KP")
            
            backup_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users_backup_kirve_point_migration')"
            )
            if backup_exists:
                backup_count = await conn.fetchval("SELECT COUNT(*) FROM users_backup_kirve_point_migration")
                print(f"✅ Backup tablosu oluşturuldu: {backup_count} kayıt")
        
        print("=" * 60)
        print("✅ MIGRATION BAŞARILI!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

