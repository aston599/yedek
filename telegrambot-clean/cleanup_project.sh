#!/bin/bash

# 🧹 Temiz Kurulum İçin Gereksiz Dosyaları Temizle
# DİKKAT: Bu script gereksiz dosyaları SİLER!

echo "🧹 Temiz kurulum için gereksiz dosyalar temizleniyor..."

# Gereksiz MD dosyalarını sil
echo "📄 Gereksiz MD dosyaları siliniyor..."
rm -f PROJE_ANALIZ_RAPORU.md
rm -f SON_GUNCELLEMELER.md
rm -f LOG_ANALIZ_RAPORU.md
rm -f DATABASE_ANALIZ_RAPORU.md
rm -f DATABASE_DURUM_RAPORU.md
rm -f DATABASE_TEST_SONUCLARI.md
rm -f MARKET_URUNLERI_LISTESI.md
rm -f TUM_URUNLER_LISTESI.md
rm -f logsnew.md
rm -f UBUNTU_*.md
rm -f CLEAN_SETUP_PLAN.md

# Docs klasöründeki analiz dosyalarını sil
echo "📚 Docs klasörü temizleniyor..."
rm -rf docs/

# Test ve geçici Python dosyalarını sil
echo "🐍 Test ve geçici Python dosyaları siliniyor..."
rm -f test_*.py
rm -f check_*.py
rm -f fix_*.py
rm -f add_*.py
rm -f remove_*.py
rm -f update_*.py
rm -f analyze_*.py
rm -f run_*.py
rm -f execute_*.py
rm -f quick_*.py
rm -f final_*.py
rm -f show_*.py
rm -f list_*.py
rm -f realistic_*.py
rm -f market_strategy.py
rm -f fix_main.py

# Gereksiz shell scriptlerini sil
echo "📜 Gereksiz shell scriptleri siliniyor..."
rm -f fix_all_ubuntu_commands.sh
rm -f fix-systemd-service.sh
rm -f fix-ubuntu-main.sh
rm -f ubuntu-fix-setup.sh
rm -f ubuntu-diagnose.sh
rm -f .git-push.sh

# Backup dosyalarını sil
echo "💾 Backup dosyaları siliniyor..."
rm -f main.py.backup*
rm -f *.backup
rm -f *.bak

# Log dosyalarını temizle (klasörü koru)
echo "📋 Log dosyaları temizleniyor..."
rm -f bot.log
rm -f bot_running.lock
rm -f sipariskabullog.txt
rm -f *.log

# Gereksiz SQL dosyalarını sil (sadece init.sql kalacak)
echo "🗄️ Gereksiz SQL dosyaları siliniyor..."
cd database/
rm -f add_*.sql
rm -f check_*.sql
rm -f cleanup_*.sql
rm -f create_*.sql
rm -f enable_*.sql
rm -f fix_*.sql
rm -f remove_*.sql
rm -f show_*.sql
rm -f update_*.sql
rm -rf market_setup/
rm -f check_rls_status.py
cd ..

# Exports klasörünü temizle (içeriği sil, klasörü koru)
echo "📦 Exports klasörü temizleniyor..."
rm -rf exports/*
touch exports/.gitkeep

# Logs klasörünü temizle (içeriği sil, klasörü koru)
echo "📋 Logs klasörü temizleniyor..."
rm -rf logs/*
touch logs/.gitkeep

echo "✅ Temizlik tamamlandı!"
echo ""
echo "📝 Sonraki adımlar:"
echo "1. .gitignore.clean dosyasını .gitignore olarak kopyala: cp .gitignore.clean .gitignore"
echo "2. README.clean.md dosyasını README.md olarak kopyala: cp README.clean.md README.md"
echo "3. Git durumunu kontrol et: git status"
echo "4. Değişiklikleri commit et: git add . && git commit -m 'Clean project structure'"


