# 🔧 Manual Database Reset

## Method 1: Railway Console (Recommended)

1. Go to [Railway Dashboard](https://railway.app)
2. Open your project
3. Click on your service
4. Go to "Console" tab
5. Run this command:

```bash
python force_reset_db.py
```

You should see:
```
🚀 Force resetting database...
📊 Connecting to: postgresql+asyncpg://...
🗑️ Dropping all tables...
✅ Dropped table: signals
✅ Dropped table: pairs
✅ Dropped table: users
✅ Dropped table: settings
✅ All tables dropped
🔨 Creating tables...
✅ Created users table
✅ Created pairs table
✅ Created signals table
✅ Created settings table
✅ Created indexes
✅ Inserted 5 default pairs
🎉 Database force reset completed!
🧪 Testing database...
✅ Test signal created with ID: 1
🎉 Database is ready!
```

## Method 2: Railway CLI

If you have Railway CLI installed:

```bash
# Login to Railway
railway login

# Connect to your project
railway link

# Run the reset script
railway run python force_reset_db.py
```

## Method 3: Direct SQL (Last Resort)

If nothing works, you can run SQL directly:

1. Go to Railway Dashboard
2. Open PostgreSQL service
3. Go to "Query" tab
4. Run this SQL:

```sql
-- Drop all tables
DROP TABLE IF EXISTS signals CASCADE;
DROP TABLE IF EXISTS pairs CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS settings CASCADE;

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    tg_id BIGINT UNIQUE NOT NULL,
    lang VARCHAR(5) DEFAULT 'en',
    risk_pct FLOAT DEFAULT 0.7,
    signals_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create pairs table
CREATE TABLE pairs (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create signals table
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
);

-- Create settings table
CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_users_tg_id ON users(tg_id);
CREATE INDEX idx_pairs_symbol ON pairs(symbol);
CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_status ON signals(status);

-- Insert default pairs
INSERT INTO pairs (symbol, enabled) VALUES 
('ETH/USDC', TRUE),
('BNB/USDC', TRUE),
('XRP/USDC', TRUE),
('SOL/USDC', TRUE),
('ADA/USDC', TRUE)
ON CONFLICT (symbol) DO NOTHING;
```

## After Reset

Once the database is reset, restart your bot and the error should be gone!
