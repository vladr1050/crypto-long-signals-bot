"""
Basic message handlers for the Telegram bot
"""
import logging
from datetime import datetime
from typing import List

from aiogram import Router, F, Bot, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.bot.keyboards.common import (
    get_back_keyboard, get_help_keyboard, get_main_menu_keyboard,
    get_pairs_management_keyboard, get_risk_keyboard, get_signal_keyboard,
    get_check_pairs_keyboard,
)
from app.bot.texts_en import *
from app.db.repo import DatabaseRepository
from app.config.settings import get_settings
from app.core.data.market import MarketDataService
from app.core.indicators.ta import TechnicalAnalysis
from app.core.risk.sizing import RiskManager
from app.services.notifier import NotificationService

logger = logging.getLogger(__name__)
router = Router()
async def safe_edit(message: Message, text: str, reply_markup=None, parse_mode: str | None = None):
    """Edit text safely: ignore 'message is not modified' errors."""
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        # Ignore if content and markup are the same
        if "message is not modified" in str(e).lower():
            return
        raise


class RiskState(StatesGroup):
    """State for risk input"""
    waiting_for_risk = State()


class PairState(StatesGroup):
    """State for pair input"""
    waiting_for_pair = State()


def _get_db_repo_from_kwargs(kwargs):
    return kwargs.get("db_repo")


@router.message(CommandStart())
async def cmd_start(message: Message, **kwargs):
    """Handle /start command"""
    try:
        # Get database repository from dispatcher data
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Get or create user
        user = await db_repo.get_or_create_user(message.from_user.id)
        
        await message.answer(
            WELCOME_MESSAGE,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        
        logger.info(f"User {message.from_user.id} started the bot")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer(ERROR_GENERIC)


@router.message(Command("health"))
async def cmd_health(message: Message, **kwargs):
    """Health check: DB + Exchange connectivity"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        pairs = await db_repo.get_all_pairs()
        enabled = [p.symbol for p in pairs if p.enabled]

        # Try fetch 1 candle for first enabled pair
        exchange_ok = "n/a"
        if enabled:
            mds = MarketDataService()
            df = await mds.get_ohlcv(enabled[0], "1h", limit=1)
            exchange_ok = "OK" if df is not None and not df.empty else "FAIL"

        text = (
            "✅ Bot health\n"
            f"DB: OK (pairs={len(pairs)}, enabled={len(enabled)})\n"
            f"Exchange: {exchange_ok} (test={enabled[0] if enabled else 'n/a'} 1h)\n"
            "Use /status to see scan stats."
        )
        await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        await message.answer("❌ Health check failed. See logs.")


@router.message(Command("mock_signal"))
async def cmd_mock_signal(message: Message, **kwargs):
    """Send a mock signal to the current user to verify delivery"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        await db_repo.get_or_create_user(message.from_user.id)
        notifier = NotificationService()
        mock = {
            "id": 0,
            "symbol": "TEST/USDC",
            "grade": "A",
            "timeframe": "15m",
            "entry": 100.0,
            "sl": 95.0,
            "tp1": 105.0,
            "tp2": 110.0,
            "risk": "Low",
            "expires": "6h",
            "reason": "Health check",
        }
        ok = await notifier.send_signal(message.bot, message.from_user.id, mock, db_repo)
        await message.answer("✅ Mock signal sent" if ok else "❌ Mock signal failed")
    except Exception as e:
        logger.error(f"Mock signal failed: {e}")
        await message.answer("❌ Mock signal failed. See logs.")


@router.message(Command("check"))
async def cmd_check(message: Message, **kwargs):
    """Start interactive check: pick a pair to analyze now."""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        pairs = await db_repo.get_enabled_pairs()
        if not pairs:
            await message.answer("No enabled pairs.")
            return
        await message.answer(
            "Choose a pair to analyze:",
            reply_markup=get_check_pairs_keyboard(pairs),
        )
    except Exception as e:
        logger.error(f"/check failed: {e}")
        await message.answer("❌ Check failed. See logs.")


@router.callback_query(F.data.startswith("check_pair:"))
async def callback_check_pair(callback: CallbackQuery, **kwargs):
    """Analyze selected pair: trend, entry triggers, and reason not-long."""
    try:
        symbol = callback.data.split(":", 1)[1]
        db_repo = _get_db_repo_from_kwargs(kwargs)
        mds = MarketDataService()
        ta = TechnicalAnalysis()
        rm = RiskManager()

        # Fetch data
        h1 = await mds.get_ohlcv(symbol, "1h", 200)
        m15 = await mds.get_ohlcv(symbol, "15m", 200)
        m5 = await mds.get_ohlcv(symbol, "5m", 200)

        if h1 is None or m15 is None or m5 is None:
            await callback.answer("No data for pair", show_alert=True)
            return

        # Indicators
        ema200_h1 = ta.calculate_ema(h1["close"], 200).iloc[-1]
        rsi_h1 = ta.calculate_rsi(h1["close"], 14).iloc[-1]
        ema50_m15 = ta.calculate_ema(m15["close"], 50).iloc[-1]
        price_h1 = float(h1["close"].iloc[-1])
        price_m15 = float(m15["close"].iloc[-1])

        trend_ok = price_h1 > ema200_h1 and price_m15 > ema50_m15 and 45 <= rsi_h1 <= 65

        # Entry triggers (sample): EMA9>EMA21 cross on 15m, BB squeeze breakout, bullish engulfing
        ema9 = ta.calculate_ema(m15["close"], 9)
        ema21 = ta.calculate_ema(m15["close"], 21)
        ema9_now = float(ema9.iloc[-1])
        ema21_now = float(ema21.iloc[-1])
        ema9_prev = float(ema9.iloc[-2])
        ema21_prev = float(ema21.iloc[-2])
        crossover = ema9_now > ema21_now and ema9_prev <= ema21_prev

        bb_up, bb_low, bb_mid = ta.calculate_bollinger_bands(m15["close"], 20, 2.0)
        curr_width = float((bb_up.iloc[-1] - bb_low.iloc[-1]) / bb_mid.iloc[-1])
        avg_width = float(((bb_up - bb_low) / bb_mid).tail(10).mean())
        squeeze = curr_width < 0.05

        last = m15.iloc[-1]
        prev = m15.iloc[-2]
        bullish_engulf = (
            last["close"] > last["open"] and prev["close"] < prev["open"]
            and last["close"] > prev["open"] and last["open"] < prev["close"]
        )
        body = float(abs(last["close"] - last["open"]))
        lower_wick = float((last["open"] - last["low"]) if last["close"] > last["open"] else (last["close"] - last["low"]))
        upper_wick = float((last["high"] - last["close"]) if last["close"] > last["open"] else (last["high"] - last["open"]))
        lower_wick_ratio = (lower_wick / body) if body > 0 else 0.0

        triggers = [
            ("EMA9>EMA21 cross", crossover),
            ("BB squeeze", squeeze),
            ("Bullish engulfing", bullish_engulf),
        ]
        triggers_hit = [name for name, ok in triggers if ok]

        reasons = []
        if not trend_ok:
            if price_h1 <= ema200_h1:
                reasons.append("Price below EMA200 (1h)")
            if price_m15 <= ema50_m15:
                reasons.append("Price below EMA50 (15m)")
            if not (45 <= rsi_h1 <= 65):
                reasons.append(f"RSI(14,1h) {rsi_h1:.1f} not in 45-65")
        if len(triggers_hit) < 2:
            reasons.append(f"Only {len(triggers_hit)} entry trigger(s) hit")

        # Compose text
        # Volume diagnostics for context
        vol_sma = m15["volume"].rolling(window=20).mean()
        vol_ratio = float(last["volume"] / vol_sma.iloc[-1]) if vol_sma.iloc[-1] else 0.0

        text = (
            f"📈 <b>{symbol}</b> status\n"
            f"Price (1h): {price_h1:.4f}, EMA200: {ema200_h1:.4f}, RSI14: {rsi_h1:.1f}\n"
            f"Price (15m): {price_m15:.4f}, EMA50: {ema50_m15:.4f}\n"
            f"Trend filter: {'OK' if trend_ok else 'FAIL'}\n\n"
            f"Entry triggers hit: {', '.join(triggers_hit) if triggers_hit else 'none'}\n"
            f"• EMA9/EMA21: {ema9_now:.4f} / {ema21_now:.4f} (prev {ema9_prev:.4f}/{ema21_prev:.4f}) → cross: {'YES' if crossover else 'NO'}\n"
            f"• BB width: {curr_width*100:.2f}% (avg 10: {avg_width*100:.2f}%) → squeeze: {'YES' if squeeze else 'NO'}\n"
            f"• Volume ratio: {vol_ratio:.2f}× (vs SMA20)\n"
            f"• Candle: bullish engulfing={str(bullish_engulf)}; lower-wick/body={lower_wick_ratio:.2f}x\n"
        )

        if reasons:
            text += "\n❌ Not long now because:\n- " + "\n- ".join(reasons)
        else:
            text += "\n✅ Conditions look good for a long (test mode)."

        await safe_edit(
            callback.message,
            text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"check_pair failed: {e}")
        await callback.answer("Error during check", show_alert=True)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    await message.answer(
        HELP_MESSAGE,
        reply_markup=get_help_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("strategy"))
async def cmd_strategy(message: Message):
    """Handle /strategy command"""
    await message.answer(
        STRATEGY_MESSAGE,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("status"))
async def cmd_status(message: Message, **kwargs):
    """Handle /status command"""
    try:
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Get user info
        user = await db_repo.get_or_create_user(message.from_user.id)
        
        # Get pairs
        pairs = await db_repo.get_enabled_pairs()
        pairs_text = ", ".join([p.symbol for p in pairs])
        
        # Get active signals count
        signals_count = await db_repo.get_signals_count()
        
        # Build status message
        status_text = STATUS_HEADER
        status_text += SIGNALS_ENABLED if user.signals_enabled else SIGNALS_DISABLED
        status_text += f"\n{SCANNING_PAIRS.format(pairs=pairs_text)}"
        status_text += f"\n{ACTIVE_SIGNALS.format(count=signals_count)}"
        status_text += f"\n{RISK_SETTING.format(risk=user.risk_pct)}"
        status_text += f"\n{LAST_SCAN.format(time=datetime.now().strftime('%H:%M:%S'))}"
        
        await message.answer(
            status_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await message.answer(ERROR_GENERIC)


@router.message(Command("pairs"))
async def cmd_pairs(message: Message, **kwargs):
    """Handle /pairs command"""
    try:
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        pairs = await db_repo.get_all_pairs()
        
        await message.answer(
            PAIRS_HEADER,
            reply_markup=get_pairs_management_keyboard(pairs),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in pairs command: {e}")
        await message.answer(ERROR_GENERIC)


@router.message(Command("risk"))
async def cmd_risk(message: Message, **kwargs):
    """Handle /risk command"""
    try:
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        user = await db_repo.get_or_create_user(message.from_user.id)
        
        await message.answer(
            f"{RISK_HEADER}{CURRENT_RISK.format(risk=user.risk_pct)}",
            reply_markup=get_risk_keyboard(user.risk_pct),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in risk command: {e}")
        await message.answer(ERROR_GENERIC)


@router.message(Command("signals_on"))
async def cmd_signals_on(message: Message, **kwargs):
    """Handle /signals_on command"""
    try:
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        enabled = await db_repo.toggle_user_signals(message.from_user.id)
        
        if enabled:
            await message.answer(
                SUCCESS_SIGNAL_ENABLED,
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await message.answer(ERROR_GENERIC)
            
    except Exception as e:
        logger.error(f"Error in signals_on command: {e}")
        await message.answer(ERROR_GENERIC)


@router.message(Command("signals_off"))
async def cmd_signals_off(message: Message, **kwargs):
    """Handle /signals_off command"""
    try:
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        enabled = await db_repo.toggle_user_signals(message.from_user.id)
        
        if not enabled:
            await message.answer(
                SUCCESS_SIGNAL_DISABLED,
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await message.answer(ERROR_GENERIC)
            
    except Exception as e:
        logger.error(f"Error in signals_off command: {e}")
        await message.answer(ERROR_GENERIC)


# Callback query handlers
@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Handle main menu callback"""
    await safe_edit(
        callback.message,
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "show_help")
async def callback_show_help(callback: CallbackQuery):
    """Handle show help callback"""
    await safe_edit(
        callback.message,
        HELP_MESSAGE,
        reply_markup=get_help_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "show_strategy")
async def callback_show_strategy(callback: CallbackQuery):
    """Handle show strategy callback"""
    await safe_edit(
        callback.message,
        STRATEGY_MESSAGE,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "show_status")
async def callback_show_status(callback: CallbackQuery, **kwargs):
    """Handle show status callback"""
    try:
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Get user info
        user = await db_repo.get_or_create_user(callback.from_user.id)
        
        # Get pairs
        pairs = await db_repo.get_enabled_pairs()
        pairs_text = ", ".join([p.symbol for p in pairs])
        
        # Get active signals count
        signals_count = await db_repo.get_signals_count()
        
        # Build status message
        status_text = STATUS_HEADER
        status_text += SIGNALS_ENABLED if user.signals_enabled else SIGNALS_DISABLED
        status_text += f"\n{SCANNING_PAIRS.format(pairs=pairs_text)}"
        status_text += f"\n{ACTIVE_SIGNALS.format(count=signals_count)}"
        status_text += f"\n{RISK_SETTING.format(risk=user.risk_pct)}"
        status_text += f"\n{LAST_SCAN.format(time=datetime.now().strftime('%H:%M:%S'))}"
        
        await safe_edit(
            callback.message,
            status_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in show status callback: {e}")
        await callback.answer(ERROR_GENERIC)


@router.callback_query(F.data == "manage_pairs")
async def callback_manage_pairs(callback: CallbackQuery, **kwargs):
    """Handle manage pairs callback"""
    try:
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        pairs = await db_repo.get_all_pairs()
        
        await safe_edit(
            callback.message,
            PAIRS_HEADER,
            reply_markup=get_pairs_management_keyboard(pairs),
            parse_mode="HTML",
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in manage pairs callback: {e}")
        await callback.answer(ERROR_GENERIC)


@router.callback_query(F.data == "set_risk")
async def callback_set_risk(callback: CallbackQuery, **kwargs):
    """Handle set risk callback"""
    try:
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        user = await db_repo.get_or_create_user(callback.from_user.id)
        
        await safe_edit(
            callback.message,
            f"{RISK_HEADER}{CURRENT_RISK.format(risk=user.risk_pct)}",
            reply_markup=get_risk_keyboard(user.risk_pct),
            parse_mode="HTML",
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in set risk callback: {e}")
        await callback.answer(ERROR_GENERIC)


@router.callback_query(F.data.startswith("set_risk:"))
async def callback_set_risk_value(callback: CallbackQuery, **kwargs):
    """Handle set risk value callback"""
    try:
        risk_value = float(callback.data.split(":")[1])
        
        # Validate risk value
        if not (0.1 <= risk_value <= 5.0):
            await callback.answer(RISK_INVALID)
            return
        
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Update user risk
        success = await db_repo.update_user_risk(callback.from_user.id, risk_value)
        
        if success:
            await callback.answer(f"Risk updated to {risk_value}%")
            # Refresh the risk keyboard
            await safe_edit(
                callback.message,
                f"{RISK_HEADER}{CURRENT_RISK.format(risk=risk_value)}",
                reply_markup=get_risk_keyboard(risk_value),
                parse_mode="HTML",
            )
        else:
            await callback.answer(ERROR_GENERIC)
            
    except Exception as e:
        logger.error(f"Error in set risk value callback: {e}")
        await callback.answer(ERROR_GENERIC)


@router.callback_query(F.data.startswith("toggle_pair:"))
async def callback_toggle_pair(callback: CallbackQuery, **kwargs):
    """Handle toggle pair callback"""
    try:
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        symbol = callback.data.split(":")[1]
        enabled = await db_repo.toggle_pair(symbol)
        
        status = "enabled" if enabled else "disabled"
        await callback.answer(f"Pair {symbol} {status}")
        
        # Refresh pairs list
        pairs = await db_repo.get_all_pairs()
        await safe_edit(
            callback.message,
            PAIRS_HEADER,
            reply_markup=get_pairs_management_keyboard(pairs),
            parse_mode="HTML",
        )
        
    except Exception as e:
        logger.error(f"Error in toggle pair callback: {e}")
        await callback.answer(ERROR_GENERIC)


@router.callback_query(F.data == "add_pair")
async def callback_add_pair(callback: CallbackQuery, state: FSMContext):
    """Handle add pair callback"""
    await callback.message.edit_text(
        ADD_PAIR_PROMPT,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PairState.waiting_for_pair)
    await callback.answer()


@router.callback_query(F.data == "enable_signals")
async def callback_enable_signals(callback: CallbackQuery, **kwargs):
    """Handle enable signals callback"""
    try:
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        enabled = await db_repo.toggle_user_signals(callback.from_user.id)
        
        if enabled:
            await callback.answer(SUCCESS_SIGNAL_ENABLED)
        else:
            await callback.answer(ERROR_GENERIC)
            
    except Exception as e:
        logger.error(f"Error in enable signals callback: {e}")
        await callback.answer(ERROR_GENERIC)


@router.callback_query(F.data == "disable_signals")
async def callback_disable_signals(callback: CallbackQuery, **kwargs):
    """Handle disable signals callback"""
    try:
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        enabled = await db_repo.toggle_user_signals(callback.from_user.id)
        
        if not enabled:
            await callback.answer(SUCCESS_SIGNAL_DISABLED)
        else:
            await callback.answer(ERROR_GENERIC)
            
    except Exception as e:
        logger.error(f"Error in disable signals callback: {e}")
        await callback.answer(ERROR_GENERIC)


# State handlers
@router.message(PairState.waiting_for_pair)
async def handle_pair_input(message: Message, state: FSMContext, **kwargs):
    """Handle pair input from user"""
    try:
        symbol = message.text.strip().upper()
        
        # Add /USDC if not present
        if "/" not in symbol:
            symbol = f"{symbol}/USDC"
        
        # Get database repository
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Add pair
        success = await db_repo.add_pair(symbol)
        
        if success:
            await message.answer(
                PAIR_ADDED.format(symbol=symbol),
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await message.answer(
                PAIR_ALREADY_EXISTS.format(symbol=symbol),
                reply_markup=get_main_menu_keyboard()
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error handling pair input: {e}")
        await message.answer(ERROR_GENERIC)
        await state.clear()


def register_handlers(dp):
    """Register all handlers with the dispatcher"""
    dp.include_router(router)