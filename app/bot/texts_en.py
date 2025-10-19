WELCOME = (
    "👋 Welcome to <b>Crypto Long Signals Bot</b>\n"
    "• Spot only, no futures\n"
    "• Max holding time 24h\n"
    "Use /pairs /risk /signals_on /signals_off /status /strategy /help"
)

STRATEGY = (
    "📘 <b>Strategy (Conservative, Long only)</b>\n"
    "• Trend filter: Price > EMA200 (1h) and > EMA50 (15m), RSI(1h) 45–65\n"
    "• Triggers: need ≥2 of breakout&retest, BB expand + volume, EMA9/21 cross > EMA50, bullish candle + volume\n"
    "• SL: below swing-low or 1.5×ATR(14,15m), whichever larger\n"
    "• TP1=1R, TP2=2R; move SL→BE at TP1\n"
    "• Expire if no trigger in 8h; max hold 24h\n"
    "⚠️ Not financial advice."
)

def render_signal(symbol: str, timeframe: str, entry: float, sl: float, tp1: float, tp2: float,
                  grade: str, risk: str, hours: int, reason: str) -> str:
    r_pct = (entry - sl) / entry * 100 if entry > 0 else 0.0
    return (
        f"🟢 <b>LONG Signal ({grade}/{risk}) — {symbol} ({timeframe})</b>\n"
        f"Entry: <b>{entry:.4f}</b>\n"
        f"SL: <b>{sl:.4f}</b>  (<i>-{r_pct:.2f}%</i>)\n"
        f"TP1 / TP2: <b>{tp1:.4f}</b> / <b>{tp2:.4f}</b>\n"
        f"Reason: {reason}\n"
        f"Expires: {hours}h | Max hold: 24h\n"
        f"Note: Move SL→BE at TP1 (50% partial)\n"
        f"⚠️ Spot only. Not financial advice."
    )
