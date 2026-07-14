#!/bin/bash
cd "$(dirname "$0")"
git add handlers/dynamic_command_creator.py
git commit -m "feat: !market komutu eklendi"
git push origin main


