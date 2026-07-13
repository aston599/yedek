#!/usr/bin/env python3
"""Hoş geldin mesajını varsayılana sıfırlar (admin panel şablonu kaydedildiyse)."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.config import load_settings
from bot.database import Database
from bot.texts import WELCOME_TEXT


async def main() -> None:
    db = Database(load_settings().database_path)
    await db.connect()
    await db.set_setting("welcome_text", WELCOME_TEXT)
    print("welcome_text sıfırlandı.")


if __name__ == "__main__":
    asyncio.run(main())
