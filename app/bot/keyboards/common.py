"""
Common keyboard layouts for the Telegram bot
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.texts_en import *


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Get main menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text=BTN_ENABLE_SIGNALS, callback_data="enable_signals"),
        InlineKeyboardButton(text=BTN_DISABLE_SIGNALS, callback_data="disable_signals")
    )
    builder.row(
        InlineKeyboardButton(text=BTN_MANAGE_PAIRS, callback_data="manage_pairs"),
        InlineKeyboardButton(text=BTN_SET_RISK, callback_data="set_risk")
    )
    builder.row(
        InlineKeyboardButton(text=BTN_SHOW_STATUS, callback_data="show_status"),
        InlineKeyboardButton(text=BTN_STRATEGY, callback_data="show_strategy")
    )
    builder.row(InlineKeyboardButton(text=BTN_HELP, callback_data="show_help"))
    
    return builder.as_markup()


def get_pairs_management_keyboard(pairs: list) -> InlineKeyboardMarkup:
    """Get pairs management keyboard"""
    builder = InlineKeyboardBuilder()
    
    for pair in pairs:
        symbol = pair.symbol
        status = "🟢" if pair.enabled else "🔴"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {symbol}", 
                callback_data=f"toggle_pair:{symbol}"
            )
        )
    
    builder.row(InlineKeyboardButton(text="➕ Add Pair", callback_data="add_pair"))
    builder.row(InlineKeyboardButton(text=BTN_BACK, callback_data="main_menu"))
    
    return builder.as_markup()


def get_risk_keyboard(current_risk: float) -> InlineKeyboardMarkup:
    """Get risk management keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Quick risk options
    risk_options = [0.5, 1.0, 1.5, 2.0, 3.0]
    for i in range(0, len(risk_options), 2):
        row_buttons = []
        for j in range(2):
            if i + j < len(risk_options):
                risk = risk_options[i + j]
                text = f"{risk}%" + (" (current)" if risk == current_risk else "")
                row_buttons.append(
                    InlineKeyboardButton(text=text, callback_data=f"set_risk:{risk}")
                )
        builder.row(*row_buttons)
    
    builder.row(InlineKeyboardButton(text="✏️ Custom", callback_data="custom_risk"))
    builder.row(InlineKeyboardButton(text=BTN_BACK, callback_data="main_menu"))
    
    return builder.as_markup()


def get_signal_keyboard(signal_id: int, symbol: str) -> InlineKeyboardMarkup:
    """Get signal action keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text=BTN_MARK_ACTIVE, callback_data=f"mark_active:{signal_id}"),
        InlineKeyboardButton(text=BTN_SNOOZE_1H, callback_data=f"snooze_signal:{signal_id}")
    )
    builder.row(
        InlineKeyboardButton(text=BTN_MUTE_PAIR, callback_data=f"mute_pair:{symbol}"),
        InlineKeyboardButton(text=BTN_EXPLAIN, callback_data=f"explain_signal:{signal_id}")
    )
    
    return builder.as_markup()


def get_confirmation_keyboard(action: str, data: str) -> InlineKeyboardMarkup:
    """Get confirmation keyboard for actions"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text=BTN_CONFIRM, callback_data=f"confirm:{action}:{data}"),
        InlineKeyboardButton(text=BTN_CANCEL, callback_data="cancel")
    )
    
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Get simple back keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=BTN_BACK, callback_data="main_menu"))
    return builder.as_markup()


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Get help keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text=BTN_STRATEGY, callback_data="show_strategy"),
        InlineKeyboardButton(text=BTN_SHOW_STATUS, callback_data="show_status")
    )
    builder.row(InlineKeyboardButton(text=BTN_BACK, callback_data="main_menu"))
    
    return builder.as_markup()