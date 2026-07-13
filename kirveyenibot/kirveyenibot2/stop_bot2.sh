#!/bin/bash

# KirveBot2 durdurma scripti

echo "🛑 KirveBot2 durduruluyor..."

# Bot2 süreçlerini durdur
pkill -f "python.*bot.py.*kirveyenibot2"

# Python süreçlerini temizle
pkill -f "python3.*bot.py"

# Webhook'u temizle
curl -X POST "https://api.telegram.org/bot8432099283:AAHUa2AiYE2IXoAmL7rZ4IzbWgR0UCKf7X8/deleteWebhook"

echo "✅ KirveBot2 durduruldu!"
