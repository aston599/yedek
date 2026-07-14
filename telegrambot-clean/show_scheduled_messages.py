#!/usr/bin/env python3
"""
📅 Zamanlanmış ve Otomatik Mesajlar Analiz Script
Windows'tan çalıştırılabilir
"""

import asyncio
import json
import os
from datetime import datetime
from database import get_db_pool, init_database

async def analyze_scheduled_messages():
    """Zamanlanmış mesajları analiz et"""
    try:
        # Database'i başlat
        print("🔌 Database'e bağlanılıyor...")
        await init_database()
        pool = await get_db_pool()
        
        if not pool:
            print("❌ Database pool oluşturulamadı!")
            return
        
        conn = await pool.acquire()
        
        try:
            # 1. Tablo yapısını göster
            print("\n" + "="*80)
            print("📊 TABLO YAPISI")
            print("="*80)
            columns = await conn.fetch("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = 'scheduled_messages_settings'
                ORDER BY ordinal_position
            """)
            
            for col in columns:
                print(f"  • {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
            
            # 2. Mevcut ayarları al
            print("\n" + "="*80)
            print("📋 MEVCUT AYARLAR")
            print("="*80)
            result = await conn.fetchrow("""
                SELECT id, settings, created_at, updated_at
                FROM scheduled_messages_settings
                WHERE id = 1
            """)
            
            if not result:
                print("  ❌ scheduled_messages_settings tablosunda veri yok!")
                print("  💡 Varsayılan ayarlar oluşturulacak.")
                return
            
            settings = result['settings']
            created_at = result['created_at']
            updated_at = result['updated_at']
            
            print(f"  📅 Oluşturulma: {created_at}")
            print(f"  📅 Son Güncelleme: {updated_at}")
            
            # JSON parse et
            if isinstance(settings, str):
                settings = json.loads(settings)
            
            # 3. Aktif botları listele
            print("\n" + "="*80)
            print("🤖 AKTİF BOTLAR")
            print("="*80)
            active_bots = settings.get('active_bots', {})
            if active_bots:
                for bot_id, is_active in active_bots.items():
                    status = "✅ Aktif" if is_active else "❌ Pasif"
                    print(f"  • Bot ID: {bot_id} - {status}")
            else:
                print("  ⚠️ Aktif bot yok")
            
            # 4. Bot profillerini listele
            print("\n" + "="*80)
            print("👤 BOT PROFİLLERİ")
            print("="*80)
            bot_profiles = settings.get('bot_profiles', {})
            if bot_profiles:
                for bot_id, profile in bot_profiles.items():
                    print(f"\n  🤖 Bot ID: {bot_id}")
                    print(f"     Mesaj: {profile.get('message', 'N/A')[:50]}...")
                    print(f"     Link: {profile.get('link', 'N/A')}")
                    print(f"     Link Text: {profile.get('link_text', 'N/A')}")
                    print(f"     Image: {profile.get('image', 'N/A')}")
                    print(f"     Interval: {profile.get('interval', 'N/A')} dakika")
                    groups = profile.get('groups', [])
                    print(f"     Gruplar: {len(groups)} grup")
                    if groups:
                        print(f"     Grup ID'leri: {groups[:5]}{'...' if len(groups) > 5 else ''}")
            else:
                print("  ⚠️ Bot profili yok")
            
            # 5. Otomatik komutları listele
            print("\n" + "="*80)
            print("⚙️ OTOMATİK KOMUTLAR")
            print("="*80)
            auto_commands = settings.get('auto_commands', {})
            if auto_commands:
                for cmd_name, cmd_data in auto_commands.items():
                    enabled = "✅ Aktif" if cmd_data.get('is_active', False) else "❌ Pasif"
                    interval = cmd_data.get('interval_minutes', 'N/A')
                    message = cmd_data.get('message_text', 'N/A')[:50]
                    print(f"\n  📢 Komut: {cmd_name}")
                    print(f"     Durum: {enabled}")
                    print(f"     Interval: {interval} dakika")
                    print(f"     Mesaj: {message}...")
            else:
                print("  ⚠️ Otomatik komut yok")
            
            # 6. Grupları listele
            print("\n" + "="*80)
            print("👥 GRUPLAR")
            print("="*80)
            groups = settings.get('groups', [])
            if groups:
                print(f"  📊 Toplam {len(groups)} grup:")
                for i, group_id in enumerate(groups[:10], 1):  # İlk 10'unu göster
                    print(f"     {i}. Group ID: {group_id}")
                if len(groups) > 10:
                    print(f"     ... ve {len(groups) - 10} grup daha")
            else:
                print("  ⚠️ Grup yok")
            
            # 7. Son mesaj zamanlarını listele
            print("\n" + "="*80)
            print("⏰ SON MESAJ ZAMANLARI")
            print("="*80)
            last_message_time = settings.get('last_message_time', {})
            if last_message_time:
                for bot_id, last_time in last_message_time.items():
                    try:
                        if isinstance(last_time, str):
                            dt = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                        else:
                            dt = last_time
                        print(f"  • Bot ID: {bot_id} - Son mesaj: {dt}")
                    except Exception as e:
                        print(f"  • Bot ID: {bot_id} - Son mesaj: {last_time} (parse hatası: {e})")
            else:
                print("  ⚠️ Son mesaj zamanı kaydı yok")
            
            # 8. Otomatik komutların son gönderilme zamanları
            print("\n" + "="*80)
            print("📨 OTOMATİK KOMUTLAR - SON GÖNDERİLME ZAMANLARI")
            print("="*80)
            auto_commands_last_sent = settings.get('auto_commands_last_sent', {})
            if auto_commands_last_sent:
                for cmd_name, last_sent in auto_commands_last_sent.items():
                    try:
                        if isinstance(last_sent, str):
                            dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                        else:
                            dt = last_sent
                        print(f"  • {cmd_name}: {dt}")
                    except Exception as e:
                        print(f"  • {cmd_name}: {last_sent} (parse hatası: {e})")
            else:
                print("  ⚠️ Son gönderilme zamanı kaydı yok")
            
            # 9. Tüm JSON yapısını güzel formatta göster
            print("\n" + "="*80)
            print("📄 TÜM JSON YAPISI (Güzel Format)")
            print("="*80)
            print(json.dumps(settings, indent=2, ensure_ascii=False, default=str))
            
            # 10. Özet istatistikler
            print("\n" + "="*80)
            print("📊 ÖZET İSTATİSTİKLER")
            print("="*80)
            print(f"  • Aktif Bot Sayısı: {sum(1 for v in active_bots.values() if v)}")
            print(f"  • Toplam Bot Sayısı: {len(active_bots)}")
            print(f"  • Bot Profil Sayısı: {len(bot_profiles)}")
            print(f"  • Otomatik Komut Sayısı: {len(auto_commands)}")
            print(f"  • Aktif Otomatik Komut: {sum(1 for cmd in auto_commands.values() if cmd.get('is_active', False))}")
            print(f"  • Grup Sayısı: {len(groups)}")
            print(f"  • Son Mesaj Kaydı: {len(last_message_time)} bot")
            
            # 11. SQL'den çıkartılan verileri JSON dosyasına kaydet
            print("\n" + "="*80)
            print("💾 SQL VERİLERİ JSON DOSYASINA KAYDEDİLİYOR")
            print("="*80)
            
            output_data = {
                'id': result['id'],
                'created_at': str(created_at),
                'updated_at': str(updated_at),
                'settings': settings
            }
            
            # Workspace dizinine kaydet
            workspace_dir = os.path.dirname(os.path.abspath(__file__))
            output_file = os.path.join(workspace_dir, "scheduled_messages_sql_backup.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"✅ SQL verileri '{os.path.basename(output_file)}' dosyasına kaydedildi!")
            print(f"📁 Dosya yolu: {output_file}")
            
        finally:
            await pool.release(conn)
            print("\n✅ Analiz tamamlandı!")
            
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Zamanlanmış Mesajlar Analiz Script'i Başlatılıyor...\n")
    try:
        asyncio.run(analyze_scheduled_messages())
    except KeyboardInterrupt:
        print("\n⏹️ Script kullanıcı tarafından durduruldu!")
    except Exception as e:
        print(f"\n❌ Script hatası: {e}")
        import traceback
        traceback.print_exc()

