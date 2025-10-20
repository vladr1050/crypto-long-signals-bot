-- Update trading pairs from USDC to USDT
-- Run this in Railway PostgreSQL Query tab

-- Delete old USDC pairs
DELETE FROM pairs WHERE symbol LIKE '%/USDC';

-- Insert new USDT pairs
INSERT INTO pairs (symbol, enabled) VALUES 
('ETH/USDT', TRUE),
('BNB/USDT', TRUE),
('XRP/USDT', TRUE),
('SOL/USDT', TRUE),
('ADA/USDT', TRUE)
ON CONFLICT (symbol) DO NOTHING;

-- Show current pairs
SELECT symbol, enabled FROM pairs ORDER BY symbol;
