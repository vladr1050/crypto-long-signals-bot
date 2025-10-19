from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select
from datetime import timedelta
from ...db.repo import Repo
from ...db.models import User, Signal
from ..texts_en import WELCOME, STRATEGY
from ...services.notifier import Notifier
from ...core.data.market import now_utc

router = Router()

@router.message(Command("start")))
async def start_cmd(m: Message, repo: Repo):
    # upsert user
    async with repo.Session() as s:
        u = (await s.scalars(select(User).where(User.tg_id == m.from_user.id))).first()
        if not u:
            s.add(User(tg_id=m.from_user.id, lang="en"))
            await s.commit()
    await m.answer(WELCOME)

@router.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(STRATEGY)


@router.message(Command("strategy"))
async def strategy_cmd(m: Message):
    await m.answer(STRATEGY)


@router.message(Command("status"))
async def status_cmd(m: Message, repo: Repo):
    st = await repo.get_state()
    onoff = "ON ✅" if (st and st.signals_enabled) else "OFF ⏸"
    pairs = ", ".join(p.symbol for p in await repo.list_pairs() if p.enabled)
    await m.answer(f"Status: <b>{onoff}</b>\nPairs: {pairs}", parse_mode="HTML")


@router.message(Command("signals_on"))
async def signals_on(m: Message, repo: Repo):
    await repo.set_signals_enabled(True)
    await m.answer("Signals: ON ✅")


@router.message(Command("signals_off"))
async def signals_off(m: Message, repo: Repo):
    await repo.set_signals_enabled(False)
    await m.answer("Signals: OFF ⏸")


@router.message(Command("pairs"))
async def pairs_cmd(m: Message, repo: Repo):
    pairs = await repo.list_pairs()
    lines = [f"{'✅' if p.enabled else '❌'} {p.symbol}" for p in pairs]
    await m.answer("Pairs:\n" + "\n".join(lines))


@router.message(Command("risk"))
async def risk_cmd(m: Message):
    await m.answer("Default risk per trade is set by the bot owner (e.g., 0.7%).\n"
                   "Personalized per-user risk can be added later.")


@router.callback_query(F.data.startswith("sig:"))
async def sig_cb(q: CallbackQuery):
    action = q.data.split(":", 1)[1]
    msg = {"active": "Marked active ✅", "snooze": "Snoozed for 1h 😴", "mute": "Pair muted 🔇",
           "explain": "Signal explained in the message above."}.get(action, "OK")
    await q.answer(msg, show_alert=False)

@router.message(Command("mock_signal"))
async def mock_signal(m: Message, repo: Repo):
    expires_at = now_utc() + timedelta(hours=6)
    sig = Signal(
        symbol="ETH/USDC", timeframe="15m",
        entry=2650.0, sl=2615.0, tp1=2676.0, tp2=2702.0,
        grade="A", risk_level="Strong", expires_at=expires_at,
        status="new", reason="test: mock signal"
    )
    signal_id = await repo.add_signal(sig)

    from app.bot.texts_en import render_signal
    text = render_signal(
        symbol="ETH/USDC", timeframe="15m",
        entry=2650.0, sl=2615.0, tp1=2676.0, tp2=2702.0,
        grade="A", risk="Strong", hours=6, reason="test: mock signal"
    )
    await m.answer(text, parse_mode="HTML")