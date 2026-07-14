"""
🌐 Site Yönetim Sistemi - KirveHub Bot
Dinamik site ekleme, güncelleme, listeleme
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from database import get_db_pool
from config import is_admin

logger = logging.getLogger(__name__)
router = Router()

# Bot instance
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

# Otomatik siteler listesi gösterimi için zaman takibi
# {group_id: datetime}
_last_site_list_shown: Dict[int, datetime] = {}
SITE_LIST_AUTO_INTERVAL_MINUTES = 120  # 120 dakika (2 saat) - Spam önleme için artırıldı
# Kontrol sıklığı - Her mesajda değil, sadece belirli durumlarda kontrol et
_last_check_time: Dict[int, datetime] = {}  # {group_id: last_check_time}
SITE_LIST_CHECK_INTERVAL_MINUTES = 5  # 5 dakikada bir kontrol et (her mesajda değil)


# =============================================
# DATABASE FONKSİYONLARI
# =============================================

async def get_active_sites() -> List[Dict]:
    """Aktif siteleri öncelik sırasına göre getir"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, name, url, description, icon, priority,
                       welcome_bonus, features, payment_methods, 
                       min_deposit, support_info, promo_code
                FROM sites
                WHERE is_active = true
                ORDER BY priority DESC, id ASC
            """)
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"❌ Aktif siteler getirme hatası: {e}")
        return []


async def get_all_sites() -> List[Dict]:
    """Tüm siteleri getir (admin için)"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, name, url, description, icon, priority, is_active
                FROM sites
                ORDER BY priority DESC, id ASC
            """)
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"❌ Tüm siteler getirme hatası: {e}")
        return []


async def add_site(name: str, url: str, description: str = "", icon: str = "🌐", priority: int = 0) -> bool:
    """Yeni site ekle"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO sites (name, url, description, icon, priority, is_active)
                VALUES ($1, $2, $3, $4, $5, true)
            """, name, url, description, icon, priority)
            logger.info(f"✅ Yeni site eklendi: {name}")
            return True
    except Exception as e:
        logger.error(f"❌ Site ekleme hatası: {e}")
        return False


async def update_site(site_id: int, **kwargs) -> bool:
    """Site bilgilerini güncelle"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Güncellenecek alanları oluştur
            updates = []
            values = []
            idx = 1
            
            for key, value in kwargs.items():
                if key in ['name', 'url', 'description', 'icon', 'priority', 'is_active']:
                    updates.append(f"{key} = ${idx}")
                    values.append(value)
                    idx += 1
            
            if not updates:
                return False
            
            values.append(site_id)
            query = f"UPDATE sites SET {', '.join(updates)} WHERE id = ${idx}"
            
            await conn.execute(query, *values)
            logger.info(f"✅ Site güncellendi: ID {site_id}")
            return True
    except Exception as e:
        logger.error(f"❌ Site güncelleme hatası: {e}")
        return False


async def delete_site(site_id: int) -> bool:
    """Site sil (soft delete - is_active = false)"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE sites SET is_active = false WHERE id = $1", site_id)
            logger.info(f"✅ Site deaktive edildi: ID {site_id}")
            return True
    except Exception as e:
        logger.error(f"❌ Site silme hatası: {e}")
        return False


async def get_site_by_id(site_id: int) -> Optional[Dict]:
    """ID'ye göre site getir"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM sites WHERE id = $1", site_id)
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"❌ Site getirme hatası: {e}")
        return None


# =============================================
# KULLANICI KOMUTU: !siteler
# =============================================

# NOT: !siteler komutu main.py'de manuel handler olarak kaydediliyor (router'dan önce)
# Bu handler devre dışı bırakıldı - çakışmayı önlemek için
# @router.message(F.text.startswith("!siteler"))
async def site_command(message: Message):
    """Aktif siteleri listele (kullanıcılar için)"""
    try:
        # !siteler komutunu yakala
        command = message.text.strip().split()[0].lower() if message.text else ""
        if command != '!siteler':
            # Eğer !siteler ile başlıyorsa ama tam değilse, atla
            return
        
        user_id = message.from_user.id
        is_group = message.chat.type in ["group", "supergroup"]
        
        # DEBUG LOG
        logger.info(f"🌐 !siteler komutu site_manager'da yakalandı! - User: {user_id}, Chat: {message.chat.type}, Text: '{message.text}'")
        
        # Grupta mesajı silme - direkt grupta göster
        
        # Aktif siteleri getir
        sites = await get_active_sites()
        
        if not sites:
            error_msg = (
                "❌ **Aktif site bulunamadı!**\n\n"
                "Lütfen daha sonra tekrar deneyin."
            )
            
            # Her zaman grupta göster (flame olmadan)
            await message.answer(error_msg, parse_mode="Markdown")
            return
        
        # Site listesi oluştur - Sadece başlık, linkler butonlarda
        response = "Kirvem güvenilir sitelerimiz aşağıda yer aldığı gibidir:"
        
        # Butonlar oluştur - Sadece linkler için basit butonlar
        keyboard = []
        
        # En üste "Tüm Siteler" linki
        keyboard.append([
            InlineKeyboardButton(
                text="🌐 TÜM SİTELER - kirve1.com",
                url="https://kirve1.com"
            )
        ])
        
        # Her site için sadece link butonu - Emojiler sırayla atanıyor
        emoji_list = ['⭐', '✨', '🍀', '👑', '💛', '🧿', '🎯']
        for idx, site in enumerate(sites):
            # Emoji listesinden sırayla al, eğer biterse baştan başla
            icon = emoji_list[idx % len(emoji_list)]
            name = site['name']
            url = site['url']
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{icon} {name}",
                    url=url
                )
            ])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Her zaman grupta göster (flame olmadan)
        await message.answer(response, reply_markup=markup, parse_mode="Markdown")
        logger.info(f"✅ Site listesi gösterildi - User: {user_id}, Group: {is_group}")
        
        # Grupta gösterildiyse zamanı kaydet
        if is_group:
            _last_site_list_shown[message.chat.id] = datetime.now()
        
    except Exception as e:
        logger.error(f"❌ Site komutu hatası: {e}", exc_info=True)
        
        error_msg = "❌ Bir hata oluştu! Lütfen tekrar deneyin."
        await message.answer(error_msg)


async def show_site_list_auto(group_id: int, bot_instance=None) -> bool:
    """
    Otomatik olarak siteler listesini grupta göster (2 saat kontrolü ile)
    
    Args:
        group_id: Grup ID
        bot_instance: Bot instance (None ise _bot_instance kullanılır)
    
    Returns:
        bool: Gösterildiyse True, gösterilmediyse False
    """
    try:
        # ÖNEMLİ: Bot başlangıç koruması - Bot başladıktan sonra 3 dakika bekle
        try:
            from handlers.chat_system import is_bot_startup_protection_active
            if is_bot_startup_protection_active():
                logger.debug(f"🛡️ Bot başlangıç koruması aktif - Otomatik siteler listesi gönderilmedi (3 dakika)")
                return False
        except Exception as protection_error:
            logger.debug(f"⏸️ Startup protection kontrolü hatası (kritik değil): {protection_error}")
        
        # ÖNEMLİ: Her mesajda kontrol etme - Sadece belirli aralıklarla kontrol et
        now = datetime.now()
        last_check = _last_check_time.get(group_id)
        if last_check:
            check_time_diff = (now - last_check).total_seconds()
            if check_time_diff < SITE_LIST_CHECK_INTERVAL_MINUTES * 60:
                # Henüz kontrol zamanı gelmemiş, hiç kontrol etme (spam önleme)
                return False
        
        # Kontrol zamanını kaydet
        _last_check_time[group_id] = now
        
        # Son gösterilme zamanını kontrol et
        last_shown = _last_site_list_shown.get(group_id)
        if last_shown:
            time_diff = (now - last_shown).total_seconds()
            if time_diff < SITE_LIST_AUTO_INTERVAL_MINUTES * 60:
                # Henüz 2 saat geçmemiş
                logger.debug(f"⏸️ Otomatik siteler listesi - Grup {group_id}: Henüz {time_diff/60:.1f} dakika geçti, {SITE_LIST_AUTO_INTERVAL_MINUTES} dakika bekleniyor")
                return False
        
        # Aktif siteleri getir
        sites = await get_active_sites()
        
        if not sites:
            logger.debug(f"⏸️ Otomatik siteler listesi - Grup {group_id}: Aktif site yok")
            return False
        
        # Site listesi oluştur - Sadece başlık, linkler butonlarda
        response = "Kirvem güvenilir sitelerimiz aşağıda yer aldığı gibidir:"
        
        # Butonlar oluştur - Sadece linkler için basit butonlar
        keyboard = []
        
        # En üste "Tüm Siteler" linki
        keyboard.append([
            InlineKeyboardButton(
                text="🌐 TÜM SİTELER - kirve1.com",
                url="https://kirve1.com"
            )
        ])
        
        # Her site için sadece link butonu - Emojiler sırayla atanıyor
        emoji_list = ['⭐', '✨', '🍀', '👑', '💛', '🧿', '🎯']
        for idx, site in enumerate(sites):
            # Emoji listesinden sırayla al, eğer biterse baştan başla
            icon = emoji_list[idx % len(emoji_list)]
            name = site['name']
            url = site['url']
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{icon} {name}",
                    url=url
                )
            ])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Bot instance kontrolü
        if not bot_instance:
            bot_instance = _bot_instance
        
        if not bot_instance:
            logger.warning(f"⚠️ Bot instance yok - Otomatik siteler listesi gösterilemedi - Grup: {group_id}")
            return False
        
        # ÖNEMLİ: Son mesaj kontrolü - Eğer son mesaj bot ise, gönderme (FLAME KORUMASI)
        try:
            from handlers.group_activity_monitor import check_group_activity
            should_send, reason = await check_group_activity(group_id)
            if not should_send:
                logger.debug(f"⏸️ Otomatik siteler listesi - Grup {group_id}: Mesaj gönderilmedi - {reason}")
                return False
        except Exception as check_error:
            logger.debug(f"⏸️ Grup aktivite kontrolü hatası (kritik değil): {check_error}")
            # Hata durumunda devam et (güvenli taraf)
        
        # Grupta göster
        await bot_instance.send_message(
            chat_id=group_id,
            text=response,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        # ÖNEMLİ: Bot mesajını grup aktivite izleyicisine kaydet (FLAME KORUMASI)
        try:
            from handlers.group_activity_monitor import record_bot_message
            bot_info = await bot_instance.get_me()
            await record_bot_message(group_id, bot_info.id)
        except Exception as record_error:
            logger.debug(f"⏸️ Bot mesajı kaydetme hatası (kritik değil): {record_error}")
        
        # Zamanı kaydet
        _last_site_list_shown[group_id] = datetime.now()
        
        logger.info(f"✅ Otomatik siteler listesi gösterildi - Grup: {group_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Otomatik siteler listesi hatası - Grup {group_id}: {e}", exc_info=True)
        return False


# =============================================
# ADMIN KOMUTLARI
# =============================================

@router.message(Command("siteekle"))
@router.message(F.text.startswith("!siteekle"))
async def add_site_command(message: Message):
    """Yeni site ekle (admin)"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not is_admin(user_id):
            await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
            return
        
        # Parametreleri al
        parts = message.text.split(maxsplit=5)
        
        if len(parts) < 3:
            await message.reply(
                "❌ **Eksik parametre!**\n\n"
                "**Kullanım:**\n"
                "`!siteekle <ad> <url> [açıklama] [emoji] [öncelik]`\n\n"
                "**Örnek:**\n"
                "`!siteekle Mersobahis https://t2m.io/merso Güvenilir site 🎰 100`",
                parse_mode="Markdown"
            )
            return
        
        name = parts[1]
        url = parts[2]
        description = parts[3] if len(parts) > 3 else ""
        icon = parts[4] if len(parts) > 4 else "🌐"
        priority = int(parts[5]) if len(parts) > 5 else 0
        
        # Site ekle
        success = await add_site(name, url, description, icon, priority)
        
        if success:
            await message.reply(
                f"✅ **Site başarıyla eklendi!**\n\n"
                f"{icon} **{name}**\n"
                f"🔗 {url}\n"
                f"📝 {description if description else 'Açıklama yok'}\n"
                f"📊 Öncelik: {priority}",
                parse_mode="Markdown"
            )
        else:
            await message.reply("❌ Site eklenemedi! Lütfen tekrar deneyin.")
        
    except ValueError:
        await message.reply("❌ Öncelik sayı olmalı!")
    except Exception as e:
        logger.error(f"❌ Site ekleme hatası: {e}", exc_info=True)
        await message.reply("❌ Bir hata oluştu!")


@router.message(Command("sitelistele"))
@router.message(F.text == "!sitelistele")
async def list_sites_command(message: Message):
    """Tüm siteleri listele (admin)"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not is_admin(user_id):
            await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
            return
        
        # Tüm siteleri getir
        sites = await get_all_sites()
        
        if not sites:
            await message.reply("❌ Hiç site bulunamadı!")
            return
        
        # Liste oluştur
        response = "🌐 **TÜM SİTELER (ADMIN)**\n"
        response += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        for site in sites:
            icon = site.get('icon', '🌐')
            name = site['name']
            url = site['url']
            description = site.get('description', '')
            priority = site.get('priority', 0)
            is_active = site.get('is_active', False)
            site_id = site['id']
            
            status = "✅ Aktif" if is_active else "❌ Pasif"
            
            response += f"{icon} **{name}** (ID: {site_id})\n"
            response += f"   └─ {status}\n"
            response += f"   └─ {url}\n"
            if description:
                response += f"   └─ {description}\n"
            response += f"   └─ Öncelik: {priority}\n\n"
        
        response += "━━━━━━━━━━━━━━━━━━━\n"
        response += f"📊 **Toplam:** {len(sites)} site\n\n"
        response += "**Komutlar:**\n"
        response += "`!siteekle` - Yeni site ekle\n"
        response += "`!siteguncelle <id>` - Site güncelle\n"
        response += "`!sitesil <id>` - Site sil"
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Site listeleme hatası: {e}", exc_info=True)
        await message.reply("❌ Bir hata oluştu!")


@router.message(Command("siteguncelle"))
@router.message(F.text.startswith("!siteguncelle"))
async def update_site_command(message: Message):
    """Site güncelle (admin)"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not is_admin(user_id):
            await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
            return
        
        # Parametreleri al
        parts = message.text.split(maxsplit=6)
        
        if len(parts) < 3:
            await message.reply(
                "❌ **Eksik parametre!**\n\n"
                "**Kullanım:**\n"
                "`!siteguncelle <id> <alan> <değer>`\n\n"
                "**Alanlar:**\n"
                "• name - Site adı\n"
                "• url - Site linki\n"
                "• description - Açıklama\n"
                "• icon - Emoji\n"
                "• priority - Öncelik (sayı)\n"
                "• is_active - Aktiflik (true/false)\n\n"
                "**Örnek:**\n"
                "`!siteguncelle 1 priority 100`\n"
                "`!siteguncelle 2 name YeniAd`",
                parse_mode="Markdown"
            )
            return
        
        site_id = int(parts[1])
        field = parts[2]
        value = parts[3]
        
        # Alan kontrolü
        if field not in ['name', 'url', 'description', 'icon', 'priority', 'is_active']:
            await message.reply(f"❌ Geçersiz alan: {field}")
            return
        
        # Değer tipi dönüşümü
        if field == 'priority':
            value = int(value)
        elif field == 'is_active':
            value = value.lower() in ['true', '1', 'yes', 'evet']
        
        # Güncelle
        success = await update_site(site_id, **{field: value})
        
        if success:
            site = await get_site_by_id(site_id)
            await message.reply(
                f"✅ **Site güncellendi!**\n\n"
                f"**ID:** {site_id}\n"
                f"**Alan:** {field}\n"
                f"**Yeni Değer:** {value}\n\n"
                f"**Güncel Bilgiler:**\n"
                f"{site.get('icon', '🌐')} {site['name']}\n"
                f"🔗 {site['url']}\n"
                f"📊 Öncelik: {site.get('priority', 0)}\n"
                f"{'✅ Aktif' if site.get('is_active') else '❌ Pasif'}",
                parse_mode="Markdown"
            )
        else:
            await message.reply("❌ Site güncellenemedi!")
        
    except ValueError:
        await message.reply("❌ Geçersiz değer! ID ve priority sayı olmalı.")
    except Exception as e:
        logger.error(f"❌ Site güncelleme hatası: {e}", exc_info=True)
        await message.reply("❌ Bir hata oluştu!")


@router.message(Command("sitesil"))
@router.message(F.text.startswith("!sitesil"))
async def delete_site_command(message: Message):
    """Site sil (admin)"""
    try:
        user_id = message.from_user.id
        
        # Admin kontrolü
        if not is_admin(user_id):
            await message.reply("❌ Bu komutu sadece adminler kullanabilir!")
            return
        
        # Parametreleri al
        parts = message.text.split()
        
        if len(parts) < 2:
            await message.reply(
                "❌ **Eksik parametre!**\n\n"
                "**Kullanım:**\n"
                "`!sitesil <id>`\n\n"
                "**Örnek:**\n"
                "`!sitesil 5`",
                parse_mode="Markdown"
            )
            return
        
        site_id = int(parts[1])
        
        # Site bilgisini al
        site = await get_site_by_id(site_id)
        
        if not site:
            await message.reply(f"❌ ID {site_id} bulunamadı!")
            return
        
        # Sil
        success = await delete_site(site_id)
        
        if success:
            await message.reply(
                f"✅ **Site silindi (deaktive edildi)!**\n\n"
                f"**ID:** {site_id}\n"
                f"{site.get('icon', '🌐')} **{site['name']}**\n\n"
                f"💡 Site veritabanında kaldı ama artık gözükmüyor.",
                parse_mode="Markdown"
            )
        else:
            await message.reply("❌ Site silinemedi!")
        
    except ValueError:
        await message.reply("❌ ID sayı olmalı!")
    except Exception as e:
        logger.error(f"❌ Site silme hatası: {e}", exc_info=True)
        await message.reply("❌ Bir hata oluştu!")


# =============================================
# CALLBACK HANDLERS
# =============================================

@router.callback_query(F.data.startswith("site_detail_"))
async def show_site_detail(callback):
    """Site detayını göster"""
    try:
        # Site ID'yi al
        site_id = int(callback.data.split("_")[-1])
        
        # Site bilgilerini al
        site = await get_site_by_id(site_id)
        
        if not site or not site.get('is_active'):
            await callback.answer("❌ Site bulunamadı!", show_alert=True)
            return
        
        # Detaylı bilgi oluştur
        icon = site.get('icon', '🌐')
        name = site['name']
        url = site['url']
        description = site.get('description', 'Açıklama yok')
        
        response = f"{icon} **{name.upper()}**\n"
        response += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Açıklama
        if description:
            response += f"📝 **Açıklama:**\n{description}\n\n"
        
        # Hoş geldin bonusu
        welcome_bonus = site.get('welcome_bonus')
        if welcome_bonus:
            response += f"🎁 **HOŞ GELDİN BONUSU:**\n{welcome_bonus}\n\n"
        
        # Özellikler
        features = site.get('features')
        if features:
            response += f"⭐ **ÖZELLİKLER:**\n{features}\n\n"
        
        # Ödeme yöntemleri
        payment_methods = site.get('payment_methods')
        if payment_methods:
            response += f"💳 **ÖDEME YÖNTEMLERİ:**\n{payment_methods}\n\n"
        
        # Minimum yatırım
        min_deposit = site.get('min_deposit')
        if min_deposit:
            response += f"💰 **Minimum Yatırım:** {min_deposit}\n\n"
        
        # Promosyon kodu
        promo_code = site.get('promo_code')
        if promo_code:
            response += f"🎟️ **Promosyon Kodu:** `{promo_code}`\n\n"
        
        # Destek bilgisi
        support_info = site.get('support_info')
        if support_info:
            response += f"📞 **DESTEK:**\n{support_info}\n\n"
        
        response += "━━━━━━━━━━━━━━━━━━━\n"
        response += "💡 Siteye gitmek için aşağıdaki butona tıklayın!"
        
        # Butonlar
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{icon} Siteye Git",
                    url=url
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Geri",
                    callback_data="site_back"
                ),
                InlineKeyboardButton(
                    text="❌ Kapat",
                    callback_data="site_close"
                )
            ]
        ]
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Mesajı güncelle
        await callback.message.edit_text(
            response,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        await callback.answer()
        
        logger.info(f"✅ Site detayı gösterildi - Site: {name}, User: {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Site detay hatası: {e}", exc_info=True)
        await callback.answer("❌ Hata oluştu!", show_alert=True)


@router.callback_query(F.data == "site_back")
async def back_to_site_list(callback):
    """Site listesine geri dön"""
    try:
        # Siteleri tekrar getir
        sites = await get_active_sites()
        
        if not sites:
            await callback.answer("❌ Aktif site bulunamadı!", show_alert=True)
            return
        
        # Liste oluştur
        response = "🌐 **AKTİF SİTELER**\n"
        response += "━━━━━━━━━━━━━━━━━━━\n\n"
        
        for idx, site in enumerate(sites, 1):
            icon = site.get('icon', '🌐')
            name = site['name']
            description = site.get('description', '')
            priority = site.get('priority', 0)
            
            response += f"{icon} **{idx}. {name}**\n"
            if description:
                response += f"   └─ {description}\n"
            response += f"   └─ Öncelik: {priority}\n\n"
        
        response += "━━━━━━━━━━━━━━━━━━━\n"
        response += f"📊 **Toplam:** {len(sites)} aktif site"
        
        # Butonlar
        keyboard = []
        for site in sites:
            site_id = site['id']
            icon = site.get('icon', '🌐')
            name = site['name']
            url = site['url']
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📋 {icon} {name} Detay",
                    callback_data=f"site_detail_{site_id}"
                ),
                InlineKeyboardButton(
                    text=f"🔗 Siteye Git",
                    url=url
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(text="❌ Kapat", callback_data="site_close")
        ])
        
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        await callback.message.edit_text(
            response,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Geri dönüş hatası: {e}", exc_info=True)
        await callback.answer("❌ Hata oluştu!", show_alert=True)


@router.callback_query(F.data == "site_close")
async def close_site_menu(callback):
    """Site menüsünü kapat"""
    try:
        await callback.message.delete()
        await callback.answer("Kapatıldı")
    except Exception as e:
        logger.error(f"❌ Menü kapatma hatası: {e}")
        await callback.answer("❌ Hata oluştu")

