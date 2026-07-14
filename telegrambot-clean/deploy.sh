#!/bin/bash

echo "🚀 KirveHub Bot - DigitalOcean Deployment"
echo "========================================="

# Renkli çıktı için
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Git durumunu kontrol et
echo -e "${YELLOW}📋 Git durumu kontrol ediliyor...${NC}"
if [[ -n $(git status --porcelain) ]]; then
    echo -e "${YELLOW}⚠️  Değişiklikler tespit edildi${NC}"
    read -p "Değişiklikleri commit etmek istiyor musun? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add .
        read -p "Commit mesajı: " commit_msg
        git commit -m "$commit_msg"
    fi
fi

# Git'e push yap
echo -e "${YELLOW}📤 GitHub'a push yapılıyor...${NC}"
git push origin main

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Push başarılı!${NC}"
else
    echo -e "${RED}❌ Push başarısız!${NC}"
    exit 1
fi

# DigitalOcean IP adresini al
echo -e "${BLUE}🌐 DigitalOcean sunucusu bilgileri:${NC}"
read -p "Droplet IP adresi: " DROPLET_IP
read -p "Kullanıcı adı (varsayılan: kirvehub): " USERNAME
USERNAME=${USERNAME:-kirvehub}

echo -e "${YELLOW}🔗 $USERNAME@$DROPLET_IP adresine bağlanılıyor...${NC}"

# SSH ile sunucuya bağlan ve güncelle
ssh $USERNAME@$DROPLET_IP << EOF
echo "🔄 Bot güncelleniyor..."
cd /home/$USERNAME/telegrambot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart kirvehub-bot
echo "✅ Bot başarıyla güncellendi!"
sudo systemctl status kirvehub-bot
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}🎉 Deployment tamamlandı!${NC}"
    echo -e "${GREEN}🤖 Bot yeniden başlatıldı ve çalışıyor.${NC}"
    echo -e "${BLUE}📊 Log kontrolü: ssh $USERNAME@$DROPLET_IP 'sudo journalctl -u kirvehub-bot -f'${NC}"
else
    echo -e "${RED}❌ Deployment başarısız!${NC}"
    echo -e "${YELLOW}💡 Manuel kontrol için: ssh $USERNAME@$DROPLET_IP${NC}"
    exit 1
fi 