from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from sneaker_bot.menu.sub_menu import sub_menu
from sneaker_bot.services.send_head_menu import send_head_menu
from sneaker_bot.services.send_messages import record_and_send
from sneaker_bot.setting import bot
from sneaker_bot.sub_checker import checker_sub
from sneaker_bot.tasks import tasks


router = Router()

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if task := tasks.pop(user_id, None):
        task.cancel()

    data = await state.get_data()
    msg_ids = data.get("msg_ids", [])
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id, mid)
        except:
            pass

    await state.clear()

    if not await checker_sub(bot, user_id):
        sent = await record_and_send(message, state, text="Чтобы пользоваться, подпишись на канал",
                                     reply_markup=sub_menu)
    else:
        sent = await send_head_menu(
            message,
            state,
            text='Выберите дальнейшее действие'
        )

    try:
        await bot.delete_message(chat_id, message.message_id)
    except:
        pass

    await state.update_data(menu_msg_id=sent.message_id)