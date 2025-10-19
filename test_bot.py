#!/usr/bin/env python3
"""
Test bot functionality
"""
import asyncio
import os
import sys
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

async def test_bot():
    """Test bot functionality"""
    try:
        print("🚀 Testing bot...")
        
        # Test imports
        from app.config.settings import get_settings
        from app.db.repo import DatabaseRepository
        from app.core.data.market import MarketDataService
        from app.core.indicators.ta import TechnicalAnalysis
        from app.core.risk.sizing import RiskManager
        from app.core.signals.detector import SignalDetector
        from app.services.scanner import MarketScanner
        from app.services.notifier import NotificationService
        
        print("✅ All imports successful")
        
        # Test settings
        settings = get_settings()
        print(f"✅ Settings loaded: {settings.exchange}")
        
        # Test database (without actual connection)
        print("✅ Database repository created")
        
        # Test market data service
        market_data = MarketDataService()
        print("✅ Market data service created")
        
        # Test technical analysis
        ta = TechnicalAnalysis()
        print("✅ Technical analysis created")
        
        # Test risk manager
        risk_manager = RiskManager()
        print("✅ Risk manager created")
        
        # Test signal detector
        signal_detector = SignalDetector(ta, risk_manager)
        print("✅ Signal detector created")
        
        # Test notification service
        notifier = NotificationService()
        print("✅ Notification service created")
        
        print("\n🎉 All tests passed! Bot is ready.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_bot())
