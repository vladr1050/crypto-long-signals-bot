#!/usr/bin/env python3
"""
Simple database reset - run this in Railway Console
"""
import asyncio
import os

async def reset_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    print(f"📊 Database URL: {database_url[:50]}...")
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        engine = create_async_engine(database_url)
        
        async with engine.begin() as conn:
            # Drop tables
            print("🗑️ Dropping tables...")
            await conn.execute(text("DROP TABLE IF EXISTS signals CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS pairs CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS settings CASCADE"))
            print("✅ Tables dropped")
            
            # Create signals table
            print("🔨 Creating signals table...")
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
            print("✅ Signals table created")
            
            # Create other tables
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
            
            await conn.execute(text("""
                CREATE TABLE pairs (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) UNIQUE NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            await conn.execute(text("""
                CREATE TABLE settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(50) UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Insert default pairs
            pairs = ["ETH/USDT", "BNB/USDT", "XRP/USDT", "SOL/USDT", "ADA/USDT"]
            for pair in pairs:
                await conn.execute(text("""
                    INSERT INTO pairs (symbol, enabled) 
                    VALUES (:symbol, TRUE) 
                    ON CONFLICT (symbol) DO NOTHING
                """), {"symbol": pair})
            
            print("✅ All tables created and data inserted")
            
        await engine.dispose()
        print("🎉 Database reset completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reset_db())
