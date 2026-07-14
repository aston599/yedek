#!/usr/bin/env python3
"""main.py dosyasındaki merge conflict'leri ve null bytes'ları temizle"""

with open('main.py', 'rb') as f:
    content = f.read()

# Null bytes'ları temizle
content = content.replace(b'\x00', b'')

# String'e çevir ve satırlara böl
try:
    text = content.decode('utf-8', errors='ignore')
except:
    text = content.decode('latin-1', errors='ignore')

lines = text.split('\n')

# İlk `if __name__ == "__main__":` bloğunun sonunu bul
end_line = None
for i in range(len(lines)):
    if i > 2020 and 'if __name__ == "__main__":' in lines[i]:
        # İkinci `if __name__ == "__main__":` bulundu, önceki satırı bitir
        end_line = i
        break

if end_line is None:
    # İkinci `if __name__ == "__main__":` bulunamadı, `=======` marker'ını ara
    for i in range(len(lines)):
        if lines[i].strip() == '=======':
            end_line = i
            break

if end_line is None:
    # `>>>>>>>` marker'ını ara
    for i in range(len(lines)):
        if '>>>>>>>' in lines[i]:
            end_line = i
            break

if end_line:
    # İlk `if __name__ == "__main__":` bloğunun sonunu bul (traceback.print_exc() sonrası)
    for i in range(2020, min(end_line, len(lines))):
        if 'traceback.print_exc()' in lines[i]:
            # Bu satırdan sonra boş satır ekle ve bitir
            clean_lines = lines[:i+1]
            # Duplicate ve marker'ları temizle
            clean_lines.append('')
            # Dosyayı yaz
            with open('main.py', 'w', encoding='utf-8') as f:
                f.write('\n'.join(clean_lines))
            print(f"✅ Dosya temizlendi! {len(clean_lines)} satır kaldı (toplam {len(lines)} satırdan)")
            exit(0)

print("❌ Dosya düzgün temizlenemedi, manuel kontrol gerekli")
exit(1)





