from aiogram.fsm.context import FSMContext

async def delete_last_prompt_on_reply(state: FSMContext, bot, chat_id: int) -> bool:
    """
    Удаляет последнюю подсказку из state['prompt_refs'].
    Вызывать в начале хэндлера, который обрабатывает ответ пользователя.
    """
    data = await state.get_data()
    prompts = data.get("prompt_refs", [])
    if not prompts:
        # ничего удалять
        return False

    last = prompts.pop()  # последний prompt
    await state.update_data(prompt_refs=prompts)

    try:
        await bot.delete_message(chat_id=last["chat_id"], message_id=last["message_id"])
        print("Deleted prompt:", last)
        return True
    except Exception as e:
        print("Failed to delete prompt:", last, e)
        return False


async def delete_all_prompts_and_sticker(state: FSMContext, bot):
    """
    Удаляет все подсказки и стикер (если сохранён в sticker_info).
    Используется при необходимости полной очистки (например, back).
    """
    data = await state.get_data()
    prompts = data.get("prompt_refs", [])
    sticker_info = data.get("sticker_info")

    for ref in prompts:
        try:
            await bot.delete_message(chat_id=ref["chat_id"], message_id=ref["message_id"])
            print("Deleted prompt:", ref)
        except Exception as e:
            print("Failed to delete prompt:", ref, e)

    if sticker_info:
        try:
            await bot.delete_message(chat_id=sticker_info["chat_id"], message_id=sticker_info["message_id"])
            print("Deleted sticker:", sticker_info)
        except Exception as e:
            print("Failed to delete sticker:", sticker_info, e)

    await state.update_data(prompt_refs=[])
    await state.update_data(sticker_info=None)
