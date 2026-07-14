# 🔧 venv Yeniden Kurulum

## Sorun
- `venv/bin/activate: No such file or directory`
- venv klasörü eksik veya bozuk

## Çözüm

### 1. Eski venv'i Sil ve Yeniden Oluştur

```bash
cd /home/kirvehub/telegrambot-clean

# Eski venv'i sil (varsa)
rm -rf venv

# Yeni venv oluştur
python3.12 -m venv venv

# venv'i aktif et
source venv/bin/activate

# pip'i güncelle
pip install --upgrade pip

# Bağımlılıkları kur
pip install -r requirements.txt

# Özellikle psutil'i kontrol et
pip install psutil

# Kurulumu kontrol et
pip list | grep psutil
```

### 2. İzinleri Düzelt

```bash
chown -R kirvehub:kirvehub /home/kirvehub/telegrambot-clean/venv
```

### 3. Systemd Service'i Yeniden Başlat

```bash
sudo systemctl restart kirvehub-bot-clean
sudo systemctl status kirvehub-bot-clean
```

### 4. Tek Komutla Çözüm

```bash
cd /home/kirvehub/telegrambot-clean && \
rm -rf venv && \
python3.12 -m venv venv && \
source venv/bin/activate && \
pip install --upgrade pip && \
pip install -r requirements.txt && \
chown -R kirvehub:kirvehub venv && \
echo "✅ venv yeniden kuruldu!" && \
sudo systemctl restart kirvehub-bot-clean && \
sudo systemctl status kirvehub-bot-clean
```

### 5. Manuel Test

```bash
cd /home/kirvehub/telegrambot-clean
source venv/bin/activate
python main.py
```

Eğer manuel test çalışıyorsa, systemd service'i de çalışmalı.


