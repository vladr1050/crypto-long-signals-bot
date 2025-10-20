"""
Middleware to inject DatabaseRepository into handler kwargs (aiogram 3.x)
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware


class DbRepoMiddleware(BaseMiddleware):
    def __init__(self, db_repo: Any) -> None:
        super().__init__()
        self._db_repo = db_repo

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        # Inject repository instance so handlers can accept `db_repo` param
        data["db_repo"] = self._db_repo
        return await handler(event, data)


