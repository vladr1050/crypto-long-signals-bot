#!/usr/bin/env python3
"""
Simple database setup script
"""
import asyncio
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

async def setup_database():
    """Setup database tables"""
    try:
        print("🚀 Setting up database...")
        
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
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created successfully!")
        
        # Test connection
        from app.db.repo import DatabaseRepository
        db_repo = DatabaseRepository(database_url)
        await db_repo.initialize()
        print("✅ Database connection test passed!")
        
        await db_repo.close()
        await engine.dispose()
        
        print("🎉 Database setup completed!")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(setup_database())
