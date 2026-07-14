#!/bin/bash
# Ubuntu sunucusunda main.py dosyasındaki merge conflict'leri düzelt

echo "🔧 main.py dosyası düzeltiliyor..."

# Dosyayı yedekle
cp main.py main.py.backup

# Null bytes'ları temizle
sed -i 's/\x00//g' main.py

# İlk 2049 satırı al ve dosyayı güncelle
head -n 2049 main.py > main.py.tmp && mv main.py.tmp main.py

# Merge conflict marker'larını kontrol et
if grep -q "^<<<<<<< HEAD" main.py || grep -q "^=======" main.py || grep -q "^>>>>>>>" main.py; then
    echo "⚠️ Merge conflict marker'ları bulundu, temizleniyor..."
    # İlk <<<<<<< HEAD satırını bul ve sil
    sed -i '/^<<<<<<< HEAD/d' main.py
    # ======= satırından başlayarak dosyanın sonuna kadar olan kısmı sil
    sed -i '/^=======/,${/^>>>>>>>/!d;}' main.py
    sed -i '/^>>>>>>>/d' main.py
fi

# Python syntax kontrolü
python3 -m py_compile main.py
if [ $? -eq 0 ]; then
    echo "✅ main.py dosyası başarıyla düzeltildi!"
    echo "📝 Yedek dosya: main.py.backup"
else
    echo "❌ Syntax hatası var! Yedekten geri yüklüyorum..."
    mv main.py.backup main.py
    exit 1
fi





