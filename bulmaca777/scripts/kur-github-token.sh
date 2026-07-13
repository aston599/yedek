#!/bin/bash
# Private repo — GitHub Personal Access Token ile kurulum
# Sunucuda: nano /tmp/kur.sh  (bu dosyayi yapistir)  ->  bash /tmp/kur.sh
set -euo pipefail

APP_DIR="/opt/bulmaca777"
REPO="aston599/bulmaca777"
DOMAIN="bulmaca777.com"
NODE_MAJOR=22

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  read -rsp "GitHub Personal Access Token: " GITHUB_TOKEN
  echo ""
fi

if [[ -z "$GITHUB_TOKEN" ]]; then
  echo "HATA: GITHUB_TOKEN bos."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git nginx curl ca-certificates

if ! command -v node >/dev/null || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt "$NODE_MAJOR" ]]; then
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash -
  apt-get install -y -qq nodejs
fi

CLONE_URL="https://${GITHUB_TOKEN}@github.com/${REPO}.git"

if [[ -d "$APP_DIR/.git" ]]; then
  cd "$APP_DIR"
  git remote set-url origin "$CLONE_URL"
  git pull origin main
  git remote set-url origin "https://github.com/${REPO}.git"
else
  rm -rf "$APP_DIR"
  git clone "$CLONE_URL" "$APP_DIR"
  cd "$APP_DIR"
  git remote set-url origin "https://github.com/${REPO}.git"
fi

unset GITHUB_TOKEN

npm install --omit=dev
mkdir -p data data/rooms

if [[ ! -f .env ]]; then
  echo ">>> .env yok. Windows aktar-ubuntu.cmd veya nano $APP_DIR/.env"
fi

if [[ -f "$APP_DIR/scripts/deploy-ubuntu-nogit.sh" ]]; then
  bash "$APP_DIR/scripts/deploy-ubuntu-nogit.sh"
else
  echo "deploy-ubuntu-nogit.sh yok — repo tam clone oldu mu kontrol edin."
  exit 1
fi
