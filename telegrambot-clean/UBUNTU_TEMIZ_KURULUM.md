# 🚀 DigitalOcean Ubuntu - Temiz Bot Kurulumu

## 📋 Adım Adım Kurulum

### 1. Yeni Klasör Oluştur ve GitHub'dan Klonla

```bash
# Yeni klasör oluştur
cd /home/kirvehub
mkdir telegrambot-clean
cd telegrambot-clean

# GitHub'da yeni repository oluşturduktan sonra klonla
# (GitHub'da yeni repo oluştur, sonra URL'yi buraya yaz)
git clone https://github.com/YOUR_USERNAME/YOUR_NEW_REPO.git .

# VEYA boş klasörde git init yap
git init
git branch -M main
```

### 2. Gerekli Dosyaları Kopyala (Mevcut Bot'tan)

```bash
# Ana dosyalar
cp ../telegrambot/main.py .
cp ../telegrambot/config.py .
cp ../telegrambot/database.py .
cp ../telegrambot/requirements.txt .
cp ../telegrambot/env.example .

# Docker dosyaları
cp ../telegrambot/Dockerfile .
cp ../telegrambot/docker-compose.yml .
cp ../telegrambot/deploy.sh .

# Handlers klasörü
cp -r ../telegrambot/handlers .

# Utils klasörü
cp -r ../telegrambot/utils .

# Database klasörü (sadece init.sql)
mkdir -p database
cp ../telegrambot/database/init.sql database/

# Assets klasörü
cp -r ../telegrambot/assets .

# Systemd klasörü
mkdir -p systemd
cp ../telegrambot/systemd/kirvehub-bot.service systemd/

# Logs ve exports klasörleri
mkdir -p logs
mkdir -p exports
```

### 3. Temiz .gitignore ve README Oluştur

```bash
# .gitignore oluştur
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

# README oluştur (basit versiyon)
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

# Database
psql -U postgres -d your_db < database/init.sql

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
```

### 4. Python Environment Kur

```bash
cd /home/kirvehub/telegrambot-clean

# Python venv oluştur
python3.12 -m venv venv
source venv/bin/activate

# Bağımlılıkları kur
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Konfigürasyon

```bash
# .env dosyasını oluştur
cp env.example .env
nano .env

# Mevcut bot'tan config.py'yi kopyaladıysan, .env'de sadece değişmesi gerekenleri düzenle
```

### 6. Systemd Service Dosyasını Düzenle

```bash
# Systemd service dosyasını kopyala ve düzenle
sudo cp systemd/kirvehub-bot.service /etc/systemd/system/kirvehub-bot-clean.service

# Düzenle
sudo nano /etc/systemd/system/kirvehub-bot-clean.service
```

**Systemd dosyasında değiştirilecekler:**
```ini
[Unit]
Description=KirveHub Telegram Bot (Clean)
Documentation=https://github.com/YOUR_USERNAME/YOUR_NEW_REPO

[Service]
User=kirvehub
Group=kirvehub
WorkingDirectory=/home/kirvehub/telegrambot-clean
Environment=PATH=/home/kirvehub/telegrambot-clean/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/home/kirvehub/telegrambot-clean
ExecStart=/usr/bin/python3 /home/kirvehub/telegrambot-clean/main.py
ReadWritePaths=/home/kirvehub/telegrambot-clean/logs /home/kirvehub/telegrambot-clean/data /home/kirvehub/telegrambot-clean
```

### 7. İzinleri Ayarla

```bash
cd /home/kirvehub
chown -R kirvehub:kirvehub telegrambot-clean
chmod +x telegrambot-clean/main.py
chmod 755 telegrambot-clean/logs
```

### 8. Systemd Service'i Aktif Et

```bash
sudo systemctl daemon-reload
sudo systemctl enable kirvehub-bot-clean
sudo systemctl start kirvehub-bot-clean
sudo systemctl status kirvehub-bot-clean
```

### 9. Logları Kontrol Et

```bash
# Systemd logları
sudo journalctl -u kirvehub-bot-clean -f

# Bot logları
tail -f /home/kirvehub/telegrambot-clean/logs/bot.log
```

## 🔄 Tek Komutla Kurulum (Hızlı)

```bash
cd /home/kirvehub && \
mkdir -p telegrambot-clean && \
cd telegrambot-clean && \
git init && \
git branch -M main && \
cp ../telegrambot/main.py . && \
cp ../telegrambot/config.py . && \
cp ../telegrambot/database.py . && \
cp ../telegrambot/requirements.txt . && \
cp ../telegrambot/env.example . && \
cp ../telegrambot/Dockerfile . && \
cp ../telegrambot/docker-compose.yml . && \
cp -r ../telegrambot/handlers . && \
cp -r ../telegrambot/utils . && \
mkdir -p database && \
cp ../telegrambot/database/init.sql database/ && \
cp -r ../telegrambot/assets . && \
mkdir -p systemd && \
cp ../telegrambot/systemd/kirvehub-bot.service systemd/ && \
mkdir -p logs exports && \
python3.12 -m venv venv && \
source venv/bin/activate && \
pip install --upgrade pip && \
pip install -r requirements.txt && \
cp env.example .env && \
chown -R kirvehub:kirvehub /home/kirvehub/telegrambot-clean && \
echo "✅ Temiz kurulum hazır! Şimdi .env dosyasını düzenle ve systemd service'i kur."
```

## 📝 Sonraki Adımlar

1. ✅ `.env` dosyasını düzenle (bot token, database URL, vb.)
2. ✅ Systemd service dosyasını düzenle ve kur
3. ✅ GitHub'da yeni repository oluştur
4. ✅ İlk commit ve push yap
5. ✅ Botu test et

## ⚠️ Önemli Notlar

- Mevcut bot (`telegrambot`) çalışmaya devam edecek
- Yeni bot (`telegrambot-clean`) ayrı bir systemd service olarak çalışacak
- İki bot aynı anda çalışabilir (farklı bot token'ları kullanmalı)
- Database'i paylaşabilirler veya ayrı database kullanabilirsin


