#!/usr/bin/env python3
"""
Force reset database - drop and recreate all tables
"""
import asyncio
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def force_reset():
    """Force reset database"""
    try:
        print("🚀 Force resetting database...")
        
        # Get database URL
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL not found")
            return
        
        print(f"📊 Connecting to: {database_url[:50]}...")
        
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        # Create engine
        engine = create_async_engine(database_url, echo=True)
        
        async with engine.begin() as conn:
            # Drop all tables in correct order (respecting foreign keys)
            print("🗑️ Dropping all tables...")
            
            # Drop tables in reverse dependency order
            tables_to_drop = [
                "signals",
                "pairs", 
                "users",
                "settings"
            ]
            
            for table in tables_to_drop:
                try:
                    await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    print(f"✅ Dropped table: {table}")
                except Exception as e:
                    print(f"⚠️ Could not drop {table}: {e}")
            
            print("✅ All tables dropped")
            
            # Now create tables
            print("🔨 Creating tables...")
            
            # Create users table
            await conn.execute(text("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    tg_id BIGINT UNIQUE NOT NULL,
                    lang VARCHAR(5) DEFAULT 'en',
                    risk_pct FLOAT DEFAULT 0.7,
                    signals_enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✅ Created users table")
            
            # Create pairs table
            await conn.execute(text("""
                CREATE TABLE pairs (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) UNIQUE NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✅ Created pairs table")
            
            # Create signals table
            await conn.execute(text("""
                CREATE TABLE signals (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    timeframe VARCHAR(10) NOT NULL,
                    entry_price FLOAT NOT NULL,
                    stop_loss FLOAT NOT NULL,
                    take_profit_1 FLOAT NOT NULL,
                    take_profit_2 FLOAT NOT NULL,
                    grade VARCHAR(1) NOT NULL,
                    risk_level FLOAT NOT NULL,
                    reason TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    expires_at TIMESTAMP NOT NULL,
                    triggered_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✅ Created signals table")
            
            # Create settings table
            await conn.execute(text("""
                CREATE TABLE settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(50) UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✅ Created settings table")
            
            # Create indexes
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pairs_symbol ON pairs(symbol)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status)"))
            print("✅ Created indexes")
            
            # Insert default pairs
            default_pairs = ["ETH/USDC", "BNB/USDC", "XRP/USDC", "SOL/USDC", "ADA/USDC"]
            for pair in default_pairs:
                await conn.execute(text("""
                    INSERT INTO pairs (symbol, enabled) 
                    VALUES (:symbol, TRUE) 
                    ON CONFLICT (symbol) DO NOTHING
                """), {"symbol": pair})
            print(f"✅ Inserted {len(default_pairs)} default pairs")
            
        print("🎉 Database force reset completed!")
        
        # Test the database
        print("🧪 Testing database...")
        from app.db.repo import DatabaseRepository
        db_repo = DatabaseRepository(database_url)
        await db_repo.initialize()
        
        # Test creating a signal
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
        
        await db_repo.close()
        await engine.dispose()
        
        print("🎉 Database is ready!")
        
    except Exception as e:
        print(f"❌ Force reset failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(force_reset())
