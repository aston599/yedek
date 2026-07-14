"""
🛍️ Market Callback Handlers - Kategori ve buton işlemleri
"""

import logging
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_user_points, get_db_pool

logger = logging.getLogger(__name__)

# Router
router = Router()

# Bot instance
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance

# Site bakiyeleri için kullanıcı adı state yönetimi
site_username_states = {}  # {user_id: {product_id, product_name, product_price, balance}}


async def show_market_menu_universal(user_id: int, message=None, callback=None):
    """
    Evrensel market menüsü - Hem mesaj hem callback için çalışır
    
    Args:
        user_id: Kullanıcı ID
        message: Message objesi (yeni mesaj göndermek için)
        callback: CallbackQuery objesi (mevcut mesajı düzenlemek için)
    """
    try:
        # Database'den kategorileri al
        pool = await get_db_pool()
        if not pool:
            if callback:
                await callback.answer("❌ Database bağlantısı hatası!", show_alert=True)
            return
        
        async with pool.acquire() as conn:
            # display_order kolonunu kontrol et, yoksa id'ye göre sırala
            try:
                # Önce kolonun var olup olmadığını kontrol et
                has_display_order = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_name = 'market_categories' 
                    AND column_name = 'display_order'
                """)
                
                if has_display_order:
                    categories = await conn.fetch("""
                        SELECT id, name, icon, emoji, display_order
                        FROM market_categories
                        WHERE is_active = true
                        ORDER BY display_order, id
                    """)
                else:
                    # display_order kolonu yok, sadece id'ye göre sırala
                    categories = await conn.fetch("""
                        SELECT id, name, icon, emoji
                        FROM market_categories
                        WHERE is_active = true
                        ORDER BY id
                    """)
            except Exception:
                # Hata durumunda basit sorgu kullan
                categories = await conn.fetch("""
                    SELECT id, name, icon, emoji
                    FROM market_categories
                    WHERE is_active = true
                    ORDER BY id
                """)
            
            # Kullanıcı bakiyesini al
            user_points = await get_user_points(user_id)
            balance = float(user_points.get('kirve_points', 0)) if user_points else 0.0
        
        # Market bakımda mesajı (API entegrasyonu bilgilendirmesi)
        market_text = "🛍️ **KIRVE MARKET**\n\n"
        market_text += f"💰 **Bakiyeniz:** {balance:.2f} KP\n\n"
        market_text += "⚠️ **Market Şu Anda Bakımda**\n\n"
        market_text += "Market sistemimiz yeni API entegrasyonu için güncelleniyor.\n"
        market_text += "Şu anda API entegrasyonu aktif değil, ancak yakında devreye girecek.\n\n"
        market_text += "📋 **API Entegrasyonu Hakkında:**\n"
        market_text += "• Hesabınız otomatik olarak senkronize edilecek\n"
        market_text += "• Kirve Point (KP) bakiyeniz web sitesi ile senkronize olacak\n"
        market_text += "• Alışverişleriniz anında hesabınıza yansıyacak\n"
        market_text += "• API token hazır olduğunda sistem otomatik aktif olacak\n\n"
        market_text += "🌐 **Şimdilik Web Market'i Kullanın:**\n"
        market_text += "https://kirve1.com/market\n\n"
        market_text += "💡 **Not:** API entegrasyonu tamamlandığında buradan bildirim alacaksınız."
        
        # Site yönlendirme butonu
        keyboard = [
            [InlineKeyboardButton(
                text="🌐 Web Market'e Git",
                url="https://kirve1.com/market"
            )],
            [InlineKeyboardButton(text="❌ Kapat", callback_data="market_close")]
        ]
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Mesaj gönder veya düzenle
        if callback:
            # Callback - Mevcut mesajı düzenle
            await callback.message.edit_text(
                market_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        elif message and _bot_instance:
            # Yeni mesaj gönder
            await _bot_instance.send_message(
                chat_id=user_id,
                text=market_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        
        logger.info(f"✅ Market menüsü gösterildi - User: {user_id}, Kategoriler: {len(categories)}")
        
        # Callback answer (eğer callback varsa)
        if callback:
            try:
                await callback.answer()
            except Exception as answer_error:
                # Query timeout hatası - sessizce geç
                if "query is too old" in str(answer_error).lower() or "timeout" in str(answer_error).lower():
                    logger.debug(f"⏸️ Market menü callback answer timeout - User: {user_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Market menü hatası: {e}", exc_info=True)
        if callback:
            try:
                await callback.answer("❌ Bir hata oluştu!", show_alert=True)
            except:
                pass  # Query timeout - sessizce geç
        return False


@router.callback_query(F.data.startswith("market_category_"))
async def handle_market_category(callback: types.CallbackQuery):
    """Market kategorisi seçildi - Şimdilik site yönlendirmesi"""
    try:
        user_id = callback.from_user.id
        
        logger.info(f"🛍️ Kategori seçildi - User: {user_id} (Site yönlendirmesi)")
        
        # Market bakımda - Site yönlendirmesi
        await callback.answer("⚠️ Market bakımda - Web sitesine yönlendiriliyorsunuz...", show_alert=True)
        
        # Site yönlendirme mesajı (API bilgilendirmesi ile)
        maintenance_text = "⚠️ **Market Bakımda**\n\n"
        maintenance_text += "Market sistemimiz yeni API entegrasyonu için güncelleniyor.\n"
        maintenance_text += "Şu anda API entegrasyonu aktif değil, ancak yakında devreye girecek.\n\n"
        maintenance_text += "📋 **API Entegrasyonu Hakkında:**\n"
        maintenance_text += "• Hesabınız otomatik olarak senkronize edilecek\n"
        maintenance_text += "• Kirve Point (KP) bakiyeniz web sitesi ile senkronize olacak\n"
        maintenance_text += "• Alışverişleriniz anında hesabınıza yansıyacak\n"
        maintenance_text += "• API token hazır olduğunda sistem otomatik aktif olacak\n\n"
        maintenance_text += "🌐 **Şimdilik Web Market'i Kullanın:**\n"
        maintenance_text += "https://kirve1.com/market\n\n"
        maintenance_text += "💡 **Not:** API entegrasyonu tamamlandığında buradan bildirim alacaksınız."
        
        keyboard = [
            [InlineKeyboardButton(
                text="🌐 Web Market'e Git",
                url="https://kirve1.com/market"
            )],
            [InlineKeyboardButton(text="🔙 Geri", callback_data="market_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        try:
            await callback.message.edit_text(
                maintenance_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as edit_error:
            # Mesaj düzenleme hatalarını yakala
            error_msg = str(edit_error).lower()
            if "message is not modified" in error_msg:
                logger.debug(f"⏸️ Market kategori mesajı değişmemiş - User: {user_id}")
            elif "message to edit not found" in error_msg:
                logger.debug(f"⏸️ Market kategori mesajı bulunamadı - User: {user_id}")
            else:
                logger.error(f"❌ Market kategori mesaj düzenleme hatası: {edit_error}")
        
        try:
            await callback.answer()
        except Exception as answer_error:
            # Query timeout hatası - sessizce geç
            if "query is too old" in str(answer_error).lower() or "timeout" in str(answer_error).lower():
                logger.debug(f"⏸️ Callback answer timeout - User: {user_id}")
        
        return
        
    except Exception as e:
        logger.error(f"❌ Market kategori hatası: {e}", exc_info=True)
        try:
            await callback.answer("❌ Bir hata oluştu!", show_alert=True)
        except:
            pass  # Query timeout - sessizce geç


@router.callback_query(F.data == "market_back")
async def handle_market_back(callback: types.CallbackQuery):
    """Market ana menüye dön"""
    try:
        user_id = callback.from_user.id
        await show_market_menu_universal(user_id, callback=callback)
        try:
            await callback.answer()
        except Exception as answer_error:
            # Query timeout hatası - sessizce geç
            if "query is too old" in str(answer_error).lower() or "timeout" in str(answer_error).lower():
                logger.debug(f"⏸️ Callback answer timeout - User: {user_id}")
            else:
                logger.warning(f"⚠️ Callback answer hatası: {answer_error}")
    except Exception as e:
        logger.error(f"❌ Market ana menü hatası: {e}", exc_info=True)
        try:
            await callback.answer("❌ Bir hata oluştu!", show_alert=True)
        except:
            pass  # Query timeout - sessizce geç


@router.callback_query(F.data == "market_close")
async def handle_market_close(callback: types.CallbackQuery):
    """Market menüsünü kapat"""
    try:
        try:
            await callback.message.delete()
        except:
            pass  # Mesaj zaten silinmiş olabilir
        
        try:
            await callback.answer("✅ Market kapatıldı!")
        except Exception as answer_error:
            # Query timeout hatası - sessizce geç
            if "query is too old" in str(answer_error).lower() or "timeout" in str(answer_error).lower():
                logger.debug(f"⏸️ Callback answer timeout - User: {callback.from_user.id}")
            else:
                try:
                    await callback.answer()
                except:
                    pass
    except Exception as e:
        logger.error(f"❌ Market kapatma hatası: {e}")
        try:
            await callback.answer()
        except:
            pass  # Query timeout - sessizce geç


@router.callback_query(F.data == "market_my_orders")
async def handle_my_orders(callback: types.CallbackQuery):
    """Siparişlerimi göster"""
    try:
        from handlers.market_system import show_my_orders
        await show_my_orders(callback)
    except Exception as e:
        logger.error(f"❌ Siparişlerim hatası: {e}")
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


@router.callback_query(F.data.startswith("skip_username_"))
async def handle_skip_username(callback: types.CallbackQuery):
    """Kullanıcı adı atlama - Direkt sipariş oluştur"""
    try:
        product_id = int(callback.data.replace("skip_username_", ""))
        user_id = callback.from_user.id
        
        # State'ten bilgileri al
        if user_id not in site_username_states:
            await callback.answer("❌ İşlem zaman aşımına uğradı!", show_alert=True)
            return
        
        state_data = site_username_states[user_id]
        if state_data['product_id'] != product_id:
            await callback.answer("❌ Ürün eşleşmedi!", show_alert=True)
            return
        
        # Kullanıcı adı olmadan sipariş oluştur
        from handlers.market_system import confirm_buy_product_with_username
        await confirm_buy_product_with_username(
            callback, 
            product_id, 
            site_username=None
        )
        
        # State'i temizle
        del site_username_states[user_id]
        
    except Exception as e:
        logger.error(f"❌ Kullanıcı adı atlama hatası: {e}", exc_info=True)
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)

