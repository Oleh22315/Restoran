from typing import Callable, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy import select
from common.locale_manager import LocaleManager
from db.user import User


class LocaleMiddleware(BaseMiddleware):
    def __init__(self, locale_dir: str):
        super().__init__()
        self.manager = LocaleManager(locale_dir)

    def get_user_id(self, event: Update):
        if event.message:
            return event.message.from_user.id
        elif event.callback_query:
            return event.callback_query.from_user.id
        elif event.inline_query:
            return event.inline_query.from_user.id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        user_id = self.get_user_id(event)
        if not user_id in LocaleManager.USER_LOCALS:
            user: User = (await data["session"].execute(select(User).filter(User.id == user_id))).scalars().first()
            LocaleManager.USER_LOCALS[user_id] = user.locale if user else "en"

        data["locale"] = self.manager.get_locale(LocaleManager.USER_LOCALS[user_id])
        data["current_locale"] = LocaleManager.USER_LOCALS[user_id]
        data["manager"] = self.manager
        return await handler(event, data)
