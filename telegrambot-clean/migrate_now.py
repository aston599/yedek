import asyncio
import sys
import os
from pathlib import Path

# Add current directory
try:
    current_dir = Path(__file__).parent.absolute()
except:
    # Fallback: use current working directory
    current_dir = Path.cwd()
os.chdir(current_dir)
sys.path.insert(0, str(current_dir))

from database import get_db_pool, init_database
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    try:
        logger.info("=" * 60)
        logger.info("🔄 KIRVE POINT MIGRATION BAŞLATILIYOR...")
        logger.info("=" * 60)
        
        await init_database()
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool oluşturulamadı!")
            return
        
        script_path = current_dir / "database" / "migration_kirve_point_gecis.sql"
        if not script_path.exists():
            logger.error(f"❌ Script bulunamadı: {script_path}")
            return
        
        logger.info(f"📄 Script okunuyor...")
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        logger.info("⚙️ Migration çalıştırılıyor...")
        logger.warning("⚠️  DİKKAT: Bu işlem kullanıcı bakiyelerini değiştirecek!")
        
        async with pool.acquire() as conn:
            await conn.execute(sql_script)
            logger.info("✅ Migration tamamlandı!")
            
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            logger.info(f"📊 Toplam kullanıcı: {user_count}")
            
            settings = await conn.fetchrow(
                "SELECT points_per_message, daily_limit, weekly_limit FROM system_settings WHERE id = 1"
            )
            if settings:
                logger.info(f"⚙️ Sistem ayarları:")
                logger.info(f"   - Mesaj başına: {settings['points_per_message']} KP")
                logger.info(f"   - Günlük limit: {settings['daily_limit']} KP")
                logger.info(f"   - Haftalık limit: {settings['weekly_limit']} KP")
            
            backup_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users_backup_kirve_point_migration')"
            )
            if backup_exists:
                logger.info("✅ Backup tablosu oluşturuldu")
        
        logger.info("=" * 60)
        logger.info("✅ MIGRATION BAŞARILI!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Hata: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())

