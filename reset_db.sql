-- Force reset database tables
-- Run this in Railway PostgreSQL Query tab

-- Drop all tables in correct order
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

-- Verify tables were created
SELECT 'Tables created successfully!' as status;
