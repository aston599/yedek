import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database import Database
from config import ADMIN_USER_ID

logger = logging.getLogger(__name__)
db = Database()

async def show_pending_applications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bekleyen başvuruları göster"""
    if update.effective_chat.type != 'private':
        return
    
    applications = db.get_pending_applications()
    
    if not applications:
        await update.message.reply_text("📋 Bekleyen başvuru bulunmuyor.")
        return
    
    message = "📋 **Bekleyen Başvurular:**\n\n"
    
    for app in applications:
        app_id, user_id, username, site_type, site_username, membership_date, screenshot_path, status, created_at, processed_at, admin_id = app
        
        message += f"""
🆔 **ID:** {app_id}
👤 **Kullanıcı:** @{username} ({user_id})
🏢 **Site:** {site_type}
📅 **Tarih:** {created_at}
📸 **Ekran Görüntüsü:** {screenshot_path}

---
        """
    
    # Her başvuru için onay/red butonları
    keyboard = []
    for app in applications:
        app_id = app[0]
        keyboard.append([
            InlineKeyboardButton(f"✅ Onayla {app_id}", callback_data=f"admin_approve_{app_id}"),
            InlineKeyboardButton(f"❌ Reddet {app_id}", callback_data=f"admin_reject_{app_id}")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def approve_application(update: Update, context: ContextTypes.DEFAULT_TYPE, application_id: int):
    """Başvuruyu onayla"""
    if update.effective_chat.type != 'private':
        return
    
    # Başvuru durumunu güncelle
    success = db.update_application_status(application_id, 'approved', update.effective_user.id)
    
    if success:
        # Kullanıcıya onay mesajı gönder
        # (Bu kısımda kullanıcı bilgilerini alıp mesaj gönderebiliriz)
        
        await update.message.reply_text(f"✅ Başvuru #{application_id} onaylandı!")
        
        # Ana gruba kullanıcıyı ekleme işlemi burada yapılabilir
        # Şimdilik sadece onay mesajı gönderiyoruz
        
        logger.info(f"Application {application_id} approved by {update.effective_user.id}")
    else:
        await update.message.reply_text(f"❌ Başvuru #{application_id} onaylanamadı!")

async def reject_application(update: Update, context: ContextTypes.DEFAULT_TYPE, application_id: int):
    """Başvuruyu reddet"""
    if update.effective_chat.type != 'private':
        return
    
    # Başvuru durumunu güncelle
    success = db.update_application_status(application_id, 'rejected', update.effective_user.id)
    
    if success:
        # Kullanıcıya red mesajı gönder
        # (Bu kısımda kullanıcı bilgilerini alıp mesaj gönderebiliriz)
        
        await update.message.reply_text(f"❌ Başvuru #{application_id} reddedildi!")
        
        logger.info(f"Application {application_id} rejected by {update.effective_user.id}")
    else:
        await update.message.reply_text(f"❌ Başvuru #{application_id} reddedilemedi!")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İstatistikleri göster"""
    if update.effective_chat.type != 'private':
        return
    
    # Basit istatistikler (şimdilik)
    stats_text = """
📊 **Bot İstatistikleri**

🔢 **Toplam Başvuru:** (Hesaplanacak)
✅ **Onaylanan:** (Hesaplanacak)
❌ **Reddedilen:** (Hesaplanacak)
⏳ **Bekleyen:** (Hesaplanacak)

📅 **Son Güncelleme:** (Şimdi)
    """
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin buton işleyicisi"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("admin_approve_"):
        application_id = int(query.data.replace("admin_approve_", ""))
        await approve_application(update, context, application_id)
    
    elif query.data.startswith("admin_reject_"):
        application_id = int(query.data.replace("admin_reject_", ""))
        await reject_application(update, context, application_id)

