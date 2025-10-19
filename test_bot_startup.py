#!/usr/bin/env python3
"""
Test script to verify bot can start without errors
"""
import os
import sys
import asyncio
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Set test environment variables
os.environ["BOT_TOKEN"] = "123456:ABC"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
os.environ["EXCHANGE"] = "binance"
os.environ["SCAN_INTERVAL_SEC"] = "180"
os.environ["DEFAULT_RISK_PCT"] = "0.7"
os.environ["DEFAULT_PAIRS"] = "ETH/USDC,BNB/USDC,XRP/USDC,SOL/USDC,ADA/USDC"

async def test_bot_initialization():
    """Test that bot can be initialized without errors"""
    try:
        print("Testing bot initialization...")
        
        from app.main import main
        from app.config.settings import get_settings
        
        # Test settings loading
        settings = get_settings()
        print(f"✅ Settings loaded: {settings.exchange}")
        
        # Test database repository initialization
        from app.db.repo import DatabaseRepository
        db_repo = DatabaseRepository(settings.database_url)
        print("✅ Database repository created")
        
        # Test bot and dispatcher creation
        from aiogram import Bot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from aiogram.fsm.storage.memory import MemoryStorage
        
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        dp = Dispatcher(storage=MemoryStorage())
        print("✅ Bot and dispatcher created")
        
        # Test handler registration
        from app.bot.handlers.basic import register_handlers
        register_handlers(dp)
        print("✅ Handlers registered")
        
        # Test dependency injection
        dp["db_repo"] = db_repo
        print("✅ Dependencies injected")
        
        print("\n🎉 Bot initialization test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Bot initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Testing Bot Startup\n")
    
    success = await test_bot_initialization()
    
    if success:
        print("\n✅ Bot is ready for deployment!")
        print("\nNext steps:")
        print("1. Set your real BOT_TOKEN and DATABASE_URL")
        print("2. Deploy to Railway")
        print("3. Test with real Telegram bot")
    else:
        print("\n❌ Bot startup test failed.")
        print("Check the errors above and fix them before deploying.")

if __name__ == "__main__":
    asyncio.run(main())
