"""
English text messages for the Telegram bot
"""

# Welcome and help messages
WELCOME_MESSAGE = """
🟢 <b>Welcome to Crypto Long Signals Bot!</b>

I help you find high-probability <b>LONG</b> signals in crypto markets.

<b>What I do:</b>
• Scan 5 major USDC pairs every 3 minutes
• Find strong long entry points only (no shorts/futures)
• Send signals with Entry, SL, TP1, TP2, and risk level
• Maximum 24h holding time per signal

<b>Quick Start:</b>
1. Use /signals_on to enable scanning
2. I'll send you signals when I find good setups
3. Use /pairs to manage which pairs to monitor
4. Use /risk to adjust your risk per trade

<b>Commands:</b>
/start - Welcome message
/pairs - Manage trading pairs
/risk - Set risk per trade
/signals_on - Enable signals
/signals_off - Pause signals
/status - Show current status
/strategy - Explain my strategy
/help - FAQ and disclaimer

⚠️ <b>Disclaimer:</b> This is for educational purposes only. Not financial advice. Trade at your own risk.
"""

HELP_MESSAGE = """
<b>📚 FAQ & Help</b>

<b>How does the bot work?</b>
I analyze market data using technical indicators to find high-probability long entry points. I only send signals when multiple conditions align.

<b>What pairs do you monitor?</b>
Default: ETH/USDC, BNB/USDC, XRP/USDC, SOL/USDC, ADA/USDC
You can add/remove pairs using /pairs

<b>How often do you scan?</b>
Every 3 minutes (180 seconds)

<b>What's the maximum holding time?</b>
24 hours maximum. Signals expire after 8 hours if not triggered.

<b>How do I set my risk?</b>
Use /risk command. Default is 0.7% per trade.

<b>What do the signal grades mean?</b>
• A (Strong): High probability, clear trend + volume
• B (Good): Decent setup, average confirmation
• C (High-risk): Weak confirmation, use smaller position

        <b>New diagnostic commands</b>
        • /health — quick health check (DB + exchange reachability)
        • /mock_signal — send a test signal to yourself (delivery check)
        • /check — pick a pair and get a current status: trend filter, entry triggers and explanation why it's not a long now (if conditions are not met)
        • /debug_scanner — detailed scanner diagnostics (pairs, signals, detection logic)
        • /force_scan — force immediate market scan to test signal detection
        • /easy_mode — toggle between conservative and easy signal detection modes
        • /mode_status — check current detection mode and conditions
        • /my_signals — show your active signals (marked with "Mark Active" button)

<b>⚠️ Important Disclaimers:</b>
• This is NOT financial advice
• Past performance doesn't guarantee future results
• Only trade with money you can afford to lose
• Always do your own research
• Spot trading only - no leverage or futures
"""

STRATEGY_MESSAGE = """
<b>📈 My Trading Strategy</b>

<b>Trend Filter (Must Pass):</b>
• Price > EMA200 (1h) AND > EMA50 (15m)
• RSI(14, 1h) between 45-65 (neutral to slightly bullish)

<b>Entry Triggers (Need ≥2):</b>
• Breakout & retest of local resistance
• Bollinger Bands squeeze expansion + volume spike
• EMA9/EMA21 bullish crossover above EMA50
• Bullish engulfing or long-wick candle + volume

<b>Risk Management:</b>
• Stop Loss: Below swing low OR 1.5×ATR (whichever is larger)
• Take Profit: TP1 = Entry + 1R, TP2 = Entry + 2R
• Risk per trade: 0.7% (adjustable)
• Max concurrent signals: 3
• Max holding time: 24 hours

<b>Signal Grading:</b>
• A: Clean uptrend + volume confirmation
• B: Decent trend + average volume
• C: Weak confirmation or wide SL

<b>Timeframes:</b>
• Trend filter: 1h
• Entry triggers: 15m
• Confirmation: 5m

This conservative approach focuses on high-probability setups with clear risk management.
"""

# Status messages
STATUS_HEADER = "📊 <b>Bot Status</b>\n"
SIGNALS_ENABLED = "🟢 Signals: <b>ENABLED</b>"
SIGNALS_DISABLED = "🔴 Signals: <b>DISABLED</b>"
SCANNING_PAIRS = "📈 Scanning: <b>{pairs}</b>"
ACTIVE_SIGNALS = "🎯 Active Signals: <b>{count}</b>"
RISK_SETTING = "💰 Risk per trade: <b>{risk}%</b>"
LAST_SCAN = "⏰ Last scan: <b>{time}</b>"

# Pair management
PAIRS_HEADER = "📈 <b>Trading Pairs</b>\n"
PAIR_ENABLED = "🟢 {symbol}"
PAIR_DISABLED = "🔴 {symbol}"
ADD_PAIR_PROMPT = "Send me the symbol to add (e.g., BTC/USDC):"
PAIR_ADDED = "✅ Added {symbol} to monitoring list"
PAIR_REMOVED = "❌ Removed {symbol} from monitoring list"
PAIR_NOT_FOUND = "❌ Pair {symbol} not found or invalid"
PAIR_ALREADY_EXISTS = "⚠️ Pair {symbol} already exists"

# Risk management
RISK_HEADER = "💰 <b>Risk Management</b>\n"
CURRENT_RISK = "Current risk per trade: <b>{risk}%</b>"
RISK_PROMPT = "Enter new risk percentage (0.1-5.0):"
RISK_UPDATED = "✅ Risk updated to <b>{risk}%</b>"
RISK_INVALID = "❌ Invalid risk. Please enter 0.1-5.0"

# Signal messages
SIGNAL_HEADER = "🟢 <b>LONG Signal ({grade})</b> — {symbol} ({timeframe})"
SIGNAL_ENTRY = "Entry: <b>{entry}</b>"
SIGNAL_SL = "SL: <b>{sl}</b> ({sl_pct}%)"
SIGNAL_TP1 = "TP1: <b>{tp1}</b> ({tp1_pct}%)"
SIGNAL_TP2 = "TP2: <b>{tp2}</b> ({tp2_pct}%)"
SIGNAL_RISK = "Risk per trade: <b>{risk}%</b> → Position: <b>{position}</b>"
SIGNAL_REASON = "Why: {reason}"
SIGNAL_EXPIRY = "Expires: <b>{expiry}h</b> | Max hold: <b>24h</b>"
SIGNAL_NOTE = "Note: Move SL to BE at TP1 (50% partial)"
SIGNAL_DISCLAIMER = "⚠️ Spot only. Not financial advice."

# Grade descriptions
GRADE_A = "Strong"
GRADE_B = "Good" 
GRADE_C = "High-risk"

# Button texts
BTN_MARK_ACTIVE = "✅ Mark Active"
BTN_SNOOZE_1H = "😴 Snooze 1h"
BTN_MUTE_PAIR = "🔇 Mute Pair"
BTN_EXPLAIN = "❓ Explain"
BTN_ENABLE_SIGNALS = "🟢 Enable Signals"
BTN_DISABLE_SIGNALS = "🔴 Disable Signals"
BTN_MANAGE_PAIRS = "📈 Manage Pairs"
BTN_SET_RISK = "💰 Set Risk"
BTN_SHOW_STATUS = "📊 Status"
BTN_STRATEGY = "📈 Strategy"
BTN_HELP = "❓ Help"
BTN_BACK = "⬅️ Back"
BTN_CANCEL = "❌ Cancel"
BTN_CONFIRM = "✅ Confirm"

# Error messages
ERROR_GENERIC = "❌ An error occurred. Please try again."
ERROR_INVALID_COMMAND = "❌ Invalid command. Use /help for available commands."
ERROR_DATABASE = "❌ Database error. Please try again later."
ERROR_MARKET_DATA = "❌ Unable to fetch market data. Please try again later."
ERROR_SIGNAL_GENERATION = "❌ Error generating signal. Please try again later."

# Success messages
SUCCESS_SIGNAL_ENABLED = "✅ Signals enabled! I'll start scanning for opportunities."
SUCCESS_SIGNAL_DISABLED = "✅ Signals disabled. I'll stop sending new signals."
SUCCESS_SETTINGS_UPDATED = "✅ Settings updated successfully."
SUCCESS_PAIR_TOGGLED = "✅ Pair {symbol} toggled successfully."