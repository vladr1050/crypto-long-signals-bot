-- Clean up malformed symbols in database
-- Run this in Railway PostgreSQL Query tab

-- Show current pairs
SELECT 'Current pairs:' as info;
SELECT id, symbol, enabled FROM pairs ORDER BY id;

-- Clean up malformed symbols (remove brackets and quotes)
UPDATE pairs 
SET symbol = TRIM(BOTH '[]"' FROM symbol)
WHERE symbol LIKE '%[%' OR symbol LIKE '%]%' OR symbol LIKE '%"%';

-- Show cleaned pairs
SELECT 'Cleaned pairs:' as info;
SELECT id, symbol, enabled FROM pairs ORDER BY id;

-- Ensure we have the correct USDC pairs
DELETE FROM pairs WHERE symbol NOT IN ('ETH/USDC', 'BNB/USDC', 'XRP/USDC', 'SOL/USDC', 'ADA/USDC');

INSERT INTO pairs (symbol, enabled) VALUES 
('ETH/USDC', TRUE),
('BNB/USDC', TRUE),
('XRP/USDC', TRUE),
('SOL/USDC', TRUE),
('ADA/USDC', TRUE)
ON CONFLICT (symbol) DO NOTHING;

-- Final result
SELECT 'Final pairs:' as info;
SELECT id, symbol, enabled FROM pairs ORDER BY id;
