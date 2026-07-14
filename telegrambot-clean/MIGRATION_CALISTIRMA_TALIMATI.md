# 🔄 Kirve Point Migration - Çalıştırma Talimatları

## 📋 Migration Yapacaklar

1. **Kullanıcı bakiyeleri endekslenecek** (3.0x - 5.0x multiplier)
2. **Sistem ayarları güncellenecek:**
   - Mesaj başına: 0.04 → 0.20 KP (5x artış)
   - Günlük limit: 5.0 → 200.0 KP (40x artış)
   - Haftalık limit: 20.0 → 1000.0 KP (50x artış)
3. **Backup tabloları oluşturulacak**

---

## 🚀 Çalıştırma Komutları

### Windows PowerShell'de:

```powershell
# 1. Proje dizinine git
cd "C:\Users\PC\Desktop\Yeni klasör (7)\telegrambot-main"

# 2. Migration script'ini çalıştır
py run_migration_final.py
```

### Alternatif (eğer yukarıdaki çalışmazsa):

```powershell
# 1. Proje dizinine git
cd "C:\Users\PC\Desktop\Yeni klasör (7)\telegrambot-main"

# 2. Python ile doğrudan çalıştır
python run_migration_final.py
```

### VEYA execute_migration_direct.py ile:

```powershell
# 1. Proje dizinine git
cd "C:\Users\PC\Desktop\Yeni klasör (7)\telegrambot-main"

# 2. Migration script'ini çalıştır
py execute_migration_direct.py
```

---

## ✅ Migration Sonrası Kontrol

Migration başarılı olduysa şunları göreceksiniz:

```
============================================================
🔄 KIRVE POINT MIGRATION BAŞLATILIYOR...
============================================================
📁 Workspace: C:\Users\PC\Desktop\Yeni klasör (7)\telegrambot-main
📄 Script okunuyor: ...
⚙️ Migration çalıştırılıyor...
⚠️  DİKKAT: Bu işlem kullanıcı bakiyelerini değiştirecek!
✅ Migration tamamlandı!
📊 Toplam kullanıcı: 2220
⚙️ Sistem ayarları:
   - Mesaj başına: 0.20 KP
   - Günlük limit: 200.0 KP
   - Haftalık limit: 1000.0 KP
✅ Backup tablosu oluşturuldu: 2220 kayıt
============================================================
✅ MIGRATION BAŞARILI!
============================================================
```

---

## 🔄 Rollback (Geri Alma)

Eğer bir sorun olursa, rollback script'ini çalıştırabilirsiniz:

```powershell
# PostgreSQL client ile
psql -h aws-0-eu-central-1.pooler.supabase.com -p 6543 -U postgres.yfbyyuejqdwiomycksxg -d postgres -f database/rollback_kirve_point_gecis.sql
```

---

## 📝 Notlar

- Migration transaction içinde çalışır (BEGIN/COMMIT)
- Hata olursa otomatik rollback yapılır
- Backup tabloları: `users_backup_kirve_point_migration` ve `system_settings_backup_kirve_point_migration`
- Migration logları: `migration_logs` tablosunda

---

**Hazırlayan:** AI Assistant  
**Tarih:** 2025-01-15

