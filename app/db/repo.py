from typing import Iterable, Sequence
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, update
from .models import Base, User, Pair, Signal, AppState


class Repo:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.Session = async_sessionmaker(bind=engine, expire_on_commit=False)

    @classmethod
    def make_engine(cls, url: str) -> AsyncEngine:
        return create_async_engine(url, pool_pre_ping=True)

    async def init_db(self, default_pairs: Sequence[str], default_risk: float) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.Session() as s:
            # seed pairs
            existing = {p.symbol for p in (await s.scalars(select(Pair))).all()}
            for sym in default_pairs:
                if sym not in existing:
                    s.add(Pair(symbol=sym, enabled=True))
            # seed app state
            if not (await s.scalars(select(AppState))).first():
                s.add(AppState(signals_enabled=False, max_concurrent=3))
            await s.commit()

    # pairs
    async def list_pairs(self) -> list[Pair]:
        async with self.Session() as s:
            rows = await s.scalars(select(Pair).order_by(Pair.symbol))
            return list(rows.all())

    async def set_pair_enabled(self, symbol: str, enabled: bool) -> None:
        async with self.Session() as s:
            await s.execute(update(Pair).where(Pair.symbol == symbol).values(enabled=enabled))
            await s.commit()

    # state
    async def get_state(self) -> AppState:
        async with self.Session() as s:
            st = (await s.scalars(select(AppState))).first()
            return st

    async def set_signals_enabled(self, enabled: bool) -> None:
        async with self.Session() as s:
            st = (await s.scalars(select(AppState))).first()
            if st:
                st.signals_enabled = enabled
                await s.commit()

    # signals
    async def add_signal(self, sig: Signal) -> int:
        async with self.Session() as s:
            s.add(sig)
            await s.commit()
            await s.refresh(sig)
            return sig.id

    async def recent_active_count(self) -> int:
        async with self.Session() as s:
            q = select(Signal).where(Signal.status.in_(("new", "sent")))
            return len((await s.scalars(q)).all())

    async def mark_sent(self, signal_id: int) -> None:
        async with self.Session() as s:
            row = await s.get(Signal, signal_id)
            if row:
                row.status = "sent"
                await s.commit()
