# Tanıtım sitesi — yayınlama rehberi

Statik dosyalar `website/` klasöründedir. Google OAuth Production için bu sayfaların **herkese açık HTTPS URL**’leri gerekir.

**Yapılacaklar (siz):**

1. `destek@ornek.com` → kendi e-postanız (`index.html`, `privacy.html`, `terms.html`)
2. Alan adı satın alın (isteğe bağlı; önce ücretsiz alt alan da olur)

---

## Seçenek A — GitHub Pages (ücretsiz, hızlı başlangıç)

1. Repoyu GitHub’a push edin.
2. **Settings → Pages → Build and deployment**
   - Source: **Deploy from a branch**
   - Branch: `main`, folder: **`/website`**
3. Birkaç dakika sonra site: `https://KULLANICI.github.io/REPO_ADI/`

**Google Cloud OAuth consent screen:**

| Alan | Örnek URL |
|------|-----------|
| Application home page | `https://KULLANICI.github.io/REPO_ADI/` |
| Privacy policy | `https://KULLANICI.github.io/REPO_ADI/privacy.html` |
| Terms (isteğe bağlı) | `https://KULLANICI.github.io/REPO_ADI/terms.html` |
| Authorized domains | `github.io` |

**Özel alan adı (ör. `bulmaca.com`):**

1. Alan adı DNS’inde **CNAME** → `KULLANICI.github.io`
2. GitHub Pages → **Custom domain** → `bulmaca.com`
3. OAuth **Authorized domains** → `bulmaca.com`

---

## Seçenek B — DigitalOcean App Platform (önerilen: kendi domain + HTTPS)

Tanıtım sitesi statik; Node uygulaması ayrı kalabilir (evde `baslat.cmd` veya ileride ikinci App).

1. [DigitalOcean](https://www.digitalocean.com/) → **Create → Apps**
2. **GitHub** ile repoyu bağlayın.
3. **Resource type:** Static Site
4. **Source directory / output:** `website` (veya build command boş, output `website`)
5. Deploy → `https://uygulama-adi-xxxxx.ondigitalocean.app`

**Özel domain:**

1. App → **Settings → Domains** → Add domain (`bulmaca.com` veya `www`)
2. DigitalOcean size DNS kaydı söyler (genelde **CNAME** veya **A**)
3. Alan adını aldığınız yerde (Cloudflare, Namecheap, DO Networking):
   - `www` → CNAME → `uygulama-adi-xxxxx.ondigitalocean.app`
   - kök `@` için DO’nun verdiği A kayıtları veya ALIAS
4. DO otomatik **Let’s Encrypt HTTPS** verir.

**Google OAuth:**

| Alan | Örnek |
|------|--------|
| Home page | `https://bulmaca.com/` |
| Privacy | `https://bulmaca.com/privacy.html` |
| Authorized domains | `bulmaca.com` |

---

## Alan adı nereden alınır?

| Sağlayıcı | Not |
|-----------|-----|
| [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/) | Ucuz, DNS hızlı |
| Namecheap, Porkbun | Kolay panel |
| DigitalOcean Domains | DO ile tek yerden |

Alan adı **zorunlu değil** — önce `*.github.io` veya `*.ondigitalocean.app` ile Google başvurusuna başlayabilirsiniz; sonra domain bağlarsınız.

---

## Node uygulaması (panel) ayrı mı?

Evet. Bu site **sadece tanıtım + gizlilik**. Panel/OBS sunucusu:

- Geliştirmede: `http://localhost:3847`
- İleride internetten panel için: DigitalOcean’da **ikinci bir App** (Web Service, `npm start`) veya Droplet + nginx

OAuth **redirect URI** panel adresinize göre kalır, örn.:

- `https://panel.bulmaca.com/auth/callback`
- Geliştirme: `http://localhost:3847/auth/callback`

Tanıtım sitesi URL’si ile redirect URI **aynı olmak zorunda değil**.

---

## Yerel önizleme

```bash
cd website
npx --yes serve .
```

Tarayıcı: `http://localhost:3000`

---

## Kontrol listesi (Google Production)

- [ ] HTTPS açılıyor, giriş gerektirmiyor
- [ ] Gizlilik sayfası Türkçe ve uygulamayı doğru anlatıyor
- [ ] OAuth consent’te domain ile URL uyumlu
- [ ] YouTube API etkin, OAuth test kullanıcısı (test modunda) eklendi
- [ ] İletişim e-postası gerçek
