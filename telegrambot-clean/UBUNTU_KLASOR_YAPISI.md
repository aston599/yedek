# 📁 Ubuntu Sunucu Klasör Yapısı Komutları

## Hızlı Klasör Yapısı Görüntüleme

### 1. Tree Komutu (En İyi - Eğer yüklüyse)
```bash
# Tree kurulumu (eğer yoksa)
sudo apt install tree -y

# Bot dizinindeki tüm yapıyı göster
cd ~/telegrambot
tree -L 3 -I '__pycache__|*.pyc|venv|.git' > klasor_yapisi.txt
cat klasor_yapisi.txt
```

### 2. Find Komutu (Her Zaman Mevcut)
```bash
cd ~/telegrambot
find . -type d -not -path '*/\.*' -not -path '*/__pycache__*' -not -path '*/venv/*' | head -50
```

### 3. Detaylı Yapı (Dosya ve Klasörler)
```bash
cd ~/telegrambot
find . -maxdepth 3 -not -path '*/\.*' -not -path '*/__pycache__*' -not -path '*/venv/*' | sort > klasor_yapisi_detayli.txt
cat klasor_yapisi_detayli.txt
```

### 4. ls Komutu ile Hiyerarşik Görünüm
```bash
cd ~/telegrambot
ls -R | grep ":$" | sed -e 's/:$//' -e 's/[^-][^\/]*\//--/g' -e 's/^/   /' -e 's/-/|/'
```

## Önerilen Komut (En Detaylı)

```bash
cd ~/telegrambot && find . -type f -o -type d | grep -v "__pycache__" | grep -v "\.pyc" | grep -v "venv" | grep -v "\.git" | sort | head -100
```

## Sadece Klasörler (Dizinler)

```bash
cd ~/telegrambot
find . -type d -not -path '*/\.*' -not -path '*/__pycache__*' -not -path '*/venv/*' -not -path '*/.git/*' | sort
```

## Sadece Python Dosyaları

```bash
cd ~/telegrambot
find . -name "*.py" -not -path "*/venv/*" -not -path "*/.git/*" | sort
```

## Tüm Dosya Türleri

```bash
cd ~/telegrambot
find . -type f -not -path "*/venv/*" -not -path "*/.git/*" -not -path "*/__pycache__/*" | head -50
```

## Sistem Bilgileri ile Birlikte

```bash
cd ~/telegrambot
echo "=== KLASÖR YAPISI ===" > sunucu_bilgileri.txt
tree -L 2 -I '__pycache__|*.pyc|venv|.git' >> sunucu_bilgileri.txt 2>/dev/null || find . -maxdepth 2 -type d | sort >> sunucu_bilgileri.txt
echo "" >> sunucu_bilgileri.txt
echo "=== PYTHON DOSYALARI ===" >> sunucu_bilgileri.txt
find . -name "*.py" -not -path "*/venv/*" | wc -l >> sunucu_bilgileri.txt
echo "" >> sunucu_bilgileri.txt
echo "=== DİZİN BOYUTLARI ===" >> sunucu_bilgileri.txt
du -sh */ 2>/dev/null | sort -h >> sunucu_bilgileri.txt
cat sunucu_bilgileri.txt
```


