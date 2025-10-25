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
from app.bot.middlewares.db import DbRepoMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global bot instance for scanner
_bot_instance = None


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
    try:
        await db_repo.initialize()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # Try to create tables manually
        try:
            from app.db.models import Base
            from sqlalchemy.ext.asyncio import create_async_engine
            engine = create_async_engine(settings.database_url)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables created manually")
        except Exception as e2:
            logger.error(f"❌ Manual table creation failed: {e2}")
            raise
    
    # Register handlers
    register_handlers(dp)
    
    # Inject db_repo via middleware (preferred for aiogram 3.x)
    dp.update.outer_middleware(DbRepoMiddleware(db_repo))
    
        # Store bot instance globally for scanner
        global _bot_instance
        _bot_instance = bot
        
        # Start bot with lifespan
        async with lifespan():
            await dp.start_polling(bot)


def get_bot_instance():
    """Get the global bot instance for scanner"""
    return _bot_instance


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
