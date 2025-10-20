"""
Basic message handlers for the Telegram bot
"""
import logging
from datetime import datetime
from typing import List

from aiogram import Router, F, Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.bot.keyboards.common import (
    get_back_keyboard, get_help_keyboard, get_main_menu_keyboard,
    get_pairs_management_keyboard, get_risk_keyboard, get_signal_keyboard
)
from app.bot.texts_en import *
from app.db.repo import DatabaseRepository
from app.config.settings import get_settings

logger = logging.getLogger(__name__)
router = Router()


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
    await callback.message.edit_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "show_help")
async def callback_show_help(callback: CallbackQuery):
    """Handle show help callback"""
    await callback.message.edit_text(
        HELP_MESSAGE,
        reply_markup=get_help_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "show_strategy")
async def callback_show_strategy(callback: CallbackQuery):
    """Handle show strategy callback"""
    await callback.message.edit_text(
        STRATEGY_MESSAGE,
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
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
        
        await callback.message.edit_text(
            status_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
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
        
        await callback.message.edit_text(
            PAIRS_HEADER,
            reply_markup=get_pairs_management_keyboard(pairs),
            parse_mode="HTML"
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
        
        await callback.message.edit_text(
            f"{RISK_HEADER}{CURRENT_RISK.format(risk=user.risk_pct)}",
            reply_markup=get_risk_keyboard(user.risk_pct),
            parse_mode="HTML"
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
            await callback.message.edit_text(
                f"{RISK_HEADER}{CURRENT_RISK.format(risk=risk_value)}",
                reply_markup=get_risk_keyboard(risk_value),
                parse_mode="HTML"
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
        await callback.message.edit_text(
            PAIRS_HEADER,
            reply_markup=get_pairs_management_keyboard(pairs),
            parse_mode="HTML"
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