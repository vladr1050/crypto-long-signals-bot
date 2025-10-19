# 🔄 Reset Database Guide

If you're getting `column signals.entry_price does not exist` error, the database needs to be reset.

## Method 1: Automatic Reset (Recommended)

The bot will automatically reset the database on next restart with the updated Procfile.

## Method 2: Manual Reset via Railway Console

1. Go to Railway Dashboard
2. Open your project
3. Click on your service
4. Go to "Console" tab
5. Run these commands:

```bash
# Reset database
python reset_db.py

# Start bot
python -m app.main
```

## Method 3: Manual SQL Reset

If the above doesn't work, you can manually drop and recreate tables:

1. Go to Railway Dashboard
2. Open your PostgreSQL service
3. Go to "Query" tab
4. Run this SQL:

```sql
-- Drop all tables
DROP TABLE IF EXISTS signals CASCADE;
DROP TABLE IF EXISTS pairs CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS settings CASCADE;

-- The bot will recreate them on next start
```

## Method 4: Complete Database Reset

If nothing works, you can reset the entire database:

1. Go to Railway Dashboard
2. Open your PostgreSQL service
3. Go to "Settings" tab
4. Click "Reset Database"
5. This will delete all data and create a fresh database

## Expected Result

After reset, you should see in logs:
```
✅ All tables dropped
✅ All tables created successfully!
✅ Database connection test passed!
✅ Test signal created with ID: 1
🎉 Database reset completed successfully!
```

And the error `column signals.entry_price does not exist` should disappear.
