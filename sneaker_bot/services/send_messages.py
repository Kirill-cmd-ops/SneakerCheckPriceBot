from typing import Union

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery


async def record_and_send(
        ctx: Union[Message, CallbackQuery],
        state: FSMContext,
        text: str,
        **kwargs
) -> Message:
    if isinstance(ctx, CallbackQuery):
        await ctx.answer()
        sent = await ctx.message.answer(text, **kwargs)
    else:
        sent = await ctx.answer(text, **kwargs)

    data = await state.get_data()
    msg_ids = data.get("msg_ids", [])
    msg_ids.append(sent.message_id)
    await state.update_data(msg_ids=msg_ids)

    return sent