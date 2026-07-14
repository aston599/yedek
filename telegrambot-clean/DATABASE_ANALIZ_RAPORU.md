# 🗄️ DATABASE ANALİZ RAPORU - KIRVEHUB BOT

**Tarih:** 2025-01-XX  
**Database:** Supabase PostgreSQL  
**Provider:** AWS EU Central 1 (Frankfurt)  
**Connection:** Pooler (Port 6543)

---

## 📋 İÇİNDEKİLER

1. [Database Bağlantısı](#database-bağlantısı)
2. [Tablolar](#tablolar)
3. [Veri Yapısı](#veri-yapısı)
4. [İlişkiler](#ilişkiler)
5. [Index'ler](#indexler)
6. [Güvenlik](#güvenlik)
7. [Veri Analizi](#veri-analizi)

---

## 🔗 DATABASE BAĞLANTISI

### Bağlantı Bilgileri:
- **Provider:** Supabase (PostgreSQL)
- **Region:** AWS EU Central 1 (Frankfurt)
- **Connection Pooler:** Port 6543
- **Database URL:** `postgresql://postgres.yfbyyuejqdwiomycksxg:Kirvebaba55!@aws-0-eu-central-1.pooler.supabase.com:6543/postgres`
- **Database Name:** postgres
- **Supabase URL:** `https://yfbyyuejqdwiomycksxg.supabase.co`

### Connection Pool Ayarları:
- **Min Size:** 1 connection
- **Max Size:** 3 connections (Supabase safe limit)
- **Command Timeout:** 5 saniye
- **Statement Cache Size:** 0 (PgBouncer için zorunlu)
- **Acquire Timeout:** 3 saniye

### Connection Pool Özellikleri:
- ✅ URL encoding desteği
- ✅ Connection retry mekanizması
- ✅ Automatic reconnection
- ✅ Health check
- ✅ Performance optimizasyonu

---

## 📊 TABLOLAR

### 1. **users** - Kullanıcı Bilgileri
```sql
- user_id (BIGINT PRIMARY KEY)
- username (VARCHAR(255))
- first_name (VARCHAR(255))
- last_name (VARCHAR(255))
- created_at (TIMESTAMP)
- last_activity (TIMESTAMP)
- is_registered (BOOLEAN)
- registration_date (TIMESTAMP)
- age (INTEGER)
- phone (VARCHAR(20))
- email (VARCHAR(255))
- interests (ARRAY)
- status (VARCHAR(50)) DEFAULT 'active'
- notes (TEXT)
- kirve_points (DECIMAL(10,2)) DEFAULT 0.00
- daily_points (DECIMAL(10,2)) DEFAULT 0.00
- last_point_date (DATE)
- total_messages (INTEGER) DEFAULT 0
- rank_id (INTEGER) DEFAULT 1
```

**Index'ler:**
- PRIMARY KEY (user_id)

**İlişkiler:**
- user_ranks (rank_id) → user_ranks(rank_id)
- daily_stats (user_id) → users(user_id) ON DELETE CASCADE
- balance_logs (user_id) → users(user_id) ON DELETE CASCADE
- event_participants (user_id) → users(user_id) ON DELETE CASCADE
- market_orders (user_id) → users(user_id) ON DELETE CASCADE

---

### 2. **registered_groups** - Grup Bilgileri
```sql
- group_id (BIGINT PRIMARY KEY)
- group_name (VARCHAR(200))
- group_username (VARCHAR(100))
- registered_by (BIGINT)
- registration_date (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
- is_active (BOOLEAN) DEFAULT TRUE
- point_multiplier (DECIMAL(3,2)) DEFAULT 1.00
- unregistered_at (TIMESTAMP)
```

**Index'ler:**
- PRIMARY KEY (group_id)

**İlişkiler:**
- daily_stats (group_id) → registered_groups(group_id)

---

### 3. **daily_stats** - Günlük İstatistikler
```sql
- id (SERIAL PRIMARY KEY)
- user_id (BIGINT NOT NULL)
- group_id (BIGINT NOT NULL)
- message_date (DATE NOT NULL)
- message_count (INTEGER) DEFAULT 0
- points_earned (DECIMAL(10,2)) DEFAULT 0.00
- character_count (INTEGER) DEFAULT 0
- created_at (TIMESTAMP) DEFAULT NOW()
```

**Index'ler:**
- PRIMARY KEY (id)
- UNIQUE (user_id, group_id, message_date)
- INDEX (user_id, message_date)
- INDEX (group_id, message_date)

**İlişkiler:**
- user_id → users(user_id) ON DELETE CASCADE
- group_id → registered_groups(group_id)

---

### 4. **events** - Etkinlikler
```sql
- id (SERIAL PRIMARY KEY)
- event_type (VARCHAR(50)) NOT NULL
- title (VARCHAR(255)) NOT NULL
- description (TEXT)
- entry_cost (DECIMAL(10,2)) DEFAULT 0.00
- max_winners (INTEGER) DEFAULT 1
- duration_minutes (INTEGER) DEFAULT 0
- bonus_multiplier (DECIMAL(5,2)) DEFAULT 1.00
- status (VARCHAR(20)) DEFAULT 'active'
- created_by (BIGINT) NOT NULL
- created_at (TIMESTAMP) DEFAULT NOW()
- ended_at (TIMESTAMP)
- participants (JSONB) DEFAULT '[]'
- winners (JSONB) DEFAULT '[]'
- group_id (BIGINT) DEFAULT 0
- completed_at (TIMESTAMP)
- completed_by (BIGINT)
- message_id (BIGINT)
```

**Index'ler:**
- PRIMARY KEY (id)
- INDEX (group_id)
- INDEX (created_by)

**İlişkiler:**
- created_by → users(user_id)
- completed_by → users(user_id)
- event_participants (event_id) → events(id) ON DELETE CASCADE

---

### 5. **event_participants** - Etkinlik Katılımcıları
```sql
- id (SERIAL PRIMARY KEY)
- event_id (INTEGER)
- user_id (BIGINT) NOT NULL
- joined_at (TIMESTAMP) DEFAULT NOW()
- withdrew_at (TIMESTAMP)
- payment_amount (DECIMAL(10,2)) DEFAULT 0.00
- status (VARCHAR(20)) DEFAULT 'active'
- is_winner (BOOLEAN) DEFAULT FALSE
```

**Index'ler:**
- PRIMARY KEY (id)
- UNIQUE (event_id, user_id)
- INDEX (event_id)
- INDEX (user_id)

**İlişkiler:**
- event_id → events(id) ON DELETE CASCADE
- user_id → users(user_id) ON DELETE CASCADE

---

### 6. **market_categories** - Market Kategorileri
```sql
- id (SERIAL PRIMARY KEY)
- name (VARCHAR(100)) NOT NULL UNIQUE
- description (TEXT)
- icon (VARCHAR(50)) DEFAULT '📦'
- display_order (INTEGER) DEFAULT 0
- is_active (BOOLEAN) DEFAULT TRUE
- created_at (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
- updated_at (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
- emoji (VARCHAR(10))
```

**Index'ler:**
- PRIMARY KEY (id)
- UNIQUE (name)

**Kategoriler:**
1. Site Bakiyeleri (💰)
2. Freespinler (🎰)
3. Oyun Hediye Kartları (🎮)
4. Oyun İçi Para (🎯)
5. Mobil Hediye Kartları (📱)
6. Dijital Ürünler (🎁)
7. Abonelikler (📺)
8. Gamer Ekipmanları (🎮)
9. Teknoloji Ürünleri (📱)

---

### 7. **market_products** - Market Ürünleri
```sql
- id (SERIAL PRIMARY KEY)
- name (VARCHAR(200)) NOT NULL
- description (TEXT)
- company_name (VARCHAR(100))
- category_id (INTEGER)
- price (DECIMAL(10,2)) NOT NULL
- original_price (DECIMAL(10,2))
- stock (INTEGER) DEFAULT 0
- sold_count (INTEGER) DEFAULT 0
- image_url (TEXT)
- is_active (BOOLEAN) DEFAULT TRUE
- is_featured (BOOLEAN) DEFAULT FALSE
- auto_delivery (BOOLEAN) DEFAULT FALSE
- delivery_content (TEXT)
- min_stock_alert (INTEGER) DEFAULT 5
- created_by (BIGINT)
- created_at (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
- updated_at (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
- site_link (VARCHAR(500))
- site_name (VARCHAR(255))
- site_requirement (VARCHAR(100))
- external_link (VARCHAR(500))
```

**Index'ler:**
- PRIMARY KEY (id)
- INDEX (category_id)

**İlişkiler:**
- category_id → market_categories(id)
- market_orders (product_id) → market_products(id) ON DELETE CASCADE

**Toplam Ürün:** ~110+ ürün

---

### 8. **market_orders** - Market Siparişleri
```sql
- id (SERIAL PRIMARY KEY)
- order_number (VARCHAR(20)) NOT NULL UNIQUE
- user_id (BIGINT)
- product_id (INTEGER)
- quantity (INTEGER) DEFAULT 1
- total_price (DECIMAL(10,2)) NOT NULL
- status (VARCHAR(20)) DEFAULT 'pending'
- payment_status (VARCHAR(20)) DEFAULT 'paid'
- admin_notes (TEXT)
- delivery_content (TEXT)
- user_notes (TEXT)
- approved_by (INTEGER)
- approved_at (TIMESTAMP)
- delivered_at (TIMESTAMP)
- cancelled_at (TIMESTAMP)
- created_at (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
- updated_at (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
- site_username (VARCHAR(255))
```

**Index'ler:**
- PRIMARY KEY (id)
- UNIQUE (order_number)
- INDEX (user_id)
- INDEX (status)
- INDEX (site_username) WHERE site_username IS NOT NULL

**İlişkiler:**
- user_id → users(user_id) ON DELETE CASCADE
- product_id → market_products(id) ON DELETE CASCADE
- market_order_logs (order_id) → market_orders(id)

**Status Değerleri:**
- pending
- approved
- rejected
- delivered

---

### 9. **market_order_logs** - Sipariş Logları
```sql
- id (SERIAL PRIMARY KEY)
- order_id (INTEGER)
- old_status (VARCHAR(20))
- new_status (VARCHAR(20))
- admin_id (BIGINT)
- notes (TEXT)
- created_at (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
```

**İlişkiler:**
- order_id → market_orders(id)

---

### 10. **custom_commands** - Dinamik Komutlar
```sql
- id (SERIAL PRIMARY KEY)
- command_name (VARCHAR(64)) NOT NULL UNIQUE
- scope (SMALLINT) NOT NULL
- reply_text (TEXT) NOT NULL
- button_text (VARCHAR(128))
- button_url (VARCHAR(256))
- created_by (BIGINT) NOT NULL
- created_at (TIMESTAMP) DEFAULT NOW()
```

**Index'ler:**
- PRIMARY KEY (id)
- UNIQUE (command_name)
- INDEX (scope)

**Scope Değerleri:**
- 1: Private only
- 2: Group only
- 3: Both

---

### 11. **user_ranks** - Kullanıcı Rütbeleri
```sql
- rank_id (SERIAL PRIMARY KEY)
- rank_name (VARCHAR(50)) UNIQUE
- rank_level (INTEGER)
- min_points (DECIMAL(10,2)) DEFAULT 0.00
- max_points (DECIMAL(10,2))
- permissions (ARRAY)
- created_date (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
```

**Index'ler:**
- PRIMARY KEY (rank_id)
- UNIQUE (rank_name)
- UNIQUE (rank_level)

**Varsayılan Rütbeler:**
1. Üye (rank_id: 1)
2. Admin 1 (rank_id: 2)
3. Üst Yetkili - Admin 2 (rank_id: 3)
4. Super Admin (rank_id: 4)

---

### 12. **point_settings** - Point Ayarları
```sql
- setting_key (VARCHAR(50)) PRIMARY KEY
- setting_value (DECIMAL(10,2))
- description (TEXT)
- updated_by (BIGINT)
- updated_at (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
```

**Varsayılan Ayarlar:**
- daily_limit: 5.00 (Günlük maksimum kazanılabilir point)
- point_per_message: 0.04 (Mesaj başına kazanılan point)
- min_message_length: 5 (Point kazanmak için minimum mesaj uzunluğu)
- flood_interval: 10 (Mesajlar arası minimum saniye)

---

### 13. **system_settings** - Sistem Ayarları
```sql
- id (SERIAL PRIMARY KEY)
- points_per_message (DECIMAL(5,2)) DEFAULT 0.04
- daily_limit (DECIMAL(5,2)) DEFAULT 5.00
- weekly_limit (DECIMAL(5,2)) DEFAULT 20.00
- created_at (TIMESTAMP) DEFAULT NOW()
- updated_at (TIMESTAMP) DEFAULT NOW()
```

---

### 14. **balance_logs** - Bakiye Logları
```sql
- id (SERIAL PRIMARY KEY)
- user_id (BIGINT) NOT NULL
- admin_id (BIGINT) NOT NULL
- action (VARCHAR(10)) NOT NULL
- amount (DECIMAL(10,2)) NOT NULL
- reason (TEXT)
- created_at (TIMESTAMP) DEFAULT NOW()
```

**İlişkiler:**
- user_id → users(user_id) ON DELETE CASCADE

**Action Değerleri:**
- add: Bakiye eklendi
- remove: Bakiye çıkarıldı

---

### 15. **sites** - Bahis Siteleri
```sql
- id (SERIAL PRIMARY KEY)
- name (VARCHAR(100)) NOT NULL
- url (VARCHAR(500))
- description (TEXT)
- is_active (BOOLEAN) DEFAULT TRUE
- display_order (INTEGER) DEFAULT 0
- site_username (VARCHAR(255))
```

**Siteler:**
- Merso Bahis
- AMG Bahis
- vb.

---

### 16. **scheduled_messages_settings** - Zamanlanmış Mesajlar
```sql
- id (INTEGER) PRIMARY KEY DEFAULT 1
- settings (JSONB) NOT NULL DEFAULT '{}'
- created_at (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
- updated_at (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
```

---

### 17. **system_logs** - Sistem Logları
```sql
- id (SERIAL PRIMARY KEY)
- log_level (VARCHAR(10)) NOT NULL
- module (VARCHAR(50))
- message (TEXT) NOT NULL
- user_id (BIGINT)
- created_at (TIMESTAMP) DEFAULT NOW()
```

**Index'ler:**
- PRIMARY KEY (id)
- INDEX (log_level)
- INDEX (created_at)

---

### 18. **bot_status** - Bot Durumu
```sql
- id (SERIAL PRIMARY KEY)
- status (VARCHAR(255)) NOT NULL
- message (TEXT)
- created_at (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
```

---

### 19. **recruitment_daily_limits** - Kayıt Günlük Limitleri
```sql
- id (SERIAL PRIMARY KEY)
- user_id (BIGINT) NOT NULL
- recruitment_date (DATE) NOT NULL
- created_at (TIMESTAMP) DEFAULT NOW()
```

**Index'ler:**
- PRIMARY KEY (id)
- UNIQUE (user_id, recruitment_date)

---

### 20. **recruitment_settings** - Kayıt Ayarları
```sql
- setting_key (VARCHAR(50)) PRIMARY KEY
- setting_value (TEXT)
- description (TEXT)
- updated_by (BIGINT)
- updated_date (TIMESTAMP) DEFAULT CURRENT_TIMESTAMP
```

---

### 21. **warnings** - Uyarılar
```sql
- id (SERIAL PRIMARY KEY)
- user_id (BIGINT) NOT NULL
- group_id (BIGINT)
- warning_count (INTEGER) DEFAULT 1
- reason (TEXT)
- warned_by (BIGINT)
- created_at (TIMESTAMP) DEFAULT NOW()
```

**İlişkiler:**
- user_id → users(user_id)
- group_id → registered_groups(group_id)
- warned_by → users(user_id)

---

### 22. **punishment_logs** - Cezalandırma Logları
```sql
- id (SERIAL PRIMARY KEY)
- user_id (BIGINT) NOT NULL
- group_id (BIGINT)
- punishment_type (VARCHAR(50)) NOT NULL
- duration (INTEGER)
- reason (TEXT)
- punished_by (BIGINT)
- created_at (TIMESTAMP) DEFAULT NOW()
```

**İlişkiler:**
- user_id → users(user_id)
- group_id → registered_groups(group_id)
- punished_by → users(user_id)

**Punishment Types:**
- mute
- ban
- kick
- warning

---

## 🔗 İLİŞKİLER

### Ana İlişkiler:
1. **users** → **user_ranks** (rank_id)
2. **users** → **daily_stats** (user_id)
3. **users** → **balance_logs** (user_id)
4. **users** → **event_participants** (user_id)
5. **users** → **market_orders** (user_id)
6. **registered_groups** → **daily_stats** (group_id)
7. **events** → **event_participants** (event_id)
8. **market_categories** → **market_products** (category_id)
9. **market_products** → **market_orders** (product_id)
10. **market_orders** → **market_order_logs** (order_id)

---

## 📊 INDEX'LER

### Performans İyileştirmeleri:
- ✅ Primary key index'ler
- ✅ Foreign key index'ler
- ✅ Unique constraint index'ler
- ✅ Composite index'ler (user_id, group_id, message_date)
- ✅ Conditional index'ler (site_username WHERE IS NOT NULL)

---

## 🔒 GÜVENLİK

### Row Level Security (RLS):
- ✅ RLS aktif (tüm tablolarda)
- ✅ Supabase güvenlik politikaları
- ✅ Connection pooling güvenliği
- ✅ SQL injection koruması

### Güvenlik Özellikleri:
- ✅ Prepared statements
- ✅ Parameterized queries
- ✅ Connection encryption
- ✅ Access control
- ✅ Audit logging

---

## 📈 VERİ ANALİZİ

### Tahmini Veri Miktarı:
- **Users:** ~1000+ kullanıcı
- **Groups:** ~10+ grup
- **Products:** ~110+ ürün
- **Orders:** ~500+ sipariş
- **Events:** ~50+ etkinlik
- **Daily Stats:** ~10000+ kayıt

### Veri Büyümesi:
- **Daily Stats:** Günlük ~1000+ kayıt
- **System Logs:** Günlük ~500+ log
- **Balance Logs:** Günlük ~50+ işlem

---

## 🎯 ÖNERİLER

### Performans:
1. ✅ Index'ler optimize edilmiş
2. ⚠️ Connection pool size artırılabilir (şu an 3)
3. ⚠️ Query optimization yapılabilir
4. ⚠️ Caching mekanizması eklenebilir

### Güvenlik:
1. ✅ RLS aktif
2. ✅ Connection encryption
3. ⚠️ Backup stratejisi oluşturulmalı
4. ⚠️ Disaster recovery planı hazırlanmalı

### Veri Yönetimi:
1. ✅ Tablolar normalize edilmiş
2. ✅ Foreign key constraint'ler var
3. ⚠️ Archiving stratejisi (eski loglar için)
4. ⚠️ Data retention policy

---

## 📊 SONUÇ

**Database Durumu:** ✅ Sağlıklı ve Çalışır Durumda

**Güçlü Yönler:**
- ✅ Modüler tablo yapısı
- ✅ İyi normalize edilmiş
- ✅ Index'ler optimize edilmiş
- ✅ RLS aktif
- ✅ Connection pooling

**İyileştirme Alanları:**
- ⚠️ Connection pool size artırılabilir
- ⚠️ Backup stratejisi
- ⚠️ Caching mekanizması
- ⚠️ Query optimization

---

**Rapor Oluşturulma Tarihi:** 2025-01-XX  
**Database Versiyonu:** PostgreSQL (Supabase)  
**Durum:** ✅ Çalışır Durumda


