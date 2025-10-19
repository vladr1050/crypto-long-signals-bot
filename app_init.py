from aiogram import Bot, Dispatcher
from app.config.settings import settings
from app.db.repo import Repo
from app.db.models import User
from sqlalchemy.ext.asyncio import AsyncEngine
from typing import List

def make_bot() -> Bot:
    return Bot(settings.bot_token)

def make_repo(engine: AsyncEngine) -> Repo:
    return Repo(engine)

async def chat_ids_provider(repo: Repo) -> List[int]:
    # simple broadcast to all known users (extend as needed)
    async with repo.Session() as s:
        rows = await s.execute(User.__table__.select())
        return [r.tg_id for r in rows]
