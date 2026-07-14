#!/bin/bash

echo "🔧 Ubuntu Bot Kurulum Düzeltme Scripti"
echo "========================================"
echo ""

# Renkli çıktılar için
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CURRENT_DIR=$(pwd)
echo "📁 Çalışma dizini: $CURRENT_DIR"
echo ""

# 1. .env dosyası oluştur
if [ ! -f ".env" ]; then
    echo "📝 .env dosyası oluşturuluyor..."
    if [ -f "env.example" ]; then
        cp env.example .env
        echo -e "${GREEN}✅ .env dosyası env.example'dan oluşturuldu${NC}"
        echo -e "${YELLOW}⚠️ Lütfen .env dosyasını düzenleyin ve BOT_TOKEN'i kontrol edin:${NC}"
        echo "   nano .env"
    else
        echo -e "${RED}❌ env.example bulunamadı!${NC}"
    fi
else
    echo -e "${GREEN}✅ .env dosyası zaten mevcut${NC}"
fi
echo ""

# 2. Virtual environment oluştur
if [ ! -d "venv" ]; then
    echo "📦 Virtual environment oluşturuluyor..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ venv oluşturuldu${NC}"
    else
        echo -e "${RED}❌ venv oluşturulamadı! python3-venv paketini yükleyin:${NC}"
        echo "   sudo apt update && sudo apt install python3-venv -y"
        exit 1
    fi
else
    echo -e "${GREEN}✅ venv zaten mevcut${NC}"
fi
echo ""

# 3. Virtual environment'ı aktif et
echo "🔄 Virtual environment aktif ediliyor..."
source venv/bin/activate
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ venv aktif edildi${NC}"
else
    echo -e "${RED}❌ venv aktif edilemedi!${NC}"
    exit 1
fi
echo ""

# 4. pip güncelle
echo "📦 pip güncelleniyor..."
pip install --upgrade pip
echo ""

# 5. Gerekli paketleri yükle
echo "📚 Gerekli paketler yükleniyor..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Paketler yüklendi${NC}"
    else
        echo -e "${RED}❌ Paket yükleme hatası!${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ requirements.txt bulunamadı!${NC}"
    exit 1
fi
echo ""

# 6. Systemd servis dosyasını güncelle (root için)
if [ "$EUID" -eq 0 ]; then
    echo "⚙️ Systemd servis dosyası güncelleniyor (root için)..."
    if [ -f "systemd/kirvehub-bot.service" ]; then
        # Root kullanıcısı için service dosyasını düzenle
        sed -i "s|User=kirvehub|User=root|g" systemd/kirvehub-bot.service
        sed -i "s|Group=kirvehub|Group=root|g" systemd/kirvehub-bot.service
        sed -i "s|/home/kirvehub/telegrambot|$CURRENT_DIR|g" systemd/kirvehub-bot.service
        
        echo -e "${GREEN}✅ Servis dosyası güncellendi${NC}"
        echo -e "${YELLOW}⚠️ Servisi yüklemek için:${NC}"
        echo "   sudo cp systemd/kirvehub-bot.service /etc/systemd/system/"
        echo "   sudo systemctl daemon-reload"
        echo "   sudo systemctl enable kirvehub-bot"
        echo "   sudo systemctl start kirvehub-bot"
    fi
else
    echo -e "${YELLOW}⚠️ Root değilsiniz - systemd servis dosyası güncellenmedi${NC}"
fi
echo ""

# 7. Test çalıştırma
echo "🧪 Bot test ediliyor..."
echo -e "${YELLOW}⚠️ 5 saniye içinde bot çalışacak, test edebilirsiniz...${NC}"
echo "   Çıkmak için Ctrl+C basın"
echo ""
sleep 2

# Python syntax kontrolü
python3 -m py_compile main.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ main.py syntax hatası yok${NC}"
else
    echo -e "${RED}❌ main.py'de syntax hatası var!${NC}"
    exit 1
fi

echo ""
echo "========================================"
echo -e "${GREEN}✅ Kurulum tamamlandı!${NC}"
echo ""
echo "🚀 Botu çalıştırmak için:"
echo "   source venv/bin/activate"
echo "   python3 main.py"
echo ""
echo "📋 Veya systemd servisi ile:"
echo "   sudo systemctl start kirvehub-bot"
echo "   sudo systemctl status kirvehub-bot"





