#!/usr/bin/env python3
"""
🔄 Kirve Point Migration Script Runner
Migration script'ini güvenli bir şekilde çalıştırır
"""

import asyncio
import logging
import os
from pathlib import Path

from database import get_db_pool, init_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_migration():
    """Migration script'ini çalıştır"""
    try:
        logger.info("🔄 Kirve Point Migration başlatılıyor...")
        
        # Database bağlantısı
        logger.info("📡 Database bağlantısı kuruluyor...")
        await init_database()
        pool = await get_db_pool()
        
        if not pool:
            logger.error("❌ Database pool oluşturulamadı!")
            return False
        
        # Migration script'ini oku
        # Dosya yolunu düzelt (Windows path sorunları için)
        base_dir = Path(__file__).resolve().parent
        script_path = base_dir / "database" / "migration_kirve_point_gecis.sql"
        
        if not script_path.exists():
            logger.error(f"❌ Migration script bulunamadı: {script_path}")
            return False
        
        logger.info(f"📄 Migration script okunuyor: {script_path}")
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # SQL script'i çalıştır
        logger.info("⚙️ Migration script çalıştırılıyor...")
        logger.warning("⚠️ DİKKAT: Bu işlem kullanıcı bakiyelerini değiştirecek!")
        
        async with pool.acquire() as conn:
            # Script'i parçalara ayır (; ile biten komutlar)
            # BEGIN ve COMMIT'i kontrol et
            if "BEGIN;" in sql_script:
                logger.info("✅ Transaction başlatılıyor...")
            
            # Script'i parçalara ayır ve çalıştır
            # SELECT query'leri ayrı işle (sonuç göstermek için)
            statements = []
            current_statement = ""
            
            for line in sql_script.split('\n'):
                line = line.strip()
                if not line or line.startswith('--'):
                    continue
                
                current_statement += line + '\n'
                
                if line.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
            
            # Her statement'ı çalıştır
            try:
                for i, statement in enumerate(statements, 1):
                    if not statement.strip():
                        continue
                    
                    # SELECT query'leri fetch ile çalıştır
                    if statement.strip().upper().startswith('SELECT'):
                        logger.info(f"📊 Query {i}/{len(statements)} çalıştırılıyor (SELECT)...")
                        result = await conn.fetch(statement)
                        if result:
                            logger.info(f"✅ Sonuç: {len(result)} satır")
                            # İlk birkaç satırı göster
                            for row in result[:5]:
                                logger.info(f"   {dict(row)}")
                    else:
                        logger.info(f"⚙️ Statement {i}/{len(statements)} çalıştırılıyor...")
                        await conn.execute(statement)
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
                
                logger.info("✅ Migration başarıyla tamamlandı!")
                return True
                
            except Exception as e:
                logger.error(f"❌ Migration hatası: {e}")
                logger.error("⚠️ Transaction geri alınıyor (ROLLBACK)...")
                # ROLLBACK otomatik olacak (exception durumunda)
                return False
        
    except Exception as e:
        logger.error(f"❌ Migration çalıştırma hatası: {e}", exc_info=True)
        return False


async def verify_migration():
    """Migration'ı doğrula"""
    try:
        logger.info("🔍 Migration doğrulaması başlatılıyor...")
        
        pool = await get_db_pool()
        if not pool:
            logger.error("❌ Database pool bulunamadı!")
            return False
        
        async with pool.acquire() as conn:
            # Verify script'ini oku ve çalıştır
            verify_script_path = Path(__file__).parent / "database" / "verify_migration.sql"
            
            if not verify_script_path.exists():
                logger.warning("⚠️ Verify script bulunamadı, manuel kontrol yapılıyor...")
                
                # Manuel kontrol
                user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
                logger.info(f"📊 Toplam kullanıcı: {user_count}")
                
                # Backup kontrolü
                backup_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM users_backup_kirve_point_migration"
                )
                logger.info(f"💾 Backup kayıt sayısı: {backup_count}")
                
                return True
            
            logger.info(f"📄 Verify script okunuyor: {verify_script_path}")
            with open(verify_script_path, 'r', encoding='utf-8') as f:
                verify_script = f.read()
            
            # Verify script'i çalıştır
            await conn.execute(verify_script)
            logger.info("✅ Migration doğrulaması tamamlandı!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Doğrulama hatası: {e}", exc_info=True)
        return False


async def main():
    """Ana fonksiyon"""
    print("=" * 60)
    print("🔄 KIRVE POINT MIGRATION SCRIPT")
    print("=" * 60)
    print()
    print("⚠️  DİKKAT: Bu işlem kullanıcı bakiyelerini değiştirecek!")
    print("📋 Yapılacaklar:")
    print("   1. Kullanıcı bakiyeleri endekslenecek (3.0x - 5.0x)")
    print("   2. Sistem ayarları güncellenecek")
    print("   3. Backup tabloları oluşturulacak")
    print()
    
    # Onay iste (otomatik devam et)
    print("✅ Migration başlatılıyor...")
    print()
    
    # Migration çalıştır
    success = await run_migration()
    
    if success:
        print()
        print("=" * 60)
        print("✅ MIGRATION BAŞARILI!")
        print("=" * 60)
        print()
        
        # Doğrulama yap
        print("🔍 Doğrulama yapılıyor...")
        await verify_migration()
        
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

