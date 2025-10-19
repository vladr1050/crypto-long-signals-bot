from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

from ..indicators.ta import ema, rsi, atr, bbands

@dataclass
class CandleData:
    ts: list[int]
    o: list[float]; h: list[float]; l: list[float]; c: list[float]; v: list[float]

@dataclass
class SignalIdea:
    entry: float
    sl: float
    tp1: float
    tp2: float
    grade: str     # A/B/C
    risk_text: str # Strong/Good/High
    reason: str

def _breakout_retest(c: CandleData, lookback: int = 30) -> bool:
    # price made a new high and then retested the broken level
    highs = c.h[-lookback:]
    recent_high = max(highs[:-3])
    broke = c.c[-3] > recent_high
    retest = min(c.l[-2], c.l[-1]) <= recent_high * 1.002  # small throwback
    return bool(broke and retest)

def _ema_cross_bullish(c: CandleData) -> bool:
    e9  = ema(c.c, 9)
    e21 = ema(c.c, 21)
    e50 = ema(c.c, 50)
    return e9[-1] > e21[-1] > e50[-1] and e9[-2] <= e21[-2]

def _bb_squeeze_expand(c: CandleData) -> bool:
    low, mid, up = bbands(c.c, 20, 2.0)
    # expansion: last band width greater than avg of previous 10
    widths = [(u - l) if all(map(lambda x: x == x, (u, l))) else 0.0 for u, l in zip(up, low)]
    if len(widths) < 22:
        return False
    last = widths[-1]
    base = sum(w for w in widths[-12:-2] if w > 0) / max(1, len([w for w in widths[-12:-2] if w > 0]))
    return last > base * 1.25

def _bullish_candle_confirm(c: CandleData) -> bool:
    # bullish engulfing or long lower wick + higher volume
    body_prev = c.c[-2] - c.o[-2]
    body_now = c.c[-1] - c.o[-1]
    engulf = body_now > 0 and abs(body_now) > abs(body_prev) and c.o[-1] <= c.c[-2] and c.c[-1] >= c.o[-2]
    lower_wick = (c.o[-1] - c.l[-1]) > (c.h[-1] - c.c[-1]) * 1.2 and body_now > 0
    vol_ok = c.v[-1] > (sum(c.v[-10:]) / 10) * 1.1
    return (engulf or lower_wick) and vol_ok

def conservative_long_signal(c15: CandleData, c5: CandleData, c1h: CandleData) -> SignalIdea | None:
    """
    Implements:
    - Trend filter: price > EMA200(1h) and > EMA50(15m), RSI(14,1h) in [45,65]
    - Triggers: need ≥2 of {breakout&retest, BB expand + vol, EMA9/21 cross > EMA50, bullish candle + vol}
    - SL = max(local swing-low, 1.5*ATR(14,15m) below entry)
    - TP1=1R, TP2=2R
    """
    ema200_1h = ema(c1h.c, 200)[-1]
    rsi1h = rsi(c1h.c, 14)[-1]
    ema50_15 = ema(c15.c, 50)[-1]

    price = c15.c[-1]
    if not (price > ema200_1h and price > ema50_15 and 45 <= rsi1h <= 65):
        return None

    triggers = 0
    reasons = []
    if _breakout_retest(c15):
        triggers += 1; reasons.append("breakout & retest")
    if _bb_squeeze_expand(c15):
        triggers += 1; reasons.append("BB squeeze expansion + volume")
    if _ema_cross_bullish(c15):
        triggers += 1; reasons.append("EMA9/21 bullish cross > EMA50")
    if _bullish_candle_confirm(c15):
        triggers += 1; reasons.append("bullish candle confirmation + volume")

    if triggers < 2:
        return None

    # SL via swing low & ATR
    swing_low = min(c15.l[-6:])
    a = atr(c15.h, c15.l, c15.c, 14)[-1]
    sl = min(swing_low, price - 1.5 * a)
    # guard: avoid negative or too tight
    if sl <= 0 or sl >= price:
        return None

    r = price - sl
    tp1 = price + r
    tp2 = price + 2 * r

    # grade
    if triggers >= 3 and rsi1h >= 50 and price > ema200_1h:
        grade, risk_text = "A", "Strong"
    elif triggers == 2:
        grade, risk_text = "B", "Good"
    else:
        grade, risk_text = "C", "High"

    return SignalIdea(entry=price, sl=sl, tp1=tp1, tp2=tp2, grade=grade, risk_text=risk_text,
                      reason=f"1h trend up (EMA200), RSI ~{rsi1h:.1f}; Triggers: {', '.join(reasons)}")
