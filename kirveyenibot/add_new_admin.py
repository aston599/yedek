#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yeni admin eklemek için yardımcı script
Çalıştırma: python3 add_new_admin.py
"""

import sqlite3
from datetime import datetime

DATABASE_PATH = "bot_database.db"

def add_admin(user_id, username):
    """Veritabanına yeni admin ekle"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Admin zaten var mı kontrol et
        cursor.execute('SELECT * FROM admins WHERE user_id = ?', (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"⚠️  Admin zaten mevcut: {username} (ID: {user_id})")
            return False
        
        # Yeni admin ekle
        cursor.execute('''
            INSERT INTO admins (user_id, username, added_by)
            VALUES (?, ?, ?)
        ''', (user_id, username, user_id))  # Kendisi tarafından eklendi
        
        conn.commit()
        print(f"✅ Yeni admin başarıyla eklendi!")
        print(f"   👤 Kullanıcı: {username}")
        print(f"   🆔 ID: {user_id}")
        print(f"   📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False
    finally:
        conn.close()

def list_all_admins():
    """Tüm adminleri listele"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT user_id, username, added_date 
            FROM admins 
            ORDER BY added_date ASC
        ''')
        
        admins = cursor.fetchall()
        
        if not admins:
            print("\n📋 Veritabanında kayıtlı admin yok.")
            return
        
        print("\n📋 KAYITLI ADMİNLER:")
        print("━" * 60)
        for admin in admins:
            user_id, username, added_date = admin
            print(f"🆔 ID: {user_id}")
            print(f"👤 Kullanıcı: {username or 'N/A'}")
            print(f"📅 Eklenme Tarihi: {added_date}")
            print("─" * 60)
        
        print(f"\n📊 Toplam Admin Sayısı: {len(admins)}")
        print("\n💡 NOT: Ana admin (config.py'deki ADMIN_USER_ID) burada görünmez.")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 KirveBot - Admin Yönetimi")
    print("=" * 60)
    
    # Yeni admin bilgileri
    NEW_ADMIN_ID = 8521478746
    NEW_ADMIN_USERNAME = "@mikedahjenkoy"
    
    print(f"\n🆕 Yeni Admin Eklenecek:")
    print(f"   👤 Ad: Mike")
    print(f"   📝 Username: {NEW_ADMIN_USERNAME}")
    print(f"   🆔 ID: {NEW_ADMIN_ID}")
    print()
    
    # Admin ekle
    add_admin(NEW_ADMIN_ID, NEW_ADMIN_USERNAME)
    
    # Tüm adminleri listele
    list_all_admins()
    
    print("\n" + "=" * 60)
    print("✅ İşlem tamamlandı!")
    print("=" * 60)

