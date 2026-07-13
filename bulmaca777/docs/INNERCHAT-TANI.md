# InnerChat tanılama (yerel vs VPS)

## 1) Panel — en kolay

Admin → **Sohbet botu** → **InnerChat canlı tap**

| Görünen | Anlam |
|---------|--------|
| `bağlı değil` | Sohbete bağlan yok |
| `bağlı, oyun bekliyor (idle)` | Bağlandı ama **Başlat** yok → mesaj okunmaz |
| `dinleniyor (live)` | InnerChat dinlemeye çalışıyor |
| Liste doluyor | Makinede de çalışıyor |
| `live` ama liste boş + canlıda yazıyorsunuz | VPS / youtube-chat sorunu |

Giriş yaptıktan sonra tarayıcıda (oda ID ile):

`GET https://bulmaca777.com/api/rooms/ODA_ID/inner-chat/diagnostic`

`hints` dizisi ne yapmanız gerektiğini yazar.

## 2) Ubuntu / VPS — komut satırı testi (önerilen)

Sunucudaki uygulamadan bağımsız, aynı `youtube-chat` paketi:

```bash
cd /opt/bulmaca777   # veya proje klasörü
git pull origin main
npm install --omit=dev

# Canlı yayın linki (CANLI olmalı)
node scripts/test-inner-chat.js "https://www.youtube.com/watch?v=q3rmzYWaIoc"

# 30 sn sonra otomatik çıkış
node scripts/test-inner-chat.js "https://www.youtube.com/watch?v=q3rmzYWaIoc" --seconds=30

# veya npm
npm run test:inner-chat -- "https://www.youtube.com/watch?v=q3rmzYWaIoc"
```

| Çıktı | Anlam |
|-------|--------|
| `[start OK]` + `@kullanıcı: mesaj` | InnerChat bu makinede çalışıyor |
| `[start FAILED]` | Yayın **canlı değil** veya ID yanlış — uygulama hatası değil |
| `[start OK]` ama mesaj yok | Yayın sessiz; sohbete bir şey yazıp tekrar deneyin |

### VPS’te OK, evde OK — sunucuda `[start FAILED]`?

Aynı link ev bilgisayarında çalışıp **kirvebotyeni**’nde çalışmıyorsa çoğunlukla:

1. **Yayın o anda canlı değil** (bitmiş video ID)
2. **VPS IP** — YouTube farklı/kısıtlı HTML veriyor (`canonical` yok → `Live Stream was not found`)

Önce tanı (JSON):

```bash
node scripts/test-inner-chat.js q3rmzYWaIoc --diagnose
```

`innerChatOK: false` ve `consentWall` / `botHint` / `blockKind: bot` görürseniz `.env`’e deneyin:

```env
YOUTUBE_CONSENT_COOKIE=CONSENT=YES+1
YOUTUBE_FETCH_LANG=tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7
```

**Tarayıcı cookie (bot duvarı için en etkili):** Chrome’da youtube.com açık ve giriş yapılı → Geliştirici araçları → Application → Cookies → `youtube.com` → `SOCS`, `VISITOR_INFO1_LIVE`, `__Secure-3PSID` vb. kopyalayın:

```env
YOUTUBE_CONSENT_COOKIE=SOCS=...; VISITOR_INFO1_LIVE=...; __Secure-3PSID=...
```

**Residential proxy (VPS IP kısıtlıysa):**

```env
YOUTUBE_HTTP_PROXY=http://kullanici:sifre@proxy-host:port
```

Sonra `git pull` + `systemctl restart bulmaca777`.

Güncel kod sırayla dener: watch + consent → `live_chat` popout → mobil → embed → **InnerTube player (ANDROID/TV)**. Tanı çıktısında `Stratejiler:` satırına bakın; `innertube:ANDROID` ile `innerChatOK: true` olabilir.

Hâlâ olmazsa: saf datacenter IP (DigitalOcean vb.) YouTube tarafından sık tamamen kilitlenir — proxy/cookie şart; uzun vadede OAuth `liveChat.messages` veya ev ağı köprüsü gerekir.

## 3) Sunucu logları (SSH)

```bash
# Son 100 satır
journalctl -u bulmaca777 -n 100 --no-pager

# InnerChat satırları (canlı izle)
journalctl -u bulmaca777 -f | grep -i "inner chat"

# Bağlantı / mod değişimi (debug açıkken)
journalctl -u bulmaca777 -f | grep "InnerChat "
```

Önemli mesajlar:

- `[Inner chat] start OK VIDEO_ID` → youtube-chat yayına bağlandı
- `[Inner chat] start FAILED VIDEO_ID` → yayın kapalı veya ID yanlış (VPS’te sık)
- `[Inner chat] Canli sohbet acilamadi` → aynı
- `[Inner chat start]` → beklenmeyen hata

## 3) Debug logunu aç (VPS .env)

```env
INNER_CHAT_DEBUG=1
INNER_CHAT_TAP=1
```

```bash
systemctl restart bulmaca777
```

Panelden bağlan + başlat; logda şunlar çıkar:

```text
[InnerChat ODA_ID] connect dQw4w9WgXcQ
[InnerChat ODA_ID] pollingMode=live game=active videos=...
```

## 4) Hızlı API kontrolleri (sunucuda)

```bash
curl -s http://127.0.0.1:3847/api/health
curl -s http://127.0.0.1:3847/api/app/chat-info
```

`chatMode` → `youtube` olmalı.

## 5) Yerel çalışıp VPS çalışmama nedenleri

| Neden | Kontrol |
|-------|--------|
| `CHAT_MODE=mock` | `grep CHAT_MODE /opt/bulmaca777/.env` |
| Kod eski | `git log -1` + `git pull` |
| Başlat unutuldu | diagnostic → `pollingMode: idle` |
| Yayın canlı değil | Aynı link yerelde canlı, VPS’te bitmiş olabilir |
| Yanlış video ID | diagnostic → `videoIds` |
| youtube-chat VPS’te blok | `start FAILED` logları; ev ağında çalışır IP kısıtı nadir |
| Başka oda live çalıyor | Aynı kullanıcıda tek oda `live` poll |

## 6) Karşılaştırma testi

1. Aynı **canlı** yayın linki
2. Yerelde: tap doluyor mu?
3. VPS: `git pull` + restart → aynı oda → tap + diagnostic
4. `activeStreamIds` dolu mu? (`start OK` logları)

Tap doluyorsa InnerChat makinede **çalışıyor**; oyun cevap vermiyorsa sorun oyun/mod tarafındadır.
