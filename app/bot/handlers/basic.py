"""
Basic message handlers for the Telegram bot
"""
import logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

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


@router.message(Command("mock_real"))
async def cmd_mock_real(message: Message, **kwargs):
    """Generate and send a realistic mock signal from live data for a chosen pair (first enabled)."""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        user = await db_repo.get_or_create_user(message.from_user.id)
        pairs = await db_repo.get_enabled_pairs()
        if not pairs:
            await message.answer("No enabled pairs.")
            return
        symbol = pairs[0].symbol

        # Check current mode
        easy_mode_str = await db_repo.get_setting("use_easy_detector")
        use_easy_detector = easy_mode_str == "true" if easy_mode_str else False

        mds = MarketDataService()
        ta = TechnicalAnalysis()
        rm = RiskManager()

        m15 = await mds.get_ohlcv(symbol, "15m", 200)
        if m15 is None or m15.empty:
            await message.answer("No market data for mock.")
            return

        price = float(m15["close"].iloc[-1])
        sl = float(ta.calculate_stop_loss(m15, price))
        
        # Use technical take profits
        tp1, tp2 = ta.calculate_technical_take_profits(m15, price)

        # Position estimate for demo: assume $10,000 account
        position = rm.calculate_max_position_value(10000.0, user.risk_pct, price, sl)

        mode_text = "Easy Mode" if use_easy_detector else "Conservative Mode"
        mock = {
            "id": 0,
            "symbol": symbol,
            "grade": "A",
            "timeframe": "15m",
            "entry": round(price, 4),
            "sl": round(sl, 4),
            "tp1": round(tp1, 4),
            "tp2": round(tp2, 4),
            "risk": f"{user.risk_pct}",
            "position": f"${position:.2f}",
            "expires": "8h",
            "reason": f"Mock signal from live data ({mode_text})",
        }

        notifier = NotificationService()
        ok = await notifier.send_signal(message.bot, message.from_user.id, mock, db_repo)
        await message.answer("✅ Mock (live) signal sent" if ok else "❌ Failed to send mock signal")
    except Exception as e:
        logger.error(f"mock_real failed: {e}")
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


@router.callback_query(F.data.startswith("mark_active:"))
async def callback_mark_active(callback: CallbackQuery, **kwargs):
    """Handle mark active callback"""
    try:
        signal_id = int(callback.data.split(":")[1])
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Update signal status to active
        success = await db_repo.update_signal_status(signal_id, "active")
        
        if success:
            await callback.answer("✅ Signal marked as active")
        else:
            await callback.answer("❌ Failed to mark signal as active", show_alert=True)
        
    except Exception as e:
        logger.exception(f"Error marking signal active: {e}")
        await callback.answer("Error marking signal active", show_alert=True)


@router.callback_query(F.data.startswith("snooze_signal:"))
async def callback_snooze_signal(callback: CallbackQuery, **kwargs):
    """Handle snooze signal callback"""
    try:
        signal_id = int(callback.data.split(":")[1])
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Snooze signal for 1 hour
        from datetime import datetime, timedelta
        snooze_until = datetime.utcnow() + timedelta(hours=1)
        success = await db_repo.snooze_signal(signal_id, snooze_until)
        
        if success:
            await callback.answer("😴 Signal snoozed for 1 hour")
        else:
            await callback.answer("❌ Failed to snooze signal", show_alert=True)
        
    except Exception as e:
        logger.exception(f"Error snoozing signal: {e}")
        await callback.answer("Error snoozing signal", show_alert=True)


@router.callback_query(F.data.startswith("mute_pair:"))
async def callback_mute_pair(callback: CallbackQuery, **kwargs):
    """Handle mute pair callback"""
    try:
        symbol = callback.data.split(":")[1]
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Disable pair
        success = await db_repo.toggle_pair(symbol)
        
        if success:
            await callback.answer(f"🔇 Pair {symbol} muted")
        else:
            await callback.answer(f"❌ Failed to mute pair {symbol}", show_alert=True)
        
    except Exception as e:
        logger.exception(f"Error muting pair: {e}")
        await callback.answer("Error muting pair", show_alert=True)


@router.callback_query(F.data.startswith("explain_signal:"))
async def callback_explain_signal(callback: CallbackQuery, **kwargs):
    """Handle explain signal callback"""
    try:
        signal_id = int(callback.data.split(":")[1])
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Get signal from database
        signal = await db_repo.get_signal_by_id(signal_id)
        if not signal:
            await callback.answer("Signal not found", show_alert=True)
            return
        
        # Create detailed explanation
        explanation = f"""
🔍 <b>Signal Explanation</b>

<b>Symbol:</b> {signal.symbol}
<b>Grade:</b> {signal.grade} ({'Strong' if signal.grade == 'A' else 'Good' if signal.grade == 'B' else 'High-risk'})
<b>Timeframe:</b> {signal.timeframe}

<b>Entry Price:</b> {signal.entry_price:.4f}
<b>Stop Loss:</b> {signal.stop_loss:.4f} ({((signal.entry_price - signal.stop_loss) / signal.entry_price * 100):.1f}%)
<b>Take Profit 1:</b> {signal.take_profit_1:.4f} ({((signal.take_profit_1 - signal.entry_price) / signal.entry_price * 100):.1f}%)
<b>Take Profit 2:</b> {signal.take_profit_2:.4f} ({((signal.take_profit_2 - signal.entry_price) / signal.entry_price * 100):.1f}%)

<b>Risk Level:</b> {signal.risk_level}%
<b>Reason:</b> {signal.reason}

<b>Created:</b> {signal.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC
<b>Expires:</b> {signal.expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC

<b>Strategy:</b> Easy Mode (testing)
• Trend filter: NONE (always pass)
• Entry triggers: Need ≥1 out of 4
• Triggers: EMA crossover, price above EMA9, volume increase, any bullish candle

⚠️ <b>Disclaimer:</b> This is for testing purposes only. Not financial advice.
        """
        
        await callback.message.edit_text(
            explanation,
            parse_mode="HTML",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        
    except Exception as e:
        logger.exception(f"Error explaining signal: {e}")
        await callback.answer("Error explaining signal", show_alert=True)


@router.callback_query(F.data.startswith("check_pair:"))
async def callback_check_pair(callback: CallbackQuery, **kwargs):
    """Analyze selected pair: trend, entry triggers, and reason not-long."""
    try:
        symbol = callback.data.split(":", 1)[1]
        db_repo = _get_db_repo_from_kwargs(kwargs)
        mds = MarketDataService()
        ta = TechnicalAnalysis()
        rm = RiskManager()

        # Check current mode
        easy_mode_str = await db_repo.get_setting("use_easy_detector")
        use_easy_detector = easy_mode_str == "true" if easy_mode_str else False

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

        # Apply trend filter based on current mode
        if use_easy_detector:
            trend_ok = True  # Easy mode: no trend filter
        else:
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
            if not use_easy_detector:  # Only show trend reasons in conservative mode
                if price_h1 <= ema200_h1:
                    reasons.append("Price below EMA200 (1h)")
                if price_m15 <= ema50_m15:
                    reasons.append("Price below EMA50 (15m)")
                if not (45 <= rsi_h1 <= 65):
                    reasons.append(f"RSI(14,1h) {rsi_h1:.1f} not in 45-65")
        
        # Check trigger requirements based on mode
        required_triggers = 1 if use_easy_detector else 2
        if len(triggers_hit) < required_triggers:
            mode_text = "Easy Mode" if use_easy_detector else "Conservative Mode"
            reasons.append(f"Only {len(triggers_hit)} entry trigger(s) hit (need ≥{required_triggers} for {mode_text})")

        # Compose text
        # Volume diagnostics for context
        vol_sma = m15["volume"].rolling(window=20).mean()
        vol_ratio = float(last["volume"] / vol_sma.iloc[-1]) if vol_sma.iloc[-1] else 0.0

        ok = lambda x: '🟢' if x else '🔴'
        hint_trend = (
            "Above EMA200/EMA50 & RSI 45-65" if trend_ok else "Need >EMA200(1h), >EMA50(15m), RSI in 45-65"
        )
        hint_cross = "Momentum shift if cross just happened" if crossover else "Wait for EMA9 crossing EMA21 up"
        hint_squeeze = "Volatility compression can precede breakout" if squeeze else "No squeeze now"
        hint_candle = (
            "Demand signal on candle" if bullish_engulf or lower_wick_ratio >= 2.0 else "No bullish candle pattern"
        )

        mode_icon = "🟢" if use_easy_detector else "🔴"
        mode_text = "Easy Mode" if use_easy_detector else "Conservative Mode"
        
        text = (
            f"📈 <b>{symbol}</b> status ({mode_icon} {mode_text})\n"
            f"Price (1h): {price_h1:.4f}, EMA200: {ema200_h1:.4f}, RSI14: {rsi_h1:.1f}\n"
            f"Price (15m): {price_m15:.4f}, EMA50: {ema50_m15:.4f}\n"
            f"Trend filter: {ok(trend_ok)} {hint_trend}\n\n"
            f"Entry triggers hit: {', '.join(triggers_hit) if triggers_hit else 'none'} (need ≥{required_triggers})\n"
            f"{ok(crossover)} EMA9/EMA21 {ema9_now:.4f}/{ema21_now:.4f} (prev {ema9_prev:.4f}/{ema21_prev:.4f}) — {hint_cross}\n"
            f"{ok(squeeze)} BB width {curr_width*100:.2f}% (avg 10: {avg_width*100:.2f}%) — {hint_squeeze}\n"
            f"ℹ️ Volume ratio: {vol_ratio:.2f}× vs SMA20\n"
            f"{ok(bullish_engulf or lower_wick_ratio>=2.0)} Candle: engulfing={str(bullish_engulf)}, lower-wick/body={lower_wick_ratio:.2f}x — {hint_candle}\n"
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
async def cmd_strategy(message: Message, **kwargs):
    """Handle /strategy command"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Get current strategy mode
        strategy_mode = await db_repo.get_strategy_mode()
        
        if strategy_mode == "easy":
            strategy_text = """
<b>📈 My Trading Strategy (🟢 Easy Mode)</b>

<b>Trend Filter:</b>
• NONE - Always passes (Easy Mode)

<b>Entry Triggers (Need ≥1):</b>
• EMA9/EMA21 bullish crossover
• Price above EMA9
• BB squeeze
• Any bullish candle pattern

<b>Risk Management:</b>
• Stop Loss: Technical analysis (support/ATR, min 0.5%)
• Take Profit: Technical analysis (resistance/ATR)
• Risk per trade: User-defined (adjustable)
• Max signals: Unlimited
• Max holding time: 24 hours

<b>Signal Grading:</b>
• A: Strong (6+ points)
• B: Good (4-5 points) 
• C: High-risk (1-3 points)

<b>Note:</b> Easy Mode generates more signals for testing purposes.
            """
        elif strategy_mode == "aggressive":
            strategy_text = """
<b>📈 My Trading Strategy (🟡 Aggressive Mode)</b>

<b>Trend Filter:</b>
• RSI bounce from oversold (< 30 then >= 30)

<b>Entry Triggers (Need ALL 3):</b>
• RSI bounce from oversold
• EMA crossover (price crosses EMA50 from below)
• Volume surge (≥1.5x average over 20 candles)
• Trend strengthening (EMA20 > EMA50)

<b>Risk Management:</b>
• Stop Loss: Technical analysis (support/ATR)
• Take Profit: Technical analysis (resistance/ATR)
• Risk per trade: User-defined
• Max signals: Unlimited
• Max holding time: 18 hours

<b>Signal Grading:</b>
• Always C grade (high risk, bounce signals)

<b>Philosophy:</b> Buy the dip, catch oversold bounces. Higher risk, reversal signals.
            """
        else:  # conservative
            strategy_text = STRATEGY_MESSAGE
        
        await message.answer(
            strategy_text,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in strategy command: {e}")
        await message.answer(ERROR_GENERIC)


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
        active_signals_count = await db_repo.get_active_signals_count()
        user_active_signals = await db_repo.get_user_active_signals_count(user.tg_id)
        
        # Get current mode
        easy_mode_str = await db_repo.get_setting("use_easy_detector")
        use_easy_detector = easy_mode_str == "true" if easy_mode_str else False
        mode_icon = "🟢" if use_easy_detector else "🔴"
        mode_text = "Easy Mode" if use_easy_detector else "Conservative Mode"
        
        # Build status message
        status_text = STATUS_HEADER
        status_text += SIGNALS_ENABLED if user.signals_enabled else SIGNALS_DISABLED
        status_text += f"\n{mode_icon} <b>Detection Mode:</b> {mode_text}"
        status_text += f"\n{SCANNING_PAIRS.format(pairs=pairs_text)}"
        status_text += f"\n{ACTIVE_SIGNALS.format(count=signals_count)}"
        status_text += f"\n📊 Your active signals: <b>{user_active_signals}</b>"
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
async def callback_show_strategy(callback: CallbackQuery, **kwargs):
    """Handle show strategy callback"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Get current strategy mode
        strategy_mode = await db_repo.get_strategy_mode()
        
        if strategy_mode == "easy":
            strategy_text = """
<b>📈 My Trading Strategy (🟢 Easy Mode)</b>

<b>Trend Filter:</b>
• NONE - Always passes (Easy Mode)

<b>Entry Triggers (Need ≥1):</b>
• EMA9/EMA21 bullish crossover
• BB squeeze
• Any bullish candle pattern
• Price above EMA9

<b>Risk Management:</b>
• Stop Loss: Technical analysis (support/ATR, min 0.5%)
• Take Profit: Technical analysis (resistance/ATR)
• Risk per trade: User-defined (adjustable)
• Max signals: Unlimited
• Max holding time: 24 hours

<b>Signal Grading:</b>
• A: Strong (6+ points)
• B: Good (4-5 points) 
• C: High-risk (1-3 points)

<b>Note:</b> Easy Mode generates more signals for testing purposes.
            """
        elif strategy_mode == "aggressive":
            strategy_text = """
<b>📈 My Trading Strategy (🟡 Aggressive Mode)</b>

<b>Trend Filter:</b>
• RSI bounce from oversold (< 30 then >= 30)

<b>Entry Triggers (Need ALL 3):</b>
• RSI bounce from oversold
• EMA crossover (price crosses EMA50 from below)
• Volume surge (≥1.5x average over 20 candles)
• Trend strengthening (EMA20 > EMA50)

<b>Risk Management:</b>
• Stop Loss: Technical analysis (support/ATR)
• Take Profit: Technical analysis (resistance/ATR)
• Risk per trade: User-defined
• Max signals: Unlimited
• Max holding time: 18 hours

<b>Signal Grading:</b>
• Always C grade (high risk, bounce signals)

<b>Philosophy:</b> Buy the dip, catch oversold bounces. Higher risk, reversal signals.
            """
        else:  # conservative
            strategy_text = STRATEGY_MESSAGE
        
        await safe_edit(
            callback.message,
            strategy_text,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in show_strategy callback: {e}")
        await callback.answer("Error loading strategy", show_alert=True)


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
        
        # Get current mode
        easy_mode_str = await db_repo.get_setting("use_easy_detector")
        use_easy_detector = easy_mode_str == "true" if easy_mode_str else False
        mode_icon = "🟢" if use_easy_detector else "🔴"
        mode_text = "Easy Mode" if use_easy_detector else "Conservative Mode"
        
        # Build status message
        status_text = STATUS_HEADER
        status_text += SIGNALS_ENABLED if user.signals_enabled else SIGNALS_DISABLED
        status_text += f"\n{mode_icon} <b>Detection Mode:</b> {mode_text}"
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


@router.message(Command("debug_scanner"))
async def cmd_debug_scanner(message: Message, **kwargs):
    """Handle /debug_scanner command to diagnose scanner issues"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        settings = get_settings()
        enabled_pairs = await db_repo.get_enabled_pairs()
        
        debug_text = "🔍 <b>Scanner Debug Report</b>\n\n"
        
        # Check enabled pairs
        debug_text += f"<b>Enabled Pairs:</b> {len(enabled_pairs)}\n"
        for pair in enabled_pairs:
            debug_text += f"  - {pair.symbol}\n"
        debug_text += "\n"
        
        # Check active signals
        active_signals = await db_repo.get_active_signals()
        debug_text += f"<b>Active Signals:</b> {len(active_signals)}\n"
        for signal in active_signals:
            debug_text += f"  - {signal.symbol} ({signal.grade}) - {signal.created_at}\n"
        debug_text += "\n"
        
        # Test market data for first pair
        if enabled_pairs:
            symbol = enabled_pairs[0].symbol
            debug_text += f"<b>Testing {symbol}:</b>\n"
            
            # Test all timeframes
            timeframes = [settings.trend_timeframe, settings.entry_timeframe, settings.confirmation_timeframe]
            for tf in timeframes:
                mds = MarketDataService()
                df = await mds.get_ohlcv(symbol, tf, limit=50)
                if df is not None and not df.empty:
                    debug_text += f"  ✅ {tf}: {len(df)} candles, latest: {df['close'].iloc[-1]:.4f}\n"
                else:
                    debug_text += f"  ❌ {tf}: No data\n"
            
            debug_text += "\n"
            
            # Test signal detection logic
            debug_text += f"<b>Signal Detection Test for {symbol}:</b>\n"
            
            # Get data for all timeframes
            trend_df = await mds.get_ohlcv(symbol, settings.trend_timeframe, limit=250)
            entry_df = await mds.get_ohlcv(symbol, settings.entry_timeframe, limit=60)
            confirmation_df = await mds.get_ohlcv(symbol, settings.confirmation_timeframe, limit=30)
            
            if all([df is not None and not df.empty for df in [trend_df, entry_df, confirmation_df]]):
                ta = TechnicalAnalysis()
                
                # Check current mode
                easy_mode_str = await db_repo.get_setting("use_easy_detector")
                use_easy_detector = easy_mode_str == "true" if easy_mode_str else False
                
                debug_text += f"  <b>Detection Mode:</b> {'🟢 Easy Mode' if use_easy_detector else '🔴 Conservative Mode'}\n"
                
                if use_easy_detector:
                    # Easy mode: no trend filter
                    debug_text += f"  Trend Filter: ✅ (Easy Mode - Always Pass)\n"
                    trend_filter_ok = True
                else:
                    # Conservative mode: full trend filter
                    trend_bullish = ta.is_trend_bullish(trend_df)
                    entry_trend_bullish = ta.is_trend_bullish(entry_df)
                    rsi_neutral = ta.is_rsi_neutral_bullish(trend_df)
                    
                    debug_text += f"  Trend Filter: {'✅' if trend_bullish else '❌'} (1h bullish: {trend_bullish})\n"
                    debug_text += f"  Entry Trend: {'✅' if entry_trend_bullish else '❌'} (15m bullish: {entry_trend_bullish})\n"
                    debug_text += f"  RSI Range: {'✅' if rsi_neutral else '❌'} (45-65: {rsi_neutral})\n"
                    
                    trend_filter_ok = trend_bullish and entry_trend_bullish and rsi_neutral
                
                debug_text += f"  <b>Trend Filter Result:</b> {'✅ PASS' if trend_filter_ok else '❌ FAIL'}\n\n"
                
                if trend_filter_ok:
                    # Test entry triggers using SAME logic as /check command
                    triggers = []
                    
                    # Test each trigger using direct calculations (same as /check)
                    # 1. EMA9/EMA21 crossover
                    ema9 = ta.calculate_ema(entry_df["close"], 9)
                    ema21 = ta.calculate_ema(entry_df["close"], 21)
                    ema9_now = float(ema9.iloc[-1])
                    ema21_now = float(ema21.iloc[-1])
                    ema9_prev = float(ema9.iloc[-2])
                    ema21_prev = float(ema21.iloc[-2])
                    crossover = ema9_now > ema21_now and ema9_prev <= ema21_prev
                    if crossover:
                        triggers.append("ema_crossover")
                    
                    # 2. BB squeeze (same logic as /check)
                    bb_up, bb_low, bb_mid = ta.calculate_bollinger_bands(entry_df["close"], 20, 2.0)
                    curr_width = float((bb_up.iloc[-1] - bb_low.iloc[-1]) / bb_mid.iloc[-1])
                    avg_width = float(((bb_up - bb_low) / bb_mid).tail(10).mean())
                    squeeze = curr_width < 0.05
                    if squeeze:
                        triggers.append("bb_squeeze")
                    
                    # 3. Bullish candle (same logic as /check)
                    last = entry_df.iloc[-1]
                    prev = entry_df.iloc[-2]
                    bullish_engulf = (
                        last["close"] > last["open"] and prev["close"] < prev["open"]
                        and last["close"] > prev["open"] and last["open"] < prev["close"]
                    )
                    body = float(abs(last["close"] - last["open"]))
                    lower_wick = float((last["open"] - last["low"]) if last["close"] > last["open"] else (last["close"] - last["low"]))
                    lower_wick_ratio = (lower_wick / body) if body > 0 else 0.0
                    bullish_candle = bullish_engulf or lower_wick_ratio >= 2.0
                    if bullish_candle:
                        triggers.append("bullish_candle")
                    
                    # 4. Price above EMA9 (Easy Mode specific)
                    if use_easy_detector:
                        price_above_ema9 = float(entry_df["close"].iloc[-1]) > ema9_now
                        if price_above_ema9:
                            triggers.append("price_above_ema9")
                    
                    debug_text += f"  <b>Entry Triggers:</b> {len(triggers)}/4\n"
                    debug_text += f"    - EMA Crossover: {'✅' if crossover else '❌'}\n"
                    debug_text += f"    - BB Squeeze: {'✅' if squeeze else '❌'}\n"
                    debug_text += f"    - Bullish Candle: {'✅' if bullish_candle else '❌'}\n"
                    if use_easy_detector:
                        debug_text += f"    - Price above EMA9: {'✅' if price_above_ema9 else '❌'}\n"
                    
                    if use_easy_detector:
                        triggers_ok = len(triggers) >= 1  # Easy mode needs only 1 trigger
                        debug_text += f"  <b>Triggers Result:</b> {'✅ PASS' if triggers_ok else '❌ FAIL'} (Easy Mode: need ≥1)\n\n"
                    else:
                        triggers_ok = len(triggers) >= 2  # Conservative mode needs 2 triggers
                        debug_text += f"  <b>Triggers Result:</b> {'✅ PASS' if triggers_ok else '❌ FAIL'} (Conservative Mode: need ≥2)\n\n"
                    
                    if triggers_ok:
                        debug_text += f"  <b>🎯 SIGNAL WOULD BE GENERATED!</b>\n"
                    else:
                        if use_easy_detector:
                            debug_text += f"  <b>❌ No signal: Need ≥1 trigger (Easy Mode)</b>\n"
                        else:
                            debug_text += f"  <b>❌ No signal: Need ≥2 triggers (Conservative Mode)</b>\n"
                else:
                    debug_text += f"  <b>❌ No signal: Trend filter failed</b>\n"
            else:
                debug_text += f"  ❌ Insufficient data for signal detection\n"
        
        debug_text += f"\n<b>Scanner Settings:</b>\n"
        debug_text += f"  - Scan interval: {settings.scan_interval_sec}s\n"
        debug_text += f"  - Max concurrent signals: {settings.max_concurrent_signals}\n"
        debug_text += f"  - Signal expiry: {settings.signal_expiry_hours}h\n"
        
        await message.answer(debug_text, parse_mode="HTML")
        
    except Exception as e:
        logger.exception(f"Error in debug scanner: {e}")
        await message.answer(f"❌ Debug error: {str(e)}")


@router.message(Command("force_scan"))
async def cmd_force_scan(message: Message, **kwargs):
    """Handle /force_scan command to force immediate market scan"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Get scanner from main app (we'll need to pass it via middleware)
        # For now, let's create a simple scan
        settings = get_settings()
        enabled_pairs = await db_repo.get_enabled_pairs()
        
        if not enabled_pairs:
            await message.answer("⚠️ No enabled pairs to scan. Use /pairs to add some.")
            return
        
        await message.answer("🔄 Starting forced scan...")
        
        # Create services
        mds = MarketDataService()
        ta = TechnicalAnalysis()
        rm = RiskManager()
        
        # Get active signals to avoid duplicates
        active_signals = await db_repo.get_active_signals()
        active_symbols = {signal.symbol for signal in active_signals}
        
        # Prepare symbols list
        symbols = [pair.symbol for pair in enabled_pairs if pair.symbol not in active_symbols]
        
        if not symbols:
            await message.answer("ℹ️ All pairs have active signals, skipping scan")
            return
        
        # Required timeframes
        timeframes = [settings.trend_timeframe, settings.entry_timeframe, settings.confirmation_timeframe]
        
        # Fetch market data for all symbols and timeframes
        market_data = await mds.get_multiple_ohlcv(symbols, timeframes)
        
        # Use appropriate detector based on database setting
        from app.core.signals.easy_detector import EasySignalDetector
        
        # Check database for current mode
        easy_mode_str = await db_repo.get_setting("use_easy_detector")
        use_easy_detector = easy_mode_str == "true" if easy_mode_str else False
        
        if use_easy_detector:
            detector = EasySignalDetector(ta, rm)
            logger.info("Force scan using EasySignalDetector")
        else:
            from app.core.signals.detector import SignalDetector
            detector = SignalDetector(ta, rm)
            logger.info("Force scan using SignalDetector")
        
        # Detect signals using the appropriate detector
        signals = detector.detect_signals(market_data)
        
        # Process signals
        signals_found = 0
        for signal_data in signals:
            try:
                # Check if we should generate this signal
                current_signals = await db_repo.get_active_signals()
                if not detector.should_generate_signal(signal_data['symbol'], current_signals):
                    continue
                
                # Create signal in database
                signal = await db_repo.create_signal(
                    symbol=signal_data['symbol'],
                    timeframe=signal_data['timeframe'],
                    entry_price=signal_data['entry_price'],
                    stop_loss=signal_data['stop_loss'],
                    take_profit_1=signal_data['take_profit_1'],
                    take_profit_2=signal_data['take_profit_2'],
                    grade=signal_data['grade'],
                    risk_level=signal_data['risk_level'],
                    reason=signal_data['reason'],
                    expires_at=signal_data['expires_at']
                )
                
                signals_found += 1
                logger.info(f"Forced scan signal: {signal.symbol} {signal.grade}")
                
            except Exception as e:
                logger.error(f"Error processing forced scan signal for {signal_data.get('symbol', 'unknown')}: {e}")
        
        await message.answer(f"✅ Forced scan completed. Found {signals_found} signals.")
        
    except Exception as e:
        logger.exception(f"Error in force scan: {e}")
        await message.answer(f"❌ Force scan error: {str(e)}")


@router.message(Command("easy_mode"))
async def cmd_easy_mode(message: Message, **kwargs):
    """Handle /easy_mode command to toggle easy signal detection"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        settings = get_settings()
        
        # Get current mode from database
        current_mode_str = await db_repo.get_setting("use_easy_detector")
        current_mode = current_mode_str == "true" if current_mode_str else False
        
        # Toggle easy mode
        new_mode = not current_mode
        
        # Save to database
        await db_repo.set_setting("use_easy_detector", "true" if new_mode else "false")
        
        # Update the global settings
        settings.use_easy_detector = new_mode
        
        if new_mode:
            await message.answer(
                "🟢 <b>Easy Mode ENABLED</b>\n\n"
                "Easy mode uses VERY lenient conditions:\n"
                "• Trend filter: NONE (always pass)\n"
                "• Entry triggers: Need ≥1 instead of ≥2\n"
                "• Triggers: EMA crossover, price above EMA9, volume increase, any bullish candle\n\n"
                "This should generate MANY signals for testing.\n\n"
                "Use /force_scan to test immediately.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "🔴 <b>Easy Mode DISABLED</b>\n\n"
                "Back to conservative strategy:\n"
                "• Trend filter: Price > EMA200 (1h) AND > EMA50 (15m) AND RSI 45-65\n"
                "• Entry triggers: Need ≥2 out of 4\n"
                "• More strict conditions for higher quality signals\n\n"
                "Use /force_scan to test immediately.",
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.exception(f"Error in easy mode: {e}")
        await message.answer(f"❌ Easy mode error: {str(e)}")


@router.message(Command("strategy_mode"))
async def cmd_strategy_mode(message: Message, **kwargs):
    """Handle /strategy_mode command to select strategy"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        current_mode = await db_repo.get_strategy_mode()
        
        mode_info = {
            "conservative": "🔴 <b>Conservative Mode</b>\n\n"
                          "• Trend filter: Price > EMA200 (1h) AND > EMA50 (15m) AND RSI 45-65\n"
                          "• Entry triggers: Need ≥2 out of 4\n"
                          "• Quality: Highest quality signals\n"
                          "• Risk: Lower risk, rare signals",
            
            "easy": "🟢 <b>Easy Mode</b>\n\n"
                    "• Trend filter: NONE (always pass)\n"
                    "• Entry triggers: Need ≥1 out of 4\n"
                    "• Quality: Medium quality, more signals\n"
                    "• Risk: Moderate risk, frequent signals",
            
            "aggressive": "🟡 <b>Aggressive Mode</b>\n\n"
                          "• Trend filter: RSI bounce from oversold\n"
                          "• Entry triggers: RSI bounce + EMA crossover + Volume surge (all 3 required)\n"
                          "• Quality: High-risk bounce signals\n"
                          "• Risk: Higher risk, reversal signals\n"
                          "• Philosophy: Buy the dip, catch oversold bounces"
        }
        
        text = f"{mode_info.get(current_mode, mode_info['conservative'])}\n\n"
        text += f"<b>Current mode:</b> {current_mode}\n\n"
        text += "<b>Select strategy mode:</b>\n"
        text += "/conservative_mode - Conservative strategy\n"
        text += "/easy_mode - Easy testing strategy\n"
        text += "/aggressive_mode - Aggressive bounce strategy"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logger.exception(f"Error in strategy_mode command: {e}")
        await message.answer("❌ Error getting strategy mode")


@router.message(Command("conservative_mode"))
async def cmd_conservative_mode(message: Message, **kwargs):
    """Handle /conservative_mode command"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        await db_repo.set_strategy_mode("conservative")
        
        await message.answer(
            "🔴 <b>Conservative Mode ENABLED</b>\n\n"
            "Conservative strategy uses the strictest conditions:\n"
            "• Trend filter: Price > EMA200 (1h) AND > EMA50 (15m) AND RSI 45-65\n"
            "• Entry triggers: Need ≥2 out of 4\n"
            "• Quality: Highest quality signals\n"
            "• Risk: Lower risk, rare signals\n\n"
            "Use /force_scan to test immediately.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.exception(f"Error in conservative_mode command: {e}")
        await message.answer("❌ Error setting conservative mode")


@router.message(Command("aggressive_mode"))
async def cmd_aggressive_mode(message: Message, **kwargs):
    """Handle /aggressive_mode command"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        await db_repo.set_strategy_mode("aggressive")
        
        await message.answer(
            "🟡 <b>Aggressive Mode ENABLED</b>\n\n"
            "Aggressive bounce strategy:\n"
            "• Trend filter: RSI bounce from oversold (< 30 then >= 30)\n"
            "• Entry triggers: Need ALL 3 - RSI bounce + EMA crossover + Volume surge\n"
            "• Philosophy: Buy the dip, catch oversold bounces\n"
            "• Quality: Higher risk, reversal signals\n"
            "• Max hold: 18 hours\n\n"
            "Use /force_scan to test immediately.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.exception(f"Error in aggressive_mode command: {e}")
        await message.answer("❌ Error setting aggressive mode")


@router.message(Command("my_signals"))
async def cmd_my_signals(message: Message, **kwargs):
    """Handle /my_signals command to show user's active signals"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        
        # Get active signals
        active_signals = await db_repo.get_active_signals()
        
        if not active_signals:
            await message.answer(
                "📊 <b>Your Active Signals</b>\n\n"
                "You have no active signals at the moment.\n\n"
                "Use /status to see all available signals and mark them as active.",
                parse_mode="HTML"
            )
            return
        
        # Format signals
        signals_text = "📊 <b>Your Active Signals</b>\n\n"
        for signal in active_signals:
            signals_text += f"🟢 <b>{signal.symbol}</b> ({signal.grade})\n"
            signals_text += f"   Entry: {signal.entry_price:.4f}\n"
            signals_text += f"   SL: {signal.stop_loss:.4f} | TP1: {signal.take_profit_1:.4f} | TP2: {signal.take_profit_2:.4f}\n"
            signals_text += f"   Status: {signal.status}\n"
            signals_text += f"   Created: {signal.created_at.strftime('%H:%M:%S')}\n\n"
        
        await message.answer(signals_text, parse_mode="HTML")
        
    except Exception as e:
        logger.exception(f"Error in my_signals: {e}")
        await message.answer("❌ Error loading your signals")


@router.message(Command("mode_status"))
async def cmd_mode_status(message: Message, **kwargs):
    """Handle /mode_status command to check current detection mode"""
    try:
        db_repo = _get_db_repo_from_kwargs(kwargs)
        settings = get_settings()
        
        # Get current mode from database
        current_mode_str = await db_repo.get_setting("use_easy_detector")
        is_easy_mode = current_mode_str == "true" if current_mode_str else False
        
        if is_easy_mode:
            mode_text = "🟢 <b>Easy Mode ACTIVE</b>"
            conditions_text = (
                "• Trend filter: NONE (always pass)\n"
                "• Entry triggers: Need ≥1 out of 4\n"
                "• Triggers: EMA crossover, price above EMA9, volume increase, any bullish candle"
            )
        else:
            mode_text = "🔴 <b>Conservative Mode ACTIVE</b>"
            conditions_text = (
                "• Trend filter: Price > EMA200 (1h) AND > EMA50 (15m) AND RSI 45-65\n"
                "• Entry triggers: Need ≥2 out of 4\n"
                "• Triggers: Breakout & retest, BB squeeze, EMA crossover, bullish candle"
            )
        
        await message.answer(
            f"{mode_text}\n\n"
            f"<b>Current conditions:</b>\n{conditions_text}\n\n"
            f"Use /easy_mode to toggle between modes.\n"
            f"Use /force_scan to test current mode.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.exception(f"Error in mode status: {e}")
        await message.answer(f"❌ Mode status error: {str(e)}")


def register_handlers(dp):
    """Register all handlers with the dispatcher"""
    dp.include_router(router)