# 🟢 Crypto Long Signals Bot

A sophisticated Telegram bot that analyzes cryptocurrency markets to detect high-probability **LONG** trading signals. Built with Python 3.12, designed for spot trading only (no futures or leverage).

## 🎯 Features

- **Spot Long Only**: Detects only long entry points, no shorts or futures
- **Conservative Strategy**: Multiple confirmation signals required
- **Risk Management**: Built-in position sizing and risk controls
- **Real-time Scanning**: Monitors 5 major USDC pairs every 3 minutes
- **Telegram Integration**: Clean English UI with interactive buttons
- **Railway Deployment**: One-click deployment with PostgreSQL

## 📈 Trading Strategy

### Trend Filter (Must Pass)
- Price > EMA200 (1h) AND > EMA50 (15m)
- RSI(14, 1h) between 45-65 (neutral to slightly bullish)

### Entry Triggers (Need ≥2)
- Breakout & retest of local resistance
- Bollinger Bands squeeze expansion + volume spike
- EMA9/EMA21 bullish crossover above EMA50
- Bullish engulfing or long-wick candle + volume

### Risk Management
- Stop Loss: Below swing low OR 1.5×ATR (whichever is larger)
- Take Profit: TP1 = Entry + 1R, TP2 = Entry + 2R
- Risk per trade: 0.7% (adjustable)
- Max concurrent signals: 3
- Max holding time: 24 hours

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <your-repo-url>
cd crypto-long-signals-bot
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env
```

### 2. Create Telegram Bot
1. Open Telegram → search @BotFather
2. Send `/newbot` → choose name → copy BOT_TOKEN
3. Paste token into `.env` file

### 3. Setup PostgreSQL on Railway
1. Go to [Railway.app](https://railway.app)
2. New Project → Add Plugin → PostgreSQL
3. Copy Database URL (postgresql+asyncpg://...)
4. Paste into `.env` file

### 4. Configure Environment
Edit `.env` file:
```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
EXCHANGE=binance
SCAN_INTERVAL_SEC=180
DEFAULT_RISK_PCT=0.7
DEFAULT_PAIRS=ETH/USDC,BNB/USDC,XRP/USDC,SOL/USDC,ADA/USDC
```

### 5. Deploy on Railway
1. Push code to GitHub
2. Railway → New Project → Deploy from GitHub
3. Add environment variables from `.env`
4. Set start command: `python -m app.main`
5. Deploy!

## 📱 Telegram Commands

- `/start` - Welcome message and setup
- `/pairs` - Manage monitored trading pairs
- `/risk` - Set risk percentage per trade
- `/signals_on` - Enable signal notifications
- `/signals_off` - Pause signal notifications
- `/status` - Show current bot status
- `/strategy` - Explain trading strategy
- `/help` - FAQ and disclaimer

## 📊 Signal Example

```
🟢 LONG Signal (Strong) — ETH/USDC (15m)

Entry: 2,650
SL: 2,615 (-1.3%)
TP1: 2,676 (+1.0%)
TP2: 2,702 (+2.0%)

Risk per trade: 0.7% → Position: 0.8 ETH

Why: Strong setup: EMA crossover + BB expansion + volume spike

Expires: 6h | Max hold: 24h
Note: Move SL to BE at TP1 (50% partial)

⚠️ Spot only. Not financial advice.

[✅ Mark Active] [😴 Snooze 1h] [🔇 Mute Pair] [❓ Explain]
```

## 🏗️ Project Structure

```
crypto-long-signals-bot/
├── app/
│   ├── bot/
│   │   ├── handlers/          # Telegram message handlers
│   │   ├── keyboards/         # Inline keyboards
│   │   └── texts_en.py        # English text messages
│   ├── config/
│   │   └── settings.py        # Configuration management
│   ├── core/
│   │   ├── data/              # Market data fetching
│   │   ├── indicators/        # Technical analysis
│   │   ├── signals/           # Signal detection logic
│   │   └── risk/              # Risk management
│   ├── db/
│   │   ├── models.py          # Database models
│   │   └── repo.py            # Database operations
│   ├── services/
│   │   ├── scanner.py         # Market scanning service
│   │   └── notifier.py        # Notification service
│   └── main.py                # Application entry point
├── main.py                    # Main entry point
├── requirements.txt           # Python dependencies
├── Procfile                   # Railway deployment
├── Makefile                   # Development commands
└── README.md                  # This file
```

## 🔧 Development

### Local Development
```bash
# Install dependencies
make install

# Run locally
make run

# Deploy to Railway
make deploy
```

### Testing
```bash
# Run with mock data
python -m app.main --mock
```

## 📋 Requirements

- Python 3.12+
- PostgreSQL (Railway provides this)
- Telegram Bot Token
- Binance API (optional, for higher rate limits)

## ⚠️ Disclaimers

- **Not Financial Advice**: This bot is for educational purposes only
- **Trade at Your Own Risk**: Only trade with money you can afford to lose
- **Spot Trading Only**: No leverage, futures, or margin trading
- **Do Your Own Research**: Always verify signals before trading
- **Past Performance**: Doesn't guarantee future results

## 🛠️ Technical Details

### Dependencies
- `aiogram` - Telegram Bot API
- `sqlalchemy` - Database ORM
- `asyncpg` - PostgreSQL async driver
- `ccxt` - Cryptocurrency exchange API
- `apscheduler` - Background task scheduling
- `pydantic` - Data validation
- `ta` - Technical analysis indicators

### Database Schema
- `users` - User preferences and settings
- `pairs` - Monitored trading pairs
- `signals` - Generated trading signals
- `settings` - Application configuration

### Signal Grading
- **A (Strong)**: High probability, clear trend + volume confirmation
- **B (Good)**: Decent setup, average confirmation signals
- **C (High-risk)**: Weak confirmation or wide stop loss

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter any issues:

1. Check the logs in Railway dashboard
2. Verify your environment variables
3. Ensure your Telegram bot token is valid
4. Check that PostgreSQL is accessible

## 🔄 Updates

The bot automatically:
- Scans markets every 3 minutes
- Expires signals after 8 hours
- Cleans up old signals after 24 hours
- Updates risk calculations in real-time

---

**Remember**: This is a tool to help identify potential trading opportunities. Always do your own research and never risk more than you can afford to lose! 🚀
