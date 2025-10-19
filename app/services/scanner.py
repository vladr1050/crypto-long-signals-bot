from __future__ import annotations
from datetime import timedelta
from typing import Iterable
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..config.settings import settings
from ..db.repo import Repo
from ..db.models import Signal
from ..core.data.market import make_exchange, fetch_ohlcv, now_utc
from ..core.signals.detector import CandleData, conservative_long_signal
from .notifier import Notifier


class Scanner:
    def __init__(self, repo: Repo, notifier: Notifier, chat_ids_provider):
        self.repo = repo
        self.notifier = notifier
        self.scheduler = AsyncIOScheduler()
        self.chat_ids_provider = chat_ids_provider  # callable -> list[int]
        self.exchange = make_exchange(
            settings.exchange,
            settings.binance_api_key,
            settings.binance_api_secret
        )

    def start(self):
        self.scheduler.add_job(self.scan_market, "interval", seconds=settings.scan_interval_sec)
        self.scheduler.start()

    async def scan_market(self):
        state = await self.repo.get_state()
        if not state or not state.signals_enabled:
            return

        pairs = [p.symbol for p in await self.repo.list_pairs() if p.enabled]
        if not pairs:
            return

        # simple concurrency limit by active signals
        if await self.repo.recent_active_count() >= state.max_concurrent:
            return

        for symbol in pairs:
            try:
                c1h = _load_cd(self.exchange, symbol, "1h")
                c15 = _load_cd(self.exchange, symbol, "15m")
                c5  = _load_cd(self.exchange, symbol, "5m")
            except Exception:
                continue

            idea = conservative_long_signal(c15, c5, c1h)
            if not idea:
                continue

            expires_at = now_utc() + timedelta(hours=6)
            sig = Signal(
                symbol=symbol, timeframe="15m",
                entry=idea.entry, sl=idea.sl, tp1=idea.tp1, tp2=idea.tp2,
                grade=idea.grade, risk_level=idea.risk_text, expires_at=expires_at,
                status="new", reason=idea.reason
            )
            signal_id = await self.repo.add_signal(sig)

            # broadcast
            chat_ids = await self.chat_ids_provider()
            payload = dict(
                symbol=symbol, timeframe="15m",
                entry=idea.entry, sl=idea.sl, tp1=idea.tp1, tp2=idea.tp2,
                grade=idea.grade, risk=idea.risk_text, hours=6, reason=idea.reason
            )
            await self.notifier.broadcast_signal(chat_ids, payload, signal_id)


def _load_cd(exchange, symbol: str, tf: str) -> CandleData:
    rows = fetch_ohlcv(exchange, symbol, tf, limit=300)
    ts, o, h, l, c, v = ([], [], [], [], [], [])
    for r in rows:
        ts.append(int(r[0])); o.append(float(r[1])); h.append(float(r[2])); l.append(float(r[3])); c.append(float(r[4])); v.append(float(r[5]))
    return CandleData(ts=ts, o=o, h=h, l=l, c=c, v=v)
