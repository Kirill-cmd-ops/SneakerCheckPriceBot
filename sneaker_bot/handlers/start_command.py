from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from sneaker_bot.menu.sub_menu import sub_menu
from sneaker_bot.services.send_head_menu import send_head_menu
from sneaker_bot.services.send_messages import record_and_send, send_prompt
from sneaker_bot.services.utils import delete_all_prompts_and_sticker
from sneaker_bot.setting import bot
from sneaker_bot.sub_checker import checker_sub
from sneaker_bot.tasks import tasks

router = Router()



@router.message(lambda m: m.text and m.text.lower() == "debug_state")
async def debug_state(message: Message, state: FSMContext):
    data = await state.get_data()
    print("STATE DEBUG:", data)
    await message.answer("State printed to logs")


@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # отменяем задачу, если была
    if task := tasks.pop(user_id, None):
        task.cancel()

    # удаляем все ранее сохранённые сообщения (msg_refs) — если есть
    data = await state.get_data()
    msg_refs = data.get("msg_refs", [])
    for ref in msg_refs:
        try:
            await bot.delete_message(ref["chat_id"], ref["message_id"])
        except Exception:
            pass

    # очищаем состояние полностью
    await state.clear()

    # удаляем также подсказки и стикер, если где-то остались (на всякий случай)
    try:
        await delete_all_prompts_and_sticker(state, bot)
    except Exception:
        pass

    # отправляем стартовое сообщение / подсказку
    if not await checker_sub(bot, user_id):
        sent = await send_prompt(message, state, "👻Чтобы пользоваться, подпишись на канал👻", reply_markup=sub_menu)
    else:
        # send_head_menu может возвращать Message; если нет — используем record_and_send
        sent = await send_head_menu(message, state, text='📩Выберите дальнейшее действие📩')

    # удаляем команду пользователя, чтобы не засорять чат
    try:
        await bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    # сохраняем id меню (если нужно)
    try:
        await state.update_data(menu_msg_id=sent.message_id)
    except Exception:
        pass
