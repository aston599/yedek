# Canlıya yükleme (bulmaca777.com)

Sunucu: **164.90.163.55** · uygulama: `/opt/bulmaca777` · servis: `bulmaca777`

## GitHub → canlı (önerilen)

Yerelde push:

```powershell
git add -A
git commit -m "aciklama"
git push origin main
```

Sunucuda (SSH):

```bash
cd /opt/bulmaca777
git pull origin main
npm install --omit=dev
bash scripts/patch-production-env.sh
systemctl restart bulmaca777
bash scripts/post-deploy-check.sh
```

Repo: https://github.com/aston599/bulmaca777

## SCP yolu (Windows — alternatif)

Proje klasöründe çift tıklayın veya PowerShell:

```powershell
cd C:\Users\gamin\OneDrive\Desktop\youtubproject
.\aktar-proje-ubuntu.cmd
```

SSH şifresi sorulur (DigitalOcean droplet root). İşlem bitince kontrol:

- https://bulmaca777.com/api/health
- https://bulmaca777.com/celebrity-overlay?room=ODA_ID
- https://bulmaca777.com/admin/

`.env` yerelde varsa sunucuya gider; ardından canlı için `PUBLIC_URL`, `CHAT_MODE`, `COOKIE_SECURE` otomatik düzeltilir.

## Sadece .env güncelleme

```powershell
.\aktar-ubuntu.cmd
```

## Git ile (repo güncel ve sunucuda git varsa)

Sunucuda:

```bash
cd /opt/bulmaca777
git pull origin main
npm install --omit=dev
chown -R www-data:www-data /opt/bulmaca777
systemctl restart bulmaca777
curl -s http://127.0.0.1:3847/api/health
```

## Canlı .env (sunucu)

```bash
nano /opt/bulmaca777/.env
systemctl restart bulmaca777
```

Örnek: `.env.production.example` — özellikle `CHAT_MODE=youtube`, `PUBLIC_URL=https://bulmaca777.com`, Google OAuth.

## Sorun giderme

| Belirti | Çözüm |
|--------|--------|
| `celebrity-overlay` 404 | Kod eski — `aktar-proje-ubuntu.cmd` tekrar |
| Sohbet mock | `.env` → `CHAT_MODE=youtube`, restart |
| Panel giriş yok | HTTPS + `COOKIE_SECURE=true` |
| SSH bağlanmıyor | DO panel → droplet IP, firewall 22 |
