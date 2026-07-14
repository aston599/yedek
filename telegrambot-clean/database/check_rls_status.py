"""
RLS durumunu kontrol et ve raporla
"""
import asyncio
from database import get_db_pool

async def check_rls_status():
    """Tüm tablolarda RLS durumunu kontrol et"""
    pool = await get_db_pool()
    if not pool:
        print("❌ Database bağlantısı kurulamadı!")
        return
    
    async with pool.acquire() as conn:
        print("=" * 80)
        print("🔍 RLS (Row Level Security) DURUM KONTROLÜ")
        print("=" * 80)
        
        # Tüm tabloları ve RLS durumlarını al
        rows = await conn.fetch("""
            SELECT 
                schemaname,
                tablename,
                rowsecurity as rls_enabled
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        if not rows:
            print("⚠️ Tablo bulunamadı!")
            return
        
        print(f"\n📊 Toplam {len(rows)} tablo bulundu\n")
        print("-" * 80)
        
        rls_enabled = []
        rls_disabled = []
        
        for row in rows:
            table_name = row['tablename']
            is_enabled = row['rls_enabled']
            
            status = "✅ RLS AÇIK" if is_enabled else "❌ RLS KAPALI"
            
            if is_enabled:
                rls_enabled.append(table_name)
            else:
                rls_disabled.append(table_name)
            
            print(f"{status} - {table_name}")
        
        print("-" * 80)
        print(f"\n📈 ÖZET:")
        print(f"   ✅ RLS Açık: {len(rls_enabled)} tablo")
        print(f"   ❌ RLS Kapalı: {len(rls_disabled)} tablo")
        
        if rls_disabled:
            print(f"\n⚠️ RLS KAPALI TABLOLAR (Güvenlik Riski):")
            for table in rls_disabled:
                print(f"   • {table}")
        
        print("\n" + "=" * 80)
        print("💡 ÖNERİLER:")
        print("=" * 80)
        
        if rls_disabled:
            print("""
1. Supabase API kullanıyorsanız:
   → RLS'yi etkinleştirin (database/enable_rls.sql)
   → Güvenlik politikaları ekleyin

2. Sadece bot üzerinden erişim varsa:
   → RLS'yi kapatabilirsiniz (güvenlik riski yok)
   → Bot'un direkt PostgreSQL bağlantısı çalışır

3. Her iki durumda da:
   → Bot'un database bağlantı bilgilerini güvende tutun
   → API anahtarlarını paylaşmayın
            """)
        else:
            print("✅ Tüm tablolarda RLS açık! Güvenlik iyi durumda.")
        
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(check_rls_status())



