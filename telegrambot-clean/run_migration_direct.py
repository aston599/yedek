#!/usr/bin/env python3
"""
🔄 Kirve Point Migration - Direct Execution
Migration script'ini doğrudan çalıştırır
"""

import asyncio
import logging
from pathlib import Path
import os

# Dosya yolunu düzelt
script_dir = Path(__file__).resolve().parent
os.chdir(script_dir)

from database import get_db_pool, init_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_migration():
    """Migration script'ini çalıştır"""
    try:
        logger.info("=" * 60)
        logger.info("🔄 KIRVE POINT MIGRATION BAŞLATILIYOR...")
        logger.info("=" * 60)
        
        # Database bağlantısı
        logger.info("📡 Database bağlantısı kuruluyor...")
        await init_database()
        pool = await get_db_pool()
        
        if not pool:
            logger.error("❌ Database pool oluşturulamadı!")
            return False
        
        logger.info("✅ Database bağlantısı başarılı!")
        
        # Migration script'ini oku
        script_path = script_dir / "database" / "migration_kirve_point_gecis.sql"
        
        if not script_path.exists():
            logger.error(f"❌ Migration script bulunamadı: {script_path}")
            return False
        
        logger.info(f"📄 Migration script okunuyor: {script_path}")
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        logger.info("⚙️ Migration script çalıştırılıyor...")
        logger.warning("⚠️  DİKKAT: Bu işlem kullanıcı bakiyelerini değiştirecek!")
        
        async with pool.acquire() as conn:
            # Transaction başlat
            await conn.execute("BEGIN;")
            logger.info("✅ Transaction başlatıldı")
            
            try:
                # Script'i çalıştır (tüm script bir transaction içinde)
                await conn.execute(sql_script)
                logger.info("✅ Migration script başarıyla çalıştırıldı!")
                
                # Sonuçları kontrol et
                logger.info("🔍 Migration sonuçları kontrol ediliyor...")
                
                # Kullanıcı sayısını kontrol et
                user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                logger.info(f"📊 Toplam kullanıcı sayısı: {user_count}")
                
                # Sistem ayarlarını kontrol et
                settings = await conn.fetchrow(
                    "SELECT points_per_message, daily_limit, weekly_limit FROM system_settings WHERE id = 1"
                )
                if settings:
                    logger.info(f"⚙️ Yeni sistem ayarları:")
                    logger.info(f"   - Mesaj başına: {settings['points_per_message']} KP")
                    logger.info(f"   - Günlük limit: {settings['daily_limit']} KP")
                    logger.info(f"   - Haftalık limit: {settings['weekly_limit']} KP")
                
                # Backup tablosunu kontrol et
                backup_exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users_backup_kirve_point_migration')"
                )
                if backup_exists:
                    logger.info("✅ Backup tablosu oluşturuldu: users_backup_kirve_point_migration")
                    backup_count = await conn.fetchval("SELECT COUNT(*) FROM users_backup_kirve_point_migration")
                    logger.info(f"💾 Backup kayıt sayısı: {backup_count}")
                
                logger.info("=" * 60)
                logger.info("✅ MIGRATION BAŞARILI!")
                logger.info("=" * 60)
                return True
                
            except Exception as e:
                logger.error(f"❌ Migration hatası: {e}", exc_info=True)
                logger.error("⚠️ Transaction geri alınıyor (ROLLBACK)...")
                await conn.execute("ROLLBACK;")
                return False
        
    except Exception as e:
        logger.error(f"❌ Migration çalıştırma hatası: {e}", exc_info=True)
        return False


async def main():
    """Ana fonksiyon"""
    success = await run_migration()
    
    if success:
        print()
        print("=" * 60)
        print("✅ MIGRATION TAMAMLANDI!")
        print("=" * 60)
        print()
        print("📋 Sonraki adımlar:")
        print("   1. Migration sonuçlarını kontrol edin")
        print("   2. Kullanıcı bakiyelerini test edin")
        print("   3. Sistem ayarlarını kontrol edin")
        print()
        print("💾 Backup tablosu: users_backup_kirve_point_migration")
        print("🔄 Rollback için: database/rollback_kirve_point_gecis.sql")
        print()
    else:
        print()
        print("=" * 60)
        print("❌ MIGRATION BAŞARISIZ!")
        print("=" * 60)
        print()
        print("⚠️  Lütfen hataları kontrol edin ve gerekirse rollback yapın")
        print()


if __name__ == "__main__":
    asyncio.run(main())

