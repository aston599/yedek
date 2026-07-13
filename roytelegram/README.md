# Betroy Affiliate Bot

Bot sahibi `/admin` panelinden mesajları, butonları, reklam banner'ını ve affiliate linklerini Telegram içinden düzenler.

## Kurulum

```bash
cd telegram-affiliate-bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

`.env` dosyasını doldurun:

- `BOT_TOKEN` — [@BotFather](https://t.me/BotFather) token
- `ADMIN_IDS` — bot sahibinin Telegram user id (virgülle birden fazla)

Botu çalıştırın:

```bash
python -m bot.main
```

## Admin paneli

Bot sahibi bota `/admin` yazar. Açılan menüden:

| Ayar | Ne işe yarar |
|------|----------------|
| Hoş geldin mesajı | `/start` sonrası ana promo metni |
| Promo görseli | Üstteki reklam görseli |
| Üst reklam banner | Mesajın en üstündeki sponsor satırı (Reklam First alanı) |
| Promo kodu | VIP / bonus kodu |
| Inline buton | Yeşil dış link butonu (metin + URL) |
| Alt menü butonu | Alttaki sabit `Giriş` butonu |
| Önizleme | Kullanıcıların gördüğü ekranı test eder |
| Toplu mesaj | Tüm kullanıcılara broadcast |
| İstatistik | Kullanıcı ve tıklama sayısı |

### Örnek düzenleme

Inline buton için admin şunu yazar:

```
🎰 900 FREESPIN | https://roygir.com/zayptv
```

Alt menü için:

```
🎁 Giriş | https://roygir.com/zayptv
```

## Kullanıcı akışı

1. Kullanıcı `/start` yazar veya reklamdan gelir
2. Üstte reklam banner + promo görsel + metin görür
3. Inline butona veya alt menüye tıklar → affiliate link
4. Tıklamalar veritabanına kaydedilir

## DigitalOcean / Ubuntu sunucu kurulumu

Sunucuda (root):

```bash
apt-get update && apt-get install -y git curl
curl -fsSL https://raw.githubusercontent.com/aston599/roytelegram/main/deploy/install.sh -o /tmp/install.sh
chmod +x /tmp/install.sh
BOT_TOKEN='TELEGRAM_BOT_TOKEN' bash /tmp/install.sh
```

Özel repo için:

```bash
GITHUB_TOKEN='ghp_...' BOT_TOKEN='...' bash /tmp/install.sh
```

Log: `journalctl -u roytelegram -f`  
Yeniden başlat: `systemctl restart roytelegram`

## Notlar

- Ayarlar SQLite'da saklanır (`data/bot.db`)
- Bot profil açıklaması için [@BotFather](https://t.me/BotFather) → Edit Bot → Description
- Telegram Ads için reklam hedefi olarak bot linkini kullanın; casino linki reklamda değil bot içinde olmalı
