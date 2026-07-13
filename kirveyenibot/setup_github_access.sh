#!/bin/bash

# GitHub Erişim Kurulum Scripti
# Bu script GitHub'a erişim için credential helper kurar

echo "🔐 GitHub Erişim Kurulumu Başlatılıyor..."
echo ""

# Proje dizinine git
cd /root/kirveyenibot || exit 1

# Remote URL'i token olmadan ayarla
echo "📝 Remote URL ayarlanıyor..."
git remote set-url origin https://github.com/aston599/kirveyenibot.git

# Credential helper'ı ayarla
echo "🔧 Credential helper ayarlanıyor..."
git config --global credential.helper store

# Token'ı kaydet
echo "💾 Token kaydediliyor..."
echo "https://[REDACTED_GITHUB_TOKEN]@github.com" > ~/.git-credentials

# Dosya izinlerini ayarla (güvenlik)
chmod 600 ~/.git-credentials

echo ""
echo "✅ Kurulum tamamlandı!"
echo ""
echo "🧪 Test ediliyor..."
git pull origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Başarılı! Artık şifre sormayacak."
else
    echo ""
    echo "❌ Hata oluştu! Lütfen kontrol edin."
    exit 1
fi

echo ""
echo "📋 Sonraki adımlar:"
echo "1. Migration çalıştır: python3 database_migration_helper.py"
echo "2. Botu yeniden başlat: systemctl restart kirvebot"
echo "3. Durumu kontrol et: systemctl status kirvebot"

