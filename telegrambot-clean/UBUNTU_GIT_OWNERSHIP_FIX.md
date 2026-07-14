# Ubuntu Git Ownership Hatası Çözümü

## Hata
```
fatal: detected dubious ownership in repository at '/home/kirvehub/telegrambot-clean'
```

## Çözüm

### 1. Git'e dizini güvenli olarak ekle
```bash
git config --global --add safe.directory /home/kirvehub/telegrambot-clean
```

### 2. Şimdi git pull yap
```bash
git pull origin main
```

### 3. Tüm işlemleri tamamla
```bash
pip install -r requirements.txt
sudo systemctl restart kirvehub-bot-clean
sudo systemctl status kirvehub-bot-clean
```

---

## Tek Komutla Tüm İşlemler
```bash
git config --global --add safe.directory /home/kirvehub/telegrambot-clean && \
git pull origin main && \
pip install -r requirements.txt && \
sudo systemctl restart kirvehub-bot-clean && \
sudo systemctl status kirvehub-bot-clean
```

---

## Alternatif Çözüm (Dizin Sahipliğini Değiştir)

Eğer yukarıdaki çözüm işe yaramazsa:

```bash
chown -R root:root /home/kirvehub/telegrambot-clean
```

**Not:** Bu komut dizinin sahibini root yapar. Eğer bot kirvehub kullanıcısı olarak çalışıyorsa, bu çözümü kullanmayın.

