"""
🧪 Test Komutları - Görsel ve seviye sistemi testleri
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import is_admin
from handlers.membership_levels import (
    get_random_avatar,
    get_level_icon_path,
    get_level_icon_file,
    get_level_info,
    get_membership_level,
    format_level_display,
    get_level_info_by_messages,
    get_next_level_info,
    check_level_up
)
from handlers.message_monitor import (
    get_random_notification_image,
    send_private_point_notification,
    send_level_up_notification
)
from pathlib import Path

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("testavatar"))
async def test_avatar_command(message: Message):
    """Avatar seçimini test et"""
    try:
        logger.info(f"🧪 testavatar komutu çağrıldı - User: {message.from_user.id}")
        if not is_admin(message.from_user.id):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        # 5 rastgele avatar seç
        avatars = []
        for i in range(5):
            avatar = get_random_avatar()
            if avatar:
                avatars.append(Path(avatar).name)
        
        if avatars:
            response = "🖼️ **AVATAR SEÇİM TESTİ**\n\n"
            response += "✅ **Seçilen Avatarlar:**\n"
            for i, avatar_name in enumerate(avatars, 1):
                response += f"{i}. `{avatar_name}`\n"
            response += f"\n📊 **Toplam:** {len(avatars)} avatar seçildi"
        else:
            response = "❌ **Avatar bulunamadı!**\n\n"
            response += "💡 `assets/avatars/` klasörüne avatar görselleri ekleyin."
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Avatar test hatası: {e}")
        await message.reply(f"❌ Test hatası: {e}")


@router.message(Command("testseviye"))
async def test_level_command(message: Message):
    """Seviye sistemini test et"""
    try:
        if not is_admin(message.from_user.id):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        # Test mesaj sayıları
        test_cases = [
            (0, "Yeni kullanıcı"),
            (250, "Bronz"),
            (500, "Gümüş'e geçiş"),
            (1000, "Gümüş"),
            (2000, "Altın'a geçiş"),
            (3000, "Altın"),
            (5000, "Platin'e geçiş"),
            (15000, "Elmas'a geçiş"),
        ]
        
        response = "🎯 **SEVİYE SİSTEMİ TESTİ**\n\n"
        
        for msg_count, description in test_cases:
            level = get_membership_level(msg_count)
            level_display = format_level_display(msg_count)
            level_info = get_level_info_by_messages(msg_count)
            next_level = get_next_level_info(msg_count)
            
            response += f"**{description}** ({msg_count:,} mesaj):\n"
            response += f"• Seviye: {level_display}\n"
            if next_level:
                response += f"• Sonraki: {next_level['emoji']} {next_level['name']} ({next_level['messages_needed']:,} mesaj)\n"
            response += "\n"
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Seviye test hatası: {e}")
        await message.reply(f"❌ Test hatası: {e}")


@router.message(Command("testikon"))
async def test_icon_command(message: Message):
    """Seviye ikonlarını test et"""
    try:
        if not is_admin(message.from_user.id):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        levels = ["bronz", "gümüş", "gold", "plat", "diamond"]
        
        response = "🏆 **SEVİYE İKONLARI TESTİ**\n\n"
        
        all_ok = True
        for level in levels:
            icon_path = get_level_icon_path(level)
            if icon_path:
                response += f"✅ **{level}**: `{Path(icon_path).name}`\n"
            else:
                response += f"❌ **{level}**: Bulunamadı\n"
                all_ok = False
        
        if all_ok:
            response += "\n✅ **Tüm ikonlar mevcut!**"
        else:
            response += "\n⚠️ **Eksik ikonlar var!** `assets/membership_levels/` klasörünü kontrol edin."
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ İkon test hatası: {e}")
        await message.reply(f"❌ Test hatası: {e}")


@router.message(Command("testbildirim"))
async def test_notification_command(message: Message):
    """Bildirim gönderme testi (GERÇEK)"""
    try:
        logger.info(f"🧪 testbildirim komutu çağrıldı - User: {message.from_user.id}")
        if not is_admin(message.from_user.id):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        
        # Point bildirimi gönder
        await send_private_point_notification(
            user_id=user_id,
            first_name=first_name,
            total_points=247.14,
            total_messages=282,
            group_name="KirveHubSohbet",
            earned_points=0.10,
            is_milestone=False
        )
        
        await message.reply("✅ **Test bildirimi gönderildi!**\n\n📱 Özel mesajınızı kontrol edin.")
        
    except Exception as e:
        logger.error(f"❌ Bildirim test hatası: {e}")
        await message.reply(f"❌ Test hatası: {e}")


@router.message(Command("testseviyeatlama"))
async def test_level_up_command(message: Message):
    """Seviye atlama bildirimi testi (GERÇEK)"""
    try:
        if not is_admin(message.from_user.id):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        
        # Seviye atlama simülasyonu (Bronz → Gümüş)
        level_up_info = check_level_up(499, 500)
        
        if not level_up_info:
            # Manuel oluştur
            from handlers.membership_levels import get_level_info
            level_up_info = {
                "old_level": "bronz",
                "new_level": "gümüş",
                "old_level_info": get_level_info("bronz"),
                "new_level_info": get_level_info("gümüş"),
                "old_messages": 499,
                "new_messages": 500
            }
        
        await send_level_up_notification(
            user_id=user_id,
            first_name=first_name,
            level_up_info=level_up_info
        )
        
        await message.reply("✅ **Seviye atlama bildirimi gönderildi!**\n\n📱 Özel mesajınızı kontrol edin.")
        
    except Exception as e:
        logger.error(f"❌ Seviye atlama test hatası: {e}")
        await message.reply(f"❌ Test hatası: {e}")


@router.message(Command("testikonlar"))
async def test_icons_send_command(message: Message):
    """Seviye ikonlarını direkt gönder (görsel test)"""
    try:
        logger.info(f"🧪 testikonlar komutu çağrıldı - User: {message.from_user.id}")
        if not is_admin(message.from_user.id):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        from aiogram import Bot
        from config import get_config
        
        config = get_config()
        bot = Bot(token=config.BOT_TOKEN)
        user_id = message.from_user.id
        
        levels = ["bronz", "gümüş", "gold", "plat", "diamond"]
        sent_count = 0
        
        for level in levels:
            level_icon = get_level_icon_file(level)
            if level_icon:
                try:
                    # Her seviye için bilgi al
                    level_info = get_level_info(level)
                    
                    caption = f"🏆 **{level_info['name']} Seviye İkonu**\n\n{level_info['emoji']} {level_info['name']}"
                    
                    await bot.send_photo(
                        user_id,
                        photo=level_icon,
                        caption=caption,
                        parse_mode="Markdown"
                    )
                    sent_count += 1
                    logger.info(f"✅ {level} ikonu gönderildi")
                except Exception as e:
                    logger.warning(f"⚠️ {level} ikonu gönderilemedi: {e}")
            else:
                logger.warning(f"⚠️ {level} ikonu bulunamadı")
        
        await bot.session.close()
        
        if sent_count > 0:
            await message.reply(f"✅ **{sent_count}/{len(levels)} seviye ikonu gönderildi!**\n\n📱 Özel mesajınızı kontrol edin.")
        else:
            await message.reply("❌ **Hiçbir ikon gönderilemedi!**\n\n📁 `assets/membership_levels/` klasörünü kontrol edin.")
        
    except Exception as e:
        logger.error(f"❌ İkon gönderme test hatası: {e}")
        await message.reply(f"❌ Test hatası: {e}")


@router.message(Command("testtum"))
async def test_all_command(message: Message):
    """Tüm testleri çalıştır"""
    try:
        if not is_admin(message.from_user.id):
            await message.reply("❌ Bu komutu sadece admin kullanabilir!")
            return
        
        response = "🧪 **TÜM TESTLER**\n\n"
        
        # 1. Avatar testi
        avatar = get_random_avatar()
        if avatar:
            response += f"✅ Avatar: `{Path(avatar).name}`\n"
        else:
            response += "❌ Avatar: Bulunamadı\n"
        
        # 2. Seviye ikonları testi
        icons_ok = all(get_level_icon_path(level) for level in ["bronz", "gümüş", "gold", "plat", "diamond"])
        if icons_ok:
            response += "✅ Seviye İkonları: Tümü mevcut\n"
        else:
            response += "❌ Seviye İkonları: Eksik var\n"
        
        # 3. Seviye sistemi testi
        test_levels = [
            (0, "bronz"),
            (500, "gümüş"),
            (2000, "gold"),
            (5000, "plat"),
            (15000, "diamond")
        ]
        levels_ok = all(get_membership_level(msg) == level for msg, level in test_levels)
        if levels_ok:
            response += "✅ Seviye Sistemi: Çalışıyor\n"
        else:
            response += "❌ Seviye Sistemi: Hata var\n"
        
        # 4. Point bildirim görselleri
        image_path = await get_random_notification_image()
        if image_path:
            response += f"✅ Point Bildirim Görseli: `{Path(image_path).name}`\n"
        else:
            response += "⚠️ Point Bildirim Görseli: Yok (isteğe bağlı)\n"
        
        response += "\n💡 **Detaylı test için:**\n"
        response += "• `/testavatar` - Avatar testi\n"
        response += "• `/testseviye` - Seviye sistemi testi\n"
        response += "• `/testikon` - İkon testi\n"
        response += "• `/testikonlar` - İkonları direkt gönder (görsel test)\n"
        response += "• `/testbildirim` - Bildirim gönderme testi\n"
        response += "• `/testseviyeatlama` - Seviye atlama testi"
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Test hatası: {e}")
        await message.reply(f"❌ Test hatası: {e}")


@router.message(Command("testyardim"))
async def test_help_command(message: Message):
    """Test komutları yardım"""
    try:
        response = """
🧪 **TEST KOMUTLARI YARDIM**

**Kontrol Testleri (Bildirim Göndermez):**
• `/testtum` - Tüm sistemleri kontrol et
• `/testavatar` - Avatar seçimini test et
• `/testseviye` - Seviye sistemini test et
• `/testikon` - Seviye ikonlarını kontrol et

**Gerçek Bildirim Testleri (Dikkat: Bildirim Gönderir):**
• `/testbildirim` - Point bildirimi gönder
• `/testseviyeatlama` - Seviye atlama bildirimi gönder
• `/testikonlar` - Tüm seviye ikonlarını direkt gönder (görsel test)

**Yardım:**
• `/testyardim` - Bu yardım mesajı

💡 **Not:** Tüm test komutları sadece admin tarafından kullanılabilir.
        """
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Yardım hatası: {e}")
        await message.reply(f"❌ Hata: {e}")

