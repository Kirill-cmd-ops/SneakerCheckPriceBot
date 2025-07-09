import os
from functools import wraps

from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from dotenv import load_dotenv

from dependencies import bot

load_dotenv()
ID_CHANNEL = os.getenv("ID_CHANNEL")

async def checker_sub(bot: Bot, user_id: int) -> bool:
    member = await bot.get_chat_member(
        chat_id=ID_CHANNEL,
        user_id=user_id,
    )
    return member.status not in ("left", "kicked")


def is_sub(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        msg = None
        query = None
        for arg in args:
            if isinstance(arg, Message):
                msg = arg
            elif isinstance(arg, CallbackQuery):
                query = arg

        if query:
            user_id = query.from_user.id

        elif msg:
            user_id = msg.from_user.id

        else:
            return await func(*args, **kwargs)

        if not await checker_sub(bot, user_id):
            return await query.answer(
                "Чтобы пользоваться, подпишись на канал",
                show_alert=True,
            )

        return await func(*args, **kwargs)

    return wrapper