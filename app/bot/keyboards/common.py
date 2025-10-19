from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def signal_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Mark Active", callback_data="sig:active"),
        InlineKeyboardButton(text="Snooze 1h", callback_data="sig:snooze"),
    ],[
        InlineKeyboardButton(text="Mute Pair", callback_data="sig:mute"),
        InlineKeyboardButton(text="Explain", callback_data="sig:explain"),
    ]])
