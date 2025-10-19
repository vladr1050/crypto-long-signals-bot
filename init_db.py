#!/usr/bin/env python3
"""
Database initialization script for Railway deployment
"""
import os
import sys
import asyncio
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Set environment variables from Railway
if not os.getenv("BOT_TOKEN"):
    print("❌ BOT_TOKEN not found in environment variables")
    sys.exit(1)

if not os.getenv("DATABASE_URL"):
    print("❌ DATABASE_URL not found in environment variables")
    sys.exit(1)

async def init_database():
    """Initialize database tables"""
    try:
        print("🚀 Initializing database...")
        
        from app.db.repo import DatabaseRepository
        from app.config.settings import get_settings
        
        settings = get_settings()
        db_repo = DatabaseRepository(settings.database_url)
        
        # Initialize database (creates tables)
        await db_repo.initialize()
        print("✅ Database tables created successfully")
        
        # Close connection
        await db_repo.close()
        print("✅ Database initialization completed")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_database())
