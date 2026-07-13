#!/bin/bash
# Sunucuda: bash /opt/bulmaca777/scripts/post-deploy-check.sh
set -euo pipefail
BASE="${1:-http://127.0.0.1:3847}"

echo "==> health"
curl -sf "${BASE}/api/health" | head -c 400
echo ""

echo "==> celebrity overlay"
code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/celebrity-overlay?room=_check")
echo "HTTP ${code} (beklenen 200)"

echo "==> celebrity sample API"
code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}/api/celebrity-sample/preview")
echo "HTTP ${code} (beklenen 200)"

echo "==> systemd"
systemctl is-active bulmaca777 || true
