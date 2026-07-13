#!/bin/bash
# Canli sunucuda .env uretim ayarlari (Google anahtarlarina dokunmaz)
set -euo pipefail
ENV="${1:-/opt/bulmaca777/.env}"
APP_DIR="$(dirname "$ENV")"

if [[ ! -f "$ENV" ]]; then
  if [[ -f "$APP_DIR/.env.example" ]]; then
    cp "$APP_DIR/.env.example" "$ENV"
  else
    echo "HATA: $ENV yok" >&2
    exit 1
  fi
fi

set_kv() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "$ENV" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV"
  else
    echo "${key}=${val}" >> "$ENV"
  fi
}

set_kv PUBLIC_URL "https://bulmaca777.com"
set_kv GOOGLE_REDIRECT_URI "https://bulmaca777.com/auth/callback"
set_kv CHAT_MODE "youtube"
set_kv NODE_ENV "production"
set_kv COOKIE_SECURE "true"
set_kv HOST "0.0.0.0"
grep -q '^PORT=' "$ENV" || echo 'PORT=3847' >> "$ENV"

chown www-data:www-data "$ENV" 2>/dev/null || true
echo "OK: $ENV guncellendi (CHAT_MODE=youtube, PUBLIC_URL=https://bulmaca777.com)"
