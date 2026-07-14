# 🤖 KirveHub Telegram Bot

Modern, production-ready Telegram bot built with Python 3.12+ and aiogram 3.x.

## ✨ Özellikler

- 🎯 **Modern Framework**: aiogram 3.4.1
- 🗄️ **PostgreSQL Database**: asyncpg ile async database işlemleri
- 🐳 **Docker Support**: Docker Compose ile kolay deployment
- 🔄 **Systemd Integration**: Otomatik restart ve service management
- 📊 **Comprehensive Features**: Market, events, points, levels, admin panel
- 🔒 **Security**: Rate limiting, spam protection, permission management

## 📋 Gereksinimler

- **Python**: 3.12+
- **PostgreSQL**: 14+ (veya Supabase)
- **OS**: Ubuntu 24.04 LTS (önerilen) veya Windows/Linux/Mac

## 🚀 Hızlı Başlangıç

### 1. Repository'yi Klonla

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd telegrambot
```

### 2. Python Environment Kur

```bash
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Konfigürasyon

```bash
cp env.example .env
nano .env  # veya editörünüzle düzenleyin
```

`.env` dosyasını düzenleyin:
- `BOT_TOKEN`: Telegram Bot Token (@BotFather'dan alın)
- `ADMIN_USER_ID`: Admin kullanıcı ID'si
- `DATABASE_URL`: PostgreSQL connection string

### 4. Database Kurulumu

```bash
# PostgreSQL'e bağlan ve init.sql'i çalıştır
psql -U postgres -d your_database < database/init.sql
```

### 5. Botu Başlat

```bash
python main.py
```

## 🐳 Docker ile Kurulum

```bash
# .env dosyasını oluşturun
cp env.example .env
nano .env

# Docker Compose ile başlat
docker-compose up -d

# Logları izle
docker-compose logs -f kirvehub-bot
```

## 🔧 Systemd Service (Ubuntu Production)

### 1. Service Dosyasını Kopyala

```bash
sudo cp systemd/kirvehub-bot.service /etc/systemd/system/
```

### 2. Service Dosyasını Düzenle

`/etc/systemd/system/kirvehub-bot.service` dosyasındaki yolları kontrol edin:
- `WorkingDirectory`: Bot klasörünün tam yolu
- `User`: Bot'u çalıştıracak kullanıcı
- `ExecStart`: Python ve main.py yolları

### 3. Service'i Aktif Et ve Başlat

```bash
sudo systemctl daemon-reload
sudo systemctl enable kirvehub-bot
sudo systemctl start kirvehub-bot
sudo systemctl status kirvehub-bot
```

### 4. Logları İzle

```bash
sudo journalctl -u kirvehub-bot -f
```

## 📁 Proje Yapısı

```
telegrambot/
├── main.py              # Ana bot dosyası
├── config.py            # Konfigürasyon yönetimi
├── database.py          # Database işlemleri
├── requirements.txt     # Python bağımlılıkları
├── .env                 # Environment variables (oluşturulacak)
├── env.example          # Environment örneği
│
├── handlers/            # Bot handler'ları
│   ├── admin_panel.py
│   ├── market_system.py
│   ├── event_management.py
│   └── ...
│
├── utils/               # Utility fonksiyonları
│   ├── logger.py
│   ├── rate_limiter.py
│   └── ...
│
├── database/            # Database scriptleri
│   └── init.sql         # İlk kurulum SQL
│
├── assets/              # Asset dosyaları
│   ├── avatars/
│   ├── membership_levels/
│   └── ...
│
├── systemd/             # Systemd service dosyası
│   └── kirvehub-bot.service
│
└── logs/                # Log dosyaları (otomatik oluşturulur)
```

## 🔑 Önemli Komutlar

### Bot Yönetimi
- `/start` - Botu başlat
- `/help` - Yardım menüsü
- `/profile` - Kullanıcı profili

### Admin Komutları
- `/admin` - Admin paneli
- `/broadcast` - Mesaj yayınla
- `/stats` - İstatistikler

## 🛠️ Geliştirme

### Yeni Handler Ekleme

1. `handlers/` klasörüne yeni dosya ekle
2. `main.py`'de handler'ı import et ve kaydet

### Database Migration

1. `database/init.sql` dosyasını güncelle
2. Veya yeni migration dosyası oluştur

## 📝 Lisans

Bu proje özel kullanım içindir.

## 🤝 Destek

Sorunlar için GitHub Issues kullanın.


