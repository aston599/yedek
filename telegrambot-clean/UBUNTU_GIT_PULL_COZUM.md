# 🔧 Ubuntu Git Pull Sorunu Çözümü

## Sorun
```
error: Your local changes to the following files would be overwritten by merge:
        main.py
Please commit your changes or stash them before you merge.
```

## Çözüm 1: Local Değişiklikleri Kaydetmeden Çek (Önerilen)

```bash
cd ~/telegrambot
git stash
git pull origin main
git stash pop
```

## Çözüm 2: Local Değişiklikleri Tamamen Sil (Dikkatli!)

```bash
cd ~/telegrambot
git reset --hard origin/main
git pull origin main
```

## Çözüm 3: Local Değişiklikleri Commit Et

```bash
cd ~/telegrambot
git add main.py
git commit -m "Local changes before pull"
git pull origin main
```

## Önerilen Komut (Güvenli)

```bash
cd ~/telegrambot && git stash && git pull origin main && git stash pop
```

Eğer conflict olursa:
```bash
git stash list
git stash show -p
# Eğer gerekli değişiklikler varsa manuel birleştir
```


