from __future__ import annotations
import ccxt
from typing import Literal, Dict, Any, List, Tuple
from datetime import datetime, timezone


Timeframe = Literal["1h", "15m", "5m"]

def make_exchange(name: str, key: str | None = None, secret: str | None = None) -> ccxt.Exchange:
    klass = getattr(ccxt, name)
    kwargs: Dict[str, Any] = {"enableRateLimit": True, "options": {"defaultType": "spot"}}
    if key and secret:
        kwargs["apiKey"] = key
        kwargs["secret"] = secret
    ex = klass(kwargs)
    return ex

def fetch_ohlcv(exchange: ccxt.Exchange, symbol: str, timeframe: Timeframe, limit: int = 300) -> List[List[float]]:
    """Returns list of [ts, open, high, low, close, volume] in ms UTC."""
    return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)
