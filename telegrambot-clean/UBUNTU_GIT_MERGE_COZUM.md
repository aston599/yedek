# 🔧 Ubuntu Git Merge Çözümü

## Durum
- ✅ Git pull başarılı
- ⚠️ main.py'de local değişiklikler var (conflict)
- 📁 Backup dosyaları var (main.py.backup, main.py.backup.1763082270)

## Çözüm Seçenekleri

### Seçenek 1: GitHub'daki Versiyonu Kullan (Önerilen)
```bash
cd ~/telegrambot
git checkout --theirs main.py
git add main.py
git status
```

### Seçenek 2: Local Değişiklikleri Koru
```bash
cd ~/telegrambot
git checkout --ours main.py
git add main.py
git status
```

### Seçenek 3: Manuel Merge (Eğer her iki tarafın değişiklikleri önemliyse)
```bash
cd ~/telegrambot
# Değişiklikleri gör
git diff main.py
# Manuel düzenle
nano main.py
git add main.py
```

## Backup Dosyalarını Temizle
```bash
cd ~/telegrambot
rm -f main.py.backup*
```

## Önerilen Komut Dizisi
```bash
cd ~/telegrambot
git checkout --theirs main.py
rm -f main.py.backup*
git status
```


