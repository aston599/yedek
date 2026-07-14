# 🤖 KirveHub Telegram Bot

**DigitalOcean Ubuntu Production Environment** için optimize edilmiş, Python 3.12+ uyumlu modern Telegram bot.

## 🚀 Özellikler

- ✅ **Python 3.12+ Uyumlu**: Ubuntu 24.04 LTS ile tam uyumlu
- ✅ **Production Ready**: Python + Systemd + Nginx
- ✅ **Docker Support**: Docker Compose ile kolay deployment
- ✅ **Database Integration**: PostgreSQL + asyncpg
- ✅ **Security**: Rate limiting, firewall, SSL support
- ✅ **Monitoring**: Structured logging, health checks
- ✅ **Auto-restart**: Systemd service management
- ✅ **Backup**: Log rotation, database backup

## 📋 Sistem Gereksinimleri

### Minimum Gereksinimler
- **OS**: Ubuntu 24.04 LTS
- **Python**: 3.12+
- **RAM**: 1GB
- **Storage**: 10GB
- **CPU**: 1 vCPU

### Önerilen Gereksinimler
- **OS**: Ubuntu 24.04 LTS
- **Python**: 3.12+
- **RAM**: 2GB+
- **Storage**: 20GB+
- **CPU**: 2 vCPU+

## 🛠️ Kurulum

### 1. Hızlı Kurulum (Otomatik)

```bash
# Repository'yi klonla
git clone https://github.com/aston599/telegrambot.git
cd telegrambot

# Deployment script'ini çalıştır
chmod +x deploy.sh
./deploy.sh
```

### 2. Manuel Kurulum

#### Sistem Paketlerini Kur
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip postgresql-client nginx curl git build-essential libssl-dev libffi-dev libpq-dev
```

#### Bot Kullanıcısı Oluştur
```bash
sudo useradd -m -s /bin/bash kirvehub
sudo usermod -aG sudo kirvehub
```

#### Repository'yi Klonla
```bash
sudo mkdir -p /home/kirvehub/telegrambot
sudo chown kirvehub:kirvehub /home/kirvehub/telegrambot
cd /home/kirvehub/telegrambot
git clone https://github.com/aston599/telegrambot.git .
```

#### Python Environment Kur
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Konfigürasyon
```bash
# .env dosyasını oluştur
cp .env.example .env
nano .env
```

#### Systemd Service Kur
```bash
sudo cp systemd/kirvehub-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable kirvehub-bot
sudo systemctl start kirvehub-bot
```

### 3. Docker ile Kurulum

```bash
# Docker Compose ile başlat
docker-compose up -d

# Logları izle
docker-compose logs -f kirvehub-bot
```

## ⚙️ Konfigürasyon

### Environment Variables (.env)

```bash
# Bot Configuration
BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_admin_id_here
DATABASE_URL=postgresql://username:password@localhost:5432/kirvehub_db

# Environment
PRODUCTION_MODE=true
DEBUG_MODE=false
MAINTENANCE_MODE=false

# Server Settings
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
WORKER_PROCESSES=2

# Database Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# Performance
MAX_CONCURRENT_UPDATES=50
UPDATE_TIMEOUT=30
RATE_LIMIT_DELAY=0.1

# Security
ENABLE_RATE_LIMITING=true
MAX_MESSAGES_PER_MINUTE=60
ENABLE_IP_WHITELIST=false
```

## 🔧 Yönetim Komutları

### Systemd Service
```bash
# Bot'u başlat
sudo systemctl start kirvehub-bot

# Bot'u durdur
sudo systemctl stop kirvehub-bot

# Bot'u yeniden başlat
sudo systemctl restart kirvehub-bot

# Bot durumunu kontrol et
sudo systemctl status kirvehub-bot

# Logları izle
sudo journalctl -u kirvehub-bot -f
```

### Docker
```bash
# Servisleri başlat
docker-compose up -d

# Servisleri durdur
docker-compose down

# Logları izle
docker-compose logs -f

# Servisleri yeniden başlat
docker-compose restart
```

### Manuel Çalıştırma
```bash
# Virtual environment aktifleştir
source venv/bin/activate

# Bot'u çalıştır
python main.py
```

## 📊 Monitoring

### Log Dosyaları
- `logs/bot.log`: Ana bot logları
- `logs/error.log`: Hata logları

### Health Check
```bash
# Bot sağlık durumu
curl http://localhost:8000/health

# Docker health check
docker-compose ps
```

### Performance Monitoring
```bash
# Sistem kaynakları
htop
iotop

# Bot process
ps aux | grep kirvehub-bot

# Memory usage
free -h
```

## 🔒 Güvenlik

### Firewall Ayarları
```bash
# SSH erişimi
sudo ufw allow ssh

# HTTP/HTTPS erişimi
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Firewall'u etkinleştir
sudo ufw --force enable
```

### SSL Sertifikası (Let's Encrypt)
```bash
# Certbot kur
sudo apt install certbot python3-certbot-nginx

# SSL sertifikası al
sudo certbot --nginx -d your-domain.com

# Otomatik yenileme
sudo crontab -e
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🗄️ Database

### PostgreSQL Kurulumu
```bash
# PostgreSQL kur
sudo apt install postgresql postgresql-contrib

# Database oluştur
sudo -u postgres createdb kirvehub_db
sudo -u postgres createuser kirvehub

# Şifre ata
sudo -u postgres psql
ALTER USER kirvehub WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE kirvehub_db TO kirvehub;
\q
```

### Backup
```bash
# Database backup
pg_dump kirvehub_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Otomatik backup (cron)
0 2 * * * pg_dump kirvehub_db > /home/kirvehub/backups/backup_$(date +\%Y\%m\%d_\%H\%M\%S).sql
```

## 🚨 Troubleshooting

### Yaygın Sorunlar

#### Bot Başlamıyor
```bash
# Logları kontrol et
sudo journalctl -u kirvehub-bot -n 50

# Konfigürasyonu kontrol et
python -c "from config import validate_config; validate_config()"
```

#### Database Bağlantı Hatası
```bash
# PostgreSQL durumu
sudo systemctl status postgresql

# Bağlantı testi
psql -h localhost -U kirvehub -d kirvehub_db
```

#### Memory Sorunları
```bash
# Memory kullanımı
free -h

# Process memory
ps aux --sort=-%mem | head -10
```

#### Port Çakışması
```bash
# Port kullanımı
sudo netstat -tulpn | grep :8000

# Process kill
sudo kill -9 <PID>
```

## 📈 Performance Optimization

### Bot Ayarları
```python
# config.py
MAX_CONCURRENT_UPDATES=50
UPDATE_TIMEOUT=30
RATE_LIMIT_DELAY=0.1
DB_POOL_SIZE=10
```

### Database Optimization
```sql
-- Index oluştur
CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_daily_stats_date ON daily_stats(message_date);

-- Vacuum
VACUUM ANALYZE;
```

### System Optimization
```bash
# Swappiness ayarla
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# File descriptor limit
echo '* soft nofile 65536' | sudo tee -a /etc/security/limits.conf
echo '* hard nofile 65536' | sudo tee -a /etc/security/limits.conf
```

## 🤝 Katkıda Bulunma

1. Fork yap
2. Feature branch oluştur (`git checkout -b feature/amazing-feature`)
3. Commit yap (`git commit -m 'Add amazing feature'`)
4. Push yap (`git push origin feature/amazing-feature`)
5. Pull Request oluştur

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakın.

## 📞 Destek

- **Email**: support@kirvehub.com
- **Telegram**: @kirvehub_support
- **Issues**: GitHub Issues

---

**🎉 KirveHub Bot - DigitalOcean Ubuntu Production Ready!** 