"""Türkçe arayüz metinleri ve admin panel betimlemeleri."""

SETTING_LABELS: dict[str, str] = {
    "welcome_text": "Hoş Geldin Mesajı",
    "ad_banner": "Üst Reklam Banner",
    "promo_code": "Promo Kodu",
    "inline_button_text": "Inline Buton Metni",
    "inline_button_url": "Inline Buton Linki",
    "menu_button_text": "Alt Menü Buton Metni",
    "menu_button_url": "Alt Menü Buton Linki",
    "welcome_image": "Promo Görseli (Sohbet)",
    "profile_image": "Profil Resmi (Avatar)",
    "profile_cover": "Kapak Görseli (Başla Öncesi)",
}

ADMIN_PANEL_TEXT = (
    "🛠 <b>Admin Paneli</b>\n\n"
    "Botun kullanıcılara göstereceği metinleri, butonları ve reklam alanını "
    "buradan düzenleyin.\n\n"
    "Bir seçeneğe dokunun, ardından botun istediği yeni değeri gönderin."
)

EDIT_PROMPTS: dict[str, str] = {
    "welcome_text": (
        "📝 <b>Hoş Geldin Mesajı</b>\n\n"
        "Kullanıcı <code>/start</code> yazdığında görünen ana promo metnidir.\n\n"
        "<b>Mevcut değer:</b>\n{current}\n\n"
        "Yeni metni gönderin. HTML desteklenir (<b>kalın</b>, <code>kod</code>).\n"
        "İptal: /cancel veya /iptal"
    ),
    "ad_banner": (
        "📢 <b>Üst Reklam Banner</b>\n\n"
        "Mesajın en üstünde görünen sponsor / reklam satırıdır.\n\n"
        "<b>Mevcut değer:</b>\n{current}\n\n"
        "Yeni banner metnini gönderin.\n"
        "İptal: /cancel"
    ),
    "promo_code": (
        "🎫 <b>Promo Kodu</b>\n\n"
        "Kullanıcılara gösterilecek VIP / bonus kodudur.\n\n"
        "<b>Mevcut değer:</b> <code>{current}</code>\n\n"
        "Yeni promo kodunu gönderin (sadece kod, örn: <code>BETROY</code>).\n"
        "İptal: /cancel"
    ),
    "welcome_image": (
        "🖼 <b>Promo Görseli (Sohbet)</b>\n\n"
        "<code>/start</code> veya herhangi bir yazıda görünen "
        "<b>yatay banner</b> görselidir.\n\n"
        "{current}\n\n"
        "Yeni görseli <b>fotoğraf olarak</b> gönderin.\n"
        "Silmek için: <code>/clear_image</code>\n"
        "İptal: /cancel"
    ),
    "profile_image": (
        "📷 <b>Profil Resmi (Avatar)</b>\n\n"
        "Sohbet listesinde ve bot adının yanında görünen "
        "<b>yuvarlak profil resmi</b>dir.\n\n"
        "{current}\n\n"
        "Kare fotoğraf gönderin (ortada logo/metin olsun).\n"
        "İptal: /cancel"
    ),
    "profile_cover": (
        "🖼 <b>Kapak Görseli (Başla Öncesi)</b>\n\n"
        "«Başla» demeden önce görünen üst kapak görselidir.\n"
        "Telegram profil fotoğrafı olarak yüklenir.\n\n"
        "{current}\n\n"
        "Kare JPG fotoğraf gönderin (640×640 önerilir).\n"
        "İptal: /cancel"
    ),
    "inline_button": (
        "🔘 <b>Inline Buton</b>\n\n"
        "Mesajın altındaki yeşil dış link butonudur.\n\n"
        "<b>Mevcut:</b> {current}\n\n"
        "Yeni değeri şu formatta gönderin:\n"
        "<code>Buton Metni | https://link.com</code>\n\n"
        "Örnek:\n"
        "<code>🎰 900 FREESPIN | https://roygir.com/zayptv</code>\n\n"
        "İptal: /cancel"
    ),
    "menu_button": (
        "⌨️ <b>Alt Menü Butonu</b>\n\n"
        "Sohbetin altında sabit duran giriş butonudur.\n\n"
        "<b>Mevcut:</b> {current}\n\n"
        "Yeni değeri şu formatta gönderin:\n"
        "<code>Buton Metni | https://link.com</code>\n\n"
        "Örnek:\n"
        "<code>🎁 Giriş | https://roygir.com/zayptv</code>\n\n"
        "İptal: /cancel"
    ),
    "broadcast": (
        "📣 <b>Toplu Mesaj</b>\n\n"
        "Tüm kayıtlı kullanıcılara duyuru gönderir.\n\n"
        "Metin veya fotoğraf+metin gönderin. HTML desteklenir.\n"
        "İptal: /cancel"
    ),
}

SAVE_SUCCESS = "✅ <b>{label}</b> güncellendi."

UNAUTHORIZED = "⛔ Bu komut yalnızca adminler içindir."

HELP_TEXT = (
    "ℹ️ <b>Betroy Bot — Komutlar</b>\n\n"
    "<b>Herkes:</b>\n"
    "/start — Bonus ve giriş mesajını gör\n"
    "/whoami — Telegram ID'nizi öğrenin\n\n"
    "<b>Admin:</b>\n"
    "/admin — Yönetim paneli\n"
    "/cancel — Devam eden düzenlemeyi iptal et\n"
    "/clear_image — Promo görselini sil"
)
