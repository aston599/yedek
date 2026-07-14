"""
🎯 Kayıt Sistemi Handler'ı
/kirvekayit komutu ve kayıt işlemleri
"""

import logging
from datetime import datetime
from aiogram import types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database import save_user_info, register_user, is_user_registered, get_registered_users_count, unregister_user, get_user_rank
from config import get_config

logger = logging.getLogger(__name__)

# Bot instance
_bot_instance = None

def set_bot_instance(bot_instance):
    """Bot instance'ını set et"""
    global _bot_instance
    _bot_instance = bot_instance


async def yardim_command(message: Message) -> None:
    """
    /yardim komutunu işle
    """
    try:
        user = message.from_user
        config = get_config()
        
        logger.info(f"👤 /yardim komutu - User: {user.first_name} ({user.id})")
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Yardım komutu mesajı silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_yardim_privately(user.id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        # Kullanıcı bilgilerini kaydet
        await save_user_info(user.id, user.username, user.first_name, user.last_name)
        
        # Kayıtlı mı kontrol et
        is_registered = await is_user_registered(user.id)
        
        if is_registered:
            # Kayıtlı kullanıcı için yardım
            response = f"""
🤖 *KirveHub Bot - Yardım Menüsü*

Merhaba {user.first_name}! İşte kullanabileceğin komutlar:

📋 *Ana Komutlar:*
/start - Ana menü ve bot durumu
/menu - Profil menüsü ve istatistikler
/yardim - Bu yardım menüsü

🎮 *Etkinlik Komutları:*
/etkinlikler - Aktif etkinlikleri gör
/katil - Etkinliğe katıl

🛍️ *Market Komutları:*
/market - Market ürünlerini gör
/siparislerim - Sipariş geçmişim

📊 *İstatistik Komutları:*
/siralama - Point sıralaması
/profil - Detaylı profil

💡 *İpuçları:*
• Grup sohbetlerinde mesaj atarak point kazanabilirsin
• Günlük 5.00 KP limitin var
• Etkinliklere katılarak bonus kazanabilirsin
• Market'ten freespin ve bakiye alabilirsin

_Herhangi bir sorun yaşarsan admin ile iletişime geç! 🎯_
            """
        else:
            # Kayıtsız kullanıcı için yardım
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Hemen Kayıt Ol!", callback_data="register_user")]
            ])
            
            response = f"""
🤖 *KirveHub Bot - Yardım Menüsü*

Merhaba {user.first_name}! 

❌ *Şu anda kayıtlı değilsin!*

Bu özellikleri kullanabilmek için önce sisteme kayıt olman gerekiyor.

🎯 *Kayıt olduktan sonra:*
✅ Point kazanma sistemi
✅ Etkinliklere katılma
✅ Market alışverişi
✅ Profil ve istatistikler
✅ Topluluk özellikleri

⬇️ **Hemen kayıt ol ve sisteme katıl!**
            """
            
            await message.answer(
                response, 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            return
        
        await message.answer(response, parse_mode="Markdown")
        logger.info(f"✅ /yardim mesajı gönderildi - User: {user.id}")
        
    except Exception as e:
        logger.error(f"❌ /yardim handler hatası: {e}")
        await message.answer("Bir hata oluştu! Lütfen daha sonra tekrar deneyin.")

async def _send_yardim_privately(user_id: int):
    """Yardım mesajını özel mesajla gönder"""
    try:
        if not _bot_instance:
            logger.error("❌ Bot instance bulunamadı!")
            return
        
        # Kullanıcı bilgilerini al
        from database import get_user_info
        user_info = await get_user_info(user_id)
        user_name = user_info.get('first_name', 'Kullanıcı') if user_info else 'Kullanıcı'
        
        # Kullanıcı bilgilerini kaydet
        await save_user_info(user_id, user_info.get('username'), user_name, user_info.get('last_name'))
        
        # Kayıtlı mı kontrol et
        is_registered = await is_user_registered(user_id)
        
        if is_registered:
            # Kayıtlı kullanıcı için yardım
            response = f"""
🤖 *KirveHub Bot - Yardım Menüsü*

Merhaba {user_name}! İşte kullanabileceğin komutlar:

📋 *Ana Komutlar:*
/start - Ana menü ve bot durumu
/menu - Profil menüsü ve istatistikler
/yardim - Bu yardım menüsü

🎮 *Etkinlik Komutları:*
/etkinlikler - Aktif etkinlikleri gör
/katil - Etkinliğe katıl

🛍️ *Market Komutları:*
/market - Market ürünlerini gör
/siparislerim - Sipariş geçmişim

📊 *İstatistik Komutları:*
/siralama - Point sıralaması
/profil - Detaylı profil

💡 *İpuçları:*
• Grup sohbetlerinde mesaj atarak point kazanabilirsin
• Günlük 5.00 KP limitin var
• Etkinliklere katılarak bonus kazanabilirsin
• Market'ten freespin ve bakiye alabilirsin

_Herhangi bir sorun yaşarsan admin ile iletişime geç! 🎯_
            """
        else:
            # Kayıtsız kullanıcı için yardım
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Hemen Kayıt Ol!", callback_data="register_user")]
            ])
            
            response = f"""
🤖 *KirveHub Bot - Yardım Menüsü*

Merhaba {user_name}! 

❌ *Şu anda kayıtlı değilsin!*

Bu özellikleri kullanabilmek için önce sisteme kayıt olman gerekiyor.

🎯 *Kayıt olduktan sonra:*
✅ Point kazanma sistemi
✅ Etkinliklere katılma
✅ Market alışverişi
✅ Profil ve istatistikler
✅ Topluluk özellikleri

⬇️ **Hemen kayıt ol ve sisteme katıl!**
            """
        
        await _bot_instance.send_message(
            user_id,
            response,
            parse_mode="Markdown",
            reply_markup=keyboard if not is_registered else None
        )
        
        logger.info(f"✅ Yardım mesajı özel mesajla gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Private yardım hatası: {e}")
        await _bot_instance.send_message(user_id, "❌ Yardım mesajı gönderilemedi!")


async def komutlar_command(message: Message) -> None:
    """
    /komutlar komutunu işle - Tüm kullanıcılar için
    """
    try:
        user = message.from_user
        
        logger.info(f"👤 /komutlar komutu - User: {user.first_name} ({user.id})")
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Komutlar komutu mesajı silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_komutlar_privately(user.id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        # Kullanıcı bilgilerini kaydet
        await save_user_info(user.id, user.username, user.first_name, user.last_name)
        
        # Kayıtlı mı kontrol et
        is_registered = await is_user_registered(user.id)
        
        if is_registered:
            # Kayıtlı kullanıcı için komut listesi
            response = f"""
📋 **KULLANILABİLİR KOMUTLAR**

🎯 **Ana Komutlar:**
/start - Ana menü ve bot durumu
/menu - Profil menüsü ve istatistikler
/komutlar - Bu komut listesi
/yardim - Detaylı yardım menüsü

🎮 **Etkinlik Komutları:**
/etkinlikler - Aktif etkinlikleri gör
/katil - Etkinliğe katıl

🛍️ **Market Komutları:**
/market - Market ürünlerini gör
/siparislerim - Sipariş geçmişim

📊 **İstatistik Komutları:**
/siralama - Point sıralaması
/profil - Detaylı profil

💡 **İpuçları:**
• Grup sohbetlerinde mesaj atarak point kazanabilirsin
• Günlük 5.00 KP limitin var
• Etkinliklere katılarak bonus kazanabilirsin
• Market'ten freespin ve bakiye alabilirsin

_Herhangi bir sorun yaşarsan admin ile iletişime geç! 🎯_
            """
        else:
            # Kayıtsız kullanıcı için komut listesi
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Hemen Kayıt Ol!", callback_data="register_user")]
            ])
            
            response = f"""
📋 **KULLANILABİLİR KOMUTLAR**

❌ **Şu anda kayıtlı değilsin!**

🎯 **Kayıt olduktan sonra kullanabileceğin komutlar:**
/start - Ana menü ve bot durumu
/menu - Profil menüsü ve istatistikler
/komutlar - Komut listesi
/yardim - Detaylı yardım menüsü
/etkinlikler - Aktif etkinlikleri gör
/market - Market ürünlerini gör
/siparislerim - Sipariş geçmişim
/siralama - Point sıralaması
/profil - Detaylı profil

⬇️ **Hemen kayıt ol ve tüm özelliklere erişim kazan!**
            """
            
            await message.answer(
                response, 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            return
        
        await message.answer(response, parse_mode="Markdown")
        logger.info(f"✅ /komutlar mesajı gönderildi - User: {user.id}")
        
    except Exception as e:
        logger.error(f"❌ /komutlar handler hatası: {e}")
        await message.answer("Bir hata oluştu! Lütfen daha sonra tekrar deneyin.")


async def _send_komutlar_privately(user_id: int):
    """Komutlar mesajını özel mesajla gönder"""
    try:
        if not _bot_instance:
            logger.error("❌ Bot instance bulunamadı!")
            return
        
        # Kullanıcı bilgilerini al
        from database import get_user_info
        user_info = await get_user_info(user_id)
        user_name = user_info.get('first_name', 'Kullanıcı') if user_info else 'Kullanıcı'
        
        # Kullanıcı bilgilerini kaydet
        await save_user_info(user_id, user_info.get('username'), user_name, user_info.get('last_name'))
        
        # Kayıtlı mı kontrol et
        is_registered = await is_user_registered(user_id)
        
        if is_registered:
            # Kayıtlı kullanıcı için komutlar
            response = f"""
📋 **KirveHub Bot - Komut Listesi**

Merhaba {user_name}! İşte kullanabileceğin komutlar:

🎯 **Ana Komutlar:**
• `/start` - Ana menü ve bot durumu
• `/menu` - Profil menüsü ve istatistikler
• `/yardim` - Detaylı yardım menüsü
• `/komutlar` - Bu komut listesi

🎮 **Etkinlik Komutları:**
• `/etkinlikler` - Aktif etkinlikleri gör
• `/katil` - Etkinliğe katıl

🛍️ **Market Komutları:**
• `/market` - Market ürünlerini gör
• `/siparislerim` - Sipariş geçmişim

📊 **İstatistik Komutları:**
• `/siralama` - Point sıralaması
• `/profil` - Detaylı profil

💡 **İpuçları:**
• Grup sohbetlerinde mesaj atarak point kazanabilirsin
• Günlük 5.00 KP limitin var
• Etkinliklere katılarak bonus kazanabilirsin
• Market'ten freespin ve bakiye alabilirsin

_Herhangi bir sorun yaşarsan admin ile iletişime geç! 🎯_
            """
        else:
            # Kayıtsız kullanıcı için komutlar
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Hemen Kayıt Ol!", callback_data="register_user")]
            ])
            
            response = f"""
📋 **KirveHub Bot - Komut Listesi**

Merhaba {user_name}! 

❌ **Şu anda kayıtlı değilsin!**

Bu komutları kullanabilmek için önce sisteme kayıt olman gerekiyor.

🎯 **Kayıt olduktan sonra:**
✅ Point kazanma sistemi
✅ Etkinliklere katılma
✅ Market alışverişi
✅ Profil ve istatistikler
✅ Topluluk özellikleri

⬇️ **Hemen kayıt ol ve sisteme katıl!**
            """
        
        await _bot_instance.send_message(
            user_id,
            response,
            parse_mode="Markdown",
            reply_markup=keyboard if not is_registered else None
        )
        
        logger.info(f"✅ Komutlar mesajı özel mesajla gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Private komutlar hatası: {e}")
        await _bot_instance.send_message(user_id, "❌ Komutlar mesajı gönderilemedi!")


async def kirvekayit_command(message: Message) -> None:
    """
    /kirvekayit komutunu işle
    """
    try:
        user = message.from_user
        
        logger.info(f"👤 /kirvekayit komutu - User: {user.first_name} ({user.id})")
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Kirvekayit komutu mesajı silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_kirvekayit_privately(user.id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        # Kullanıcı bilgilerini kaydet
        await save_user_info(user.id, user.username, user.first_name, user.last_name)
        
        # Zaten kayıtlı mı kontrol et
        if await is_user_registered(user.id):
            await message.answer("✅ Zaten sistemde kayıtlısınız!")
            return
        
        # Kayıt butonu oluştur
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Kayıt Ol!", callback_data="register_user")]
        ])
        
        # Kayıt mesajı
        welcome_text = f"""
🌟 *KirveHub Kayıt Sistemi*

Merhaba {user.first_name}! 

KirveHub topluluğuna katılmak için aşağıdaki butona tıklayın.

📊 *Sistem Bilgileri:*
✅ Güvenli kayıt sistemi
✅ Özel özellikler erişimi
✅ Topluluk etkileşimi

👥 Şu anda *{await get_registered_users_count()}* kişi kayıtlı!

Hazırsanız kayıt olun! ⬇️
        """
        
        await message.answer(
            welcome_text, 
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        logger.info(f"✅ /kirvekayit mesajı gönderildi - User: {user.id}")
        
    except Exception as e:
        logger.error(f"❌ /kirvekayit handler hatası: {e}")
        await message.answer("Bir hata oluştu! Lütfen daha sonra tekrar deneyin.")


async def private_message_handler(message: Message) -> None:
    """
    Özel mesajları karşıla (komut olmayan mesajlar)
    """
    try:
        user = message.from_user
        config = get_config()
        
        logger.info(f"👤 Private mesaj - User: {user.first_name} ({user.id}) - Text: {message.text[:50] if message.text else 'No text'}")
        
        # Admin kontrolü - adminler için mesaj gösterme
        user_rank = await get_user_rank(user.id)
        rank_level = user_rank.get("rank_level", 1)
        
        # Admin 1 ve üstü için mesaj gösterme (rank_level >= 2)
        if rank_level >= 2:
            logger.info(f"🔒 Admin private mesajı - yanıt verilmiyor - User: {user.id}, Rank: {user_rank.get('rank_name', 'Unknown')}")
            return
        
        # Kullanıcı bilgilerini kaydet
        await save_user_info(user.id, user.username, user.first_name, user.last_name)
        
        # Zaten kayıtlı mı kontrol et
        if await is_user_registered(user.id):
            # Kayıtlı kullanıcı - komut olmayan mesaj uyarısı
            response = f"""
⚠️ *Komut Bulunamadı - {user.first_name}*

Yazdığınız şey bir komut değil ya da bir karşılığı yok.

💬 *Mesajınız:* _{message.text[:50] if message.text else 'Dosya/medya'}..._

🤖 *Kullanılabilir Komutlar:*
/start - Ana menü ve bot durumu
/menu - Profil menüsü ve istatistikler
/kirvekayit - Kayıt durumu kontrolü

ℹ️ *Yardım için:* /yardim yazarak komutları öğrenebilirsin ya da /menu gibi şeyler yaz.

_Lütfen geçerli bir komut kullanın! 🎯_
            """
            
            await message.answer(response, parse_mode="Markdown")
        else:
            # KAYIT OLMASI GEREKİYOR - Uyarı ver
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Hemen Kayıt Ol!", callback_data="register_user")],
                [InlineKeyboardButton(text="ℹ️ Neden Kayıt?", callback_data="get_info")]
            ])
            
            registered_count = await get_registered_users_count()
            
            response = f"""
⚠️ *Kayıt Gerekli - {user.first_name}!*

Bu özelliği kullanabilmek için önce sisteme kayıt olmanız gerekiyor.

🚫 *Şu anda erişiminiz yok:*
❌ Mesaj gönderme
❌ Özel içerikler
❌ Topluluk özellikleri

🎯 *Kayıt olduktan sonra:*
✅ Tam erişim
✅ Özel özellikler
✅ Topluluk etkileşimi

👥 Şu anda *{registered_count}* kişi kayıtlı!

⬇️ **Hemen kayıt olun ve sisteme katılın!**
            """
            
            await message.answer(
                response, 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        
        logger.info(f"✅ Private message yanıtı gönderildi - User: {user.id}")
        
    except Exception as e:
        logger.error(f"❌ Private message handler hatası: {e}")
        await message.answer("Bir hata oluştu! Lütfen daha sonra tekrar deneyin.")


async def kayitol_command(message: Message) -> None:
    """
    !kayitol komutu - Grupta yazıldığında otomatik kayıt
    """
    try:
        user = message.from_user
        chat = message.chat
        
        # Sadece grup/supergroup'da çalış
        if chat.type not in ["group", "supergroup"]:
            return
        
        logger.info(f"🎯 !kayitol komutu - User: {user.first_name} ({user.id}), Group: {chat.id}")
        
        # Kullanıcı bilgilerini kaydet
        await save_user_info(user.id, user.username, user.first_name, user.last_name)
        
        # Zaten kayıtlı mı kontrol et
        if await is_user_registered(user.id):
            # Komut mesajını sil
            try:
                await message.delete()
            except:
                pass
            
            # Özelden zaten kayıtlı mesajı gönder
            if _bot_instance:
                try:
                    await _bot_instance.send_message(
                        user.id,
                        f"""
✅ <b>Zaten Kayıtlısınız!</b>

Merhaba {user.first_name}! 

Sistemde zaten kayıtlısınız. Tüm özelliklere erişebilirsiniz.

💡 <b>Komutlar:</b>
• <code>/menu</code> - Ana menü
• <code>/market</code> - Market
• <code>/profil</code> - Profil

🎯 <b>Point kazanmaya devam edin!</b>
                        """,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.debug(f"⏸️ Özel mesaj gönderilemedi - User: {user.id}, Error: {e}")
            return
        
        # Kullanıcıyı kayıt et
        success = await register_user(user.id)
        
        if success:
            # Başarılı kayıt
            registered_count = await get_registered_users_count()
            
            # Komut mesajını sil
            try:
                await message.delete()
            except:
                pass
            
            # Özelden tebrik mesajı gönder
            if _bot_instance:
                try:
                    welcome_message = f"""
🎉 <b>TEBRİKLER! KAYIT OLDUNUZ!</b>

Merhaba {user.first_name}! 

✅ <b>Başarıyla kayıt oldunuz!</b>

📊 <b>Sistem Bilgileri:</b>
• Toplam kayıtlı üye: <b>{registered_count}</b>
• Kayıt tarihi: <b>{datetime.now().strftime('%d.%m.%Y %H:%M')}</b>

🎯 <b>Artık Yapabilecekleriniz:</b>
• 💎 <b>Point kazanma</b> - Her mesajınız point kazandırır
• 🛍️ <b>Market alışverişi</b> - Point'lerinizle freespin ve bakiye alın
• 🎮 <b>Etkinliklere katılma</b> - Özel etkinliklerde yer alın
• 📊 <b>Profil ve istatistikler</b> - İlerlemenizi takip edin
• 🏆 <b>Sıralama</b> - En aktif üyeler arasında yer alın

💡 <b>Hemen Başlayın:</b>
• <code>/menu</code> - Ana menüyü açın
• <code>/market</code> - Market'e göz atın
• <code>/profil</code> - Profilinizi görüntüleyin

🎯 <b>Point Kazanmak İçin:</b>
Grup sohbetlerinde mesaj atarak otomatik olarak point kazanırsınız!

🚀 <b>Başarılar dileriz!</b>
                    """
                    
                    await _bot_instance.send_message(
                        user.id,
                        welcome_message,
                        parse_mode="HTML"
                    )
                    
                    logger.info(f"✅ Kayıt başarılı ve tebrik mesajı gönderildi - User: {user.id}")
                except Exception as e:
                    logger.error(f"❌ Tebrik mesajı gönderilemedi - User: {user.id}, Error: {e}")
        else:
            # Kayıt başarısız
            try:
                await message.delete()
            except:
                pass
            
            if _bot_instance:
                try:
                    await _bot_instance.send_message(
                        user.id,
                        "❌ Kayıt işlemi sırasında bir hata oluştu! Lütfen daha sonra tekrar deneyin.",
                        parse_mode="HTML"
                    )
                except:
                    pass
            
    except Exception as e:
        logger.error(f"❌ !kayitol komutu hatası: {e}", exc_info=True)
        try:
            await message.delete()
        except:
            pass


async def register_callback_handler(callback: CallbackQuery) -> None:
    """
    Kayıt butonu callback'ini işle
    """
    try:
        user = callback.from_user
        
        if callback.data == "register_user":
            logger.info(f"🎯 Kayıt callback - User: {user.first_name} ({user.id})")
            
            # Zaten kayıtlı mı kontrol et
            if await is_user_registered(user.id):
                await callback.answer("✅ Zaten kayıtlısınız!", show_alert=True)
                return
            
            # Kullanıcıyı kayıt et
            success = await register_user(user.id)
            
            if success:
                # Başarılı kayıt
                registered_count = await get_registered_users_count()
                
                # İlk üye bonusu kontrol et ve ver (DEPRECATED - removed)
                # bonus_given = await check_and_give_first_user_bonus(callback.message)
                bonus_given = False
                
                if bonus_given:
                    # Bonus verildi, özel mesaj
                    success_message = f"""
🎉 *Kayıt Başarılı!*

Tebrikler {user.first_name}! KirveHub topluluğuna başarıyla katıldınız!

🎁 *HOŞ GELDİN BONUSU!*
💰 +1.00 Kirve Point hesabınıza eklendi!

📊 *Kayıt Bilgileri:*
✅ Üye ID: {user.id}
✅ Kayıt Tarihi: Şimdi
✅ Durum: Aktif
🎁 Bonus: Verildi

👥 Siz {registered_count}. üyemizsiniz!

🚀 *Artık Erişebileceğiniz Özellikler:*
🎯 Özel komutlar
📊 İstatistikler  
🎪 Etkinlikler
💬 Topluluk sohbeti

_Hoş geldiniz! 🌟_
                    """
                else:
                    # Normal kayıt mesajı
                    success_message = f"""
🎉 *Kayıt Başarılı!*

Tebrikler {user.first_name}! KirveHub topluluğuna başarıyla katıldınız!

📊 *Kayıt Bilgileri:*
✅ Üye ID: {user.id}
✅ Kayıt Tarihi: Şimdi
✅ Durum: Aktif

👥 Siz {registered_count}. üyemizsiniz!

🚀 *Artık Erişebileceğiniz Özellikler:*
🎯 Özel komutlar
📊 İstatistikler  
🎪 Etkinlikler
💬 Topluluk sohbeti

_Hoş geldiniz! 🌟_
                    """
                
                # Eski mesajı düzenle
                await callback.message.edit_text(
                    success_message,
                    parse_mode="Markdown"
                )
                
                await callback.answer("🎉 Başarıyla kayıt oldunuz!")
                
                logger.info(f"✅ Kullanıcı kayıt edildi - User: {user.id}")
                
            else:
                await callback.answer("❌ Kayıt sırasında hata oluştu!", show_alert=True)
                logger.error(f"❌ Kayıt başarısız - User: {user.id}")
        
        elif callback.data == "get_info":
            info_text = """
ℹ️ *KirveHub Hakkında*

KirveHub, teknoloji meraklıları için özel bir topluluktur.

🎯 *Özellikler:*
• Güncel teknoloji haberleri
• Özel eğitim içerikleri  
• Projeler ve iş birlikleri
• Networking imkanları

📝 *Kayıt Süreci:*
1. "Kayıt Ol!" butonuna tıklayın
2. Otomatik kayıt tamamlanır
3. Özel özelliklere erişim kazanırsınız

_Bizi tercih ettiğiniz için teşekkürler! 🙏_
            """
            
            await callback.answer()
            await callback.message.answer(info_text, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"❌ Register callback hatası: {e}")
        await callback.answer("Bir hata oluştu!", show_alert=True)


async def kayitsil_command(message: Message) -> None:
    """
    /kayitsil komutunu işle
    """
    try:
        user = message.from_user
        
        logger.info(f"👤 /kayitsil komutu - User: {user.first_name} ({user.id})")
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Kayitsil komutu mesajı silindi - Group: {message.chat.id}")
                
                # ÖZELİNDE YANIT VER
                if _bot_instance:
                    await _send_kayitsil_privately(user.id)
                return
                
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        # Kullanıcı bilgilerini kaydet
        await save_user_info(user.id, user.username, user.first_name, user.last_name)
        
        # Kullanıcı kayıtlı mı kontrol et
        if not await is_user_registered(user.id):
            await message.answer("❌ Zaten kayıtlı değilsiniz!")
            return
        
        # Kaydı sil
        success = await unregister_user(user.id)
        
        if success:
            registered_count = await get_registered_users_count()
            
            response = f"""
🗑️ *Kayıt Silindi!*

{user.first_name}, kaydınız başarıyla silindi.

📊 *Durum:*
❌ Artık kayıtlı değilsiniz
🔄 Yeniden kayıt olabilirsiniz
👥 Kalan kayıtlı: {registered_count} kişi

⚠️ *Bu bir test komutuydu!*

🎯 Yeniden kayıt olmak için:
/kirvekayit komutunu kullanın

_Test başarılı! 🧪_
            """
            
            await message.answer(response, parse_mode="Markdown")
            logger.info(f"✅ Kayıt silme işlemi tamamlandı - User: {user.id}")
            
        else:
            await message.answer("❌ Kayıt silme sırasında hata oluştu!")
            
    except Exception as e:
        logger.error(f"❌ /kayitsil handler hatası: {e}")
        await message.answer("Bir hata oluştu! Lütfen daha sonra tekrar deneyin.") 

async def _send_kirvekayit_privately(user_id: int):
    """Kirvekayit mesajını özel mesajla gönder"""
    try:
        if not _bot_instance:
            logger.error("❌ Bot instance bulunamadı!")
            return
        
        # Kullanıcı bilgilerini al
        from database import get_user_info
        user_info = await get_user_info(user_id)
        user_name = user_info.get('first_name', 'Kullanıcı') if user_info else 'Kullanıcı'
        
        # Kullanıcı bilgilerini kaydet
        await save_user_info(user_id, user_info.get('username'), user_name, user_info.get('last_name'))
        
        # Kayıtlı mı kontrol et
        is_registered = await is_user_registered(user_id)
        
        if is_registered:
            response = f"""
✅ **Zaten Kayıtlısın!**

Merhaba {user_name}! 

Sen zaten KirveHub sistemine kayıtlısın. 
Tüm özellikleri kullanabilirsin!

🎯 **Kullanabileceğin Komutlar:**
• `/menu` - Profil menüsü ve istatistikler
• `/market` - Market ürünleri
• `/etkinlikler` - Aktif etkinlikler
• `/yardim` - Yardım menüsü

💎 **Hemen sohbete katıl ve point kazanmaya başla!**
            """
        else:
            # Kayıtsız kullanıcı için kayıt teşviki
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Hemen Kayıt Ol!", callback_data="register_user")]
            ])
            
            response = f"""
🎉 **KirveHub'a Hoş Geldin!**

Merhaba {user_name}! 

❌ **Henüz kayıtlı değilsin!**

🎁 **Kayıt olduktan sonra:**
• 💎 **Günlük 5 Kirve Point** - Her mesajın point kazandırır!
• 🛍️ **Market sistemi** - Freespinler, site bakiyeleri
• 🎮 **Etkinliklere katılım** - Çekilişler, bonus hunt'lar
• 📊 **Detaylı istatistikler** - Sıralamadaki yerini takip et!
• 🏆 **Özel ayrıcalıklar** - Sadece kayıtlı üyeler!

⬇️ **Hemen kayıt ol ve sisteme katıl!**
            """
        
        await _bot_instance.send_message(
            user_id,
            response,
            parse_mode="Markdown",
            reply_markup=keyboard if not is_registered else None
        )
        
        logger.info(f"✅ Kirvekayit mesajı özel mesajla gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Private kirvekayit hatası: {e}")
        await _bot_instance.send_message(user_id, "❌ Kayıt mesajı gönderilemedi!")

async def _send_kayitsil_privately(user_id: int):
    """Kayitsil mesajını özel mesajla gönder"""
    try:
        if not _bot_instance:
            logger.error("❌ Bot instance bulunamadı!")
            return
        
        # Kullanıcı bilgilerini al
        from database import get_user_info
        user_info = await get_user_info(user_id)
        user_name = user_info.get('first_name', 'Kullanıcı') if user_info else 'Kullanıcı'
        
        # Kullanıcı bilgilerini kaydet
        await save_user_info(user_id, user_info.get('username'), user_name, user_info.get('last_name'))
        
        # Kayıtlı mı kontrol et
        is_registered = await is_user_registered(user_id)
        
        if not is_registered:
            response = f"""
❌ **Zaten Kayıtsızsın!**

Merhaba {user_name}! 

Sen zaten KirveHub sisteminde kayıtlı değilsin.
Kayıt olmak için `/kirvekayit` komutunu kullanabilirsin.
            """
        else:
            # Kayıtlı kullanıcı için silme onayı
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑️ Kaydımı Sil", callback_data="delete_user_confirm")],
                [InlineKeyboardButton(text="❌ İptal", callback_data="delete_user_cancel")]
            ])
            
            response = f"""
⚠️ **Kayıt Silme Onayı**

Merhaba {user_name}! 

✅ **Şu anda kayıtlısın!**

🗑️ **Kaydını silmek istediğinden emin misin?**

**Bu işlem geri alınamaz ve:**
• Tüm pointlerin silinir
• Profil bilgilerin silinir
• Etkinlik geçmişin silinir
• Market siparişlerin silinir

**Onaylıyor musun?**
            """
        
        await _bot_instance.send_message(
            user_id,
            response,
            parse_mode="Markdown",
            reply_markup=keyboard if is_registered else None
        )
        
        logger.info(f"✅ Kayitsil mesajı özel mesajla gönderildi - User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Private kayitsil hatası: {e}")
        await _bot_instance.send_message(user_id, "❌ Kayıt silme mesajı gönderilemedi!") 