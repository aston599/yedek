"""
🏛️ Grup Yönetimi Handler'ı
/kirvegrup komutu ve grup kayıt sistemi
"""

import logging
from aiogram import types
from aiogram.types import Message

from database import register_group, is_group_registered, has_permission, get_user_rank
from config import get_config

logger = logging.getLogger(__name__)

# Global bot instance
_bot_instance = None

def set_bot_instance(bot):
    """Bot instance'ını ayarla"""
    global _bot_instance
    _bot_instance = bot


async def botlog_command(message: Message) -> None:
    """
    /botlog komutunu işle - Log grubu olarak ayarla
    """
    try:
        user = message.from_user
        chat_id = message.chat.id
        chat_title = message.chat.title or "Log Grubu"
        chat_username = message.chat.username
        chat_type = message.chat.type
        
        logger.info(f"📝 /botlog komutu - User: {user.first_name} ({user.id}), Chat: {chat_title} ({chat_id})")
        
        # Sadece grup/supergroup'da çalış
        if chat_type not in ["group", "supergroup"]:
            await message.reply("❌ Bu komut sadece gruplarda kullanılabilir!")
            return
        
        # Yetki kontrolü - Admin veya üstü
        has_admin_permission = await has_permission(user.id, "admin")
        user_rank = await get_user_rank(user.id)
        
        if not has_admin_permission:
            await message.reply("❌ Bu komutu kullanmak için admin yetkisine sahip olmalısınız!")
            return
        
        # Log grubu olarak ayarla
        success = await register_group(
            group_id=chat_id,
            group_name=chat_title,
            group_username=chat_username,
            registered_by=user.id
        )
        
        if success:
            response = f"""
✅ **Log Grubu Ayarlandı!**

**{chat_title}** grubu artık bot log grubu olarak ayarlandı.

📊 **Grup Bilgileri:**
🏷️ Ad: {chat_title}
🆔 ID: `{chat_id}`
📝 Username: @{chat_username if chat_username else 'Yok'}

🔧 **Log Sistemi:**
📝 Sistem logları buraya gönderilecek
⚠️ Hata bildirimleri buraya gelecek
📊 İstatistik raporları buraya iletilecek
🎯 Önemli bildirimler buraya gönderilecek

_Log grubu başarıyla ayarlandı! 📝_
            """
            
            await message.reply(response, parse_mode="Markdown")
            
        else:
            await message.reply("❌ Log grubu ayarlanamadı! Lütfen tekrar deneyin.")
            
    except Exception as e:
        logger.error(f"❌ /botlog handler hatası: {e}")
        await message.reply("❌ Sistem hatası oluştu!")


async def kirvegrup_command(message: Message) -> None:
    """
    /kirvegrup komutunu işle
    """
    try:
        user = message.from_user
        chat_id = message.chat.id
        chat_title = message.chat.title or "Bilinmeyen Grup"
        chat_username = message.chat.username
        chat_type = message.chat.type
        
        logger.info(f"👥 /kirvegrup komutu - User: {user.first_name} ({user.id}), Chat: {chat_title} ({chat_id})")
        logger.info(f"🔍 Chat type: {message.chat.type}, Chat ID: {chat_id}")
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            logger.info(f"🔍 Grup chatinde - message.delete() çağrılıyor...")
            try:
                await message.delete()
                logger.info(f"🔇 Kirvegrup komutu mesajı silindi - Group: {chat_id}")
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                # Mesaj silinmese bile devam et
            
            # ÖZELİNDE YANIT VER
            logger.info(f"🔍 Bot instance kontrolü: {_bot_instance is not None}")
            if _bot_instance:
                logger.info(f"✅ _send_kirvegrup_privately çağrılıyor - User: {user.id}, Chat: {chat_id}")
                await _send_kirvegrup_privately(user.id, chat_id)
            else:
                logger.error(f"❌ Bot instance bulunamadı! _bot_instance: {_bot_instance}")
            return
        
        # Sadece grup/supergroup'da çalış
        if chat_type not in ["group", "supergroup"]:
            await message.reply("❌ Bu komut sadece gruplarda kullanılabilir! Lütfen bir grupta deneyin.")
            return
        
        # Yetki kontrolü - Üst Yetkili - Admin 2 veya üstü
        has_group_permission = await has_permission(user.id, "register_group")
        user_rank = await get_user_rank(user.id)
        
        if not has_group_permission:
            # YETKİ HATASI: Sadece özel mesajla bildir, grup chatinde hiçbir şey yazma
            try:
                from aiogram import Bot
                from config import get_config
                config = get_config()
                
                temp_bot = Bot(token=config.BOT_TOKEN)
                
                error_response = f"""
🚫 **Yetki Hatası - /kirvegrup**

Bu komutu **{chat_title}** grubunda kullanmaya çalıştınız ancak yetkiniz yok.

👤 **Mevcut Durumunuz:**
🎖️ Rütbe: {user_rank.get('rank_name', 'Üye')}
⭐ Seviye: {user_rank.get('rank_level', 1)}

⚠️ **Gerekli Yetki:**
👑 Üst Yetkili - Admin 2 (Seviye 3)
🛡️ Grup kayıt yetkisi

📝 **Grup Bilgileri:**
🏷️ Grup: {chat_title}
🆔 ID: `{chat_id}`

_Yetki talebi için Super Admin'le iletişime geçin._
                """
                
                await temp_bot.send_message(
                    chat_id=user.id,
                    text=error_response,
                    parse_mode="Markdown"
                )
                await temp_bot.session.close()
                
            except Exception as e:
                logger.error(f"❌ Yetki hatası mesajı gönderilemedi: {e}")
            
            return
        
        # Grup zaten kayıtlı mı kontrol et
        if await is_group_registered(chat_id):
            # ZATEN KAYITLI: Sadece özel mesajla bildir
            try:
                from aiogram import Bot
                from config import get_config
                config = get_config()
                
                temp_bot = Bot(token=config.BOT_TOKEN)
                
                already_registered_response = f"""
ℹ️ **Grup Durumu - /kirvegrup**

**{chat_title}** grubu zaten sistemde kayıtlı!

✅ **Mevcut Durum:**
💎 Kirve Point sistemi aktif
📈 Otomatik sistem çalışıyor
🎯 Güvenlik koruması aktif
💰 Sessiz mod aktif

📊 **Grup Bilgileri:**
🏷️ Ad: {chat_title}
🆔 ID: `{chat_id}`
📝 Username: @{chat_username if chat_username else 'Yok'}

_Grup zaten aktif durumda! 🚀_
                """
                
                await temp_bot.send_message(
                    chat_id=user.id,
                    text=already_registered_response,
                    parse_mode="Markdown"
                )
                await temp_bot.session.close()
                
            except Exception as e:
                logger.error(f"❌ Zaten kayıtlı mesajı gönderilemedi: {e}")
            
            return
        
        # Grubu kayıt et
        logger.info(f"🔄 Grup kayıt işlemi başlatılıyor - Group: {chat_title} ({chat_id})")
        success = await register_group(
            group_id=chat_id,
            group_name=chat_title,
            group_username=chat_username,
            registered_by=user.id
        )
        logger.info(f"✅ Grup kayıt sonucu: {success} - Group: {chat_title} ({chat_id})")
        
        if success:
            # GRUP CHATİNDE: Hiçbir şey yazma - sadece sessizlik
            
            # ADMİN'E ÖZEL: Hem başarı hem grup kayıt detayları
            admin_response = f"""
🔐 **Admin Bildirimi - Grup Kayıt**

✅ **Grup başarıyla sisteme kayıt edildi!**

📊 *Grup Bilgileri:*
🏷️ **Ad:** {chat_title}
🆔 **ID:** `{chat_id}`
📝 **Username:** @{chat_username if chat_username else 'Yok'}
👥 **Tip:** {chat_type.title()}

👤 *İşlem Detayları:*
🎯 **Kayıt Eden:** {user.first_name} {user.last_name or ''}
🆔 **Admin ID:** `{user.id}`
👑 **Rütbe:** {user_rank.get('rank_name', 'Admin')} (Level {user_rank.get('rank_level', 0)})

💎 *Kirve Point Sistemi:*
✅ **Durum:** Aktif
🎯 **Sistem:** Otomatik çalışıyor
🛡️ **Güvenlik:** Spam koruması aktif
🔇 **Mod:** Sessiz çalışma

⚙️ *Sistem Özellikleri:*
🎮 Otomatik sistem çalışıyor
📊 Limit kontrolü aktif
🚫 Flood koruması (10sn interval)
📈 İstatistik takibi aktif
🔄 Auto-recruitment aktif
🔇 Grup sessizlik modu

_Grup artık sisteme kayıtlı! Bot sessizce çalışıyor._ 🛡️
            """
            
            # Admin'e özel mesaj gönder
            try:
                from aiogram import Bot
                from config import get_config
                config = get_config()
                
                # Bot instance oluştur (geçici)
                temp_bot = Bot(token=config.BOT_TOKEN)
                await temp_bot.send_message(
                    chat_id=user.id,
                    text=admin_response,
                    parse_mode="Markdown"
                )
                await temp_bot.session.close()
                
            except Exception as e:
                logger.error(f"❌ Admin'e özel mesaj gönderilemedi: {e}")
                # Grup chatinde hata bildirimi verme
            
            logger.info(f"✅ Grup kayıt edildi - Group: {chat_title} ({chat_id}) by User: {user.id}")
            
        else:
            # HATA DURUMU: Sadece özel mesajla bildir
            try:
                from aiogram import Bot
                from config import get_config
                config = get_config()
                
                temp_bot = Bot(token=config.BOT_TOKEN)
                
                error_response = f"""
❌ **Grup Kayıt Hatası**

**{chat_title}** grubu kayıt edilirken bir hata oluştu!

📊 **Denenen İşlem:**
🏷️ Grup: {chat_title}
🆔 ID: `{chat_id}`
👤 Admin: {user.first_name}

🔧 **Çözüm Önerileri:**
• Birkaç dakika bekleyip tekrar deneyin
• Bot'un grup yöneticisi olduğundan emin olun
• Database bağlantısı kontrol ediliyor

_Sorun devam ederse Super Admin'e bildirin._
                """
                
                await temp_bot.send_message(
                    chat_id=user.id,
                    text=error_response,
                    parse_mode="Markdown"
                )
                await temp_bot.session.close()
                
            except Exception as e:
                logger.error(f"❌ Hata mesajı gönderilemedi: {e}")
            
    except Exception as e:
        logger.error(f"❌ /kirvegrup handler hatası: {e}")
        
        # GENEL HATA: Sadece özel mesajla bildir
        try:
            from aiogram import Bot
            from config import get_config
            config = get_config()
            
            temp_bot = Bot(token=config.BOT_TOKEN)
            
            general_error = f"""
❌ **Sistem Hatası - /kirvegrup**

Beklenmeyen bir hata oluştu!

🔧 **Hata Detayları:**
📝 Komut: /kirvegrup
🏷️ Grup: {chat_title if 'chat_title' in locals() else 'Bilinmiyor'}
👤 Kullanıcı: {user.first_name}

⚠️ **Bu hata loglandı ve incelenecek.**

_Lütfen daha sonra tekrar deneyin veya Super Admin'e bildirin._
            """
            
            await temp_bot.send_message(
                chat_id=user.id,
                text=general_error,
                parse_mode="Markdown"
            )
            await temp_bot.session.close()
            
        except:
            pass  # Çifte hata durumunda sessiz kal


async def group_info_command(message: Message) -> None:
    """
    /grupbilgi komutu - Grup hakkında bilgi al
    """
    try:
        user = message.from_user
        chat_id = message.chat.id
        chat_title = message.chat.title or "Bilinmeyen Grup"
        chat_username = message.chat.username
        chat_type = message.chat.type
        
        logger.info(f"ℹ️ /grupbilgi komutu - User: {user.first_name} ({user.id}) - Chat: {chat_id}")
        
        # Chat tipi kontrolü
        if chat_type not in ['group', 'supergroup']:
            # Private'daysa normal cevap ver
            await message.answer(
                "❌ Bu komut sadece gruplarda kullanılabilir!",
                reply_to_message_id=message.message_id
            )
            return
        
        # GRUP BİLGİLERİ: Sadece özel mesajla gönder
        try:
            from aiogram import Bot
            from config import get_config
            config = get_config()
            
            temp_bot = Bot(token=config.BOT_TOKEN)
            
            # Grup kayıtlı mı kontrol et
            is_registered = await is_group_registered(chat_id)
            
            if is_registered:
                response = f"""
ℹ️ **Grup Bilgileri - /grupbilgi**

🏷️ **Grup Adı:** {chat_title}
🆔 **Grup ID:** `{chat_id}`
👥 **Tip:** {chat_type.title()}
📝 **Username:** @{chat_username if chat_username else 'Yok'}

💎 **Kirve Point Sistemi:**
✅ **Durum:** Aktif
🎯 **Sistem:** Otomatik çalışıyor
🛡️ **Güvenlik:** Spam koruması aktif
🔇 **Mod:** Sessiz çalışma

📊 **Aktif Özellikler:**
🎮 Otomatik sistem
📈 İstatistik takibi  
🚫 Güvenlik koruması
🎯 Auto-recruitment sistemi
🔇 Grup sessizlik modu

⚙️ **Admin Özellikleri:**
• Dinamik ayarlar
• Limit kontrolü  
• Gerçek zamanlı monitoring

_Sistem otomatik olarak çalışıyor! 🚀_
                """
            else:
                response = f"""
ℹ️ **Grup Bilgileri - /grupbilgi**

🏷️ **Grup Adı:** {chat_title}
🆔 **Grup ID:** `{chat_id}`
👥 **Tip:** {chat_type.title()}
📝 **Username:** @{chat_username if chat_username else 'Yok'}

💎 **Kirve Point Sistemi:**
❌ **Durum:** Pasif

⚠️ **Point Kazanımı Mevcut Değil**
Bu grupta henüz point sistemi aktif değil.

🔧 **Grup Kayıt İçin:**
Üst Yetkili - Admin 2 rütbesindeki yöneticiler `/kirvegrup` komutunu kullanabilir.

🎯 **Kayıt Sonrası:**
• Otomatik sistem aktif olur
• Güvenlik koruması devreye girer
• Auto-recruitment sistemi çalışır
• Sessiz mod aktif olur

_Grup kayıt edilirse sistem aktif olur! 📈_
                """
                
            await temp_bot.send_message(
                chat_id=user.id,
                text=response,
                parse_mode="Markdown"
            )
            await temp_bot.session.close()
            
        except Exception as e:
            logger.error(f"❌ Grup bilgisi mesajı gönderilemedi: {e}")
        
    except Exception as e:
        logger.error(f"❌ /grupbilgi handler hatası: {e}")
        
        # GRUP BİLGİ HATASI: Sadece özel mesajla bildir
        try:
            from aiogram import Bot
            from config import get_config
            config = get_config()
            
            temp_bot = Bot(token=config.BOT_TOKEN)
            
            error_response = f"""
❌ **Sistem Hatası - /grupbilgi**

Grup bilgileri alınırken hata oluştu!

🔧 **Hata Detayları:**
📝 Komut: /grupbilgi
🏷️ Grup: {chat_title if 'chat_title' in locals() else 'Bilinmiyor'}
👤 Kullanıcı: {user.first_name}

⚠️ **Bu hata loglandı ve incelenecek.**

_Lütfen daha sonra tekrar deneyin._
            """
            
            await temp_bot.send_message(
                chat_id=user.id,
                text=error_response,
                parse_mode="Markdown"
            )
            await temp_bot.session.close()
            
        except:
            pass  # Çifte hata durumunda sessiz kal 


async def _send_kirvegrup_privately(user_id: int, chat_id: int):
    """Kirvegrup mesajını özel mesajla gönder"""
    logger.info(f"🚀 _send_kirvegrup_privately başladı - User: {user_id}, Chat: {chat_id}")
    try:
        if not _bot_instance:
            logger.error("❌ Bot instance bulunamadı!")
            return
        
        # Kullanıcı bilgilerini al
        from database import get_user_info
        user_info = await get_user_info(user_id)
        user_name = user_info.get('first_name', 'Kullanıcı') if user_info else 'Kullanıcı'
        
        # Grup bilgilerini al - Frozen instance hatası için güvenli yöntem
        chat_title = f"Grup {chat_id}"
        try:
            # Chat bilgilerini güvenli şekilde al
            chat_info = await _bot_instance.get_chat(chat_id)
            if hasattr(chat_info, 'title') and chat_info.title:
                chat_title = chat_info.title
        except Exception as e:
            logger.warning(f"⚠️ Chat bilgileri alınamadı: {e}")
            chat_title = f"Grup {chat_id}"
        
        # Admin kontrolü
        from config import get_config
        config = get_config()
        is_admin = user_id == config.ADMIN_USER_ID
        
        if not is_admin:
            response = f"""
❌ **Yetkisiz İşlem!**

Merhaba {user_name}! 

Bu komutu sadece admin kullanabilir.
Grup kayıt işlemi için admin ile iletişime geçin.
            """
        else:
            # Grup zaten kayıtlı mı kontrol et
            from database import is_group_registered
            is_registered = await is_group_registered(chat_id)
            
            if is_registered:
                response = f"""
✅ **Grup Zaten Kayıtlı!**

Merhaba {user_name}! 

**Grup:** {chat_title}
**ID:** `{chat_id}`

Bu grup zaten KirveHub sistemine kayıtlı.
Bot bu grupta aktif olarak çalışıyor.
                """
            else:
                # Grubu kayıt et
                from database import register_group
                success = await register_group(
                    group_id=chat_id,
                    group_name=chat_title,
                    group_username=None,  # Bot API'den alamayız
                    registered_by=user_id
                )
                
                if success:
                    response = f"""
✅ **Grup Başarıyla Kayıt Edildi!**

Merhaba {user_name}! 

**Grup:** {chat_title}
**ID:** `{chat_id}`

✅ **Kayıt sonrası:**
• Bot bu grupta aktif olacak
• Kullanıcılar point kazanabilecek
• Etkinlikler bu grupta çalışacak
• Market sistemi aktif olacak
• Grup sessizlik modu aktif

🎉 **Grup artık sisteme kayıtlı!**
                    """
                else:
                    response = f"""
❌ **Grup Kayıt Hatası!**

Merhaba {user_name}! 

**Grup:** {chat_title}
**ID:** `{chat_id}`

Grup kayıt işlemi başarısız oldu.
Lütfen daha sonra tekrar deneyin.
                    """
        
        # Mesajı gönder
        await _bot_instance.send_message(
            chat_id=user_id,
            text=response,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Kirvegrup özel mesajı gönderildi - User: {user_id}, Group: {chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Kirvegrup özel mesaj hatası: {e}")
        # Hata durumunda basit mesaj gönder
        try:
            if _bot_instance:
                await _bot_instance.send_message(
                    chat_id=user_id,
                    text="❌ Grup kayıt işlemi sırasında hata oluştu. Lütfen daha sonra tekrar deneyin."
                )
        except Exception as inner_e:
            logger.error(f"❌ Hata mesajı da gönderilemedi: {inner_e}") 