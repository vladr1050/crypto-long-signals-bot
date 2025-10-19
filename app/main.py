"""
Main application entry point for Crypto Long Signals Bot
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config.settings import get_settings
from app.core.data.market import MarketDataService
from app.core.indicators.ta import TechnicalAnalysis
from app.core.signals.detector import SignalDetector
from app.core.risk.sizing import RiskManager
from app.db.repo import DatabaseRepository
from app.services.scanner import MarketScanner
from app.services.notifier import NotificationService
from app.bot.handlers.basic import register_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan():
    """Application lifespan manager"""
    settings = get_settings()
    
    # Initialize database
    db_repo = DatabaseRepository(settings.database_url)
    await db_repo.initialize()
    
    # Initialize services
    market_data = MarketDataService()
    ta = TechnicalAnalysis()
    risk_manager = RiskManager()
    signal_detector = SignalDetector(ta, risk_manager)
    notifier = NotificationService()
    
    # Initialize scanner
    scanner = MarketScanner(
        db_repo=db_repo,
        market_data=market_data,
        signal_detector=signal_detector,
        notifier=notifier,
        settings=settings
    )
    
    # Start background tasks
    await scanner.start()
    
    logger.info("🚀 Crypto Long Signals Bot started successfully")
    logger.info(f"📊 Scanning pairs: {settings.default_pairs}")
    logger.info(f"⏱️ Scan interval: {settings.scan_interval_sec}s")
    logger.info(f"💰 Default risk: {settings.default_risk_pct}%")
    
    yield
    
    # Cleanup
    await scanner.stop()
    await db_repo.close()
    logger.info("🛑 Bot stopped")


async def main():
    """Main application function"""
    settings = get_settings()
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Initialize database
    db_repo = DatabaseRepository(settings.database_url)
    await db_repo.initialize()
    
    # Register handlers
    register_handlers(dp)
    
    # Store dependencies in bot data
    bot["db_repo"] = db_repo
    
    # Start bot with lifespan
    async with lifespan():
        await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
