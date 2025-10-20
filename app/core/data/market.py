"""
Market data service for fetching OHLCV data from Binance
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from functools import partial

import ccxt
import requests
import pandas as pd

from app.config.settings import settings

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching market data from exchanges"""

    def __init__(self):
        self.exchange = self._init_exchange()
        self._markets: Optional[Dict[str, Any]] = None
        # fallback if not present in Settings
        self._min_volume_24h: float = float(getattr(settings, "min_volume_24h", 1_000_000.0))

    def _init_exchange(self) -> ccxt.Exchange:
        """Initialize exchange connection (spot-only)"""
        # ccxt exchange names — строчными буквами, settings.exchange='binance'
        exchange_class = getattr(ccxt, settings.exchange)
        # Tune HTTP session pool sizes to avoid urllib3 pool warnings
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=getattr(settings, "http_pool_connections", 20),
            pool_maxsize=getattr(settings, "http_pool_maxsize", 50),
            max_retries=3,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        config: Dict[str, Any] = {
            "sandbox": False,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},  # spot only
            "session": session,
        }
        # API creds if provided (не обязательны для публичных OHLCV)
        if settings.binance_api_key and settings.binance_api_secret:
            config.update(
                {"apiKey": settings.binance_api_key, "secret": settings.binance_api_secret}
            )
        ex = exchange_class(config)
        return ex

    async def _ensure_markets(self) -> Dict[str, Any]:
        """Lazy-load and cache markets."""
        if self._markets is None:
            loop = asyncio.get_running_loop()
            self._markets = await loop.run_in_executor(None, self.exchange.load_markets)
        return self._markets

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data for a symbol

        Args:
            symbol: Trading pair symbol (e.g., 'ETH/USDC')
            timeframe: Timeframe (e.g., '1h', '15m', '5m')
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            await self._ensure_markets()
            # Convert timeframe to ccxt format (по сути идентично, но оставим мап)
            tf_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "4h": "4h",
                "1d": "1d",
            }
            ccxt_timeframe = tf_map.get(timeframe, timeframe)

            loop = asyncio.get_running_loop()
            fetch = partial(self.exchange.fetch_ohlcv, symbol, ccxt_timeframe, None, limit)
            ohlcv = await loop.run_in_executor(None, fetch)

            if not ohlcv:
                logger.warning("No data received for %s %s", symbol, timeframe)
                return None

            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            # Если хочешь наивную UTC:
            # df["timestamp"] = df["timestamp"].dt.tz_convert(None)
            df.set_index("timestamp", inplace=True)

            # Ensure numeric types
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            logger.debug("Fetched %d candles for %s %s", len(df), symbol, timeframe)
            return df

        except Exception as e:
            logger.exception("Error fetching OHLCV for %s %s: %s", symbol, timeframe, e)
            return None

    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current ticker data for a symbol
        """
        try:
            await self._ensure_markets()
            loop = asyncio.get_running_loop()
            fetch = partial(self.exchange.fetch_ticker, symbol)
            ticker = await loop.run_in_executor(None, fetch)
            return ticker
        except Exception as e:
            logger.exception("Error fetching ticker for %s: %s", symbol, e)
            return None

    async def get_24h_volume(self, symbol: str) -> Optional[float]:
        """
        24h volume in quote currency (if provided by exchange)
        """
        try:
            ticker = await self.get_ticker(symbol)
            if ticker is None:
                return None
            # ccxt обычно даёт quoteVolume
            vol = ticker.get("quoteVolume")
            if vol is None:
                return None
            return float(vol)
        except Exception as e:
            logger.exception("Error fetching 24h volume for %s: %s", symbol, e)
            return None

    async def is_symbol_valid(self, symbol: str) -> bool:
        """
        Check if symbol exists and has sufficient 24h volume
        """
        try:
            markets = await self._ensure_markets()
            if symbol not in markets:
                logger.warning("Symbol %s not in markets list", symbol)
                return False

            volume_24h = await self.get_24h_volume(symbol)
            if volume_24h is None or volume_24h < self._min_volume_24h:
                logger.warning(
                    "Symbol %s has insufficient volume: %s (< %s)",
                    symbol,
                    volume_24h,
                    self._min_volume_24h,
                )
                return False

            return True
        except Exception as e:
            logger.exception("Error validating symbol %s: %s", symbol, e)
            return False

    async def get_multiple_ohlcv(
        self,
        symbols: List[str],
        timeframes: List[str],
        limit: int = 500,
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Fetch OHLCV data for multiple symbols and timeframes concurrently

        Returns:
            Nested dict: {symbol: {timeframe: DataFrame}}
        """
        await self._ensure_markets()
        results: Dict[str, Dict[str, pd.DataFrame]] = {sym: {} for sym in symbols}

        semaphore = asyncio.Semaphore(getattr(settings, "max_concurrent_requests", 5))

        async def fetch_one(sym: str, tf: str):
            async with semaphore:
                df = await self.get_ohlcv(sym, tf, limit=limit)
                if df is not None:
                    results[sym][tf] = df

        tasks = [asyncio.create_task(fetch_one(sym, tf)) for sym in symbols for tf in timeframes]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return results
