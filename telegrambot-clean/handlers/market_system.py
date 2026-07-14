"""
🛍️ Market System - Ürün satın alma ve sipariş yönetimi
"""

import logging
import uuid
from datetime import datetime
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_db_pool, get_user_points
from handlers.balance_management import remove_balance_simple

logger = logging.getLogger(__name__)

# Bot instance
_bot_instance = None

def set_bot_instance(bot_instance):
    global _bot_instance
    _bot_instance = bot_instance


async def show_product_details_modern(callback: types.CallbackQuery, data: str):
    """Ürün detaylarını göster ve satın alma butonu ekle"""
    try:
        product_id = int(data.replace("view_product_", ""))
        user_id = callback.from_user.id
        
        logger.info(f"🛍️ Ürün detayları gösteriliyor - Product ID: {product_id}, User: {user_id}")
        
        pool = await get_db_pool()
        if not pool:
            await callback.answer("❌ Database bağlantısı hatası!", show_alert=True)
            return
        
        async with pool.acquire() as conn:
            # Ürün bilgilerini al - image_url, is_featured ve delivery_content kolonları kontrolü
            try:
                has_image_url = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_name = 'market_products' 
                    AND column_name = 'image_url'
                """)
                
                has_is_featured = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_name = 'market_products' 
                    AND column_name = 'is_featured'
                """)
                
                # Ürün bilgilerini al
                if has_image_url and has_is_featured:
                    product = await conn.fetchrow("""
                        SELECT 
                            id, 
                            COALESCE(name, product_name) as product_name,
                            description,
                            price, 
                            stock,
                            image_url,
                            is_featured,
                            category_id
                        FROM market_products
                        WHERE id = $1 AND is_active = true
                    """, product_id)
                else:
                    product = await conn.fetchrow("""
                        SELECT 
                            id, 
                            COALESCE(name, product_name) as product_name,
                            description,
                            price, 
                            stock,
                            NULL as image_url,
                            FALSE as is_featured,
                            category_id
                        FROM market_products
                        WHERE id = $1 AND is_active = true
                    """, product_id)
            except Exception:
                # Hata durumunda basit sorgu
                product = await conn.fetchrow("""
                    SELECT 
                        id, 
                        COALESCE(name, product_name) as product_name,
                        description,
                        price, 
                        stock,
                        category_id
                    FROM market_products
                    WHERE id = $1 AND is_active = true
                """, product_id)
            
            if not product:
                await callback.answer("❌ Ürün bulunamadı!", show_alert=True)
                return
            
            # Kullanıcı bakiyesini al
            user_points = await get_user_points(user_id)
            balance = float(user_points.get('kirve_points', 0)) if user_points else 0.0
            product_price = float(product['price'])
        
        # Mesajı hazırla
        message_text = f"📦 **{product['product_name']}**\n\n"
        
        if product.get('description'):
            message_text += f"{product['description']}\n\n"
        
        message_text += f"💰 **Fiyat:** {product_price:.2f} KP\n"
        message_text += f"📊 **Stok:** {product['stock']} adet\n"
        message_text += f"💳 **Bakiyeniz:** {balance:.2f} KP\n"
        
        # Butonları hazırla
        keyboard_buttons = []
        
        if product['stock'] > 0:
            if balance >= product_price:
                keyboard_buttons.append([InlineKeyboardButton(
                    text="🛒 Satın Al",
                    callback_data=f"buy_product_{product_id}"
                )])
            elif balance < product_price:
                needed = product_price - balance
                keyboard_buttons.append([InlineKeyboardButton(text="❌ Yetersiz Bakiye", callback_data="insufficient_balance")])
        
        # Kategori butonu
        if product['category_id']:
            try:
                category = await conn.fetchrow("""
                    SELECT name FROM market_categories WHERE id = $1
                """, product['category_id'])
                if category:
                    keyboard_buttons.append([InlineKeyboardButton(
                        text=f"📂 {category['name']}",
                        callback_data=f"market_category_{product['category_id']}"
                    )])
            except Exception:
                pass
        
        keyboard_buttons.append([InlineKeyboardButton(text="🔙 Geri", callback_data="market_back")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await callback.message.edit_text(
                message_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception as edit_error:
            # Mesaj düzenleme hatalarını yakala
            error_msg = str(edit_error).lower()
            if "message is not modified" in error_msg:
                logger.debug(f"⏸️ Ürün detay mesajı değişmemiş - Product: {product_id}, User: {user_id}")
            elif "message to edit not found" in error_msg:
                logger.debug(f"⏸️ Ürün detay mesajı bulunamadı - Product: {product_id}, User: {user_id}")
            else:
                logger.error(f"❌ Ürün detay mesaj düzenleme hatası: {edit_error}")
        
        try:
            await callback.answer()
        except Exception as answer_error:
            # Query timeout hatası - sessizce geç
            if "query is too old" in str(answer_error).lower() or "timeout" in str(answer_error).lower():
                logger.debug(f"⏸️ Ürün detay callback answer timeout - Product: {product_id}, User: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ürün detayları hatası: {e}", exc_info=True)
        try:
            await callback.answer("❌ Bir hata oluştu!", show_alert=True)
        except:
            pass  # Query timeout - sessizce geç


async def handle_buy_product_modern(callback: types.CallbackQuery, data: str):
    """Satın alma işlemini başlat - Onay ekranı göster"""
    try:
        product_id = int(data.replace("buy_product_", ""))
        user_id = callback.from_user.id
        
        logger.info(f"🛒 Satın alma başlatılıyor - Product ID: {product_id}, User: {user_id}")
        
        pool = await get_db_pool()
        if not pool:
            await callback.answer("❌ Database bağlantısı hatası!", show_alert=True)
            return
        
        async with pool.acquire() as conn:
            # Ürün bilgilerini al - kategori bilgisi de dahil
            product = await conn.fetchrow("""
                SELECT 
                    p.id, 
                    COALESCE(p.name, p.product_name) as product_name,
                    p.price, 
                    p.stock,
                    p.category_id,
                    c.name as category_name
                FROM market_products p
                LEFT JOIN market_categories c ON p.category_id = c.id
                WHERE p.id = $1 AND p.is_active = true
            """, product_id)
            
            if not product:
                await callback.answer("❌ Ürün bulunamadı!", show_alert=True)
                return
            
            # Kullanıcı bakiyesini al
            user_points = await get_user_points(user_id)
            balance = float(user_points.get('kirve_points', 0)) if user_points else 0.0
            product_price = float(product['price'])
        
        # Kontroller
        if product['stock'] <= 0:
            await callback.answer("❌ Stokta ürün bulunmamaktadır!", show_alert=True)
            return
        
        if balance < product_price:
            needed = product_price - balance
            await callback.answer(f"❌ Yetersiz bakiye! Gerekli: {needed:.2f} KP daha", show_alert=True)
            return
        
        # Site bakiyeleri kategorisi kontrolü
        category_name = product.get('category_name', '').lower() if product.get('category_name') else ''
        is_site_balance = (
            'bakiye' in category_name or 
            'balance' in category_name or
            product.get('category_name', '').lower() == 'balance'
        )
        
        # Eğer site bakiyeleri kategorisindeyse, kullanıcı adı adımına geç
        if is_site_balance:
            # Kullanıcı adı input state'i başlat
            from handlers.market_callbacks import site_username_states
            site_username_states[user_id] = {
                'product_id': product_id,
                'product_name': product['product_name'],
                'product_price': product_price,
                'balance': balance
            }
            
            message_text = f"🛒 **SİTE BAKİYESİ SATIN ALMA**\n\n"
            message_text += f"📦 **Ürün:** {product['product_name']}\n"
            message_text += f"💰 **Fiyat:** {product_price:.2f} KP\n"
            message_text += f"💳 **Mevcut Bakiye:** {balance:.2f} KP\n\n"
            message_text += "👤 **Kullanıcı Adı (Opsiyonel)**\n\n"
            message_text += "Site bakiyesi için kullanıcı adınızı girebilirsiniz.\n"
            message_text += "Atlamak için `-` yazın veya direkt onaylayın.\n\n"
            message_text += "**Örnek:** `kullanici123` veya `-`"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="⏭️ Kullanıcı Adı Olmadan Devam Et",
                    callback_data=f"skip_username_{product_id}"
                )],
                [InlineKeyboardButton(
                    text="❌ İptal",
                    callback_data=f"view_product_{product_id}"
                )]
            ])
            
            await callback.message.edit_text(
                message_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        # Normal ürünler için direkt onay ekranı
        message_text = f"🛒 **SATIN ALMA ONAYI**\n\n"
        message_text += f"📦 **Ürün:** {product['product_name']}\n"
        message_text += f"💰 **Fiyat:** {product_price:.2f} KP\n"
        message_text += f"💳 **Mevcut Bakiye:** {balance:.2f} KP\n"
        message_text += f"💳 **Kalan Bakiye:** {balance - product_price:.2f} KP\n\n"
        message_text += "⚠️ **Onaylıyor musunuz?**"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Evet, Satın Al",
                callback_data=f"confirm_buy_{product_id}"
            )],
            [InlineKeyboardButton(
                text="❌ İptal",
                callback_data=f"view_product_{product_id}"
            )]
        ])
        
        await callback.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Satın alma başlatma hatası: {e}", exc_info=True)
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


# Çift işleme önleme için set
_processing_orders = set()

async def confirm_buy_product_modern(callback: types.CallbackQuery, data: str, site_username: str = None):
    """Satın alma işlemini onayla ve sipariş oluştur"""
    try:
        product_id = int(data.replace("confirm_buy_", ""))
        user_id = callback.from_user.id
        
        # Çift işleme önleme
        order_key = f"{user_id}_{product_id}_{callback.message.message_id}"
        if order_key in _processing_orders:
            await callback.answer("⏳ İşlem zaten devam ediyor...", show_alert=True)
            return
        
        _processing_orders.add(order_key)
        
        try:
            logger.info(f"✅ Satın alma onaylandı - Product ID: {product_id}, User: {user_id}, Username: {site_username}")
            
            pool = await get_db_pool()
            if not pool:
                await callback.answer("❌ Database bağlantısı hatası!", show_alert=True)
                return
            
            async with pool.acquire() as conn:
                # Ürün bilgilerini al
                product = await conn.fetchrow("""
                    SELECT 
                        id, 
                        COALESCE(name, product_name) as product_name,
                        price, 
                        stock
                    FROM market_products
                    WHERE id = $1 AND is_active = true
                """, product_id)
                
                if not product:
                    await callback.answer("❌ Ürün bulunamadı!", show_alert=True)
                    return
                
                # Kullanıcı bakiyesini kontrol et
                user_points = await get_user_points(user_id)
                balance = float(user_points.get('kirve_points', 0)) if user_points else 0.0
                product_price = float(product['price'])
                
                # Son kontroller
                if product['stock'] <= 0:
                    await callback.answer("❌ Stokta ürün bulunmamaktadır!", show_alert=True)
                    return
                
                if balance < product_price:
                    await callback.answer("❌ Yetersiz bakiye!", show_alert=True)
                    return
                
                # Sipariş numarası oluştur
                order_number = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
                
                # Bakiyeyi düş
                result = await remove_balance_simple(user_id, product_price)
                if not result.get('success'):
                    await callback.answer("❌ Bakiye düşürme hatası!", show_alert=True)
                    return
                
                # Sipariş oluştur - site_username kolonu kontrolü
                # Önce kolonun var olup olmadığını kontrol et
                has_site_username = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_name = 'market_orders' 
                    AND column_name = 'site_username'
                """)
                
                if has_site_username:
                    # site_username kolonu varsa, değeri ekle
                    order_id = await conn.fetchval("""
                        INSERT INTO market_orders (
                            order_number, user_id, product_id, quantity, total_price, status, site_username, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                        RETURNING id
                    """, order_number, user_id, product_id, 1, product_price, 'pending', site_username)
                else:
                    # site_username kolonu yoksa, eski format
                    order_id = await conn.fetchval("""
                        INSERT INTO market_orders (
                            order_number, user_id, product_id, quantity, total_price, status, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
                        RETURNING id
                    """, order_number, user_id, product_id, 1, product_price, 'pending')
                
                # Stok düş - sold_count kolonu yoksa sadece stock güncelle
                try:
                    # sold_count kolonunu kontrol et
                    has_sold_count = await conn.fetchval("""
                        SELECT COUNT(*) 
                        FROM information_schema.columns 
                        WHERE table_name = 'market_products' 
                        AND column_name = 'sold_count'
                    """)
                    
                    if has_sold_count:
                        await conn.execute("""
                            UPDATE market_products
                            SET stock = stock - 1, sold_count = COALESCE(sold_count, 0) + 1
                            WHERE id = $1
                        """, product_id)
                    else:
                        await conn.execute("""
                            UPDATE market_products
                            SET stock = stock - 1
                            WHERE id = $1
                        """, product_id)
                except Exception:
                    # Hata durumunda sadece stock güncelle
                    await conn.execute("""
                        UPDATE market_products
                        SET stock = stock - 1
                        WHERE id = $1
                    """, product_id)
                
                logger.info(f"✅ Sipariş oluşturuldu - Order: {order_number}, User: {user_id}, Product: {product_id}, Username: {site_username}")
                
                # Admin'e bildirim gönder
                try:
                    from config import get_config
                    config = get_config()
                    
                    logger.info(f"🔍 Admin bildirimi kontrolü - Bot instance: {_bot_instance is not None}, Has ADMIN_USER_ID: {hasattr(config, 'ADMIN_USER_ID')}")
                    
                    if not _bot_instance:
                        logger.warning("⚠️ Bot instance yok, admin bildirimi gönderilemedi")
                    elif not hasattr(config, 'ADMIN_USER_ID'):
                        logger.warning("⚠️ ADMIN_USER_ID yok, admin bildirimi gönderilemedi")
                    else:
                        admin_id = config.ADMIN_USER_ID
                        logger.info(f"🔍 Admin ID: {admin_id}")
                        
                        user_info = await conn.fetchrow("""
                            SELECT first_name, username FROM users WHERE user_id = $1
                        """, user_id)
                        
                        user_name = user_info['first_name'] if user_info else 'Bilinmeyen'
                        user_username = user_info['username'] if user_info else 'Kullanıcı adı yok'
                        
                        admin_message = f"🛒 **YENİ SİPARİŞ**\n\n"
                        admin_message += f"📦 **Ürün:** {product['product_name']}\n"
                        admin_message += f"💰 **Fiyat:** {product_price:.2f} KP\n"
                        admin_message += f"📋 **Sipariş No:** `{order_number}`\n"
                        admin_message += f"👤 **Kullanıcı:** {user_name} (@{user_username})\n"
                        admin_message += f"🆔 **User ID:** `{user_id}`\n"
                        
                        # Kullanıcı adı varsa göster
                        if site_username:
                            admin_message += f"👤 **Site Kullanıcı Adı:** `{site_username}`\n"
                        
                        admin_message += f"\n📊 **Durum:** Beklemede"
                        
                        await _bot_instance.send_message(
                            chat_id=admin_id,
                            text=admin_message,
                            parse_mode="Markdown"
                        )
                        logger.info(f"✅ Admin bildirimi gönderildi - Admin: {admin_id}")
                except Exception as e:
                    logger.error(f"❌ Admin bildirimi hatası: {e}", exc_info=True)
                
                # Başarı mesajı
                success_message = f"✅ **SİPARİŞ OLUŞTURULDU!**\n\n"
                success_message += f"📦 **Ürün:** {product['product_name']}\n"
                success_message += f"💰 **Fiyat:** {product_price:.2f} KP\n"
                success_message += f"📋 **Sipariş No:** `{order_number}`\n"
                
                if site_username:
                    success_message += f"👤 **Site Kullanıcı Adı:** `{site_username}`\n"
                
                success_message += f"\n💳 **Kalan Bakiye:** {result['new_balance']:.2f} KP\n\n"
                success_message += "⏳ Siparişiniz admin onayı bekliyor. Onaylandığında size bildirim gönderilecektir."
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📦 Siparişlerim", callback_data="market_my_orders")],
                    [InlineKeyboardButton(text="🛍️ Market", callback_data="market_back")]
                ])
                
                await callback.message.edit_text(
                    success_message,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                await callback.answer("✅ Sipariş oluşturuldu!", show_alert=True)
                
        finally:
            _processing_orders.discard(order_key)
            
    except Exception as e:
        logger.error(f"❌ Satın alma onay hatası: {e}", exc_info=True)
        await callback.answer("❌ Bir hata oluştu!", show_alert=True)


async def confirm_buy_product_with_username(callback_or_message, product_id: int, site_username: str = None):
    """Kullanıcı adı ile sipariş oluştur (site bakiyeleri için)"""
    # Hem CallbackQuery hem de Message objesi kabul eder
    if isinstance(callback_or_message, types.CallbackQuery):
        await confirm_buy_product_modern(callback_or_message, f"confirm_buy_{product_id}", site_username=site_username)
    else:
        # Message objesi ise, fake callback oluştur
        class FakeCallback:
            def __init__(self, message, data):
                self.message = message
                self.data = data
                self.from_user = message.from_user
            
            async def answer(self, *args, **kwargs):
                pass
        
        fake_callback = FakeCallback(callback_or_message, f"confirm_buy_{product_id}")
        await confirm_buy_product_modern(fake_callback, f"confirm_buy_{product_id}", site_username=site_username)


# ... existing code ...
