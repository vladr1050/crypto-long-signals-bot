#!/usr/bin/env python3
"""
Debug and fix pairs in database
"""
import asyncio
import os

async def debug_pairs():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    print("🔍 Debugging pairs in database...")
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        engine = create_async_engine(database_url)
        
        async with engine.begin() as conn:
            # Check current pairs
            print("📊 Current pairs in database:")
            result = await conn.execute(text("SELECT id, symbol, enabled FROM pairs ORDER BY id"))
            pairs = result.fetchall()
            
            for pair in pairs:
                print(f"  ID: {pair.id}, Symbol: '{pair.symbol}', Enabled: {pair.enabled}")
                print(f"    Symbol type: {type(pair.symbol)}")
                print(f"    Symbol repr: {repr(pair.symbol)}")
                print(f"    Symbol length: {len(pair.symbol)}")
                print()
            
            # Check for malformed symbols
            print("🔍 Checking for malformed symbols...")
            malformed_result = await conn.execute(text("""
                SELECT id, symbol FROM pairs 
                WHERE symbol LIKE '%[%' OR symbol LIKE '%]%' OR symbol LIKE '%"%'
            """))
            malformed = malformed_result.fetchall()
            
            if malformed:
                print(f"❌ Found {len(malformed)} malformed symbols:")
                for pair in malformed:
                    print(f"  ID: {pair.id}, Symbol: {repr(pair.symbol)}")
                
                # Fix malformed symbols
                print("\n🔧 Fixing malformed symbols...")
                for pair in malformed:
                    # Remove brackets and quotes
                    clean_symbol = pair.symbol.strip('[]"\'')
                    print(f"  Fixing '{pair.symbol}' -> '{clean_symbol}'")
                    
                    await conn.execute(text("""
                        UPDATE pairs SET symbol = :clean_symbol WHERE id = :id
                    """), {"clean_symbol": clean_symbol, "id": pair.id})
                
                print("✅ Malformed symbols fixed")
            else:
                print("✅ No malformed symbols found")
            
            # Show final pairs
            print("\n📊 Final pairs:")
            result = await conn.execute(text("SELECT id, symbol, enabled FROM pairs ORDER BY id"))
            pairs = result.fetchall()
            
            for pair in pairs:
                print(f"  ID: {pair.id}, Symbol: '{pair.symbol}', Enabled: {pair.enabled}")
            
        await engine.dispose()
        print("\n🎉 Database check completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_pairs())
