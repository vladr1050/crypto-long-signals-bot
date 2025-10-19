#!/usr/bin/env python3
"""
Test script to verify the bot setup
"""
import os
import sys
import asyncio
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Set test environment variables
os.environ["BOT_TOKEN"] = "123456:ABC"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@host:port/db"
os.environ["EXCHANGE"] = "binance"
os.environ["SCAN_INTERVAL_SEC"] = "180"
os.environ["DEFAULT_RISK_PCT"] = "0.7"
os.environ["DEFAULT_PAIRS"] = "ETH/USDC,BNB/USDC,XRP/USDC,SOL/USDC,ADA/USDC"

async def test_imports():
    """Test that all modules can be imported"""
    try:
        print("Testing imports...")
        
        # Test core modules
        from app.config.settings import get_settings
        print("✅ Settings module imported")
        
        from app.core.data.market import MarketDataService
        print("✅ Market data service imported")
        
        from app.core.indicators.ta import TechnicalAnalysis
        print("✅ Technical analysis imported")
        
        from app.core.signals.detector import SignalDetector
        print("✅ Signal detector imported")
        
        from app.core.risk.sizing import RiskManager
        print("✅ Risk manager imported")
        
        from app.db.models import Base, User, Pair, Signal
        print("✅ Database models imported")
        
        from app.db.repo import DatabaseRepository
        print("✅ Database repository imported")
        
        from app.services.scanner import MarketScanner
        print("✅ Market scanner imported")
        
        from app.services.notifier import NotificationService
        print("✅ Notification service imported")
        
        from app.bot.handlers.basic import register_handlers
        print("✅ Bot handlers imported")
        
        from app.bot.keyboards.common import get_main_menu_keyboard
        print("✅ Bot keyboards imported")
        
        from app.bot.texts_en import WELCOME_MESSAGE
        print("✅ Bot texts imported")
        
        print("\n🎉 All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

async def test_basic_functionality():
    """Test basic functionality"""
    try:
        print("\nTesting basic functionality...")
        
        # Test settings
        from app.config.settings import get_settings
        settings = get_settings()
        print(f"✅ Settings loaded: {settings.exchange}")
        
        # Test technical analysis
        from app.core.indicators.ta import TechnicalAnalysis
        from app.core.risk.sizing import RiskManager
        import pandas as pd
        import numpy as np
        
        ta = TechnicalAnalysis()
        risk_manager = RiskManager()
        
        # Create mock data
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        mock_data = pd.DataFrame({
            'open': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(100, 200, 100),
            'low': np.random.uniform(100, 200, 100),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        }, index=dates)
        
        # Test indicators
        ema = ta.calculate_ema(mock_data['close'], 20)
        rsi = ta.calculate_rsi(mock_data['close'])
        print(f"✅ Technical indicators working: EMA={len(ema)}, RSI={len(rsi)}")
        
        # Test risk management
        position_size = risk_manager.calculate_position_size(10000, 1.0, 150, 145)
        tp1, tp2 = risk_manager.calculate_take_profits(150, 145)
        print(f"✅ Risk management working: Position={position_size:.2f}, TP1={tp1:.2f}, TP2={tp2:.2f}")
        
        print("\n🎉 Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Functionality test error: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Testing Crypto Long Signals Bot Setup\n")
    
    # Test imports
    imports_ok = await test_imports()
    
    if imports_ok:
        # Test functionality
        functionality_ok = await test_basic_functionality()
        
        if functionality_ok:
            print("\n✅ All tests passed! Bot setup is ready.")
            print("\nNext steps:")
            print("1. Copy env.example to .env")
            print("2. Add your BOT_TOKEN and DATABASE_URL")
            print("3. Run: python main.py")
        else:
            print("\n❌ Some functionality tests failed.")
    else:
        print("\n❌ Import tests failed. Check your dependencies.")

if __name__ == "__main__":
    asyncio.run(main())
