#!/bin/bash
# Git olmadan: /opt/bulmaca777 zaten dolu (scp ile geldiyse)
set -euo pipefail
APP_DIR="/opt/bulmaca777"
DOMAIN="${DOMAIN:-bulmaca777.com}"
NODE_MAJOR=22

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx curl ca-certificates

if ! command -v node >/dev/null || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt "$NODE_MAJOR" ]]; then
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash -
  apt-get install -y -qq nodejs
fi

cd "$APP_DIR"
npm install --omit=dev
mkdir -p data data/rooms

if [[ ! -f .env ]]; then
  cp .env.example .env 2>/dev/null || true
  sed -i "s|PUBLIC_URL=.*|PUBLIC_URL=https://${DOMAIN}|" .env
  sed -i "s|GOOGLE_REDIRECT_URI=.*|GOOGLE_REDIRECT_URI=https://${DOMAIN}/auth/callback|" .env
  grep -q '^NODE_ENV=' .env || echo 'NODE_ENV=production' >> .env
  grep -q '^COOKIE_SECURE=' .env || echo 'COOKIE_SECURE=true' >> .env
fi

cat > /etc/systemd/system/bulmaca777.service <<EOF
[Unit]
Description=Bulmaca777
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

cat > /etc/nginx/sites-available/bulmaca777 <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} www.${DOMAIN};
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
nginx -t && systemctl reload nginx

curl -s http://127.0.0.1:3847/api/health || true
echo ""
systemctl is-active bulmaca777
