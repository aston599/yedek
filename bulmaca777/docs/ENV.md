# .env rehberi

## Tum degiskenler

| Degisken | Zorunlu | Varsayilan | Aciklama |
|----------|---------|------------|----------|
| `PORT` | Hayir | `3847` | Dinlenen port. DigitalOcean App `PORT` verir; VPS'te 3847 kalabilir (nginx proxy). |
| `HOST` | Hayir | `0.0.0.0` | `localhost` yazilirsa kod yine `0.0.0.0` kullanir. |
| `PUBLIC_URL` | Canlida evet | `http://localhost:PORT` | Overlay/admin linkleri, OAuth on yuz. |
| `PUBLIC_HOST` | Hayir | `localhost` | Sadece `PUBLIC_URL` yoksa. |
| `NODE_ENV` | Hayir | — | `production` → oturum cerezi `secure` (HTTPS). |
| `COOKIE_SECURE` | Hayir | production'da `true` | `true` / `false` ile zorla. |
| `CHAT_MODE` | Hayir | `mock` | `youtube` veya `mock`. |
| `GOOGLE_CLIENT_ID` | youtube modunda | — | OAuth istemci ID. |
| `GOOGLE_CLIENT_SECRET` | youtube modunda | — | OAuth gizli anahtar. |
| `GOOGLE_REDIRECT_URI` | youtube modunda | — | `https://DOMAIN/auth/callback` |
| `WIN_MESSAGE` | Hayir | (sabit metin) | Dogru cevap sohbet sablonu. |
| `NEXT_QUESTION_DELAY_MS` | Hayir | `5000` | Sonraki soruya gecis gecikmesi (klasik bulmaca; ucretli modda uygulanmaz). |
| `HOLD_WINNER_UNTIL_NEXT` | Hayir | `1` | `0` = ucretli yas modunda da 5 sn sonra gecis. `1` = son bilen ekranda kalir, sonraki dogru cevaba kadar. |
| `CELEBRITY_CLOSE_YEARS` | Hayir | `2` | Yas tahmininde \"yaklastin\" mesaji (+- yil). |
| `CELEBRITY_WARM_YEARS` | Hayir | `5` | \"Biraz daha\" mesaji araligi. |
| `BROADCAST_HOLD_MS` | Hayir | `6500` | OBS duyuru seridinde mesaj suresi (ms). |
| `WRONG_BROADCAST_HOLD_MS` | Hayir | `5000` | Yanlis cevap seridi: her kisi icin ekranda kalma suresi (ms), kuyruk sirayla. |
| `WRONG_BROADCAST_QUEUE_MAX` | Hayir | `15` | Ayni anda gelen yanlis cevap kuyrugu ust siniri (fazlasi atilir). |
| `YOUTUBE_CHAT_STAY_CONNECTED` | Hayir | `1` | `1` = Sohbete baglaninca dinleme oyun durunca da acik kalir. `0` = eski (sadece tur aktifken live). |
| `YOUTUBE_CHAT_KEEPALIVE_MS` | Hayir | `45000` | Bagli odalarda kopuk stream varsa yeniden dinlemeyi dener (ms). |
| `INNER_CHAT_POLL_MS` | Hayir | `4500` | youtube-chat poll araligi (ms). Dusuk deger = daha fazla 400 riski. |
| `INNER_CHAT_ERROR_BACKOFF_MS` | Hayir | `12000` | 400/hata sonrasi yeniden baglanma bekleme tabani (ms), ust sinir ~120 sn. |
| `CELEBRITY_CORRECT_FLASH_MS` | Hayir | `5000` | Ünlü yaş: «BİLDİN!» seridi (ms), sonra PR metinleri. |
| `CELEBRITY_PR_ROTATE_MS` | Hayir | `5500` | Ünlü yaş: abone/beğen ve PR metinleri dönüş süresi (ms). |
| `CELEBRITY_PRIZE_LABEL` | Hayir | `EN YÜKSEK PUANA ÖDÜL VAR!` | Ucretli yas OBS duyurusu / kurdele metni (max 72 karakter). |
| `CHAT_POLL_MS` | Hayir | — | **Kodda kullanilmiyor** (gelecek / dokuman). |
| `PLAYGROUND` | Hayir | acik | `0` = /play/ oyun alanini kapatir. Varsayilan: acik (ayar gerekmez). |
| `APP_VERSION` | Hayir | package.json | Panel surum kontrolu. |
| `STARTED_AT` | Hayir | timestamp | Surum etiketi. |

## Google Cloud Console eslesmesi

| .env | Console |
|------|---------|
| `GOOGLE_CLIENT_ID` | OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth Client secret |
| `GOOGLE_REDIRECT_URI` | Authorized redirect URIs |

Consent screen:

- Home: `https://bulmaca777.com/`
- Privacy: `https://bulmaca777.com/privacy.html`
- Authorized domains: `bulmaca777.com`

## Yerel (.env)

```env
PUBLIC_URL=http://localhost:3847
GOOGLE_REDIRECT_URI=http://localhost:3847/auth/callback
CHAT_MODE=youtube
NODE_ENV=development
```

## Canli VPS (bulmaca777.com)

Tam sablon: `.env.production.example` veya yerelde `deploy/bulmaca777-production.env` (git disi).

```env
CHAT_MODE=youtube
PUBLIC_URL=https://bulmaca777.com
NODE_ENV=production
COOKIE_SECURE=true
YOUTUBE_CHAT_STAY_CONNECTED=1
INNER_CHAT_POLL_MS=5000
INNER_CHAT_ERROR_BACKOFF_MS=15000
WRONG_BROADCAST_HOLD_MS=5000
HOLD_WINNER_UNTIL_NEXT=1
INNER_CHAT_TAP=1
AUDIT_LOG=1
AUDIT_LOG_CONSOLE=1
```

`YOUTUBE_MIN_POLL_MS` vb. **InnerChat icin kullanilmaz** (eski OAuth API). Kaldirilabilir.

`GOOGLE_CLIENT_ID` ve `GOOGLE_CLIENT_SECRET` — yerel `.env` ile **ayni** kalabilir; sadece redirect URI Console'da canli adres de eklenmeli.

## Sunucuda duzenleme

```bash
nano /opt/bulmaca777/.env
systemctl restart bulmaca777
```

## Guvenlik

- `.env` asla GitHub'a push edilmez.
- Gizli anahtar sohbet/logda paylasmayin; sizdirdiyseniz Google Console'dan secret yenileyin.
