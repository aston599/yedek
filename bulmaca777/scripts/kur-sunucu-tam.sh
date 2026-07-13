#!/bin/bash
# Ilk kurulum: repo yoksa clone + .env + servis
# Sunucuda: bash kur-sunucu-tam.sh
set -euo pipefail

APP_DIR="/opt/bulmaca777"
REPO="https://github.com/aston599/bulmaca777.git"

apt-get update -qq
apt-get install -y -qq git nginx curl

if ! command -v node >/dev/null || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 22 ]]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y -qq nodejs
fi

if [[ -d "$APP_DIR/.git" ]]; then
  cd "$APP_DIR" && git pull origin main
else
  git clone "$REPO" "$APP_DIR"
  cd "$APP_DIR"
fi

npm install --omit=dev
mkdir -p data data/rooms

if [[ ! -f .env ]]; then
  cp .env.production.example .env
  echo ""
  echo ">>> .env olusturuldu. Windows'tan aktar-ubuntu.cmd calistirin"
  echo ">>> veya: nano $APP_DIR/.env"
  exit 0
fi

bash "$APP_DIR/scripts/deploy-ubuntu.sh"
