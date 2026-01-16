from typing import Union
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

async def record_and_send(
        ctx: Union[Message, CallbackQuery],
        state: FSMContext,
        text: str,
        **kwargs
) -> Message:
    """
    Для обычных сообщений (результат, уведомления).
    Сохраняет в state['msg_refs'] список {"chat_id","message_id"}.
    """
    if isinstance(ctx, CallbackQuery):
        await ctx.answer()
        sent = await ctx.message.answer(text, **kwargs)
    else:
        sent = await ctx.answer(text, **kwargs)

    data = await state.get_data()
    refs = data.get("msg_refs", [])
    refs.append({"chat_id": sent.chat.id, "message_id": sent.message_id})
    await state.update_data(msg_refs=refs)

    return sent


async def send_prompt(
        ctx: Union[Message, CallbackQuery],
        state: FSMContext,
        text: str,
        **kwargs
) -> Message:
    """
    Для подсказок (prompts) типа "Введите бренд".
    Сохраняет в state['prompt_refs'] и также добавляет в msg_refs.
    """
    if isinstance(ctx, CallbackQuery):
        await ctx.answer()
        sent = await ctx.message.answer(text, **kwargs)
    else:
        sent = await ctx.answer(text, **kwargs)

    data = await state.get_data()
    prompts = data.get("prompt_refs", [])
    prompts.append({"chat_id": sent.chat.id, "message_id": sent.message_id})
    await state.update_data(prompt_refs=prompts)

    refs = data.get("msg_refs", [])
    refs.append({"chat_id": sent.chat.id, "message_id": sent.message_id})
    await state.update_data(msg_refs=refs)

    return sent
