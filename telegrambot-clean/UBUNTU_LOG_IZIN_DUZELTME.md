# 🔧 Log İzin Hatası Çözümü

## Sorun
```
PermissionError: [Errno 13] Permission denied: '/home/kirvehub/telegrambot-clean/bot.log'
```

## Çözüm

### 1. Logs Klasörü ve İzinleri Düzelt

```bash
cd /home/kirvehub/telegrambot-clean

# Logs klasörünü oluştur (yoksa)
mkdir -p logs

# Eski bot.log dosyasını sil (varsa)
rm -f bot.log

# İzinleri düzelt
chown -R kirvehub:kirvehub /home/kirvehub/telegrambot-clean
chmod 755 logs
chmod 755 /home/kirvehub/telegrambot-clean
```

### 2. main.py'de Log Yolunu Kontrol Et

Eğer main.py'de hala `bot.log` yazıyorsa, `logs/bot.log` olarak değiştirilmeli.

### 3. Tek Komutla Çözüm

```bash
cd /home/kirvehub/telegrambot-clean && \
mkdir -p logs && \
rm -f bot.log && \
chown -R kirvehub:kirvehub /home/kirvehub/telegrambot-clean && \
chmod 755 logs && \
chmod 755 /home/kirvehub/telegrambot-clean && \
echo "✅ İzinler düzeltildi!" && \
sudo systemctl restart kirvehub-bot-clean && \
sudo systemctl status kirvehub-bot-clean
```

### 4. main.py'de Log Yolunu Kontrol Et

```bash
# main.py'de bot.log geçen yerleri kontrol et
grep -n "bot.log" /home/kirvehub/telegrambot-clean/main.py

# Eğer varsa, logs/bot.log olarak değiştir
# nano main.py ile düzenle
```


