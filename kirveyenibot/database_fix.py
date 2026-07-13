#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Düzeltme Scripti
Eksik kolonları ekler ve database'i düzeltir
"""

import sqlite3
from config import DATABASE_PATH
from database import init_db

def fix_database():
    """Database'i düzelt - eksik kolonları ekle"""
    print("=" * 60)
    print("🔧 DATABASE DÜZELTME")
    print("=" * 60)
    print()
    
    # Önce init_db() çalıştır
    print("1️⃣ init_db() çalıştırılıyor...")
    try:
        init_db()
        print("✅ init_db() tamamlandı!")
    except Exception as e:
        print(f"⚠️ init_db() hatası: {e}")
    
    print()
    print("2️⃣ Kolonları kontrol ediliyor...")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Mevcut kolonları kontrol et
    cursor.execute("PRAGMA table_info(applications)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print(f"📊 Mevcut kolonlar ({len(columns)}): {columns}")
    print()
    
    # Gerekli kolonlar
    gerekli_kolonlar = {
        'merso_username': 'TEXT',
        'merso_screenshot': 'TEXT',
        'amg_username': 'TEXT',
        'amg_screenshot': 'TEXT',
        'betpuan_username': 'TEXT',
        'betpuan_screenshot': 'TEXT',
        'bot_source': 'TEXT',
        'red_reason': 'TEXT'
    }
    
    eklenen = []
    for kolon, tip in gerekli_kolonlar.items():
        if kolon not in columns:
            try:
                if kolon == 'bot_source':
                    cursor.execute(f'ALTER TABLE applications ADD COLUMN {kolon} {tip} DEFAULT "main"')
                else:
                    cursor.execute(f'ALTER TABLE applications ADD COLUMN {kolon} {tip}')
                eklenen.append(kolon)
                print(f"✅ {kolon} eklendi")
            except Exception as e:
                print(f"❌ {kolon} eklenemedi: {e}")
        else:
            print(f"ℹ️  {kolon} zaten mevcut")
    
    conn.commit()
    
    # Tekrar kontrol et
    cursor.execute("PRAGMA table_info(applications)")
    columns_after = [col[1] for col in cursor.fetchall()]
    
    print()
    print("📊 Güncel kolonlar:")
    for col in columns_after:
        print(f"  - {col}")
    
    conn.close()
    
    print()
    if eklenen:
        print(f"✅ {len(eklenen)} kolon eklendi: {eklenen}")
    else:
        print("✅ Tüm kolonlar mevcut!")
    
    print()
    print("=" * 60)
    print("✅ DATABASE DÜZELTME TAMAMLANDI!")
    print("=" * 60)

if __name__ == "__main__":
    fix_database()

