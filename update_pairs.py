#!/usr/bin/env python3
"""
Update trading pairs from USDC to USDT
"""
import asyncio
import os

async def update_pairs():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    print("🔄 Updating trading pairs from USDC to USDT...")
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        engine = create_async_engine(database_url)
        
        async with engine.begin() as conn:
            # Delete old USDC pairs
            print("🗑️ Removing old USDC pairs...")
            await conn.execute(text("DELETE FROM pairs WHERE symbol LIKE '%/USDC'"))
            
            # Insert new USDT pairs
            print("➕ Adding new USDT pairs...")
            pairs = ["ETH/USDT", "BNB/USDT", "XRP/USDT", "SOL/USDT", "ADA/USDT"]
            for pair in pairs:
                await conn.execute(text("""
                    INSERT INTO pairs (symbol, enabled) 
                    VALUES (:symbol, TRUE) 
                    ON CONFLICT (symbol) DO NOTHING
                """), {"symbol": pair})
                print(f"✅ Added {pair}")
            
            # Show current pairs
            result = await conn.execute(text("SELECT symbol, enabled FROM pairs ORDER BY symbol"))
            pairs_list = result.fetchall()
            print(f"\n📊 Current pairs ({len(pairs_list)}):")
            for pair in pairs_list:
                status = "✅ enabled" if pair.enabled else "❌ disabled"
                print(f"  {pair.symbol} - {status}")
            
        await engine.dispose()
        print("\n🎉 Pairs updated successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(update_pairs())
