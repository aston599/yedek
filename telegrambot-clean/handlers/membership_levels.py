"""
🏆 Üyelik Seviyeleri Sistemi - KirveHub Bot
Point miktarına göre üyelik seviyesi belirleme ve görsel gösterimi
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)

# Üyelik seviyeleri ve eşikleri (MESAJ SAYISINA GÖRE - ZOR EŞİKLER)
MEMBERSHIP_LEVELS = {
    "bronz": {
        "name": "Bronz",
        "min_messages": 0,
        "max_messages": 500,
        "icon_file": "bronz icon png.png",
        "emoji": "🥉"
    },
    "gümüş": {
        "name": "Gümüş",
        "min_messages": 500,
        "max_messages": 2000,
        "icon_file": "gümüş icon png.png",
        "emoji": "🥈"
    },
    "gold": {
        "name": "Altın",
        "min_messages": 2000,
        "max_messages": 5000,
        "icon_file": "gold icon png.png",
        "emoji": "🥇"
    },
    "plat": {
        "name": "Platin",
        "min_messages": 5000,
        "max_messages": 15000,
        "icon_file": "plat icon png.png",
        "emoji": "💎"
    },
    "diamond": {
        "name": "Elmas",
        "min_messages": 15000,
        "max_messages": float('inf'),
        "icon_file": "diamond icon png.png",
        "emoji": "💠"
    }
}

# Seviye sırası
LEVEL_ORDER = ["bronz", "gümüş", "gold", "plat", "diamond"]


def get_membership_level(message_count: int) -> str:
    """
    Mesaj sayısına göre üyelik seviyesini döndür
    
    Args:
        message_count: Kullanıcının toplam mesaj sayısı
        
    Returns:
        Seviye anahtarı (bronz, gümüş, gold, plat, diamond)
    """
    message_count = int(message_count) if message_count else 0
    
    # En yüksek seviyeden başla
    for level_key in reversed(LEVEL_ORDER):
        level_info = MEMBERSHIP_LEVELS[level_key]
        if message_count >= level_info["min_messages"]:
            return level_key
    
    # Varsayılan olarak bronz
    return "bronz"


def get_level_info(level_key: str) -> Dict:
    """
    Seviye bilgilerini döndür
    
    Args:
        level_key: Seviye anahtarı
        
    Returns:
        Seviye bilgileri dict'i
    """
    return MEMBERSHIP_LEVELS.get(level_key, MEMBERSHIP_LEVELS["bronz"])


def get_level_info_by_messages(message_count: int) -> Dict:
    """
    Mesaj sayısına göre seviye bilgilerini döndür
    
    Args:
        message_count: Kullanıcının toplam mesaj sayısı
        
    Returns:
        Seviye bilgileri dict'i
    """
    level_key = get_membership_level(message_count)
    return get_level_info(level_key)


def get_level_icon_path(level_key: str) -> Optional[str]:
    """
    Seviye ikon dosyasının yolunu döndür
    
    Args:
        level_key: Seviye anahtarı
        
    Returns:
        İkon dosyası yolu veya None
    """
    try:
        level_info = get_level_info(level_key)
        icon_file = level_info["icon_file"]
        
        # Görseller klasörü
        icons_dir = Path("assets/membership_levels")
        
        if not icons_dir.exists():
            icons_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"📁 Seviye ikonları klasörü oluşturuldu: {icons_dir}")
            return None
        
        # Önce tam dosya adını kontrol et
        icon_path = icons_dir / icon_file
        if icon_path.exists():
            logger.debug(f"✅ Seviye ikonu bulundu: {icon_path}")
            return str(icon_path)
        
        # Dosya adındaki boşlukları ve uzantıyı temizle
        base_name = icon_file.replace('.png', '').replace('.jpg', '').replace('.jpeg', '').replace('.webp', '').strip()
        
        # Farklı uzantıları ve varyasyonları dene
        for ext in ['.png', '.jpg', '.jpeg', '.webp']:
            # Varyasyon 1: Tam dosya adı
            alt_path = icons_dir / icon_file
            if alt_path.exists():
                logger.debug(f"✅ Seviye ikonu bulundu (tam ad): {alt_path}")
                return str(alt_path)
            
            # Varyasyon 2: Base name + extension
            alt_path = icons_dir / f"{base_name}{ext}"
            if alt_path.exists():
                logger.debug(f"✅ Seviye ikonu bulundu (base+ext): {alt_path}")
                return str(alt_path)
            
            # Varyasyon 3: Base name (boşluksuz) + extension
            alt_path = icons_dir / f"{base_name.replace(' ', '')}{ext}"
            if alt_path.exists():
                logger.debug(f"✅ Seviye ikonu bulundu (boşluksuz): {alt_path}")
                return str(alt_path)
            
            # Varyasyon 4: Base name (küçük harf) + extension
            alt_path = icons_dir / f"{base_name.lower().replace(' ', '')}{ext}"
            if alt_path.exists():
                logger.debug(f"✅ Seviye ikonu bulundu (küçük harf): {alt_path}")
                return str(alt_path)
        
        # Klasördeki tüm dosyaları listele (debug için)
        all_files = list(icons_dir.glob("*"))
        logger.warning(f"⚠️ Seviye ikonu bulunamadı: {icon_file}")
        logger.warning(f"📁 Klasördeki dosyalar: {[f.name for f in all_files]}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Seviye ikonu yolu alma hatası: {e}")
        return None


def get_level_icon_file(level_key: str) -> Optional[FSInputFile]:
    """
    Seviye ikon dosyasını FSInputFile olarak döndür
    
    Args:
        level_key: Seviye anahtarı
        
    Returns:
        FSInputFile veya None
    """
    try:
        icon_path = get_level_icon_path(level_key)
        if icon_path:
            return FSInputFile(icon_path)
        return None
    except Exception as e:
        logger.error(f"❌ Seviye ikonu dosyası alma hatası: {e}")
        return None


def get_next_level_info(current_messages: int) -> Optional[Dict]:
    """
    Bir sonraki seviye bilgilerini döndür
    
    Args:
        current_messages: Kullanıcının mevcut mesaj sayısı
        
    Returns:
        Bir sonraki seviye bilgileri veya None (en yüksek seviyede ise)
    """
    current_level = get_membership_level(current_messages)
    current_index = LEVEL_ORDER.index(current_level)
    
    # En yüksek seviyede ise None döndür
    if current_index >= len(LEVEL_ORDER) - 1:
        return None
    
    # Bir sonraki seviye
    next_level_key = LEVEL_ORDER[current_index + 1]
    next_level_info = get_level_info(next_level_key)
    
    # Bir sonraki seviyeye ulaşmak için gereken mesaj sayısı
    messages_needed = next_level_info["min_messages"] - current_messages
    
    return {
        **next_level_info,
        "level_key": next_level_key,
        "messages_needed": messages_needed
    }


def check_level_up(old_messages: int, new_messages: int) -> Optional[Dict]:
    """
    Seviye atlama kontrolü yap
    
    Args:
        old_messages: Eski mesaj sayısı
        new_messages: Yeni mesaj sayısı
        
    Returns:
        Seviye atlama bilgileri veya None (seviye atlamadıysa)
    """
    old_level = get_membership_level(old_messages)
    new_level = get_membership_level(new_messages)
    
    # Seviye değişmediyse None döndür
    if old_level == new_level:
        return None
    
    # Seviye atladı
    old_level_info = get_level_info(old_level)
    new_level_info = get_level_info(new_level)
    
    return {
        "old_level": old_level,
        "new_level": new_level,
        "old_level_info": old_level_info,
        "new_level_info": new_level_info,
        "old_messages": old_messages,
        "new_messages": new_messages
    }


def format_level_display(message_count: int, include_emoji: bool = True) -> str:
    """
    Seviye bilgisini görüntüleme formatında döndür
    
    Args:
        message_count: Kullanıcının mesaj sayısı
        include_emoji: Emoji dahil edilsin mi
        
    Returns:
        Formatlanmış seviye string'i
    """
    level_info = get_level_info_by_messages(message_count)
    emoji = level_info["emoji"] if include_emoji else ""
    name = level_info["name"]
    
    return f"{emoji} {name}" if emoji else name


def get_random_avatar() -> Optional[str]:
    """
    Rastgele bir avatar görseli seç
    
    Returns:
        Avatar dosya yolu veya None
    """
    try:
        import random
        from pathlib import Path
        
        # Avatar görselleri klasörü
        avatars_dir = Path("assets/avatars")
        
        if not avatars_dir.exists():
            avatars_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"📁 Avatar klasörü oluşturuldu: {avatars_dir}")
            return None
        
        # Desteklenen görsel formatları
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        
        # Klasördeki tüm avatar görsellerini bul
        avatars = []
        for ext in allowed_extensions:
            avatars.extend(list(avatars_dir.glob(f"*{ext}")))
            avatars.extend(list(avatars_dir.glob(f"*{ext.upper()}")))
        
        if not avatars:
            logger.debug(f"📷 Avatar bulunamadı: {avatars_dir}")
            return None
        
        # Rastgele bir avatar seç
        selected_avatar = random.choice(avatars)
        logger.debug(f"📷 Avatar seçildi: {selected_avatar.name}")
        return str(selected_avatar)
        
    except Exception as e:
        logger.error(f"❌ Avatar seçme hatası: {e}")
        return None


def get_random_avatar_file() -> Optional[FSInputFile]:
    """
    Rastgele bir avatar görseli FSInputFile olarak döndür
    
    Returns:
        FSInputFile veya None
    """
    try:
        avatar_path = get_random_avatar()
        if avatar_path:
            return FSInputFile(avatar_path)
        return None
    except Exception as e:
        logger.error(f"❌ Avatar dosyası alma hatası: {e}")
        return None

