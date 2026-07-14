# 🚀 Temiz Kurulum - Devam Adımları

## ✅ Şu Ana Kadar Yapılanlar

- ✅ Yeni klasör oluşturuldu: `/home/kirvehub/telegrambot-clean`
- ✅ Git repository başlatıldı
- ✅ Dosyalar kopyalandı (assets yok, sorun değil)
- ✅ Python venv oluşturuldu
- ✅ Bağımlılıklar kuruldu

## 📝 Şimdi Yapılacaklar

### 1. Git Branch'i Düzelt

```bash
cd /home/kirvehub/telegrambot-clean
git branch -m main
```

### 2. Assets Klasörünü Oluştur (Opsiyonel)

```bash
mkdir -p assets/avatars assets/membership_levels assets/point_notifications assets/vip_images
touch assets/.gitkeep
```

### 3. .env Dosyasını Düzenle

```bash
cd /home/kirvehub/telegrambot-clean
nano .env
```

**İçeriği düzenle:**
- `BOT_TOKEN`: Mevcut bot token'ı veya yeni bir bot token'ı
- `ADMIN_USER_ID`: Admin ID
- `DATABASE_URL`: Database connection string
- Diğer ayarlar

### 4. Systemd Service Dosyasını Hazırla

```bash
cd /home/kirvehub/telegrambot-clean

# Systemd service dosyasını düzenle
nano systemd/kirvehub-bot.service
```

**İçeriği şöyle olmalı:**
```ini
[Unit]
Description=KirveHub Telegram Bot (Clean)
Documentation=https://github.com/YOUR_USERNAME/YOUR_NEW_REPO
After=network.target

[Service]
Type=simple
User=kirvehub
Group=kirvehub
WorkingDirectory=/home/kirvehub/telegrambot-clean
Environment=PATH=/home/kirvehub/telegrambot-clean/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/home/kirvehub/telegrambot-clean
ExecStart=/usr/bin/python3 /home/kirvehub/telegrambot-clean/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
ReadWritePaths=/home/kirvehub/telegrambot-clean/logs /home/kirvehub/telegrambot-clean/data /home/kirvehub/telegrambot-clean

[Install]
WantedBy=multi-user.target
```

### 5. Systemd Service'i Kur

```bash
# Service dosyasını kopyala
sudo cp /home/kirvehub/telegrambot-clean/systemd/kirvehub-bot.service /etc/systemd/system/kirvehub-bot-clean.service

# Systemd'yi yenile
sudo systemctl daemon-reload

# Service'i aktif et
sudo systemctl enable kirvehub-bot-clean

# Service'i başlat
sudo systemctl start kirvehub-bot-clean

# Durumu kontrol et
sudo systemctl status kirvehub-bot-clean
```

### 6. Logları Kontrol Et

```bash
# Systemd logları
sudo journalctl -u kirvehub-bot-clean -f

# Bot logları (eğer oluşturulduysa)
tail -f /home/kirvehub/telegrambot-clean/logs/bot.log
```

### 7. GitHub'a Push (İsteğe Bağlı)

```bash
cd /home/kirvehub/telegrambot-clean

# .gitignore oluştur
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
venv/
env/
.venv

# Environment
.env

# Logs
*.log
logs/
bot_running.lock

# IDE
.vscode/
.idea/

# OS
.DS_Store

# Backup
*.backup
*.bak
*.tmp

# Exports
exports/
*.zip
EOF

# README oluştur
cat > README.md << 'EOF'
# 🤖 KirveHub Telegram Bot (Clean)

Temiz kurulum - Production ready Telegram bot.

## 🚀 Kurulum

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
nano .env
```
EOF

# Git commit
git add .
git commit -m "Initial commit: Clean bot setup"

# GitHub'da yeni repo oluştur, sonra:
# git remote add origin <YENİ_REPO_URL>
# git push -u origin main
```

## ⚠️ Önemli Notlar

1. **İki Bot Aynı Anda Çalışabilir:**
   - Eski bot: `kirvehub-bot` service
   - Yeni bot: `kirvehub-bot-clean` service
   - Farklı bot token'ları kullanmalılar!

2. **Database:**
   - Aynı database'i kullanabilirler
   - Veya ayrı database kullanabilirsin

3. **Test:**
   - Önce yeni botu test et
   - Çalışıyorsa eski botu durdur
   - Veya ikisini de farklı gruplarda kullan

## 🔍 Hata Kontrolü

Eğer bot başlamazsa:

```bash
# Detaylı loglar
sudo journalctl -u kirvehub-bot-clean -n 100 --no-pager

# Manuel test
cd /home/kirvehub/telegrambot-clean
source venv/bin/activate
python main.py
```


