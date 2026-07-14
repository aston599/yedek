#!/usr/bin/env python3
"""Verify migration results"""
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
        print("🔍 MIGRATION DOĞRULAMA BAŞLATILIYOR...")
        print("=" * 60)
        
        await init_database()
        pool = await get_db_pool()
        if not pool:
            print("❌ Database pool oluşturulamadı!")
            return
        
        async with pool.acquire() as conn:
            # 1. Sistem ayarlarını kontrol et
            print("\n📊 1. SİSTEM AYARLARI KONTROLÜ:")
            print("-" * 60)
            settings = await conn.fetchrow(
                "SELECT points_per_message, daily_limit, weekly_limit FROM system_settings WHERE id = 1"
            )
            if settings:
                print(f"✅ Mesaj başına: {settings['points_per_message']} KP (beklenen: 0.20)")
                print(f"✅ Günlük limit: {settings['daily_limit']} KP (beklenen: 200.0)")
                print(f"✅ Haftalık limit: {settings['weekly_limit']} KP (beklenen: 1000.0)")
                
                # Kontrol
                if float(settings['points_per_message']) == 0.20 and float(settings['daily_limit']) == 200.0 and float(settings['weekly_limit']) == 1000.0:
                    print("✅ Sistem ayarları DOĞRU!")
                else:
                    print("⚠️ Sistem ayarları beklenen değerlerle eşleşmiyor!")
            else:
                print("❌ Sistem ayarları bulunamadı!")
            
            # 2. Backup tablolarını kontrol et
            print("\n💾 2. BACKUP TABLOLARI KONTROLÜ:")
            print("-" * 60)
            backup_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users_backup_kirve_point_migration')"
            )
            if backup_exists:
                backup_count = await conn.fetchval("SELECT COUNT(*) FROM users_backup_kirve_point_migration")
                print(f"✅ Backup tablosu mevcut: {backup_count} kayıt")
            else:
                print("❌ Backup tablosu bulunamadı!")
            
            # 3. Migration öncesi/sonrası karşılaştırma
            print("\n📈 3. MİGRATION ÖNCESİ/SONRASI KARŞILAŞTIRMA:")
            print("-" * 60)
            
            # Öncesi
            before_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as kullanici_sayisi,
                    SUM(kirve_points) as toplam_puan,
                    AVG(kirve_points) as ortalama_puan,
                    MAX(kirve_points) as max_puan,
                    MIN(kirve_points) as min_puan
                FROM users_backup_kirve_point_migration
                WHERE kirve_points > 0
            """)
            
            # Sonrası
            after_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as kullanici_sayisi,
                    SUM(kirve_points) as toplam_puan,
                    AVG(kirve_points) as ortalama_puan,
                    MAX(kirve_points) as max_puan,
                    MIN(kirve_points) as min_puan
                FROM users
                WHERE kirve_points > 0
            """)
            
            if before_stats and after_stats:
                print("ÖNCESİ:")
                print(f"  - Kullanıcı sayısı: {before_stats['kullanici_sayisi']}")
                print(f"  - Toplam puan: {float(before_stats['toplam_puan'] or 0):.2f} KP")
                print(f"  - Ortalama puan: {float(before_stats['ortalama_puan'] or 0):.2f} KP")
                print(f"  - Max puan: {float(before_stats['max_puan'] or 0):.2f} KP")
                print(f"  - Min puan: {float(before_stats['min_puan'] or 0):.2f} KP")
                
                print("\nSONRASI:")
                print(f"  - Kullanıcı sayısı: {after_stats['kullanici_sayisi']}")
                print(f"  - Toplam puan: {float(after_stats['toplam_puan'] or 0):.2f} KP")
                print(f"  - Ortalama puan: {float(after_stats['ortalama_puan'] or 0):.2f} KP")
                print(f"  - Max puan: {float(after_stats['max_puan'] or 0):.2f} KP")
                print(f"  - Min puan: {float(after_stats['min_puan'] or 0):.2f} KP")
                
                # Artış oranı
                if float(before_stats['toplam_puan'] or 0) > 0:
                    artis_orani = (float(after_stats['toplam_puan'] or 0) / float(before_stats['toplam_puan'] or 0)) * 100
                    print(f"\n📊 Artış oranı: %{artis_orani:.1f}")
            
            # 4. Multiplier dağılımı
            print("\n📊 4. MULTIPLIER DAĞILIMI:")
            print("-" * 60)
            multiplier_stats = await conn.fetch("""
                SELECT 
                    CASE 
                        WHEN (u.kirve_points / NULLIF(b.kirve_points, 0)) BETWEEN 3.0 AND 3.5 THEN '3.0x - 3.5x'
                        WHEN (u.kirve_points / NULLIF(b.kirve_points, 0)) BETWEEN 3.5 AND 4.0 THEN '3.5x - 4.0x'
                        WHEN (u.kirve_points / NULLIF(b.kirve_points, 0)) BETWEEN 4.0 AND 4.5 THEN '4.0x - 4.5x'
                        WHEN (u.kirve_points / NULLIF(b.kirve_points, 0)) BETWEEN 4.5 AND 5.0 THEN '4.5x - 5.0x'
                        ELSE 'Diğer'
                    END as multiplier_range,
                    COUNT(*) as kullanici_sayisi,
                    ROUND(AVG(u.kirve_points / NULLIF(b.kirve_points, 0))::NUMERIC, 2) as ortalama_multiplier
                FROM users u
                JOIN users_backup_kirve_point_migration b ON u.user_id = b.user_id
                WHERE b.kirve_points > 0
                GROUP BY multiplier_range
                ORDER BY multiplier_range
            """)
            
            if multiplier_stats:
                for row in multiplier_stats:
                    print(f"  {row['multiplier_range']}: {row['kullanici_sayisi']} kullanıcı (ortalama: {row['ortalama_multiplier']}x)")
            else:
                print("⚠️ Multiplier istatistikleri bulunamadı!")
            
            # 5. Migration logları
            print("\n📝 5. MİGRATION LOGLARI:")
            print("-" * 60)
            migration_log = await conn.fetchrow("""
                SELECT 
                    migration_name,
                    migration_date,
                    affected_users,
                    total_points_before,
                    total_points_after,
                    status,
                    notes
                FROM migration_logs
                WHERE migration_name = 'kirve_point_migration_v1'
                ORDER BY migration_date DESC
                LIMIT 1
            """)
            
            if migration_log:
                print(f"✅ Migration adı: {migration_log['migration_name']}")
                print(f"✅ Tarih: {migration_log['migration_date']}")
                print(f"✅ Etkilenen kullanıcı: {migration_log['affected_users']}")
                print(f"✅ Öncesi toplam puan: {float(migration_log['total_points_before'] or 0):.2f} KP")
                print(f"✅ Sonrası toplam puan: {float(migration_log['total_points_after'] or 0):.2f} KP")
                print(f"✅ Durum: {migration_log['status']}")
            else:
                print("⚠️ Migration logu bulunamadı!")
            
            # 6. Örnek kullanıcı kontrolü
            print("\n👤 6. ÖRNEK KULLANICI KONTROLÜ:")
            print("-" * 60)
            sample_user = await conn.fetchrow("""
                SELECT 
                    u.user_id,
                    u.first_name,
                    b.kirve_points as onceki_puan,
                    u.kirve_points as yeni_puan,
                    ROUND((u.kirve_points / NULLIF(b.kirve_points, 0))::NUMERIC, 2) as multiplier,
                    u.total_messages,
                    u.last_activity
                FROM users u
                JOIN users_backup_kirve_point_migration b ON u.user_id = b.user_id
                WHERE b.kirve_points > 0
                ORDER BY u.kirve_points DESC
                LIMIT 3
            """)
            
            if sample_user:
                print("En yüksek bakiyeli 3 kullanıcı:")
                users = await conn.fetch("""
                    SELECT 
                        u.user_id,
                        u.first_name,
                        b.kirve_points as onceki_puan,
                        u.kirve_points as yeni_puan,
                        ROUND((u.kirve_points / NULLIF(b.kirve_points, 0))::NUMERIC, 2) as multiplier,
                        u.total_messages
                    FROM users u
                    JOIN users_backup_kirve_point_migration b ON u.user_id = b.user_id
                    WHERE b.kirve_points > 0
                    ORDER BY u.kirve_points DESC
                    LIMIT 3
                """)
                for i, user in enumerate(users, 1):
                    print(f"\n  {i}. {user['first_name']} (ID: {user['user_id']})")
                    print(f"     Önceki: {float(user['onceki_puan']):.2f} KP")
                    print(f"     Yeni: {float(user['yeni_puan']):.2f} KP")
                    print(f"     Multiplier: {user['multiplier']}x")
                    print(f"     Mesaj sayısı: {user['total_messages']}")
            else:
                print("⚠️ Örnek kullanıcı bulunamadı!")
        
        print("\n" + "=" * 60)
        print("✅ DOĞRULAMA TAMAMLANDI!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

