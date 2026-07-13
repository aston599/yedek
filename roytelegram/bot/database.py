import json
from pathlib import Path
from typing import Any

import aiosqlite

from bot.texts import WELCOME_TEXT

DEFAULT_SETTINGS: dict[str, str] = {
    "ad_banner": "",
    "welcome_text": WELCOME_TEXT,
    "welcome_image": "",
    "inline_button_text": "✅ Hemen Oyna",
    "inline_button_url": "https://roygir.com/zayptv",
    "menu_button_text": "🎁 Giriş",
    "menu_button_url": "https://roygir.com/zayptv",
    "promo_code": "BETROY",
}

SETTING_KEYS = tuple(DEFAULT_SETTINGS.keys())


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    joined_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    clicked_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY
                )
                """
            )
            for key, value in DEFAULT_SETTINGS.items():
                await db.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )
            await db.commit()

    async def get_setting(self, key: str) -> str:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            )
            row = await cursor.fetchone()
            if row is None:
                return DEFAULT_SETTINGS.get(key, "")
            return row[0]

    async def get_all_settings(self) -> dict[str, str]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT key, value FROM settings")
            rows = await cursor.fetchall()
        return {key: value for key, value in rows}

    async def set_setting(self, key: str, value: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
            await db.commit()

    async def upsert_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name
                """,
                (user_id, username, first_name),
            )
            await db.commit()

    async def count_users(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    async def count_clicks(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM clicks")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    async def count_clicks_by_source(self) -> dict[str, int]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT source, COUNT(*) FROM clicks GROUP BY source ORDER BY COUNT(*) DESC"
            )
            rows = await cursor.fetchall()
        return {source: count for source, count in rows}

    async def log_click(self, user_id: int, source: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO clicks (user_id, source) VALUES (?, ?)",
                (user_id, source),
            )
            await db.commit()

    async def all_user_ids(self) -> list[int]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT user_id FROM users")
            rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def get_admin_ids(self, env_admin_ids: tuple[int, ...]) -> tuple[int, ...]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("SELECT user_id FROM admins")
            rows = await cursor.fetchall()
        db_admins = tuple(row[0] for row in rows)
        return tuple(dict.fromkeys((*env_admin_ids, *db_admins)))

    async def add_admin(self, user_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO admins (user_id) VALUES (?)",
                (user_id,),
            )
            await db.commit()

    async def export_settings(self) -> str:
        settings = await self.get_all_settings()
        return json.dumps(settings, ensure_ascii=False, indent=2)

    async def import_settings(self, payload: dict[str, Any]) -> list[str]:
        updated: list[str] = []
        for key in SETTING_KEYS:
            if key in payload and isinstance(payload[key], str):
                await self.set_setting(key, payload[key])
                updated.append(key)
        return updated
