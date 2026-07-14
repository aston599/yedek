# 🔧 psutil Modül Hatası Çözümü

## Sorun
```
ModuleNotFoundError: No module named 'psutil'
```

## Çözüm

### 1. venv'i Aktif Et ve Bağımlılıkları Kur

```bash
cd /home/kirvehub/telegrambot-clean

# venv'i aktif et
source venv/bin/activate

# Bağımlılıkları kur
pip install --upgrade pip
pip install -r requirements.txt

# Özellikle psutil'i kontrol et
pip install psutil

# Tüm bağımlılıkları kontrol et
pip list | grep psutil
```

### 2. Systemd Service'inin Doğru venv'i Kullandığını Kontrol Et

```bash
# Systemd service dosyasını kontrol et
cat /etc/systemd/system/kirvehub-bot-clean.service

# PATH'in doğru olduğundan emin ol
# Environment=PATH=/home/kirvehub/telegrambot-clean/venv/bin:...
```

### 3. Manuel Test

```bash
cd /home/kirvehub/telegrambot-clean
source venv/bin/activate
python main.py
```

Eğer manuel test çalışıyorsa, systemd service'i yeniden başlat:

```bash
sudo systemctl restart kirvehub-bot-clean
sudo systemctl status kirvehub-bot-clean
```

### 4. Tek Komutla Çözüm

```bash
cd /home/kirvehub/telegrambot-clean && \
source venv/bin/activate && \
pip install --upgrade pip && \
pip install -r requirements.txt && \
pip install psutil && \
echo "✅ Bağımlılıklar kuruldu!" && \
sudo systemctl restart kirvehub-bot-clean && \
sudo systemctl status kirvehub-bot-clean
```


