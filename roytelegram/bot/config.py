import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: tuple[int, ...]
    setup_secret: str
    database_path: Path


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is required in .env")

    raw_admins = os.getenv("ADMIN_IDS", "").strip()
    admin_ids = tuple(
        int(item.strip())
        for item in raw_admins.split(",")
        if item.strip().isdigit()
    )

    setup_secret = os.getenv("SETUP_SECRET", "").strip()

    if not admin_ids and not setup_secret:
        raise RuntimeError("Set ADMIN_IDS or SETUP_SECRET in .env")

    db_path = Path(os.getenv("DATABASE_PATH", "data/bot.db"))
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    return Settings(
        bot_token=token,
        admin_ids=admin_ids,
        setup_secret=setup_secret,
        database_path=db_path,
    )
