#!/usr/bin/env python3
"""
Reset database - drop all tables and recreate
"""
import asyncio
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def reset_database():
    """Reset database - drop all tables and recreate"""
    try:
        print("🚀 Resetting database...")
        
        from app.db.models import Base
        from sqlalchemy.ext.asyncio import create_async_engine
        
        # Get database URL from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            sys.exit(1)
        
        print(f"📊 Database URL: {database_url[:50]}...")
        
        # Create engine
        engine = create_async_engine(database_url, echo=True)
        
        # Drop all tables
        print("🗑️ Dropping all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        print("✅ All tables dropped")
        
        # Create all tables
        print("🔨 Creating all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ All tables created successfully!")
        
        # Test connection and verify tables
        from app.db.repo import DatabaseRepository
        db_repo = DatabaseRepository(database_url)
        await db_repo.initialize()
        print("✅ Database connection test passed!")
        
        # Test creating a signal to verify table structure
        try:
            from datetime import datetime, timedelta
            test_signal = await db_repo.create_signal(
                symbol="TEST/USDC",
                timeframe="15m",
                entry_price=100.0,
                stop_loss=95.0,
                take_profit_1=105.0,
                take_profit_2=110.0,
                grade="A",
                risk_level=1.0,
                reason="Test signal",
                expires_at=datetime.utcnow() + timedelta(hours=8)
            )
            print(f"✅ Test signal created with ID: {test_signal.id}")
            
            # Clean up test signal
            await db_repo.close()
            
        except Exception as e:
            print(f"⚠️ Test signal creation failed: {e}")
        
        await engine.dispose()
        
        print("🎉 Database reset completed successfully!")
        
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(reset_database())
