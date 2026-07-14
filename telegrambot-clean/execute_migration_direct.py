#!/usr/bin/env python3
"""Direct migration execution - no file path issues"""
import asyncio
import sys
import os
from pathlib import Path

# Get workspace path from environment or use current directory
workspace = os.getenv('WORKSPACE_PATH', None)
if not workspace:
    # Try to find the workspace by looking for database.py
    current = Path.cwd()
    for parent in [current] + list(current.parents)[:5]:
        if (parent / "database.py").exists():
            workspace = str(parent)
            break

if workspace:
    os.chdir(workspace)
    sys.path.insert(0, workspace)
else:
    # Fallback: use current directory
    workspace = str(Path.cwd())
    sys.path.insert(0, workspace)

from database import get_db_pool, init_database
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    try:
        logger.info("=" * 60)
        logger.info("🔄 KIRVE POINT MIGRATION BAŞLATILIYOR...")
        logger.info("=" * 60)
        logger.info(f"📁 Workspace: {workspace}")
        
        await init_database()
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool oluşturulamadı!")
            return
        
        script_path = Path(workspace) / "database" / "migration_kirve_point_gecis.sql"
        if not script_path.exists():
            logger.error(f"❌ Script bulunamadı: {script_path}")
            return
        
        logger.info(f"📄 Script okunuyor: {script_path}")
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
                backup_count = await conn.fetchval("SELECT COUNT(*) FROM users_backup_kirve_point_migration")
                logger.info(f"✅ Backup tablosu oluşturuldu: {backup_count} kayıt")
        
        logger.info("=" * 60)
        logger.info("✅ MIGRATION BAŞARILI!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Hata: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())

