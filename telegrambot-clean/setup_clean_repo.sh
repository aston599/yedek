#!/bin/bash

# 🚀 Yeni Temiz Repository Kurulum Scripti

echo "🚀 Temiz repository kurulumu başlatılıyor..."

# 1. Yeni klasör oluştur
REPO_NAME="telegrambot-clean"
echo "📁 Yeni klasör oluşturuluyor: $REPO_NAME"
mkdir -p ../$REPO_NAME
cd ../$REPO_NAME

# 2. Git init
echo "🔧 Git repository başlatılıyor..."
git init
git branch -M main

# 3. Gerekli dosyaları kopyala
echo "📋 Gerekli dosyalar kopyalanıyor..."

# Ana dosyalar
cp ../telegrambot-main/main.py .
cp ../telegrambot-main/config.py .
cp ../telegrambot-main/database.py .
cp ../telegrambot-main/requirements.txt .
cp ../telegrambot-main/env.example .

# Docker dosyaları
cp ../telegrambot-main/Dockerfile .
cp ../telegrambot-main/docker-compose.yml .
cp ../telegrambot-main/deploy.sh .

# Handlers klasörü
echo "📂 Handlers klasörü kopyalanıyor..."
cp -r ../telegrambot-main/handlers .

# Utils klasörü
echo "🔧 Utils klasörü kopyalanıyor..."
cp -r ../telegrambot-main/utils .

# Database klasörü (sadece init.sql)
echo "🗄️ Database klasörü hazırlanıyor..."
mkdir -p database
cp ../telegrambot-main/database/init.sql database/

# Assets klasörü
echo "🎨 Assets klasörü kopyalanıyor..."
cp -r ../telegrambot-main/assets .

# Systemd klasörü
echo "⚙️ Systemd klasörü kopyalanıyor..."
mkdir -p systemd
cp ../telegrambot-main/systemd/kirvehub-bot.service systemd/

# Temiz .gitignore
echo "📝 .gitignore oluşturuluyor..."
cp ../telegrambot-main/.gitignore.clean .gitignore

# Temiz README
echo "📖 README oluşturuluyor..."
cp ../telegrambot-main/README.clean.md README.md

# Logs ve exports klasörleri (boş)
echo "📁 Logs ve exports klasörleri oluşturuluyor..."
mkdir -p logs
mkdir -p exports
touch logs/.gitkeep
touch exports/.gitkeep

# 4. .env dosyası oluştur (example'dan)
echo "⚙️ .env.example kopyalandı (manuel düzenleme gerekli)"

# 5. İlk commit
echo "💾 İlk commit yapılıyor..."
git add .
git commit -m "Initial commit: Clean bot setup"

echo ""
echo "✅ Temiz repository hazır!"
echo ""
echo "📝 Sonraki adımlar:"
echo "1. GitHub'da yeni repository oluştur"
echo "2. Remote ekle: git remote add origin <YENİ_REPO_URL>"
echo "3. Push yap: git push -u origin main"
echo "4. .env dosyasını düzenle ve bot token'ı ekle"
echo "5. Database'i kur: psql -U postgres -d your_db < database/init.sql"
echo "6. Botu başlat: python main.py"


