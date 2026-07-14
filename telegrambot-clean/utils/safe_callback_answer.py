"""
Güvenli callback answer utility - Query timeout hatalarını yakalar
"""

import logging
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)


async def safe_callback_answer(
    callback: CallbackQuery,
    text: str = None,
    show_alert: bool = False,
    silent: bool = True
) -> bool:
    """
    Güvenli callback answer - Query timeout hatalarını yakalar
    
    Args:
        callback: CallbackQuery objesi
        text: Answer metni (None ise sadece answer çağrılır)
        show_alert: Alert gösterilsin mi
        silent: Timeout hatalarını sessizce geç (True) veya logla (False)
    
    Returns:
        bool: Başarılı ise True, hata ise False
    """
    try:
        if text:
            await callback.answer(text, show_alert=show_alert)
        else:
            await callback.answer()
        return True
    except Exception as e:
        error_msg = str(e).lower()
        
        # Query timeout hataları - normal durum
        if "query is too old" in error_msg or "timeout" in str(e).lower():
            if not silent:
                logger.debug(f"⏸️ Callback answer timeout - User: {callback.from_user.id}")
            return False
        
        # Diğer hatalar - logla
        logger.warning(f"⚠️ Callback answer hatası: {e} - User: {callback.from_user.id}")
        return False

