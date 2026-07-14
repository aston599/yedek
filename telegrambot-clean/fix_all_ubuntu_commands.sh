#!/bin/bash
# Ubuntu'daki main.py dosyasını tamamen düzelt - Tüm admin panel komutlarını handler fonksiyonlarına çevir

cd ~/telegrambot || exit 1

# Yedek al
cp main.py main.py.backup.$(date +%s)

# Python script ile tüm direkt kullanımları düzelt
python3 << 'PYEOF'
import re

with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
skip_next = False

while i < len(lines):
    line = lines[i]
    indent = len(line) - len(line.lstrip())
    indent_str = ' ' * indent
    
    # Direkt admin panel komut kullanımlarını bul ve düzelt
    if 'dp.message(Command("adminpanel"))(admin_panel_command)' in line:
        # İlk admin panel handler'ı - önceki yorum satırlarını koru
        new_lines.append(indent_str + '# MANUEL HANDLER KAYITLARI - TEK ADMİN PANELİ\n')
        new_lines.append(indent_str + '# Lazy import ile admin panel komutları\n')
        new_lines.append(indent_str + 'async def handle_admin_panel(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import admin_panel_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("adminpanel"))(handle_admin_panel)\n')
        i += 1
    elif 'dp.message(Command("adminkomutlar"))(admin_panel_command)' in line:
        new_lines.append(indent_str + '\n')
        new_lines.append(indent_str + 'async def handle_admin_komutlar(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import admin_panel_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("adminkomutlar"))(handle_admin_komutlar)\n')
        i += 1
    elif 'dp.message(Command("updatebot"))(update_bot_command)' in line:
        new_lines.append(indent_str + '\n')
        new_lines.append(indent_str + 'async def handle_update_bot(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import update_bot_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("updatebot"))(handle_update_bot)\n')
        i += 1
    elif 'dp.message(Command("temizle"))(clean_messages_command)' in line:
        new_lines.append(indent_str + '\n')
        new_lines.append(indent_str + '# Mesaj silme komutu - lazy import\n')
        new_lines.append(indent_str + 'async def handle_clean_messages(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import clean_messages_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("temizle"))(handle_clean_messages)\n')
        i += 1
    elif 'dp.message(Command("gruplar"))(list_groups_command)' in line:
        new_lines.append(indent_str + '\n')
        new_lines.append(indent_str + 'async def handle_list_groups(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import list_groups_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("gruplar"))(handle_list_groups)\n')
        i += 1
    elif 'dp.message(Command("grupsil"))(delete_group_command)' in line:
        new_lines.append(indent_str + '\n')
        new_lines.append(indent_str + 'async def handle_delete_group(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import delete_group_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("grupsil"))(handle_delete_group)\n')
        i += 1
    elif 'dp.message(Command("yardim"))(help_command)' in line:
        new_lines.append(indent_str + '\n')
        new_lines.append(indent_str + 'async def handle_help(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import help_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("yardim"))(handle_help)\n')
        i += 1
    elif 'dp.message(Command("siparisonayla"))(approve_order_command)' in line:
        new_lines.append(indent_str + '\n')
        new_lines.append(indent_str + 'async def handle_approve_order(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import approve_order_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("siparisonayla"))(handle_approve_order)\n')
        i += 1
    elif 'dp.message(Command("testmarket"))(test_market_system_command)' in line:
        new_lines.append(indent_str + '\n')
        new_lines.append(indent_str + '# Test komutları - lazy import\n')
        new_lines.append(indent_str + 'async def handle_test_market(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import test_market_system_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("testmarket"))(handle_test_market)\n')
        i += 1
    elif 'dp.message(Command("testsql"))(test_sql_queries_command)' in line:
        new_lines.append(indent_str + '\n')
        new_lines.append(indent_str + 'async def handle_test_sql(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import test_sql_queries_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("testsql"))(handle_test_sql)\n')
        i += 1
    elif 'dp.message(Command("testsiparis"))(test_user_orders_command)' in line:
        new_lines.append(indent_str + '\n')
        new_lines.append(indent_str + 'async def handle_test_siparis(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import test_user_orders_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("testsiparis"))(handle_test_siparis)\n')
        i += 1
    elif 'dp.message(Command("fixscheduled"))(fix_scheduled_messages_command)' in line:
        new_lines.append(indent_str + '\n')
        new_lines.append(indent_str + 'async def handle_fix_scheduled(message: Message):\n')
        new_lines.append(indent_str + '    from handlers.admin_panel import fix_scheduled_messages_command as cmd\n')
        new_lines.append(indent_str + '    await cmd(message)\n')
        new_lines.append(indent_str + 'dp.message(Command("fixscheduled"))(handle_fix_scheduled)\n')
        i += 1
    else:
        new_lines.append(line)
        i += 1

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"✅ Handler kayıtları düzeltildi! {len(lines)} satırdan {len(new_lines)} satıra güncellendi")
PYEOF

if [ $? -eq 0 ]; then
    # Syntax kontrolü
    python3 -m py_compile main.py
    if [ $? -eq 0 ]; then
        echo "✅ Dosya başarıyla düzeltildi ve syntax kontrolü geçti!"
        sudo systemctl restart kirvebot
        sleep 2
        sudo journalctl -u kirvebot -n 50 --no-pager
    else
        echo "❌ Syntax hatası var!"
        cp main.py.backup.* main.py 2>/dev/null || echo "Backup yok, manuel düzeltme gerekli"
    fi
else
    echo "❌ Script hatası!"
fi





