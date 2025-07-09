from typing import Union

from aiogram.types import Message, CallbackQuery

from sneaker_bot.dependencies import record_and_send
from sneaker_bot.menu.head_menu import head_menu


async def send_head_menu(
        source: Union[Message, CallbackQuery],
        state,
        text):
    return await record_and_send(source, state, text, reply_markup=head_menu)