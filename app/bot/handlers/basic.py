from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from ...db.repo import Repo
from ..texts_en import WELCOME, STRATEGY

router = Router()


@router.message(Command("start"))
async def start_cmd(m: Message, repo: Repo):
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
