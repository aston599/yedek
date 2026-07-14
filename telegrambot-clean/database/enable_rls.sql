-- =============================================
-- ROW LEVEL SECURITY (RLS) ETKİNLEŞTİRME
-- Supabase/PostgreSQL için güvenlik politikaları
-- =============================================

-- ÖNEMLİ: Bu script, tüm tablolarda RLS'yi etkinleştirir
-- Ancak politikaları manuel olarak ayarlamanız gerekebilir

-- 1. balance_logs tablosu
ALTER TABLE balance_logs ENABLE ROW LEVEL SECURITY;

-- 2. bot_status tablosu
ALTER TABLE bot_status ENABLE ROW LEVEL SECURITY;

-- 3. custom_commands tablosu
ALTER TABLE custom_commands ENABLE ROW LEVEL SECURITY;

-- 4. daily_stats tablosu
ALTER TABLE daily_stats ENABLE ROW LEVEL SECURITY;

-- 5. event_participants tablosu
ALTER TABLE event_participants ENABLE ROW LEVEL SECURITY;

-- 6. event_participations tablosu
ALTER TABLE event_participations ENABLE ROW LEVEL SECURITY;

-- 7. events tablosu
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- 8. market_categories tablosu
ALTER TABLE market_categories ENABLE ROW LEVEL SECURITY;

-- 9. market_order_logs tablosu
ALTER TABLE market_order_logs ENABLE ROW LEVEL SECURITY;

-- 10. market_orders tablosu
ALTER TABLE market_orders ENABLE ROW LEVEL SECURITY;

-- 11. market_products tablosu
ALTER TABLE market_products ENABLE ROW LEVEL SECURITY;

-- 12. point_settings tablosu
ALTER TABLE point_settings ENABLE ROW LEVEL SECURITY;

-- 13. recruitment_daily_limits tablosu
ALTER TABLE recruitment_daily_limits ENABLE ROW LEVEL SECURITY;

-- 14. registered_groups tablosu
ALTER TABLE registered_groups ENABLE ROW LEVEL SECURITY;

-- 15. scheduled_messages_settings tablosu
ALTER TABLE scheduled_messages_settings ENABLE ROW LEVEL SECURITY;

-- 16. sites tablosu
ALTER TABLE sites ENABLE ROW LEVEL SECURITY;

-- 17. system_settings tablosu
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;

-- 18. users tablosu
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 19. warnings tablosu
ALTER TABLE warnings ENABLE ROW LEVEL SECURITY;

-- 20. punishment_logs tablosu
ALTER TABLE punishment_logs ENABLE ROW LEVEL SECURITY;

-- 21. blocked_bots tablosu
ALTER TABLE blocked_bots ENABLE ROW LEVEL SECURITY;

-- =============================================
-- TEMEL GÜVENLİK POLİTİKALARI
-- =============================================

-- NOT: Bu politikalar, bot'un kendi bağlantısından erişim sağlar
-- Ancak Supabase API üzerinden erişimi engeller

-- Örnek: users tablosu için - Sadece bot erişebilir
-- (Supabase API üzerinden erişim engellenir, bot'un direkt bağlantısı çalışır)

-- ÖNEMLİ: Eğer Supabase API kullanmıyorsanız ve sadece bot üzerinden erişim varsa,
-- RLS'yi etkinleştirmek yeterlidir. Bot'un direkt PostgreSQL bağlantısı çalışmaya devam eder.

-- =============================================
-- ALTERNATİF: RLS'Yİ KAPATMAK (SADECE BOT ERİŞİMİ)
-- =============================================

-- Eğer Supabase API kullanmıyorsanız ve sadece bot üzerinden erişim varsa,
-- RLS'yi kapatabilirsiniz (güvenlik riski yok):

-- ALTER TABLE balance_logs DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE bot_status DISABLE ROW LEVEL SECURITY;
-- ... (diğer tablolar için)

-- =============================================
-- KONTROL SORGUSU
-- =============================================

-- RLS durumunu kontrol etmek için:
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;



