#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gelişmiş Conflict çözücü script - Tüm nested conflict'leri HEAD versiyonuna göre çözer
"""
import re

def resolve_all_conflicts(content):
    """Tüm conflict marker'larını (nested dahil) HEAD versiyonuna göre çözer"""
    
    # Önce nested conflict'leri çöz
    lines = content.split('\n')
    resolved_lines = []
    i = 0
    in_conflict = False
    conflict_start = None
    conflict_depth = 0
    head_lines = []
    
    while i < len(lines):
        line = lines[i]
        
        # Conflict başlangıcı
        if line.strip().startswith('<<<<<<< HEAD'):
            if not in_conflict:
                in_conflict = True
                conflict_start = i
                conflict_depth = 1
                head_lines = []
            else:
                conflict_depth += 1
            i += 1
            continue
        
        # Conflict separator
        if line.strip() == '=======' and in_conflict:
            conflict_depth -= 1
            if conflict_depth == 0:
                # HEAD kısmını al, geri kalanını atla
                i += 1
                # >>>>>>> satırını bul ve atla
                while i < len(lines) and not lines[i].strip().startswith('>>>>>>>'):
                    i += 1
                if i < len(lines):
                    i += 1  # >>>>>>> satırını atla
                # HEAD lines'i ekle
                resolved_lines.extend(head_lines)
                in_conflict = False
                head_lines = []
            else:
                i += 1
            continue
        
        # Conflict bitişi
        if line.strip().startswith('>>>>>>>') and in_conflict:
            conflict_depth -= 1
            if conflict_depth == 0:
                # HEAD lines'i ekle
                resolved_lines.extend(head_lines)
                in_conflict = False
                head_lines = []
            i += 1
            continue
        
        # Normal satır
        if in_conflict and conflict_depth == 1:
            # HEAD kısmındaki satırlar
            head_lines.append(line)
        elif not in_conflict:
            # Normal satır
            resolved_lines.append(line)
        else:
            # İç içe conflict içindeki satır - atla
            pass
        
        i += 1
    
    # Eğer conflict kapatılmamışsa, HEAD kısmını ekle
    if in_conflict:
        resolved_lines.extend(head_lines)
    
    return '\n'.join(resolved_lines)

if __name__ == '__main__':
    # main.py dosyasını oku
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Conflict'leri çöz
    resolved_content = resolve_all_conflicts(content)
    
    # Dosyayı yaz
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(resolved_content)
    
    print("Tüm conflict'ler çözüldü!")

