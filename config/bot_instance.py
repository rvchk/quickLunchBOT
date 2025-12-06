from aiogram import Bot
from typing import Optional

bot_instance: Optional[Bot] = None

def get_bot() -> Bot:
    if bot_instance is None:
        raise RuntimeError("Bot instance not initialized")
    return bot_instance

def set_bot(bot: Bot) -> None:
    global bot_instance
    bot_instance = bot

