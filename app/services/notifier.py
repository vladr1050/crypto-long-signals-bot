from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from typing import Iterable
from datetime import datetime
from ..bot.texts_en import render_signal
from ..db.repo import Repo

class Notifier:
    def __init__(self, bot: Bot, repo: Repo):
        self.bot = bot
        self.repo = repo

    async def broadcast_signal(self, chat_ids: Iterable[int], signal_dict: dict, signal_id: int) -> None:
        text = render_signal(**signal_dict)
        for chat_id in chat_ids:
            try:
                await self.bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True)
            except TelegramBadRequest:
                continue
        await self.repo.mark_sent(signal_id)
