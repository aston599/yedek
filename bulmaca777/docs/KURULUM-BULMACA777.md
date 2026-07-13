# bulmaca777.com — GitHub + DigitalOcean + Porkbun DNS

Tek sunucuda hem **ana sayfa** hem **panel** (`/admin/`) çalışır.

| Adres | Ne var? |
|-------|---------|
| https://bulmaca777.com/ | Tanıtım (ana ekran) |
| https://bulmaca777.com/admin/ | Yönetim paneli |
| https://bulmaca777.com/login/ | Giriş |
| https://bulmaca777.com/privacy.html | Gizlilik (Google OAuth) |
| https://bulmaca777.com/auth/callback | YouTube OAuth dönüş |

---

## 1) Nameserver — değiştirmeyin

Domain Porkbun’da kayıtlı ve nameserver’lar zaten Porkbun:

- `curitiba.ns.porkbun.com`
- `fortaleza.ns.porkbun.com`
- `maceio.ns.porkbun.com`
- `salvador.ns.porkbun.com`

**Yapmanız gereken:** Nameserver’ları olduğu gibi bırakın. DNS kayıtlarını **Porkbun → Domain Management → bulmaca777.com → DNS** ekranından eklersiniz.

DigitalOcean nameserver’a geçmeniz **gerekmez**.

---

## 2) GitHub’a yükleme

Proje klasöründe (PowerShell):

```powershell
cd "C:\Users\gamin\OneDrive\Desktop\youtubproject"
git init
git add .
git commit -m "Bulmaca777: site, panel, DigitalOcean deploy"
```

Repo: **https://github.com/aston599/bulmaca777**

```powershell
git remote add origin https://github.com/aston599/bulmaca777.git
# Zaten remote varsa: git remote set-url origin https://github.com/aston599/bulmaca777.git
git branch -M main
git push -u origin main
```

`.env` dosyası `.gitignore`’da — **asla push etmeyin**.

---

## 3) DigitalOcean App oluşturma

1. [cloud.digitalocean.com](https://cloud.digitalocean.com) → **Create → Apps**
2. **GitHub** → repoyu seçin → branch `main`
3. Tip: **Web Service** (Node.js)
4. Build: `npm install` · Run: `npm start` · Port: **8080** (DO `PORT` verir, uygulama otomatik kullanır)
5. **App Spec** kullanıyorsanız kökteki `.do/app.yaml` import edilebilir

### Ortam değişkenleri (Settings → App → web → Environment)

| Anahtar | Değer |
|---------|--------|
| `NODE_ENV` | `production` |
| `HOST` | `0.0.0.0` |
| `PUBLIC_URL` | `https://bulmaca777.com` |
| `CHAT_MODE` | `youtube` |
| `GOOGLE_REDIRECT_URI` | `https://bulmaca777.com/auth/callback` |
| `COOKIE_SECURE` | `true` |
| `GOOGLE_CLIENT_ID` | (Secret) |
| `GOOGLE_CLIENT_SECRET` | (Secret) |

### Kalıcı veri (önemli)

SQLite ve YouTube token’ları `data/` klasöründe. App yeniden deploy olunca silinmesin diye:

1. App → **Settings → web → Volumes**
2. Volume ekleyin, mount path: **`/workspace/data`**
3. (Spec’te `bulmaca-data` volume tanımlı)

### Domain (DigitalOcean tarafı)

1. App → **Settings → Domains**
2. **Add Domain** → `bulmaca777.com`
3. **Add Domain** → `www.bulmaca777.com`
4. DO size DNS talimatı gösterir (genelde `CNAME` hedefi `xxxxx.ondigitalocean.app` veya benzeri)

Deploy bitince geçici adres: `https://bulmaca777-xxxxx.ondigitalocean.app` — önce bunu test edin.

---

## 4) Porkbun DNS kayıtları

Porkbun panel → **bulmaca777.com** → **DNS Records**.

DigitalOcean’un verdiği hedefe göre (örnek — sizinki farklı olabilir):

| Tip | Host | Answer / Value |
|-----|------|----------------|
| **ALIAS** veya **ANAME** | `@` (kök) | DigitalOcean’un verdiği hostname (`….ondigitalocean.app`) |
| **CNAME** | `www` | Aynı hostname veya `bulmaca777.com` |

Porkbun’da kök domain için **ALIAS** kaydı varsa onu kullanın; yoksa DO panelindeki **A record** IP’lerini `@` için girin.

Kayıt sonrası 5–60 dakika bekleyin. Kontrol:

```text
https://bulmaca777.com/api/health
→ {"ok":true,...}
```

---

## 5) Google Cloud OAuth

[Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → **OAuth consent screen**

| Alan | URL |
|------|-----|
| Application home page | `https://bulmaca777.com/` |
| Privacy policy | `https://bulmaca777.com/privacy.html` |
| Authorized domains | `bulmaca777.com` |

**Credentials** → OAuth client → Authorized redirect URIs:

```text
https://bulmaca777.com/auth/callback
```

(Geliştirme için ek olarak: `http://localhost:3847/auth/callback`)

Test modunda: **Test users** → kanal Gmail’inizi ekleyin.

---

## 6) İlk kullanım

1. `https://bulmaca777.com/` — ana sayfa
2. `https://bulmaca777.com/login/` — kayıt
3. `https://bulmaca777.com/admin/` — oda oluştur, YouTube bağla, overlay URL kopyala

---

## Sorun giderme

| Sorun | Çözüm |
|-------|--------|
| Domain açılmıyor | Porkbun DNS + DO domain “Active” mi bekleyin |
| 403 Google OAuth | Test kullanıcısına Gmail ekleyin |
| Panel giriş olmuyor | `COOKIE_SECURE=true` ve site **HTTPS** olmalı |
| Veriler silindi | Volume `/workspace/data` mount kontrolü |
| SSL hatası | DO domain doğrulaması tamamlanana kadar bekleyin |

---

## VPS kurulumu (Ubuntu — örn. DigitalOcean Droplet)

Sunucu IP örneği: `164.90.163.55` — Porkbun DNS:

| Tip | Host | Value |
|-----|------|--------|
| A | `@` | `164.90.163.55` |
| A | `www` | `164.90.163.55` |

Sunucuda (root):

```bash
curl -fsSL https://raw.githubusercontent.com/aston599/bulmaca777/main/scripts/deploy-ubuntu.sh -o /tmp/deploy.sh
bash /tmp/deploy.sh
nano /opt/bulmaca777/.env
# GOOGLE_CLIENT_ID ve GOOGLE_CLIENT_SECRET doldurun
systemctl restart bulmaca777
apt install -y certbot python3-certbot-nginx
certbot --nginx -d bulmaca777.com -d www.bulmaca777.com
```

Kontrol: `https://bulmaca777.com/api/health`

---

## Yerel test (domain olmadan)

```powershell
npm start
```

- http://localhost:3847/ — ana sayfa  
- http://localhost:3847/admin/ — panel  

`.env`: `PUBLIC_URL=http://localhost:3847`
