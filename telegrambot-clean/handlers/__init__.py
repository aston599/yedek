"""
🎯 Handler Modülleri - aiogram
"""

from .start_handler import start_command
from .register_handler import kirvekayit_command, register_callback_handler, kayitsil_command, yardim_command, komutlar_command
# private_message_handler kullanılmıyor - main.py'de simple_message_handler kullanılıyor
from .group_handler import kirvegrup_command, group_info_command, botlog_command
from .message_monitor import monitor_group_message, start_cleanup_task
from .profile_handler import menu_command, profile_callback_handler, siparislerim_command, siralama_command, profil_command
# Admin commands artık router olarak import ediliyor
from .system_notifications import send_maintenance_notification, send_startup_notification, send_emergency_broadcast
from .recruitment_system import start_recruitment_background, handle_recruitment_response
# Chat system - lazy import kullanılıyor (message_monitor.py ve main.py içinde)
# handle_chat_message, send_chat_response, bot_write_command artık lazy import
from .admin_market_management import market_management_command, handle_product_creation_input, start_product_creation, confirm_product_creation, cancel_product_creation
from .smart_response_system import get_smart_response


__all__ = [
    'start_command',
    'kirvekayit_command',
    'kayitsil_command',
    'kirvegrup_command',
    'group_info_command',
    'botlog_command',
    'menu_command',
    'profile_callback_handler',
    'send_maintenance_notification',
    'send_startup_notification',
    'send_emergency_broadcast',
    'start_recruitment_background',
    'handle_recruitment_response',
    # Chat system functions removed - lazy import kullanılıyor
    'market_management_command',
    'yardim_command',
    'komutlar_command',
    # private_message_handler kaldırıldı - kullanılmıyor
    'register_callback_handler',
    'siparislerim_command',
    'siralama_command',
    'profil_command',
    'get_smart_response'
] 