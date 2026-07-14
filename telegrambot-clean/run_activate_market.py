"""
Market otomatik komutunu aktif et ve özelden gönderecek şekilde ayarla
"""
import asyncio
import logging
import os
from pathlib import Path
import sys

# Find workspace
current = Path.cwd()
workspace = None
for p in [current] + list(current.parents)[:10]:
    if (p / "database.py").exists() and (p / "database" / "activate_market_auto_command.sql").exists():
        workspace = p
        break

if not workspace:
    print("ERROR: Workspace bulunamadi!")
    sys.exit(1)

os.chdir(workspace)
sys.path.insert(0, str(workspace))

from database import get_db_pool, init_database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    try:
        print("=" * 60)
        print("🛍️ MARKET OTOMATIK KOMUTU AKTİF EDİLİYOR...")
        print("=" * 60)
        print(f"📁 Workspace: {workspace}")
        
        await init_database()
        pool = await get_db_pool()
        if not pool:
            print("❌ Database pool oluşturulamadı!")
            return
        
        script_path = workspace / "database" / "activate_market_auto_command.sql"
        print(f"📄 Script okunuyor: {script_path}")
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print("⚙️ SQL script çalıştırılıyor...")
        
        async with pool.acquire() as conn:
            await conn.execute(sql_script)
            print("✅ Market otomatik komutu aktif edildi!")
            
            # Kontrol et
            result = await conn.fetchrow("""
                SELECT jsonb_pretty(settings->'auto_commands'->'market') as market_command
                FROM scheduled_messages_settings
                WHERE id = 1
            """)
            
            if result:
                print("\n📊 Market komutu ayarları:")
                print(result['market_command'])
        
        print("=" * 60)
        print("✅ İŞLEM TAMAMLANDI!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

