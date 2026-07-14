"""
Grup aktivite izleme sistemi - Zamanlanmış mesajlar için akıllı kontrol
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from aiogram import Bot
from aiogram.types import Message
from config import get_config
from utils.logger import setup_logger

logger = setup_logger()

# Grup aktivite durumu: {group_id: {'last_message_time': datetime, 'last_sender_id': int, 'is_bot_message': bool, 'status': 'active'|'inactive', 'notified': bool}}
# ⚠️ NOT: Bu veriler sadece RAM'de tutulur, SQL'e yazılmaz (performans için)
group_activity_status: Dict[int, Dict] = {}

# Son N mesajı takip etmek için: {group_id: [{'time': datetime, 'is_bot': bool, 'user_id': int}, ...]}
# Son 50 mesajı takip ediyoruz (bot mesaj kontrolü için)
recent_messages_by_group: Dict[int, list] = {}
MAX_RECENT_MESSAGES = 50  # Son 50 mesajı takip et
MIN_USER_MESSAGES_REQUIRED = 20  # Bot mesaj göndermek için en az 20 kullanıcı mesajı gerekli

# Grup kapalı sayılma süresi (dakika) - 2 saat
GROUP_INACTIVE_THRESHOLD_MINUTES = 120

# Admin bildirim durumu: {group_id: {'inactive_notified': bool, 'active_notified': bool}}
# ⚠️ NOT: Bu veriler sadece RAM'de tutulur, SQL'e yazılmaz
admin_notification_status: Dict[int, Dict] = {}

# Eski kayıtları temizleme süresi (saat) - 24 saatten eski kayıtları sil
CLEANUP_OLD_RECORDS_HOURS = 24

_bot_instance: Optional[Bot] = None

def set_bot_instance(bot_instance: Bot):
    """Bot instance'ını set et"""
    global _bot_instance
    _bot_instance = bot_instance

async def record_group_message(message: Message):
    """
    Grup mesajını kaydet - Son mesaj zamanı ve gönderen bilgisini güncelle
    ⚠️ NOT: Bu veriler sadece RAM'de tutulur, SQL'e yazılmaz (performans için)
    """
    try:
        if message.chat.type not in ["group", "supergroup"]:
            return
        
        group_id = message.chat.id
        sender_id = message.from_user.id if message.from_user else None
        is_bot = message.from_user.is_bot if message.from_user else False
        current_time = datetime.now()
        
        # Bot'un kendi ID'sini al
        bot_id = None
        if _bot_instance:
            bot_info = await _bot_instance.get_me()
            bot_id = bot_info.id
        
        # Grup durumunu güncelle (sadece RAM'de)
        is_bot_msg = is_bot and sender_id == bot_id
        group_activity_status[group_id] = {
            'last_message_time': current_time,
            'last_sender_id': sender_id,
            'is_bot_message': is_bot_msg,
            'status': 'active',
            'notified': False
        }
        
        # Son N mesajı takip et (bot mesaj kontrolü için)
        if group_id not in recent_messages_by_group:
            recent_messages_by_group[group_id] = []
        
        recent_messages_by_group[group_id].append({
            'time': current_time,
            'is_bot': is_bot_msg,
            'user_id': sender_id
        })
        
        # Son 50 mesajı tut (eski mesajları temizle)
        if len(recent_messages_by_group[group_id]) > MAX_RECENT_MESSAGES:
            recent_messages_by_group[group_id] = recent_messages_by_group[group_id][-MAX_RECENT_MESSAGES:]
        
        # Eğer grup daha önce kapalıydı ve şimdi aktif olduysa, admin'e bildir
        if group_id in admin_notification_status:
            if admin_notification_status[group_id].get('inactive_notified', False):
                # Grup tekrar aktif oldu
                await notify_admin_group_active(group_id, message.chat.title or f"Grup {group_id}")
                admin_notification_status[group_id]['inactive_notified'] = False
                admin_notification_status[group_id]['active_notified'] = True
        
        # Eski kayıtları temizle (bellek optimizasyonu)
        await cleanup_old_records()
        
        logger.debug(f"📝 Grup mesajı kaydedildi (RAM) - Group: {group_id}, Sender: {sender_id}, IsBot: {is_bot and sender_id == bot_id}")
        
    except Exception as e:
        logger.error(f"❌ Grup mesajı kaydetme hatası: {e}")

async def record_bot_message(group_id: int, bot_id: int):
    """
    Bot mesajını kaydet - Zamanlanmış mesajlar için
    ⚠️ NOT: Bu veriler sadece RAM'de tutulur, SQL'e yazılmaz (performans için)
    """
    try:
        current_time = datetime.now()
        
        # Grup durumunu güncelle (sadece RAM'de)
        group_activity_status[group_id] = {
            'last_message_time': current_time,
            'last_sender_id': bot_id,
            'is_bot_message': True,  # Bot mesajı
            'status': 'active',
            'notified': False
        }
        
        # Bot mesajını da recent_messages listesine ekle
        if group_id not in recent_messages_by_group:
            recent_messages_by_group[group_id] = []
        
        recent_messages_by_group[group_id].append({
            'time': current_time,
            'is_bot': True,
            'user_id': bot_id
        })
        
        # Son 50 mesajı tut (eski mesajları temizle)
        if len(recent_messages_by_group[group_id]) > MAX_RECENT_MESSAGES:
            recent_messages_by_group[group_id] = recent_messages_by_group[group_id][-MAX_RECENT_MESSAGES:]
        
        logger.debug(f"📝 Bot mesajı kaydedildi (RAM) - Group: {group_id}, Bot: {bot_id}")
        
    except Exception as e:
        logger.error(f"❌ Bot mesajı kaydetme hatası: {e}")

async def cleanup_old_records():
    """
    Eski kayıtları temizle - Bellek optimizasyonu
    24 saatten eski kayıtları sil (grup kapalı olsa bile)
    """
    try:
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=CLEANUP_OLD_RECORDS_HOURS)
        
        # Eski grup aktivite kayıtlarını temizle
        groups_to_remove = []
        for group_id, status in group_activity_status.items():
            last_message_time = status.get('last_message_time')
            if last_message_time and last_message_time < cutoff_time:
                groups_to_remove.append(group_id)
        
        for group_id in groups_to_remove:
            del group_activity_status[group_id]
            logger.debug(f"🧹 Eski grup aktivite kaydı temizlendi - Group: {group_id}")
        
        # Eski admin bildirim kayıtlarını temizle (sadece aktif olanlar)
        notifications_to_remove = []
        for group_id, notification_status in admin_notification_status.items():
            # Eğer grup aktivite kaydı yoksa, bildirim kaydını da sil
            if group_id not in group_activity_status:
                notifications_to_remove.append(group_id)
        
        for group_id in notifications_to_remove:
            del admin_notification_status[group_id]
            logger.debug(f"🧹 Eski admin bildirim kaydı temizlendi - Group: {group_id}")
        
        # recent_messages_by_group temizliği (1 saatten eski mesajları temizle)
        message_cutoff_time = datetime.now() - timedelta(hours=1)
        for group_id, messages in list(recent_messages_by_group.items()):
            # 1 saatten eski mesajları filtrele
            recent_messages_by_group[group_id] = [
                msg for msg in messages 
                if msg.get('time', datetime.now()) > message_cutoff_time
            ]
            # Eğer liste boşaldıysa, grup kaydını sil
            if not recent_messages_by_group[group_id]:
                del recent_messages_by_group[group_id]
        
    except Exception as e:
        logger.error(f"❌ Eski kayıt temizleme hatası: {e}")

async def check_group_activity(group_id: int) -> Tuple[bool, str]:
    """
    Grup aktivite durumunu kontrol et - GRUP YAZMA İZİNLERİ KONTROLÜ EKLENDİ
    Returns: (should_send_message: bool, reason: str)
    """
    try:
        # ÖNEMLİ: Bot'un grup yazma izinlerini kontrol et
        try:
            if _bot_instance:
                bot_info = await _bot_instance.get_me()
                bot_member = await _bot_instance.get_chat_member(group_id, bot_info.id)
                
                # Bot'un mesaj gönderme izni var mı kontrol et
                if hasattr(bot_member, 'status'):
                    # Bot gruptan çıkarılmış veya yasaklanmış
                    if bot_member.status in ['left', 'kicked']:
                        return False, "Bot gruptan çıkarılmış veya yasaklanmış"
                
                # Bot'un izinlerini kontrol et (sadece admin ise)
                if hasattr(bot_member, 'can_send_messages'):
                    if not bot_member.can_send_messages:
                        return False, "Bot'un grup yazma izni yok (grup yazma kapatılmış)"
        except Exception as perm_error:
            # İzin kontrolü hatası - "chat not found" gibi hatalar normal olabilir
            if "chat not found" in str(perm_error).lower() or "not found" in str(perm_error).lower():
                return False, "Grup bulunamadı (bot gruptan çıkarılmış olabilir)"
            logger.debug(f"⏸️ Bot izin kontrolü hatası (kritik değil): {perm_error}")
            # Hata durumunda devam et (güvenli taraf)
        
        if group_id not in group_activity_status:
            # Grup durumu bilinmiyor, gönder (ilk kez)
            return True, "Grup durumu bilinmiyor, ilk mesaj"
        
        group_status = group_activity_status[group_id]
        last_message_time = group_status.get('last_message_time')
        is_bot_message = group_status.get('is_bot_message', False)
        
        if not last_message_time:
            return True, "Son mesaj zamanı bilinmiyor"
        
        # Son mesaj zamanını kontrol et
        time_diff = datetime.now() - last_message_time
        minutes_since_last_message = time_diff.total_seconds() / 60
        
        # Eğer son mesaj bot tarafından gönderildiyse, birisi yazana kadar bekle
        if is_bot_message:
            return False, "Son mesaj bot tarafından gönderildi, kullanıcı mesajı bekleniyor"
        
        # ÖNEMLİ: Son N mesajda yeterli kullanıcı mesajı var mı kontrol et
        if group_id in recent_messages_by_group:
            recent_messages = recent_messages_by_group[group_id]
            # Son 50 mesajdan kullanıcı mesajlarını say
            user_message_count = sum(1 for msg in recent_messages if not msg.get('is_bot', False))
            
            if user_message_count < MIN_USER_MESSAGES_REQUIRED:
                return False, f"Yetersiz kullanıcı aktivitesi (Son 50 mesajda {user_message_count}/{MIN_USER_MESSAGES_REQUIRED} kullanıcı mesajı)"
        
        # Eğer grup uzun süredir aktif değilse (kapalı), mesaj gönderme
        if minutes_since_last_message > GROUP_INACTIVE_THRESHOLD_MINUTES:
            # Admin'e bildir (sadece bir kez)
            if group_id not in admin_notification_status or not admin_notification_status[group_id].get('inactive_notified', False):
                group_name = await get_group_name(group_id)
                await notify_admin_group_inactive(group_id, group_name, minutes_since_last_message)
                if group_id not in admin_notification_status:
                    admin_notification_status[group_id] = {}
                admin_notification_status[group_id]['inactive_notified'] = True
                admin_notification_status[group_id]['active_notified'] = False
            
            return False, f"Grup {int(minutes_since_last_message)} dakikadır aktif değil (kapalı)"
        
        # Grup aktif, mesaj gönderilebilir
        return True, "Grup aktif"
        
    except Exception as e:
        logger.error(f"❌ Grup aktivite kontrolü hatası: {e}")
        # Hata durumunda gönder (güvenli taraf)
        return True, f"Hata: {str(e)}"

async def get_group_name(group_id: int) -> str:
    """Grup adını al"""
    try:
        if _bot_instance:
            chat = await _bot_instance.get_chat(group_id)
            return chat.title or f"Grup {group_id}"
    except Exception as chat_error:
        logger.debug(f"Grup bilgisi alma hatası (kritik değil): {chat_error}")
    return f"Grup {group_id}"

async def notify_admin_group_inactive(group_id: int, group_name: str, minutes_inactive: float):
    """Admin'e grup kapalı bildirimi gönder"""
    try:
        if not _bot_instance:
            return
        
        config = get_config()
        # MAIN_ADMIN_ID yoksa ADMIN_USER_ID kullan
        admin_id = getattr(config, 'MAIN_ADMIN_ID', None) or getattr(config, 'ADMIN_USER_ID', None)
        
        if not admin_id:
            logger.warning("⚠️ Admin ID tanımlı değil, admin bildirimi gönderilemedi")
            return
        
        hours = int(minutes_inactive // 60)
        minutes = int(minutes_inactive % 60)
        time_str = f"{hours} saat {minutes} dakika" if hours > 0 else f"{int(minutes)} dakika"
        
        message = f"""
⚠️ <b>Grup Kapalı Bildirimi</b>

📊 <b>Grup:</b> {group_name}
🆔 <b>ID:</b> <code>{group_id}</code>
⏰ <b>Süre:</b> {time_str} boyunca mesaj yok

ℹ️ Zamanlanmış mesajlar bu gruba gönderilmeyecek.
✅ Grup tekrar aktif olduğunda bildirim alacaksınız.
        """
        
        await _bot_instance.send_message(
            chat_id=admin_id,
            text=message,
            parse_mode="HTML"
        )
        
        logger.info(f"📢 Admin'e grup kapalı bildirimi gönderildi - Group: {group_id} ({group_name})")
        
    except Exception as e:
        logger.error(f"❌ Admin bildirimi gönderme hatası: {e}")

async def notify_admin_group_active(group_id: int, group_name: str):
    """Admin'e grup tekrar aktif bildirimi gönder"""
    try:
        if not _bot_instance:
            return
        
        config = get_config()
        # MAIN_ADMIN_ID yoksa ADMIN_USER_ID kullan
        admin_id = getattr(config, 'MAIN_ADMIN_ID', None) or getattr(config, 'ADMIN_USER_ID', None)
        
        if not admin_id:
            logger.warning("⚠️ Admin ID tanımlı değil, admin bildirimi gönderilemedi")
            return
        
        message = f"""
✅ <b>Grup Tekrar Aktif</b>

📊 <b>Grup:</b> {group_name}
🆔 <b>ID:</b> <code>{group_id}</code>

🎉 Grup tekrar aktif oldu, zamanlanmış mesajlar gönderilmeye devam edecek.
        """
        
        await _bot_instance.send_message(
            chat_id=admin_id,
            text=message,
            parse_mode="HTML"
        )
        
        logger.info(f"📢 Admin'e grup aktif bildirimi gönderildi - Group: {group_id} ({group_name})")
        
    except Exception as e:
        logger.error(f"❌ Admin bildirimi gönderme hatası: {e}")

async def get_group_last_message_info(group_id: int) -> Optional[Dict]:
    """Grup son mesaj bilgisini al"""
    return group_activity_status.get(group_id)

