# 🚀 Ubuntu Sunucu Güncelleme Komutları

## Hızlı Güncelleme (Tek Komut)

```bash
cd ~/telegrambot && git pull origin main && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart kirvehub-bot && sudo systemctl status kirvehub-bot
```

## Adım Adım Güncelleme

### 1. Bot dizinine git
```bash
cd ~/telegrambot
```

### 2. GitHub'dan son değişiklikleri çek
```bash
git pull origin main
```

### 3. Virtual environment'ı aktifleştir
```bash
source venv/bin/activate
```

### 4. Gereksinimleri güncelle (eğer requirements.txt değiştiyse)
```bash
pip install -r requirements.txt
```

### 5. Botu yeniden başlat
```bash
sudo systemctl restart kirvehub-bot
```

### 6. Bot durumunu kontrol et
```bash
sudo systemctl status kirvehub-bot
```

## Log Kontrolü

### Canlı log takibi
```bash
sudo journalctl -u kirvehub-bot -f
```

### Son 100 satır log
```bash
sudo journalctl -u kirvehub-bot -n 100
```

### Bugünkü loglar
```bash
sudo journalctl -u kirvehub-bot --since today
```

## Sorun Giderme

### Bot çalışmıyorsa
```bash
# Bot durumunu kontrol et
sudo systemctl status kirvehub-bot

# Hata loglarını gör
sudo journalctl -u kirvehub-bot -n 50 --no-pager

# Botu manuel başlat (test için)
cd ~/telegrambot
source venv/bin/activate
python main.py
```

### Git pull hata verirse
```bash
# Değişiklikleri kaydetmeden çek
git fetch origin
git reset --hard origin/main

# Veya stash yap
git stash
git pull origin main
git stash pop
```

## Notlar

- ✅ Systemd service kullanılıyorsa: `sudo systemctl restart kirvehub-bot`
- ✅ Manuel çalıştırıyorsanız: `pkill -f "python.*main.py"` sonra `nohup python main.py &`
- ✅ Lock file sorunu varsa: `rm -f ~/telegrambot/bot_running.lock`


