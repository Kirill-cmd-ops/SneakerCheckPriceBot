import asyncio

from aiogram import Router

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message

from sneaker_bot.menu.back_menu import back_menu
from sneaker_bot.parsers.price_parser import process_price_search
from sneaker_bot.services.send_messages import record_and_send
from sneaker_bot.setting import bot
from sneaker_bot.sub_checker import is_sub
from sneaker_bot.tasks import tasks


class KnowPriceSG(StatesGroup):
    waiting_for_query = State()


router = Router()


@router.callback_query(lambda c: c.data == "know_button")
@is_sub
async def search_know_button(query: CallbackQuery, state: FSMContext):
    await query.answer()

    user_id = query.from_user.id
    if prev := tasks.get(user_id):
        prev.cancel()

    await state.set_state(KnowPriceSG.waiting_for_query)

    prompt = await record_and_send(query, state, text="Введите название кроссовок:", reply_markup=back_menu)
    await query.message.delete()

    await state.update_data(prompt_id=prompt.message_id)


@router.message(KnowPriceSG.waiting_for_query)
@is_sub
async def know_button_query(message: Message, state: FSMContext):
    data = await state.get_data()

    q = message.text.strip().lower()
    user_id = message.from_user.id
    prompt_id = data.get("prompt_id")

    if prompt_id:
        try:
            await bot.delete_message(message.chat.id, prompt_id)
        except TelegramBadRequest:
            pass

    await state.clear()

    if prev := tasks.get(user_id):
        prev.cancel()

    task = asyncio.create_task(
        process_price_search(user_id, message, state, q)
    )
    tasks[user_id] = task

    if prompt := data.get("prompt_id"):
        try:
            await bot.delete_message(message.chat.id, prompt)
        except:
            pass

    try:
        await message.delete()
    except:
        pass
