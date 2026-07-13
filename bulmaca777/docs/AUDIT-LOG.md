# Denetim günlüğü (AUDIT_LOG)

Teknik olaylar: API, YouTube/InnerChat, sohbet, config, disk kayıtları.

## Panel

Admin → **Denetim günlüğü (teknik)** — canlı socket + son 150 kayıt.

## Sunucu (SSH)

```bash
journalctl -u bulmaca777 -f | grep "\[Audit\]"
```

## .env

```env
AUDIT_LOG=1
AUDIT_LOG_PERSIST=1
AUDIT_LOG_CONSOLE=1
INNER_CHAT_DEBUG=1
```

Değişiklikten sonra: `systemctl restart bulmaca777`

## API (giriş gerekli)

- `GET /api/rooms/{oda}/audit-log?limit=150&category=youtube`
- `POST /api/rooms/{oda}/audit-log/clear`
