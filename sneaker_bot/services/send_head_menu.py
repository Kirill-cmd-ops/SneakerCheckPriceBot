from typing import Union

from aiogram.types import Message, CallbackQuery

from sneaker_bot.menu.head_menu import head_menu
from sneaker_bot.services.send_messages import record_and_send


async def send_head_menu(
        source: Union[Message, CallbackQuery],
        state,
        text):
    return await record_and_send(source, state, text, reply_markup=head_menu)