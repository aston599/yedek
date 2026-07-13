#!/bin/bash
# Bulmaca777 — Ubuntu VPS (DigitalOcean vb.)
# Kullanim: sudo bash deploy-ubuntu.sh
set -euo pipefail

APP_DIR="/opt/bulmaca777"
REPO="https://github.com/aston599/bulmaca777.git"
DOMAIN="${DOMAIN:-bulmaca777.com}"
NODE_MAJOR=22

echo "==> Paketler"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git nginx curl ca-certificates

if ! command -v node >/dev/null || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt "$NODE_MAJOR" ]]; then
  echo "==> Node.js ${NODE_MAJOR}"
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash -
  apt-get install -y -qq nodejs
fi

echo "==> Repo: ${APP_DIR}"
if [[ -d "$APP_DIR/.git" ]]; then
  cd "$APP_DIR"
  git pull origin main
else
  git clone "$REPO" "$APP_DIR"
  cd "$APP_DIR"
fi

npm install --omit=dev
mkdir -p data data/rooms

if [[ ! -f .env ]]; then
  cp .env.example .env
  sed -i "s|PUBLIC_URL=.*|PUBLIC_URL=https://${DOMAIN}|" .env
  sed -i "s|GOOGLE_REDIRECT_URI=.*|GOOGLE_REDIRECT_URI=https://${DOMAIN}/auth/callback|" .env
  sed -i "s|HOST=.*|HOST=0.0.0.0|" .env
  echo "COOKIE_SECURE=true" >> .env
  echo "NODE_ENV=production" >> .env
  echo ""
  echo "*** .env olusturuldu. Google bilgilerini duzenleyin:"
  echo "    nano ${APP_DIR}/.env"
fi

echo "==> systemd: bulmaca777"
cat > /etc/systemd/system/bulmaca777.service <<EOF
[Unit]
Description=Bulmaca777 YouTube bulmaca botu
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
Environment=NODE_ENV=production
ExecStart=/usr/bin/node server/index.js
Restart=on-failure
RestartSec=5
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
EOF

chown -R www-data:www-data "$APP_DIR"
systemctl daemon-reload
systemctl enable bulmaca777
systemctl restart bulmaca777

echo "==> nginx"
cat > /etc/nginx/sites-available/bulmaca777 <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} www.${DOMAIN};

    client_max_body_size 4m;

    location / {
        proxy_pass http://127.0.0.1:3847;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

ln -sf /etc/nginx/sites-available/bulmaca777 /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo ""
echo "=============================================="
echo " Kurulum tamam."
echo " Uygulama: http://127.0.0.1:3847 (nginx :80)"
echo " DNS: ${DOMAIN} -> bu sunucunun IP (A kaydi)"
echo ""
echo " Sonraki adimlar:"
echo " 1) nano ${APP_DIR}/.env  (GOOGLE_CLIENT_ID/SECRET)"
echo " 2) systemctl restart bulmaca777"
echo " 3) SSL: apt install -y certbot python3-certbot-nginx"
echo "    certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
echo "=============================================="
systemctl status bulmaca777 --no-pager || true
