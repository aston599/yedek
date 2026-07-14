"""
Activity Reward System - Aktiflik Odul Sistemi
Gercek sohbet eden kullanicilari tespit edip puanlar
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import is_admin
from database import get_db_pool

router = Router()
logger = logging.getLogger(__name__)

# Aktif etkinlikler
active_activities: Dict[int, Dict[str, Any]] = {}

# Her grup icin son activity sonuclari (cache)
activity_results_cache: Dict[int, Dict[str, Any]] = {}


def calculate_message_quality_score(text: str, is_reply: bool = False) -> float:
    """
    Mesaj kalite puani hesapla
    
    Faktörler:
    - Mesaj uzunlugu
    - Kelime sayisi
    - Emoji kullanimi
    - Reply mi?
    - Spam mi?
    """
    if not text or len(text.strip()) == 0:
        return 0.0
    
    score = 0.0
    text_clean = text.strip()
    length = len(text_clean)
    
    # 1. UZUNLUK PUANI
    if length < 5:
        # Cok kisa mesaj (spam potansiyeli)
        score += 0.2
    elif 5 <= length < 20:
        # Kisa ama anlamli olabilir
        score += 0.5
    elif 20 <= length < 50:
        # Orta uzunluk (ideal)
        score += 1.0
    elif 50 <= length < 100:
        # Uzun mesaj (daha degerli)
        score += 1.5
    else:
        # Cok uzun mesaj
        score += 2.0
    
    # 2. KELIME SAYISI PUANI
    words = text_clean.split()
    word_count = len(words)
    
    if word_count >= 3:
        score += 0.5
    if word_count >= 8:
        score += 0.5
    if word_count >= 15:
        score += 0.5
    
    # 3. EMOJI KULLANIMI (dogal sohbet gostergesi)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Yuz ifadeleri
        "\U0001F300-\U0001F5FF"  # Semboller
        "\U0001F680-\U0001F6FF"  # Tasitlar
        "\U0001F700-\U0001F77F"  # Semboller
        "\U0001F780-\U0001F7FF"  # Geometrik sekiller
        "\U0001F800-\U0001F8FF"  # Ok isaretleri
        "\U0001F900-\U0001F9FF"  # Ek semboller
        "\U0001FA00-\U0001FA6F"  # Ek semboller
        "\U0001FA70-\U0001FAFF"  # Ek semboller
        "\U00002702-\U000027B0"  # Dingbats
        "]+", flags=re.UNICODE
    )
    
    emoji_count = len(emoji_pattern.findall(text))
    
    if emoji_count > 0 and emoji_count <= 3:
        # Dogal emoji kullanimi
        score += 0.3
    elif emoji_count > 5:
        # Cok fazla emoji (spam potansiyeli)
        score -= 0.5
    
    # Sadece emoji mi? (spam)
    text_without_emoji = emoji_pattern.sub('', text_clean).strip()
    if len(text_without_emoji) < 3 and emoji_count > 0:
        # Sadece emoji, cok dusuk puan
        score = 0.2
    
    # 4. REPLY BONUSU (etkilesim gostergesi)
    if is_reply:
        score += 1.0
    
    # 5. SPAM PATTERANLARI KONTROL
    # Tekrar eden karakterler (aaaaa, !!!!!!!)
    repeated_char_pattern = r'(.)\1{4,}'
    if re.search(repeated_char_pattern, text):
        score -= 0.3
    
    # Capslock spam (AAAAA BBBBBB)
    if length > 10 and text.isupper():
        score -= 0.2
    
    # Link spam
    if 'http://' in text.lower() or 'https://' in text.lower() or 'www.' in text.lower():
        score -= 0.5
    
    # Minimum puan 0
    return max(0.0, score)


def detect_spam_user(user_messages: List[Dict[str, Any]]) -> bool:
    """
    Kullanici spam yapiyor mu kontrol et
    
    Spam gostergeleri:
    - Cok hizli mesaj (flood)
    - Ayni mesaji tekrar tekrar
    - Sadece cok kisa mesajlar
    """
    if len(user_messages) < 3:
        return False
    
    # 1. FLOOD KONTROL (2 saniyeden hizli mesajlar)
    rapid_messages = 0
    for i in range(1, len(user_messages)):
        time_diff = (user_messages[i]['timestamp'] - user_messages[i-1]['timestamp']).total_seconds()
        if time_diff < 2:
            rapid_messages += 1
    
    flood_ratio = rapid_messages / len(user_messages)
    if flood_ratio > 0.5:  # %50'den fazlasi flood
        return True
    
    # 2. TEKRAR EDEN MESAJ KONTROL
    message_texts = [msg['text'].lower().strip() for msg in user_messages]
    unique_messages = set(message_texts)
    
    repeat_ratio = len(unique_messages) / len(message_texts)
    if repeat_ratio < 0.3:  # %70'i ayni mesaj
        return True
    
    # 3. COK KISA MESAJLAR (spam botu olabilir)
    short_messages = sum(1 for msg in user_messages if len(msg['text']) < 5)
    short_ratio = short_messages / len(user_messages)
    
    if short_ratio > 0.7 and len(user_messages) > 10:  # %70'i cok kisa
        return True
    
    return False


def calculate_user_score(user_messages: List[Dict[str, Any]]) -> float:
    """
    Kullanici toplam puanini hesapla
    
    Algoritmalar:
    1. Her mesajin kalite puani
    2. Cesitlilik bonusu
    3. Tutarlilik bonusu
    4. Spam cezasi
    """
    if not user_messages:
        return 0.0
    
    # Spam kontrolu
    is_spam = detect_spam_user(user_messages)
    if is_spam:
        logger.info(f"Spam kullanici tespit edildi, puan: 0")
        return 0.0
    
    total_score = 0.0
    
    # 1. HER MESAJ ICIN KALITE PUANI
    for msg in user_messages:
        msg_score = calculate_message_quality_score(
            msg['text'],
            is_reply=msg.get('is_reply', False)
        )
        total_score += msg_score
    
    # 2. CESITLILIK BONUSU
    # Farkli kelimeler kullanma
    all_words = []
    for msg in user_messages:
        words = msg['text'].lower().split()
        all_words.extend(words)
    
    if len(all_words) > 0:
        unique_words = set(all_words)
        diversity_ratio = len(unique_words) / len(all_words)
        
        # Yuksek cesitlilik = gercek sohbet
        if diversity_ratio > 0.6:
            total_score += 2.0
        elif diversity_ratio > 0.4:
            total_score += 1.0
    
    # 3. TUTARLILIK BONUSU
    # Duzenli araliklarla mesaj atma (gercek sohbet)
    if len(user_messages) >= 5:
        time_intervals = []
        for i in range(1, len(user_messages)):
            interval = (user_messages[i]['timestamp'] - user_messages[i-1]['timestamp']).total_seconds()
            time_intervals.append(interval)
        
        avg_interval = sum(time_intervals) / len(time_intervals)
        
        # Ortalama 30 saniye - 10 dakika arasi ideal
        if 30 <= avg_interval <= 600:
            total_score += 1.5
    
    # 4. MESAJ SAYISI CARPANI
    # Cok fazla mesaj da bonus degil, kalite onemli
    message_count_multiplier = 1.0
    
    if 5 <= len(user_messages) <= 15:
        # Ideal mesaj sayisi
        message_count_multiplier = 1.2
    elif 16 <= len(user_messages) <= 30:
        message_count_multiplier = 1.1
    elif len(user_messages) > 50:
        # Cok fazla mesaj, potansiyel spam
        message_count_multiplier = 0.9
    
    total_score *= message_count_multiplier
    
    return round(total_score, 2)


@router.message(F.text == "!aktiflikodul")
async def start_activity_event(message: types.Message):
    """Aktiflik etkinligi baslat"""
    user_id = message.from_user.id
    group_id = message.chat.id
    
    # Admin kontrolu
    if not is_admin(user_id):
        await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
        return
    
    # Grup kontrolu
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ Bu komut sadece gruplarda kullanılabilir!")
        return
    
    # Zaten aktif etkinlik var mi?
    if group_id in active_activities:
        await message.reply(
            "⚠️ Bu grupta zaten aktif bir etkinlik var!\n"
            "Önce `!aktiflikodulbitir` ile sonlandırın."
        )
        return
    
    # Samimi bir duyuru mesaji gonder
    announcement_message = await message.reply(
        "🎉 **HEYECANLI BİR ETKİNLİK BAŞLADI!**\n\n"
        "Merhaba arkadaşlar! 👋\n\n"
        "🎯 **Ne yapacağız?**\n"
        "• Sadece sohbet edin, kendiniz olun\n"
        "• Grubumuzun havasını yaşatın\n"
        "• Eğlenceli konuşmalar yapın\n\n"
        "🎁 **Ödüller:**\n"
        "• En aktif ve samimi sohbet edenler\n"
        "• Sürpriz ödüller kazanacak\n\n"
        "🔥 **Kim grubun en enerjik üyesi?**\n"
        "Hadi gönlünüzce konuşun, eğlencenin tadını çıkarın! 😊",
        parse_mode="Markdown"
    )
    
    # Yeni etkinlik olustur
    active_activities[group_id] = {
        "admin_id": user_id,
        "admin_username": message.from_user.username or message.from_user.first_name,
        "started_at": datetime.now(),
        "status": "active",
        "participants": {},
        "announcement_message_id": announcement_message.message_id  # Sabitleme icin kaydet
    }
    
    logger.info(f"🎯 Aktiflik etkinligi basladi - Group: {group_id}, Admin: {user_id}")
    
    # Mesaji sabitle
    try:
        await message.chat.pin_message(
            message_id=announcement_message.message_id,
            disable_notification=True  # Sessiz sabitleme (spam degil)
        )
        logger.info(f"📌 Etkinlik mesaji sabitlendi - Group: {group_id}")
    except Exception as e:
        logger.warning(f"⚠️ Mesaj sabitlenemedi (izin gerekli): {e}")
        # Sabitleme basarisiz olsa da etkinlik devam eder


@router.message(F.text == "!aktiflikodulbitir")
async def end_activity_event(message: types.Message):
    """Aktiflik etkinligini bitir ve sonuclari goster"""
    user_id = message.from_user.id
    group_id = message.chat.id
    
    # Admin kontrolu
    if not is_admin(user_id):
        await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
        return
    
    # Aktif etkinlik var mi?
    if group_id not in active_activities:
        await message.reply("❌ Bu grupta aktif etkinlik yok!")
        return
    
    activity = active_activities[group_id]
    activity['ended_at'] = datetime.now()
    activity['status'] = "ended"
    
    # Puanlari hesapla
    results = []
    
    for user_id_str, user_data in activity['participants'].items():
        user_score = calculate_user_score(user_data['messages'])
        
        results.append({
            'user_id': user_data['user_id'],
            'username': user_data['username'],
            'message_count': len(user_data['messages']),
            'score': user_score
        })
    
    # Puana gore sirala
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Sabitli mesaji kaldir
    announcement_msg_id = activity.get('announcement_message_id')
    if announcement_msg_id:
        try:
            await message.chat.unpin_message(message_id=announcement_msg_id)
            logger.info(f"📌 Etkinlik mesaji sabitten kaldirildi - Group: {group_id}")
        except Exception as e:
            logger.warning(f"⚠️ Mesaj sabitten kaldirilamadi: {e}")
    
    # Cache'e kaydet
    activity_results_cache[group_id] = {
        'results': results,
        'started_at': activity['started_at'],
        'ended_at': activity['ended_at'],
        'duration': (activity['ended_at'] - activity['started_at']).total_seconds() / 60
    }
    
    # Aktif etkinliklerden kaldir
    del active_activities[group_id]
    
    logger.info(f"🏁 Aktiflik etkinligi sonlandi - Group: {group_id}, Katilimci: {len(results)}")
    
    # Kisa ozet mesaji
    duration_min = activity_results_cache[group_id]['duration']
    
    await message.reply(
        f"🎊 **ETKİNLİK SONA ERDİ!**\n\n"
        f"Ne kadar güzel bir sohbet oldu! 😊\n\n"
        f"📊 **İstatistikler:**\n"
        f"⏱️ Süre: {duration_min:.1f} dakika\n"
        f"👥 Katılımcı: {len(results)} kişi\n"
        f"💬 Toplam Mesaj: {sum(r['message_count'] for r in results)}\n\n"
        f"🎉 Hepinize teşekkürler, çok eğlenceli bir etkinlikti!\n\n"
        f"📋 Detaylı sıralamaya adminler `!aktiflikliste` yazarak ulaşabilir.",
        parse_mode="Markdown"
    )


@router.message(F.chat.type.in_(["group", "supergroup"]))
async def monitor_activity_messages(message: types.Message):
    """Etkinlik aktifken mesajlari kaydet"""
    group_id = message.chat.id
    
    # Aktif etkinlik var mi?
    if group_id not in active_activities:
        return
    
    # Bot komutu mu? (ignore)
    if message.text and message.text.startswith('!'):
        return
    
    # Mesaj yok mu? (foto, sticker vs.)
    if not message.text:
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "Anonim"
    
    activity = active_activities[group_id]
    
    # Kullanici ilk kez mi?
    if user_id not in activity['participants']:
        activity['participants'][user_id] = {
            'user_id': user_id,
            'username': username,
            'messages': []
        }
    
    # Mesaj bilgilerini kaydet
    message_data = {
        'text': message.text,
        'length': len(message.text),
        'timestamp': datetime.now(),
        'is_reply': message.reply_to_message is not None
    }
    
    activity['participants'][user_id]['messages'].append(message_data)
    
    # Log (sadece debug)
    if len(activity['participants'][user_id]['messages']) == 1:
        logger.debug(f"📝 Yeni katilimci - User: {username} ({user_id}), Group: {group_id}")


@router.message(F.text == "!aktiflikliste")
async def show_activity_results(message: types.Message):
    """Aktiflik sonuclarini goster (sadece admin)"""
    user_id = message.from_user.id
    group_id = message.chat.id
    
    # Admin kontrolu
    if not is_admin(user_id):
        # Sadece admin'e mesaj gonder (grupta herkese gosterme)
        return
    
    # Sonuc var mi?
    if group_id not in activity_results_cache:
        await message.reply("❌ Bu grupta henüz tamamlanmış etkinlik yok!")
        return
    
    cache_data = activity_results_cache[group_id]
    results = cache_data['results']
    duration = cache_data['duration']
    
    # Top 10
    top_10 = results[:10]
    
    # Mesaj olustur
    result_message = f"""
╔═══════════════════════════════════╗
║    🏆 AKTİFLİK ETKİNLİĞİ SONUÇ    ║
╚═══════════════════════════════════╝

📊 **İstatistikler:**
⏱️ Süre: {duration:.1f} dakika
👥 Katılımcı: {len(results)} kişi
💬 Toplam Mesaj: {sum(r['message_count'] for r in results)}

🏆 **TOP 10 EN AKTİF KULLANICILAR:**
"""
    
    for idx, user in enumerate(top_10, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        
        result_message += f"\n{medal} **{user['username']}**\n"
        result_message += f"   💬 {user['message_count']} mesaj | 🎯 {user['score']:.2f} puan\n"
    
    result_message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Puanlama Sistemi:**
• Mesaj kalitesi (uzunluk, kelime sayısı)
• Etkileşim (reply, emoji)
• Çeşitlilik (farklı kelimeler)
• Tutarlılık (düzenli mesajlaşma)
• Spam filtreleme (otomatik)

🎯 Gerçek sohbet edenlere öncelik!
"""
    
    await message.reply(result_message, parse_mode="Markdown")
    
    logger.info(f"📋 Aktiflik listesi goruntulendi - Admin: {user_id}, Group: {group_id}")

