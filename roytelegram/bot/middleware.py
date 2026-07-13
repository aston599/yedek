from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.database import Database


class AppMiddleware(BaseMiddleware):
    def __init__(
        self,
        db: Database,
        env_admin_ids: tuple[int, ...],
        setup_secret: str,
    ) -> None:
        self.db = db
        self.env_admin_ids = env_admin_ids
        self.setup_secret = setup_secret

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["db"] = self.db
        data["env_admin_ids"] = self.env_admin_ids
        data["setup_secret"] = self.setup_secret
        data["admin_ids"] = await self.db.get_admin_ids(self.env_admin_ids)
        return await handler(event, data)
