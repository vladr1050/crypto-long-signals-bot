import asyncio
import logging
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config.settings import settings
from app.db.repo import Repo
from app.services.notifier import Notifier
from app.services.scanner import Scanner
from app.bot.handlers.basic import router as basic_router
from app_init import make_bot, make_repo, chat_ids_provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")

async def on_startup(dp: Dispatcher, repo: Repo, scanner: Scanner):
    await repo.init_db(settings.default_pairs, settings.default_risk_pct)
    scanner.start()
    log.info("Scheduler started")

async def main():
    log.info("🚀 Starting crypto-long-signals-bot...")
    repo = make_repo(Repo.make_engine(settings.database_url))
    bot = make_bot()
    notifier = Notifier(bot, repo)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(basic_router)

    # DI into handlers
    dp["repo"] = repo

    # scanner
    scanner = Scanner(repo, notifier, lambda: chat_ids_provider(repo))

    await on_startup(dp, repo, scanner)
    log.info("Bot listening...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
