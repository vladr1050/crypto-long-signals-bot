"""
Middleware to inject DatabaseRepository into handler kwargs (aiogram 3.x)
"""
import logging
from typing import Any, Callable, Dict

from aiogram import BaseMiddleware

logger = logging.getLogger(__name__)


class DbRepoMiddleware(BaseMiddleware):
    def __init__(self, db_repo: Any) -> None:
        super().__init__()
        self._db_repo = db_repo
        logger.info(f"DbRepoMiddleware initialized with db_repo: {db_repo is not None}")

    async def __call__(
        self,
        handler: Callable,
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        # Inject repository instance so handlers can accept `db_repo` param
        data["db_repo"] = self._db_repo
        logger.debug(f"DbRepoMiddleware: injecting db_repo into data")
        return await handler(event, data)


