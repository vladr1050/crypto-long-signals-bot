from __future__ import annotations
from typing import Sequence, Tuple
import math

def ema(values: Sequence[float], period: int) -> list[float]:
    k = 2 / (period + 1)
    out: list[float] = []
    ema_prev = sum(values[:period]) / period
    out.extend([math.nan]*(period-1))
    out.append(ema_prev)
    for v in values[period:]:
        ema_prev = v * k + ema_prev * (1 - k)
        out.append(ema_prev)
    return out

def rsi(closes: Sequence[float], period: int = 14) -> list[float]:
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    # initial avg
    avg_gain = sum(gains[1:period+1]) / period
    avg_loss = sum(losses[1:period+1]) / period
    rs = avg_gain / (avg_loss if avg_loss != 0 else 1e-9)
    out = [math.nan]*period + [100 - (100 / (1+rs))]
    for i in range(period+1, len(closes)):
        avg_gain = (avg_gain*(period-1)+gains[i]) / period
        avg_loss = (avg_loss*(period-1)+losses[i]) / period
        rs = avg_gain / (avg_loss if avg_loss != 0 else 1e-9)
        out.append(100 - (100 / (1+rs)))
    return out

def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> list[float]:
    trs = [abs(highs[0]-lows[0])]
    for i in range(1, len(closes)):
        tr = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        trs.append(tr)
    # Wilder's smoothing
    atrs = [math.nan]*period
    first = sum(trs[1:period+1]) / period
    atrs.append(first)
    for i in range(period+1, len(trs)):
        prev = atrs[-1]
        atrs.append((prev*(period-1)+trs[i]) / period)
    return atrs

def bbands(closes: Sequence[float], period: int = 20, mult: float = 2.0) -> tuple[list[float], list[float], list[float]]:
    mavg: list[float] = []
    stds: list[float] = []
    for i in range(len(closes)):
        if i+1 < period:
            mavg.append(float("nan"))
            stds.append(float("nan"))
            continue
        window = closes[i+1-period:i+1]
        mean = sum(window)/period
        var = sum((x-mean)**2 for x in window)/period
        mavg.append(mean)
        stds.append(var**0.5)
    upper = [m + mult*s if not (math.isnan(m) or math.isnan(s)) else float("nan") for m,s in zip(mavg, stds)]
    lower = [m - mult*s if not (math.isnan(m) or math.isnan(s)) else float("nan") for m,s in zip(mavg, stds)]
    return lower, mavg, upper
