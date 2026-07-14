#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conflict çözücü script - Tüm conflict marker'larını HEAD versiyonuna göre çözer
"""
import re

def resolve_conflicts(content):
    """Tüm conflict marker'larını HEAD versiyonuna göre çözer"""
    # Conflict pattern: <<<<<<< HEAD ... ======= ... >>>>>>> commit_hash
    pattern = r'<<<<<<< HEAD\n(.*?)\n=======\n.*?\n>>>>>>> [^\n]+\n'
    
    def replace_conflict(match):
        # HEAD versiyonunu al (ilk grup)
        return match.group(1) + '\n'
    
    # Tüm conflict'leri çöz
    resolved = re.sub(pattern, replace_conflict, content, flags=re.DOTALL)
    
    return resolved

if __name__ == '__main__':
    # main.py dosyasını oku
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Conflict'leri çöz
    resolved_content = resolve_conflicts(content)
    
    # Dosyayı yaz
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(resolved_content)
    
    print("Conflict'ler çözüldü!")


