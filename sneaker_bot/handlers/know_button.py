import asyncio
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message

from sneaker_bot.menu.back_menu import back_menu
from sneaker_bot.parsers.price_parser import process_price_search
from sneaker_bot.services.send_messages import record_and_send, send_prompt
from sneaker_bot.services.utils import delete_last_prompt_on_reply
from sneaker_bot.setting import bot
from sneaker_bot.sub_checker import is_sub
from sneaker_bot.tasks import tasks


class KnowPriceSG(StatesGroup):
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_size = State()


router = Router()


@router.callback_query(lambda c: c.data == "know_button")
@is_sub
async def search_know_button(query: CallbackQuery, state: FSMContext):
    # подтверждаем нажатие сразу
    try:
        await query.answer(cache_time=2)
    except TelegramBadRequest:
        pass

    user_id = query.from_user.id
    if prev := tasks.get(user_id):
        prev.cancel()

    await state.set_state(KnowPriceSG.waiting_for_brand)

    # отправляем подсказку как prompt (send_prompt) — будет сохранена в prompt_refs
    prompt = await send_prompt(
        query,
        state,
        text="👇Введите бренд кроссовок (например, Adidas, Nike):👇",
        reply_markup=back_menu
    )

    try:
        await query.message.delete()
    except TelegramBadRequest:
        pass

    # опционально сохраняем id подсказки в state, но send_prompt уже добавил в prompt_refs
    await state.update_data(prompt_id=prompt.message_id)


@router.message(KnowPriceSG.waiting_for_brand)
@is_sub
async def know_button_brand(message: Message, state: FSMContext):
    # удаляем предыдущую подсказку (тот самый "Введите бренд")
    await delete_last_prompt_on_reply(state, message.bot, message.chat.id)

    brand = message.text.strip().lower()
    await state.update_data(brand=brand)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await state.set_state(KnowPriceSG.waiting_for_model)

    # отправляем следующую подсказку как prompt
    await send_prompt(
        message,
        state,
        text="👇Введите название модели (например, Superstar, Air Max).\n"
             "Или напишите 'Посмотреть все', чтобы показать все модели бренда:👇",
        reply_markup=back_menu
    )


@router.message(KnowPriceSG.waiting_for_model)
@is_sub
async def know_button_model(message: Message, state: FSMContext):
    # удаляем предыдущую подсказку "Введите модель"
    await delete_last_prompt_on_reply(state, message.bot, message.chat.id)

    model = message.text.strip().lower()

    if model == "посмотреть все":
        await state.update_data(model="")  # пустая модель
    else:
        await state.update_data(model=model)

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await state.set_state(KnowPriceSG.waiting_for_size)

    # отправляем подсказку для размера как prompt
    await send_prompt(
        message,
        state,
        text="👇Введите размер (например, 42). Если не важно — напишите 'нет':👇",
        reply_markup=back_menu
    )


@router.message(KnowPriceSG.waiting_for_size)
@is_sub
async def know_button_size(message: Message, state: FSMContext):
    # удаляем предыдущую подсказку "Введите размер"
    await delete_last_prompt_on_reply(state, message.bot, message.chat.id)

    size = message.text.strip().lower()
    data = await state.get_data()

    brand = data.get("brand", "")
    model = data.get("model", "")
    user_id = message.from_user.id

    # формируем запрос: бренд + модель + размер (если указан)
    q = brand
    if model:
        q += f" {model}"
    if size != "нет":
        q += f" {size}"

    await state.clear()

    if prev := tasks.get(user_id):
        prev.cancel()

    # запускаем поиск в фоне
    task = asyncio.create_task(
        process_price_search(user_id, message, state, q)
    )
    tasks[user_id] = task

    try:
        await message.delete()
    except TelegramBadRequest:
        pass
