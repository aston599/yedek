#!/bin/bash

# 🚀 DigitalOcean Ubuntu - Temiz Bot Kurulum Scripti
# Bu script yeni bir klasör oluşturup temiz bot kurulumu yapar

set -e  # Hata durumunda dur

echo "🚀 Temiz bot kurulumu başlatılıyor..."

# Klasör adı
NEW_DIR="telegrambot-clean"
OLD_DIR="telegrambot"
BASE_DIR="/home/kirvehub"

# 1. Yeni klasör oluştur
echo "📁 Yeni klasör oluşturuluyor: $BASE_DIR/$NEW_DIR"
cd $BASE_DIR
mkdir -p $NEW_DIR
cd $NEW_DIR

# 2. Git init
echo "🔧 Git repository başlatılıyor..."
git init
git branch -M main

# 3. Gerekli dosyaları kopyala
echo "📋 Gerekli dosyalar kopyalanıyor..."

# Ana dosyalar
cp ../$OLD_DIR/main.py .
cp ../$OLD_DIR/config.py .
cp ../$OLD_DIR/database.py .
cp ../$OLD_DIR/requirements.txt .
cp ../$OLD_DIR/env.example .

# Docker dosyaları
if [ -f ../$OLD_DIR/Dockerfile ]; then
    cp ../$OLD_DIR/Dockerfile .
fi
if [ -f ../$OLD_DIR/docker-compose.yml ]; then
    cp ../$OLD_DIR/docker-compose.yml .
fi
if [ -f ../$OLD_DIR/deploy.sh ]; then
    cp ../$OLD_DIR/deploy.sh .
fi

# Handlers klasörü
echo "📂 Handlers klasörü kopyalanıyor..."
cp -r ../$OLD_DIR/handlers .

# Utils klasörü
echo "🔧 Utils klasörü kopyalanıyor..."
cp -r ../$OLD_DIR/utils .

# Database klasörü (sadece init.sql)
echo "🗄️ Database klasörü hazırlanıyor..."
mkdir -p database
if [ -f ../$OLD_DIR/database/init.sql ]; then
    cp ../$OLD_DIR/database/init.sql database/
elif [ -f ../$OLD_DIR/database/init_updated.sql ]; then
    cp ../$OLD_DIR/database/init_updated.sql database/init.sql
fi

# Assets klasörü
echo "🎨 Assets klasörü kopyalanıyor..."
if [ -d ../$OLD_DIR/assets ]; then
    cp -r ../$OLD_DIR/assets .
fi

# Systemd klasörü
echo "⚙️ Systemd klasörü kopyalanıyor..."
mkdir -p systemd
if [ -f ../$OLD_DIR/systemd/kirvehub-bot.service ]; then
    cp ../$OLD_DIR/systemd/kirvehub-bot.service systemd/
fi

# Logs ve exports klasörleri
echo "📁 Logs ve exports klasörleri oluşturuluyor..."
mkdir -p logs
mkdir -p exports
touch logs/.gitkeep
touch exports/.gitkeep

# 4. Temiz .gitignore oluştur
echo "📝 .gitignore oluşturuluyor..."
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv

# Environment
.env
.env.local
.env.*.local

# Logs
*.log
logs/
bot_running.lock

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
desktop.ini

# Backup files
*.backup
*.bak
*.tmp

# Database
*.db
*.sqlite
*.sqlite3

# Test
.pytest_cache/
.coverage
htmlcov/

# Distribution
dist/
build/
*.egg-info/

# Exports
exports/
*.zip

# Lock files
*.lock
poetry.lock

# Temporary files
*.tmp
*.temp
EOF

# 5. Temiz README oluştur
echo "📖 README oluşturuluyor..."
cat > README.md << 'EOF'
# 🤖 KirveHub Telegram Bot

Modern, production-ready Telegram bot built with Python 3.12+ and aiogram 3.x.

## 🚀 Hızlı Kurulum

```bash
# Python environment
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Konfigürasyon
cp env.example .env
nano .env

# Systemd service
sudo cp systemd/kirvehub-bot.service /etc/systemd/system/kirvehub-bot-clean.service
sudo nano /etc/systemd/system/kirvehub-bot-clean.service  # Yolları düzenle
sudo systemctl daemon-reload
sudo systemctl enable kirvehub-bot-clean
sudo systemctl start kirvehub-bot-clean
```

## 📁 Proje Yapısı

```
telegrambot-clean/
├── main.py
├── config.py
├── database.py
├── requirements.txt
├── handlers/
├── utils/
├── database/
│   └── init.sql
├── assets/
└── systemd/
    └── kirvehub-bot.service
```
EOF

# 6. Python environment kur
echo "🐍 Python environment kuruluyor..."
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 7. İzinleri ayarla
echo "🔐 İzinler ayarlanıyor..."
chown -R kirvehub:kirvehub $BASE_DIR/$NEW_DIR
chmod +x $BASE_DIR/$NEW_DIR/main.py
chmod 755 $BASE_DIR/$NEW_DIR/logs

# 8. Systemd service dosyasını hazırla (kullanıcı manuel düzenleyecek)
echo "⚙️ Systemd service dosyası hazırlanıyor..."
if [ -f systemd/kirvehub-bot.service ]; then
    # Service dosyasındaki yolları güncelle
    sed -i "s|/home/kirvehub/telegrambot|/home/kirvehub/$NEW_DIR|g" systemd/kirvehub-bot.service
    sed -i "s|kirvehub-bot|kirvehub-bot-clean|g" systemd/kirvehub-bot.service
    sed -i "s|Description=KirveHub Telegram Bot|Description=KirveHub Telegram Bot (Clean)|g" systemd/kirvehub-bot.service
fi

echo ""
echo "✅ Temiz kurulum tamamlandı!"
echo ""
echo "📝 Sonraki adımlar:"
echo "1. .env dosyasını düzenle: nano $BASE_DIR/$NEW_DIR/.env"
echo "2. Systemd service'i kur:"
echo "   sudo cp $BASE_DIR/$NEW_DIR/systemd/kirvehub-bot.service /etc/systemd/system/kirvehub-bot-clean.service"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable kirvehub-bot-clean"
echo "   sudo systemctl start kirvehub-bot-clean"
echo "3. GitHub'da yeni repository oluştur ve push yap:"
echo "   cd $BASE_DIR/$NEW_DIR"
echo "   git add ."
echo "   git commit -m 'Initial commit: Clean bot setup'"
echo "   git remote add origin <YENİ_REPO_URL>"
echo "   git push -u origin main"
echo ""
echo "📍 Klasör konumu: $BASE_DIR/$NEW_DIR"


