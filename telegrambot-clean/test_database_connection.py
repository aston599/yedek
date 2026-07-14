"""
🗄️ Database Bağlantı Test Script
Database bağlantısını test eder ve tabloları kontrol eder
"""

import asyncio
import sys
from database import init_database, get_db_pool, close_database
from config import get_config

async def test_database_connection():
    """Database bağlantısını test et"""
    print("=" * 80)
    print("🔍 DATABASE BAĞLANTI TESTİ")
    print("=" * 80)
    
    try:
        # Config kontrolü
        config = get_config()
        print(f"\n📋 Config Bilgileri:")
        print(f"   Database URL: {config.DATABASE_URL[:50]}...")
        print(f"   Supabase URL: {config.SUPABASE_URL}")
        print(f"   Pool Min Size: {config.DB_MIN_SIZE}")
        print(f"   Pool Max Size: {config.DB_MAX_SIZE}")
        
        # Database bağlantısını başlat
        print(f"\n🔗 Database bağlantısı kuruluyor...")
        success = await init_database()
        
        if not success:
            print("❌ Database bağlantısı başarısız!")
            return False
        
        print("✅ Database bağlantısı başarılı!")
        
        # Pool'u al
        pool = await get_db_pool()
        if not pool:
            print("❌ Database pool alınamadı!")
            return False
        
        print(f"✅ Database pool alındı!")
        print(f"   Pool Size: {pool.get_size()}")
        print(f"   Pool Free: {pool.get_idle_size()}")
        
        # Tabloları listele
        print(f"\n📊 Tablolar listeleniyor...")
        async with pool.acquire() as conn:
            # Tüm tabloları al
            tables = await conn.fetch("""
                SELECT 
                    table_name,
                    table_type
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            print(f"\n📋 Toplam {len(tables)} tablo bulundu:")
            print("-" * 80)
            for table in tables:
                print(f"   ✅ {table['table_name']}")
            
            # Her tablonun kayıt sayısını al
            print(f"\n📈 Tablo Kayıt Sayıları:")
            print("-" * 80)
            for table in tables:
                table_name = table['table_name']
                try:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    print(f"   {table_name}: {count} kayıt")
                except Exception as e:
                    print(f"   {table_name}: ❌ Hata - {e}")
            
            # Users tablosu örnek veriler
            print(f"\n👤 Users Tablosu Örnek Veriler:")
            print("-" * 80)
            users = await conn.fetch("""
                SELECT 
                    user_id,
                    username,
                    first_name,
                    kirve_points,
                    total_messages,
                    is_registered
                FROM users
                ORDER BY kirve_points DESC
                LIMIT 5
            """)
            
            if users:
                for user in users:
                    print(f"   👤 {user['first_name']} (@{user['username'] or 'N/A'})")
                    print(f"      KP: {user['kirve_points']}, Mesaj: {user['total_messages']}, Kayıtlı: {user['is_registered']}")
            else:
                print("   ⚠️ Kullanıcı bulunamadı")
            
            # Groups tablosu örnek veriler
            print(f"\n👥 Groups Tablosu Örnek Veriler:")
            print("-" * 80)
            try:
                # Önce kolonları kontrol et
                columns = await conn.fetch("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'registered_groups'
                    ORDER BY ordinal_position
                """)
                column_names = [col['column_name'] for col in columns]
                
                # Mevcut kolonlara göre sorgu oluştur
                select_fields = ['group_id', 'group_name', 'is_active']
                if 'point_multiplier' in column_names:
                    select_fields.append('point_multiplier')
                if 'registration_date' in column_names:
                    order_by = 'ORDER BY registration_date DESC'
                else:
                    order_by = 'ORDER BY group_id DESC'
                
                groups = await conn.fetch(f"""
                    SELECT 
                        {', '.join(select_fields)}
                    FROM registered_groups
                    {order_by}
                    LIMIT 5
                """)
                
                if groups:
                    for group in groups:
                        group_name = group['group_name'] or f'Grup {group["group_id"]}'
                        info_parts = [f"Aktif: {group['is_active']}"]
                        if 'point_multiplier' in group:
                            info_parts.append(f"Çarpan: {group['point_multiplier']}")
                        print(f"   👥 {group_name}")
                        print(f"      {', '.join(info_parts)}")
                else:
                    print("   ⚠️ Grup bulunamadı")
            except Exception as e:
                print(f"   ❌ Hata: {e}")
                # Alternatif: Sadece temel kolonları kullan
                try:
                    groups = await conn.fetch("""
                        SELECT 
                            group_id,
                            group_name,
                            is_active
                        FROM registered_groups
                        LIMIT 5
                    """)
                    if groups:
                        for group in groups:
                            group_name = group['group_name'] or f'Grup {group["group_id"]}'
                            print(f"   👥 {group_name}")
                            print(f"      Aktif: {group['is_active']}")
                except Exception as e2:
                    print(f"   ❌ Alternatif sorgu da başarısız: {e2}")
            
            # Market products örnek veriler
            print(f"\n🛍️ Market Products Örnek Veriler:")
            print("-" * 80)
            products = await conn.fetch("""
                SELECT 
                    p.id,
                    p.name,
                    c.name as category,
                    p.price,
                    p.stock,
                    p.is_active
                FROM market_products p
                LEFT JOIN market_categories c ON c.id = p.category_id
                WHERE p.is_active = TRUE
                ORDER BY p.created_at DESC
                LIMIT 5
            """)
            
            if products:
                for product in products:
                    print(f"   🛍️ {product['name']}")
                    print(f"      Kategori: {product['category']}, Fiyat: {product['price']} KP, Stok: {product['stock']}")
            else:
                print("   ⚠️ Ürün bulunamadı")
            
            # Market categories
            print(f"\n📦 Market Categories:")
            print("-" * 80)
            try:
                categories = await conn.fetch("""
                    SELECT 
                        id,
                        name,
                        emoji,
                        display_order,
                        is_active
                    FROM market_categories
                    WHERE is_active = TRUE
                    ORDER BY display_order
                """)
                
                if categories:
                    for category in categories:
                        emoji = category.get('emoji') or '📦'
                        name = category.get('name') or 'Kategori'
                        order = category.get('display_order', 0)
                        print(f"   {emoji} {name} (Sıra: {order})")
                else:
                    print("   ⚠️ Kategori bulunamadı")
            except Exception as e:
                print(f"   ❌ Hata: {e}")
                # Alternatif: Sadece temel kolonları kullan
                try:
                    categories = await conn.fetch("""
                        SELECT 
                            id,
                            name,
                            display_order
                        FROM market_categories
                        WHERE is_active = TRUE
                        ORDER BY display_order
                    """)
                    if categories:
                        for category in categories:
                            name = category.get('name') or 'Kategori'
                            order = category.get('display_order', 0)
                            print(f"   📦 {name} (Sıra: {order})")
                    else:
                        print("   ⚠️ Kategori bulunamadı")
                except Exception as e2:
                    print(f"   ❌ Alternatif sorgu da başarısız: {e2}")
            
            # Events örnek veriler
            print(f"\n🎉 Events Örnek Veriler:")
            print("-" * 80)
            try:
                # Önce kolonları kontrol et
                event_columns = await conn.fetch("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'events'
                    ORDER BY ordinal_position
                """)
                event_column_names = [col['column_name'] for col in event_columns]
                
                # Mevcut kolonlara göre sorgu oluştur
                event_select_fields = ['id']
                event_name_field = None
                
                # title veya event_name kolonunu kontrol et
                if 'title' in event_column_names:
                    event_select_fields.append('title')
                    event_name_field = 'title'
                elif 'event_name' in event_column_names:
                    event_select_fields.append('event_name')
                    event_name_field = 'event_name'
                
                if 'event_type' in event_column_names:
                    event_select_fields.append('event_type')
                if 'status' in event_column_names:
                    event_select_fields.append('status')
                if 'created_at' in event_column_names:
                    event_order_by = 'ORDER BY created_at DESC'
                else:
                    event_order_by = 'ORDER BY id DESC'
                
                events = await conn.fetch(f"""
                    SELECT 
                        {', '.join(event_select_fields)}
                    FROM events
                    {event_order_by}
                    LIMIT 5
                """)
                
                if events:
                    for event in events:
                        event_name = event.get(event_name_field) or event.get('event_name') or f"Etkinlik #{event['id']}"
                        event_type = event.get('event_type', 'N/A')
                        event_status = event.get('status', 'N/A')
                        print(f"   🎉 {event_name}")
                        print(f"      Tip: {event_type}, Durum: {event_status}")
                else:
                    print("   ⚠️ Etkinlik bulunamadı")
            except Exception as e:
                print(f"   ❌ Hata: {e}")
                # Alternatif: Sadece temel kolonları kullan
                try:
                    events = await conn.fetch("""
                        SELECT 
                            id,
                            event_type,
                            status
                        FROM events
                        LIMIT 5
                    """)
                    if events:
                        for event in events:
                            print(f"   🎉 Etkinlik #{event['id']}")
                            print(f"      Tip: {event.get('event_type', 'N/A')}, Durum: {event.get('status', 'N/A')}")
                    else:
                        print("   ⚠️ Etkinlik bulunamadı")
                except Exception as e2:
                    print(f"   ❌ Alternatif sorgu da başarısız: {e2}")
            
            # System settings
            print(f"\n⚙️ System Settings:")
            print("-" * 80)
            settings = await conn.fetch("""
                SELECT 
                    points_per_message,
                    daily_limit,
                    weekly_limit
                FROM system_settings
                LIMIT 1
            """)
            
            if settings:
                setting = settings[0]
                print(f"   Mesaj Başına Point: {setting['points_per_message']}")
                print(f"   Günlük Limit: {setting['daily_limit']}")
                print(f"   Haftalık Limit: {setting['weekly_limit']}")
            else:
                print("   ⚠️ Sistem ayarları bulunamadı")
            
            # Point settings
            print(f"\n💰 Point Settings:")
            print("-" * 80)
            point_settings = await conn.fetch("""
                SELECT 
                    setting_key,
                    setting_value,
                    description
                FROM point_settings
                ORDER BY setting_key
            """)
            
            if point_settings:
                for setting in point_settings:
                    print(f"   {setting['setting_key']}: {setting['setting_value']} - {setting['description']}")
            else:
                print("   ⚠️ Point ayarları bulunamadı")
        
        print("\n" + "=" * 80)
        print("✅ DATABASE TESTİ TAMAMLANDI!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Database bağlantısını kapat
        await close_database()
        print("\n🔌 Database bağlantısı kapatıldı")

if __name__ == "__main__":
    print("🚀 Database bağlantı testi başlatılıyor...\n")
    result = asyncio.run(test_database_connection())
    sys.exit(0 if result else 1)

