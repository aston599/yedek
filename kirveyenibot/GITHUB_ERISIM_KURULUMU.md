# 🔐 GitHub Erişim Kurulumu

## 📋 **YÖNTEM 1: Git Credential Helper (Önerilen)**

### **Sunucuda Çalıştır:**

```bash
cd /root/kirveyenibot

# Remote URL'i token olmadan ayarla
git remote set-url origin https://github.com/aston599/kirveyenibot.git

# Credential helper'ı ayarla
git config --global credential.helper store

# Token'ı kaydet (bir kere yapılır)
echo "https://[REDACTED_GITHUB_TOKEN]@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials

# Test et
git pull origin main
```

**Artık şifre sormayacak!** ✅

---

## 📋 **YÖNTEM 2: Environment Variable (Alternatif)**

### **Sunucuda Çalıştır:**

```bash
cd /root/kirveyenibot

# Remote URL'i token olmadan ayarla
git remote set-url origin https://github.com/aston599/kirveyenibot.git

# Token'ı environment variable olarak ayarla
export GIT_ASKPASS=echo
export GIT_USERNAME=[REDACTED_GITHUB_TOKEN]
export GIT_PASSWORD=[REDACTED_GITHUB_TOKEN]

# Veya .bashrc'ye ekle (kalıcı için)
echo 'export GIT_USERNAME=[REDACTED_GITHUB_TOKEN]' >> ~/.bashrc
echo 'export GIT_PASSWORD=[REDACTED_GITHUB_TOKEN]' >> ~/.bashrc
source ~/.bashrc

# Test et
git pull origin main
```

---

## 📋 **YÖNTEM 3: .git/config Dosyasını Düzenle (Manuel)**

### **Sunucuda Çalıştır:**

```bash
cd /root/kirveyenibot

# .git/config dosyasını düzenle
nano .git/config
```

**İçeriği şöyle değiştir:**
```ini
[remote "origin"]
    url = https://[REDACTED_GITHUB_TOKEN]@github.com/aston599/kirveyenibot.git
    fetch = +refs/heads/*:refs/remotes/origin/*
```

**Kaydet ve çık (Ctrl+X, Y, Enter)**

---

## 📋 **YÖNTEM 4: SSH Key (En Güvenli - Uzun Vadeli)**

### **Sunucuda Çalıştır:**

```bash
# SSH key oluştur
ssh-keygen -t ed25519 -C "kirvebot@server" -f ~/.ssh/github_key

# Public key'i göster
cat ~/.ssh/github_key.pub
```

**GitHub'a Ekle:**
1. GitHub → Settings → SSH and GPG keys
2. "New SSH key" butonuna tıkla
3. Public key'i yapıştır
4. Kaydet

**Git'i SSH kullanacak şekilde ayarla:**
```bash
cd /root/kirveyenibot
git remote set-url origin git@github.com:aston599/kirveyenibot.git

# SSH config dosyası oluştur
cat > ~/.ssh/config << EOF
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_key
    IdentitiesOnly yes
EOF

chmod 600 ~/.ssh/config
chmod 600 ~/.ssh/github_key

# Test et
ssh -T git@github.com
git pull origin main
```

---

## ✅ **ÖNERİLEN: YÖNTEM 1 (Credential Helper)**

**Neden?**
- ✅ Kolay kurulum
- ✅ Güvenli (dosya izinleri ile korunuyor)
- ✅ Otomatik çalışıyor
- ✅ Şifre sormuyor

**Kurulum:**
```bash
cd /root/kirveyenibot
git remote set-url origin https://github.com/aston599/kirveyenibot.git
git config --global credential.helper store
echo "https://[REDACTED_GITHUB_TOKEN]@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials
git pull origin main
```

---

## 🔒 **GÜVENLİK NOTLARI**

1. **Token'ı asla commit etme!**
2. **.git-credentials dosyasını .gitignore'a ekle**
3. **Dosya izinlerini kontrol et:** `chmod 600 ~/.git-credentials`
4. **Token süresi dolduğunda yenile**

---

## 🧪 **TEST**

```bash
# Pull test
git pull origin main

# Push test
git push origin main
```

Her iki komut da şifre sormadan çalışmalı! ✅

