# VPS hizli kurulum (repo private ise)

Repo gizliyse `curl raw.githubusercontent.com` calismaz. Asagidaki bloklari sunucuda root olarak yapistirin.

## A) Repo public ise

```bash
apt update -y && apt install -y git nginx curl
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs

git clone https://github.com/aston599/bulmaca777.git /opt/bulmaca777
cd /opt/bulmaca777
npm install --omit=dev
```

## B) Repo private ise

GitHub → Settings → Developer settings → Personal access token (repo okuma).

```bash
git clone https://TOKEN@github.com/aston599/bulmaca777.git /opt/bulmaca777
```

veya repoyu **Public** yapin: GitHub repo → Settings → Danger zone → Change visibility.

## C) Ortak adimlar (clone sonrasi)

```bash
cd /opt/bulmaca777
cp .env.example .env
nano .env
```

Doldurun: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, ve:

```
PUBLIC_URL=https://bulmaca777.com
GOOGLE_REDIRECT_URI=https://bulmaca777.com/auth/callback
HOST=0.0.0.0
NODE_ENV=production
COOKIE_SECURE=true
CHAT_MODE=youtube
```

Sonra systemd + nginx script:

```bash
bash /opt/bulmaca777/scripts/deploy-ubuntu.sh
```

(Script sadece nginx/systemd kurar; repo zaten clone ise `git pull` yapar.)
