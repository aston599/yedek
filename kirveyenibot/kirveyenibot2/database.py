import sqlite3
from datetime import datetime
from config import DATABASE_PATH

def init_db():
    """Veritabanini baslat"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Ana grup tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS main_groups (
            group_id INTEGER PRIMARY KEY,
            group_name TEXT,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Basvuru tablosu - hem Merso hem AMG için
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            merso_username TEXT,
            merso_screenshot TEXT,
            amg_username TEXT,
            amg_screenshot TEXT,
            status TEXT DEFAULT 'pending',
            application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_date TIMESTAMP
        )
    ''')
    
    # Yapılandırma tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Admin tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            added_by INTEGER
        )
    ''')
    
    # Ban tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            reason TEXT,
            banned_by INTEGER,
            banned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Başvuru notları tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS application_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER,
            note TEXT,
            added_by INTEGER,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES applications(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_main_group(group_id, group_name):
    """Ana grup ekle"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO main_groups (group_id, group_name)
        VALUES (?, ?)
    ''', (group_id, group_name))
    
    conn.commit()
    conn.close()

def add_application(user_id, username, merso_username, merso_screenshot, amg_username, amg_screenshot, bot_source='bot2'):
    """Basvuru ekle - her iki site için"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO applications 
        (user_id, username, merso_username, merso_screenshot, amg_username, amg_screenshot, bot_source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, merso_username, merso_screenshot, amg_username, amg_screenshot, bot_source))
    
    application_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return application_id

def get_application(application_id):
    """Basvuru getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM applications WHERE id = ?', (application_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result

def update_application_status(application_id, status):
    """Basvuru durumunu guncelle"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Eğer onaylanıyorsa, onay tarihini de kaydet
    if status == 'approved':
        cursor.execute('''
            UPDATE applications 
            SET status = ?, approved_date = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (status, application_id))
    else:
        cursor.execute('UPDATE applications SET status = ? WHERE id = ?', 
                      (status, application_id))
    
    conn.commit()
    conn.close()

def get_pending_applications():
    """Bekleyen basvurulari getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM applications WHERE status = "pending"')
    results = cursor.fetchall()
    
    conn.close()
    return results

def get_approved_applications():
    """Onaylanan basvurulari getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM applications WHERE status = "approved"')
    results = cursor.fetchall()
    
    conn.close()
    return results

def get_config(key):
    """Yapılandırma değeri getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def set_config(key, value):
    """Yapılandırma değeri ayarla"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO config (key, value)
        VALUES (?, ?)
    ''', (key, value))
    
    conn.commit()
    conn.close()

def check_user_has_application(user_id):
    """Kullanıcının bekleyen veya onaylı başvurusu var mı kontrol et"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM applications 
        WHERE user_id = ? AND status IN ('pending', 'approved')
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def add_admin(user_id, username, added_by):
    """Yeni admin ekle"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO admins (user_id, username, added_by)
            VALUES (?, ?, ?)
        ''', (user_id, username, added_by))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Zaten admin
    finally:
        conn.close()

def remove_admin(user_id):
    """Admin yetkisini kaldır"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    return deleted

def is_admin(user_id):
    """Kullanıcı admin mi kontrol et"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM admins WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result is not None

def get_all_admin_ids():
    """Tüm admin ID'lerini getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM admins')
    admin_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Ana admin ID'sini de ekle
    from config import ADMIN_USER_ID
    if ADMIN_USER_ID not in admin_ids:
        admin_ids.append(ADMIN_USER_ID)
    
    return admin_ids

def get_all_admins():
    """Tüm adminleri getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, username, added_date, added_by 
        FROM admins 
        ORDER BY added_date ASC
    ''')
    
    admins = cursor.fetchall()
    conn.close()
    
    return admins

def ban_user(user_id, username, reason, banned_by):
    """Kullanıcıyı engelle"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO banned_users (user_id, username, reason, banned_by)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, reason, banned_by))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Zaten engellenmiş
    finally:
        conn.close()

def unban_user(user_id):
    """Kullanıcının engelini kaldır"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    return deleted

def is_user_banned(user_id):
    """Kullanıcı engellenmiş mi kontrol et"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM banned_users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result is not None

def get_banned_users():
    """Tüm engellenmiş kullanıcıları getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, username, reason, banned_by, banned_date 
        FROM banned_users 
        ORDER BY banned_date DESC
    ''')
    
    banned = cursor.fetchall()
    conn.close()
    
    return banned

def add_application_note(application_id, note, added_by):
    """Başvuruya not ekle"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO application_notes (application_id, note, added_by)
        VALUES (?, ?, ?)
    ''', (application_id, note, added_by))
    
    conn.commit()
    conn.close()
    return True

def get_application_notes(application_id):
    """Başvurunun notlarını getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, note, added_by, added_date 
        FROM application_notes 
        WHERE application_id = ? 
        ORDER BY added_date DESC
    ''', (application_id,))
    
    notes = cursor.fetchall()
    conn.close()
    
    return notes

def get_last_application_time(user_id):
    """Kullanıcının son başvuru zamanını getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT application_date 
        FROM applications 
        WHERE user_id = ? 
        ORDER BY application_date DESC 
        LIMIT 1
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    return None

def get_user_application(user_id):
    """Kullanıcının başvurusunu getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM applications 
        WHERE user_id = ? 
        ORDER BY application_date DESC 
        LIMIT 1
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result

def get_all_applications():
    """Tüm başvuruları getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM applications ORDER BY application_date DESC')
    results = cursor.fetchall()
    
    conn.close()
    return results

def get_rejected_applications():
    """Reddedilen başvuruları getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM applications WHERE status = "rejected"')
    results = cursor.fetchall()
    
    conn.close()
    return results

def get_statistics():
    """İstatistikleri getir"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    stats = {}
    
    # Toplam başvuru sayısı
    cursor.execute('SELECT COUNT(*) FROM applications')
    stats['total'] = cursor.fetchone()[0]
    
    # Bekleyen başvuru sayısı
    cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "pending"')
    stats['pending'] = cursor.fetchone()[0]
    
    # Onaylanan başvuru sayısı
    cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "approved"')
    stats['approved'] = cursor.fetchone()[0]
    
    # Reddedilen başvuru sayısı
    cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "rejected"')
    stats['rejected'] = cursor.fetchone()[0]
    
    # Her iki siteye de başvuru yapıldığı için site bazında sayı göstermeye gerek yok
    # Tüm başvurular hem Merso hem AMG içeriyor
    stats['by_site'] = {'merso': stats['total'], 'amg': stats['total']}
    
    # Bugünkü başvuru sayısı
    cursor.execute('''
        SELECT COUNT(*) FROM applications 
        WHERE DATE(application_date) = DATE('now')
    ''')
    stats['today'] = cursor.fetchone()[0]
    
    # Bu haftaki başvuru sayısı
    cursor.execute('''
        SELECT COUNT(*) FROM applications 
        WHERE DATE(application_date) >= DATE('now', '-7 days')
    ''')
    stats['week'] = cursor.fetchone()[0]
    
    conn.close()
    return stats

def update_application_status_with_reason(application_id, status, reason=None):
    """Basvuru durumunu sebep ile guncelle"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Eğer red_reason kolonu yoksa ekle
    cursor.execute("PRAGMA table_info(applications)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'red_reason' not in columns:
        cursor.execute('ALTER TABLE applications ADD COLUMN red_reason TEXT')
    
    # Eğer onaylanıyorsa, onay tarihini de kaydet
    if status == 'approved':
        cursor.execute('''
            UPDATE applications 
            SET status = ?, approved_date = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (status, application_id))
    elif status == 'rejected' and reason:
        cursor.execute('''
            UPDATE applications 
            SET status = ?, red_reason = ? 
            WHERE id = ?
        ''', (status, reason, application_id))
    else:
        cursor.execute('UPDATE applications SET status = ? WHERE id = ?', 
                      (status, application_id))
    
    conn.commit()
    conn.close()
