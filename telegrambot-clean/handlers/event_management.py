"""
🏁 Çekiliş Yönetimi Sistemi - KirveHub Bot
/cekilisbitir komutu ve çekiliş sonlandırma işlemleri
"""

import logging
from datetime import datetime
from typing import Optional, Dict
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config import get_config
from database import db_pool, end_event, get_event_participant_count, get_event_winners, get_latest_active_event_in_group, get_event_info_for_end, cancel_event, get_event_status
from utils.logger import logger

router = Router()

# Bot instance setter
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

async def end_lottery_command(message: Message):
    """Çekiliş bitirme komutu - /cekilisbitir"""
    try:
        # Admin kontrolü (DB tabanlı)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(message.from_user.id, 3):
            return
        
        # 🔥 GRUP SESSİZLİK: Grup chatindeyse sil ve özel mesajla yanıt ver
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Çekiliş bitir komutu mesajı silindi - Group: {message.chat.id}")
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                # Silme başarısız olsa da devam et
        
        # ID kontrolü - Direkt komuttan
        args = message.text.split()
        event_id = None
        target_group_id = None
        
        if len(args) >= 2:
            try:
                event_id = int(args[1])
                logger.info(f"🎯 ID ile çekiliş bitirme: {event_id}")
                
                # Eğer 3. parametre varsa grup ID'si
                if len(args) >= 3:
                    try:
                        target_group_id = int(args[2])
                        logger.info(f"🎯 Grup ID ile çekiliş bitirme: Event {event_id}, Group {target_group_id}")
                    except ValueError:
                        logger.warning(f"⚠️ Geçersiz grup ID: {args[2]}")
                        
            except ValueError:
                error_message = "❌ Geçersiz çekiliş ID! Örnek: `/cekilisbitir 123` veya `/cekilisbitir 123 456789`"
                if message.chat.type == "private":
                    await message.reply(error_message)
                else:
                    if _bot_instance:
                        await _bot_instance.send_message(message.from_user.id, error_message)
                return
        
        # ID yoksa reply kontrolü
        if not event_id:
            if message.reply_to_message:
                try:
                    # Reply'den event ID'sini çıkar
                    reply_text = message.reply_to_message.text
                    # Event ID'sini bul (örnek: "🎯 ID: 123" formatında)
                    import re
                    id_match = re.search(r'🎯\s*ID:\s*(\d+)', reply_text)
                    if id_match:
                        event_id = int(id_match.group(1))
                        logger.info(f"🎯 Reply'den çekiliş ID'si alındı: {event_id}")
                except Exception as e:
                    logger.error(f"❌ Reply'den ID çıkarma hatası: {e}")
            
            if not event_id:
                error_message = "❌ Çekiliş ID'si bulunamadı!\n\n" \
                               "**Kullanım:**\n" \
                               "• `/cekilisbitir 123` (ID ile)\n" \
                               "• `/cekilisbitir 123 456789` (ID ve Grup ID ile)\n" \
                               "• Çekiliş mesajına reply yapıp `/cekilisbitir`"
                if message.chat.type == "private":
                    await message.reply(error_message, parse_mode="Markdown")
                else:
                    if _bot_instance:
                        await _bot_instance.send_message(message.from_user.id, error_message, parse_mode="Markdown")
                return
        
        logger.info(f"🎯 Bitirilecek çekiliş ID: {event_id}, Hedef Grup: {target_group_id}")
        
        # Çekiliş detaylarını al
        event_details = await get_event_info_for_end(event_id)
        if not event_details:
            error_message = "❌ Çekiliş bulunamadı veya zaten bitmiş!"
            if message.chat.type == "private":
                await message.reply(error_message)
            else:
                if _bot_instance:
                    await _bot_instance.send_message(message.from_user.id, error_message)
            return
        
        # Grup kontrolü - Eğer hedef grup belirtilmişse kontrol et
        if target_group_id:
            event_group_id = event_details.get('group_id')
            if event_group_id and event_group_id != target_group_id:
                error_message = f"❌ Bu çekiliş farklı bir grupta! (Event: {event_id}, Event Group: {event_group_id}, Target Group: {target_group_id})"
                if message.chat.type == "private":
                    await message.reply(error_message)
                else:
                    if _bot_instance:
                        await _bot_instance.send_message(message.from_user.id, error_message)
                return
        
        # Çekiliş bitirme işlemi - Sadece bitirme, kazanan işleme yok
        success = await end_event(event_id)
        
        if success:
            # Kazananları tekrar al (end_event'ten sonra)
            participant_count = await get_event_participant_count(event_id)
            winners = await get_event_winners(event_id, event_details.get('max_winners', 1))
            
            # Point havuzu hesapla
            total_pool = participant_count * event_details.get('entry_cost', 0)
            winner_share = total_pool / len(winners) if winners else 0
            
            # Kazananlara point ver
            if winners:
                from database import add_message_to_user
                for winner in winners:
                    try:
                        # Kazananlara point ver
                        await add_message_to_user(
                            winner['user_id'], 
                            winner_share,
                            group_id=event_details.get('group_id')
                        )
                        
                        # Kazananlara özel bildirim gönder
                        winner_message = f"""
🎉 **TEBRİKLER! ÇEKİLİŞ KAZANDINIZ!** 🎉

🏆 **Çekiliş:** {event_details.get('title', 'Çekiliş')}
💰 **Kazandığınız:** {winner_share:.2f} KP
👥 **Toplam Katılımcı:** {participant_count} kişi
🎯 **Çekiliş ID:** {event_id}

🎊 **İyi şanslar!**
                        """
                        
                        # Mesaj context bot'u ile gönder
                        await message.bot.send_message(
                            winner['user_id'],
                            winner_message,
                            parse_mode="Markdown"
                        )
                        logger.info(f"🎉 Kazanan bildirimi gönderildi: User {winner['user_id']}")
                    except Exception as e:
                        logger.error(f"❌ Kazanan bildirimi gönderilemedi: User {winner['user_id']}, Error: {e}")
            
            # Kazanan listesi oluştur - DETAYLI
            winner_list = []
            winner_mentions = []
            logger.info(f"🔍 Event {event_id} - Winners processing: {winners}")
            
            for winner in winners:
                username = winner.get('username')
                user_id = winner.get('user_id')
                first_name = winner.get('first_name', '')
                last_name = winner.get('last_name', '')
                payment_amount = winner.get('payment_amount', 0)
                
                logger.info(f"🔍 Event {event_id} - Processing winner: username={username}, user_id={user_id}, first_name={first_name}, last_name={last_name}, payment_amount={payment_amount}")
                
                # Kullanıcı adı varsa
                if username:
                    winner_info = f"@{username}"
                    winner_mentions.append(f"@{username}")
                # Ad soyad varsa
                elif first_name or last_name:
                    full_name = f"{first_name} {last_name}".strip()
                    winner_info = f"<b>{full_name}</b>"
                    winner_mentions.append(full_name)
                # Sadece ID
                elif user_id:
                    winner_info = f"<b>ID: {user_id}</b>"
                    winner_mentions.append("ID: {user_id}")
                else:
                    winner_info = f"<b>Bilinmeyen Kullanıcı</b>"
                    winner_mentions.append("Bilinmeyen Kullanıcı")
                
                # Katılım miktarını da ekle
                winner_info += f" <code>({payment_amount:.2f} KP)</code>"
                winner_list.append(winner_info)
                logger.info(f"🔍 Event {event_id} - Winner info created: {winner_info}")
            
            logger.info(f"🔍 Event {event_id} - Winner list: {winner_list}")
            logger.info(f"🔍 Event {event_id} - Winner mentions: {winner_mentions}")
            
            if winner_list:
                winners_text = "\n".join([f"🏆 {winner}" for winner in winner_list])
            else:
                winners_text = "❌ <b>Kazanan bulunamadı</b>"
            
            # Çekiliş sonuç mesajı - DETAYLI
            event_completion_message = f"""
╔══════════════════════╗
║   🏁 <b>ÇEKİLİŞ SONUÇLANDI</b> 🏁   ║
╚══════════════════════╝

📊 <b>Çekiliş Detayları:</b>
• 🎯 ID: <code>{event_id}</code>
• 👥 Katılımcı: <code>{participant_count}</code> kişi
• 🏆 Kazanan: <code>{len(winners)}</code> kişi
• 📅 Bitiş: <code>{datetime.now().strftime('%d.%m.%Y %H:%M')}</code>

🎉 <b>KAZANANLAR:</b>
{winners_text}

💰 <b>Point Dağıtımı:</b>
• Toplam Havuz: <code>{total_pool:.2f} KP</code>
• Kazanan Başına: <code>{winner_share:.2f} KP</code>

╔══════════════════════╗
║   🎊 <b>ÇEKİLİŞ TAMAMLANDI</b> 🎊   ║
╚══════════════════════╝
            """
            
            # 1. KİRVEBOT SOHBETİNDE SONUÇ GÖSTER
            completion_msg = await message.answer(event_completion_message, parse_mode="HTML")
            
            # 2. ÇEKİLİŞİN OLDUĞU GRUPTA DA SONUÇ GÖSTER
            try:
                # Öncelik: hedef grup parametresi veya etkinliğin kayıtlı grup_id'si
                announce_group_id = target_group_id or event_details.get('group_id')
                if announce_group_id:
                    try:
                        await message.bot.send_message(
                            announce_group_id,
                            event_completion_message,
                            parse_mode="HTML"
                        )
                        logger.info(f"✅ Çekiliş sonucu etkinlik grubuna gönderildi: Group {announce_group_id}")
                    except Exception as send_err:
                        logger.error(f"❌ Çekiliş sonucu grup gönderimi başarısız: Group {announce_group_id}, Error: {send_err}")
                else:
                    logger.info("ℹ️ Etkinliğe bağlı grup bulunamadı, yalnızca komut sohbetinde gösterildi")
            except Exception as e:
                logger.error(f"❌ Grup mesajı gönderim blok hatası: {e}")
            
            logger.info(f"✅ Çekiliş başarıyla bitirildi: Event {event_id}, Winners: {len(winners)}")
            
        else:
            error_message = "❌ Çekiliş bitirilemedi! Sistem hatası."
            if message.chat.type == "private":
                await message.reply(error_message)
            else:
                if _bot_instance:
                    await _bot_instance.send_message(message.from_user.id, error_message)
            
    except Exception as e:
        logger.error(f"❌ Çekiliş bitirme hatası: {e}")
        error_message = "❌ Çekiliş bitirme sırasında hata oluştu!"
        if message.chat.type == "private":
            await message.reply(error_message)
        else:
            if _bot_instance:
                await _bot_instance.send_message(message.from_user.id, error_message)

@router.message(Command("etkinlikiptal"))
async def cancel_event_command(message: Message):
    """Etkinlik iptal etme komutu - /etkinlikiptal ID"""
    try:
        # Admin kontrolü (DB tabanlı)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(message.from_user.id, 3):
            return
        
        # Grup chatindeyse komut mesajını sil ve sessiz çalış
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
            return
        
        # Komut metnini parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        if len(parts) != 2:
            await message.reply("❌ Kullanım: `/etkinlikiptal ID`")
            return
        
        try:
            event_id = int(parts[1])
        except ValueError:
            await message.reply("❌ Geçersiz ID! Sayı olmalı.")
            return
        
        # Etkinliği iptal et
        success = await cancel_event(event_id)
        
        if success:
            await message.reply(f"✅ Etkinlik başarıyla iptal edildi! ID: {event_id}")
        else:
            await message.reply(f"❌ Etkinlik iptal edilemedi! ID: {event_id}")
        
    except Exception as e:
        logger.error(f"❌ Etkinlik iptal hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

@router.message(Command("etkinlikdurum"))
async def event_status_command(message: Message):
    """Etkinlik durumu komutu - /etkinlikdurum ID"""
    try:
        # Admin kontrolü (DB tabanlı)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(message.from_user.id, 3):
            return
        
        # Grup chatindeyse komut mesajını sil ve sessiz çalış
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
            return
        
        # Komut metnini parse et
        command_text = message.text.strip()
        parts = command_text.split()
        
        if len(parts) != 2:
            await message.reply("❌ Kullanım: `/etkinlikdurum ID`")
            return
        
        try:
            event_id = int(parts[1])
        except ValueError:
            await message.reply("❌ Geçersiz ID! Sayı olmalı.")
            return
        
        # Etkinlik durumunu getir
        event_info = await get_event_status(event_id)
        
        if event_info:
            response = f"""
📊 **ETKİNLİK DURUMU**

🎯 **ID:** {event_id}
📝 **Başlık:** {event_info['title']}
💰 **Katılım:** {event_info['entry_cost']:.2f} KP
🏆 **Kazanan:** {event_info['max_winners']} kişi
👥 **Katılımcı:** {event_info['participant_count']} kişi
📅 **Durum:** {event_info['status']}
⏰ **Oluşturulma:** {event_info['created_at']}
            """
        else:
            response = f"❌ Etkinlik bulunamadı! ID: {event_id}"
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Etkinlik durum hatası: {e}")
        await message.reply("❌ Bir hata oluştu!") 

@router.message(Command("etkinlikyardım"))
async def event_help_command(message: Message):
    """Etkinlik komutları yardım: /etkinlikyardım"""
    try:
        # Admin kontrolü (DB tabanlı)
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(message.from_user.id, 3):
            return
        
        # Grup chatindeyse komut mesajını sil ve sessiz çalış
        if message.chat.type != "private":
            try:
                await message.delete()
            except:
                pass
            return
        
        response = """
🎯 **ETKİNLİK SİSTEMİ YARDIM**

**🎲 Etkinlik Oluşturma:**
• `/etkinlik` - Yeni etkinlik oluştur
• `/cekilisyap` - Çekiliş oluştur (alias)

**🏁 Etkinlik Yönetimi:**
• `/cekilisbitir ID` - Çekiliş bitir ve kazananları seç
• `/etkinlikiptal ID` - Etkinlik iptal et (point geri ver)
• `/etkinlikdurum ID` - Etkinlik durumu görüntüle

**📋 Etkinlik Listesi:**
• `/etkinlikler` - Aktif etkinlikleri listele
• `/cekilisler` - Aktif çekilişleri listele (alias)

**👥 Katılım Sistemi:**
• Etkinlik mesajlarındaki butonlarla katılım
• Point kontrolü otomatik
• Çifte katılım önleme aktif

**🎉 Kazanan Seçimi:**
• Katılım miktarına göre ağırlıklı seçim
• Point dağıtımı otomatik
• Sonuç bildirimi otomatik

**📝 Kullanım Örnekleri:**
• `/cekilisbitir 123` - ID 123'lü çekilişi bitir
• `/etkinlikiptal 123` - ID 123'lü etkinliği iptal et
• `/etkinlikdurum 123` - ID 123'lü etkinlik durumu
        """
        
        await message.reply(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Etkinlik yardım hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

# ========================================
# HİLELİ KAZANAN ATAMA KOMUTLARI
# ========================================

@router.message(Command("kazananayarla"))
async def set_forced_winners_command(message: Message):
    """Hileli kazanan atama komutu - /kazananayarla"""
    logger.info(f"🎯 KAZANANAYARLA HANDLER ÇALIŞTI - User: {message.from_user.id}, Text: {message.text}")
    
    try:
        # Admin kontrolü (DB tabanlı) - Rank 4+ gerekli
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(message.from_user.id, 4):
            return
        
        # Sadece private sohbet
        if message.chat.type != "private":
            try:
                await message.delete()
                logger.info(f"🔇 Hileli kazanan komutu mesajı silindi - Group: {message.chat.id}")
                
                # Özel mesajla uyarı
                if _bot_instance:
                    await _bot_instance.send_message(
                        message.from_user.id,
                        "⚠️ **Hileli kazanan komutları sadece özel sohbette kullanılabilir!**\n\n"
                        "Lütfen bot ile özel sohbet başlatın.",
                        parse_mode="Markdown"
                    )
                return
            except Exception as e:
                logger.error(f"❌ Komut mesajı silinemedi: {e}")
                return
        
        # Komut parsing
        command_text = message.text.strip()
        parts = command_text.split()
        
        if len(parts) < 3:
            await message.reply(
                "❌ **Kullanım:** `/kazananayarla <event_id> <user_id1> [user_id2] [user_id3] ... [--ekle] [--not \"sebep\"]`\n\n"
                "**Örnek:** `/kazananayarla 125 123456789 987654321 555666777 --ekle --not \"sponsor seçimi\"`",
                parse_mode="Markdown"
            )
            return
        
        try:
            event_id = int(parts[1])
        except ValueError:
            await message.reply("❌ Geçersiz event ID! Sayı olmalı.")
            return
        
        # User ID'leri ve flag'leri parse et
        user_ids = []
        auto_join = False
        note = None
        
        for part in parts[2:]:
            if part == "--ekle":
                auto_join = True
            elif part.startswith("--not"):
                # --not "sebep" parsing
                note_index = command_text.find("--not")
                if note_index != -1:
                    note_part = command_text[note_index + 5:].strip()
                    if note_part.startswith('"') and note_part.endswith('"'):
                        note = note_part[1:-1]
                    else:
                        note = note_part
            else:
                try:
                    user_ids.append(int(part))
                except ValueError:
                    await message.reply(f"❌ Geçersiz user ID: `{part}`", parse_mode="Markdown")
                    return
        
        if not user_ids:
            await message.reply("❌ En az bir user ID belirtmelisiniz!")
            return
        
        # Etkinlik kontrolü
        from database import get_event_info_for_end
        event_info = await get_event_info_for_end(event_id)
        if not event_info:
            await message.reply(f"❌ Event {event_id} bulunamadı veya aktif değil!")
            return
        
        # Kullanıcıları kontrol et ve ekle
        added_count = 0
        failed_users = []
        
        for i, user_id in enumerate(user_ids, 1):
            try:
                # Kullanıcı kayıtlı mı kontrol et
                from database import is_user_registered
                if not await is_user_registered(user_id):
                    if auto_join:
                        # Otomatik kayıt
                        from database import register_user
                        await register_user(user_id)
                        logger.info(f"✅ User {user_id} otomatik kayıt edildi")
                    else:
                        failed_users.append(f"{user_id} (kayıtsız)")
                        continue
                
                # Hileli kazanan olarak ekle
                from database import upsert_forced_winner
                success = await upsert_forced_winner(
                    event_id=event_id,
                    user_id=user_id,
                    added_by=message.from_user.id,
                    note=note,
                    rank_order=i
                )
                
                if success:
                    added_count += 1
                    logger.info(f"✅ Forced winner added: Event {event_id}, User {user_id}, Rank {i}")
                else:
                    failed_users.append(f"{user_id} (ekleme hatası)")
                    
            except Exception as e:
                logger.error(f"❌ User {user_id} ekleme hatası: {e}")
                failed_users.append(f"{user_id} (hata)")
        
        # Sonuç mesajı
        result_message = f"✅ **Hileli Kazanan Atama Tamamlandı**\n\n"
        result_message += f"🎯 **Event ID:** {event_id}\n"
        result_message += f"✅ **Başarılı:** {added_count} kişi\n"
        
        if failed_users:
            result_message += f"❌ **Başarısız:** {len(failed_users)} kişi\n"
            result_message += f"📝 **Detay:** {', '.join(failed_users)}\n"
        
        if note:
            result_message += f"📝 **Not:** {note}\n"
        
        result_message += f"\n💡 **Kontrol:** `/kazananliste {event_id}`"
        
        await message.reply(result_message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Set forced winners hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

@router.message(Command("kazananliste"))
async def list_forced_winners_command(message: Message):
    """Hileli kazanan listesi komutu - /kazananliste"""
    try:
        # Admin kontrolü (DB tabanlı) - Rank 4+ gerekli
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(message.from_user.id, 4):
            return
        
        # Sadece private sohbet
        if message.chat.type != "private":
            try:
                await message.delete()
                if _bot_instance:
                    await _bot_instance.send_message(
                        message.from_user.id,
                        "⚠️ **Bu komut sadece özel sohbette kullanılabilir!**",
                        parse_mode="Markdown"
                    )
                return
            except:
                pass
            return
        
        # Komut parsing
        command_text = message.text.strip()
        parts = command_text.split()
        
        if len(parts) != 2:
            await message.reply("❌ **Kullanım:** `/kazananliste <event_id>`")
            return
        
        try:
            event_id = int(parts[1])
        except ValueError:
            await message.reply("❌ Geçersiz event ID! Sayı olmalı.")
            return
        
        # Hileli kazananları getir
        from database import get_forced_winners_by_event
        forced_winners = await get_forced_winners_by_event(event_id)
        
        if not forced_winners:
            await message.reply(f"📋 **Event {event_id} için hileli kazanan bulunamadı.**")
            return
        
        # Liste mesajı oluştur
        list_message = f"🎯 **Hileli Kazananlar (Event: {event_id})**\n\n"
        
        for winner in forced_winners:
            rank = winner.get('rank_order', 0)
            user_id = winner.get('user_id', 0)
            username = winner.get('username', '')
            first_name = winner.get('first_name', '')
            last_name = winner.get('last_name', '')
            note = winner.get('note', '')
            created_at = winner.get('created_at', '')
            
            # Kullanıcı adı oluştur
            if username:
                user_display = f"@{username}"
            elif first_name or last_name:
                user_display = f"{first_name} {last_name}".strip()
            else:
                user_display = f"ID: {user_id}"
            
            list_message += f"**{rank}.** {user_display} (`{user_id}`)\n"
            
            if note:
                list_message += f"   📝 {note}\n"
            
            if created_at:
                list_message += f"   📅 {created_at.strftime('%d.%m.%Y %H:%M')}\n"
            
            list_message += "\n"
        
        list_message += f"💡 **Toplam:** {len(forced_winners)} kişi"
        
        await message.reply(list_message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ List forced winners hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

@router.message(Command("kazananayrimsil"))
async def remove_forced_winner_command(message: Message):
    """Hileli kazanan silme komutu - /kazananayrimsil"""
    try:
        # Admin kontrolü (DB tabanlı) - Rank 4+ gerekli
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(message.from_user.id, 4):
            return
        
        # Sadece private sohbet
        if message.chat.type != "private":
            try:
                await message.delete()
                if _bot_instance:
                    await _bot_instance.send_message(
                        message.from_user.id,
                        "⚠️ **Bu komut sadece özel sohbette kullanılabilir!**",
                        parse_mode="Markdown"
                    )
                return
            except:
                pass
            return
        
        # Komut parsing
        command_text = message.text.strip()
        parts = command_text.split()
        
        if len(parts) != 3:
            await message.reply("❌ **Kullanım:** `/kazananayrimsil <event_id> <user_id>`")
            return
        
        try:
            event_id = int(parts[1])
            user_id = int(parts[2])
        except ValueError:
            await message.reply("❌ Geçersiz ID! Sayı olmalı.")
            return
        
        # Hileli kazanandan çıkar
        from database import remove_forced_winner
        success = await remove_forced_winner(event_id, user_id)
        
        if success:
            await message.reply(f"✅ **User {user_id} hileli kazanan listesinden çıkarıldı.**\n\n💡 **Kontrol:** `/kazananliste {event_id}`")
        else:
            await message.reply(f"❌ **User {user_id} hileli kazanan listesinde bulunamadı!**")
        
    except Exception as e:
        logger.error(f"❌ Remove forced winner hatası: {e}")
        await message.reply("❌ Bir hata oluştu!")

@router.message(Command("kazananayrimhepsi"))
async def clear_forced_winners_command(message: Message):
    """Tüm hileli kazananları temizle komutu - /kazananayrimhepsi"""
    try:
        # Admin kontrolü (DB tabanlı) - Rank 4+ gerekli
        from handlers.admin_permission_manager import has_min_rank_db
        if not await has_min_rank_db(message.from_user.id, 4):
            return
        
        # Sadece private sohbet
        if message.chat.type != "private":
            try:
                await message.delete()
                if _bot_instance:
                    await _bot_instance.send_message(
                        message.from_user.id,
                        "⚠️ **Bu komut sadece özel sohbette kullanılabilir!**",
                        parse_mode="Markdown"
                    )
                return
            except:
                pass
            return
        
        # Komut parsing
        command_text = message.text.strip()
        parts = command_text.split()
        
        if len(parts) != 2:
            await message.reply("❌ **Kullanım:** `/kazananayrimhepsi <event_id>`")
            return
        
        try:
            event_id = int(parts[1])
        except ValueError:
            await message.reply("❌ Geçersiz event ID! Sayı olmalı.")
            return
        
        # Tüm hileli kazananları temizle
        from database import clear_forced_winners
        success = await clear_forced_winners(event_id)
        
        if success:
            await message.reply(f"✅ **Event {event_id} için tüm hileli kazananlar temizlendi.**\n\n💡 **Kontrol:** `/kazananliste {event_id}`")
        else:
            await message.reply(f"❌ **Temizleme işlemi başarısız!**")
        
    except Exception as e:
        logger.error(f"❌ Clear forced winners hatası: {e}")
        await message.reply("❌ Bir hata oluştu!") 