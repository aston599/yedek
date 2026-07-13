#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/roytelegram"
SERVICE="roytelegram"
REPO="https://github.com/aston599/roytelegram.git"

if [[ -z "${BOT_TOKEN:-}" ]]; then
  echo "HATA: BOT_TOKEN gerekli. Ornek:"
  echo "  BOT_TOKEN='xxx' bash install.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git ca-certificates

# Düşük RAM droplet'lerde OOM önlemek için 1GB swap
if [[ ! -f /swapfile ]]; then
  echo "Swap alanı oluşturuluyor (1GB)..."
  fallocate -l 1G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=1024 status=progress
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

CLONE_URL="$REPO"
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  CLONE_URL="https://aston599:${GITHUB_TOKEN}@github.com/aston599/roytelegram.git"
fi

if [[ -d "$APP_DIR/.git" ]]; then
  cd "$APP_DIR"
  git fetch --all
  git reset --hard origin/main 2>/dev/null || git reset --hard origin/master
else
  rm -rf "$APP_DIR"
  git clone "$CLONE_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q
mkdir -p data

cat > .env <<EOF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_IDS=${ADMIN_IDS:-}
SETUP_SECRET=${SETUP_SECRET:-betroy-setup-2026}
DATABASE_PATH=data/bot.db
SYNC_PROFILE_PHOTOS=0
EOF
chmod 600 .env

install -m 644 deploy/roytelegram.service /etc/systemd/system/${SERVICE}.service
systemctl daemon-reload
systemctl enable "${SERVICE}"
systemctl restart "${SERVICE}"

echo ""
echo "Kurulum tamam. Durum:"
systemctl status "${SERVICE}" --no-pager -l | head -n 15
