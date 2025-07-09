import asyncio

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from sneaker_bot.dependencies import dp
from sneaker_bot.main import process_news_flow
from sneaker_bot.sub_checker import is_sub
from sneaker_bot.tasks import tasks


@dp.callback_query(lambda c: c.data == "news_button")
@is_sub
async def search_news_button(query: CallbackQuery, state: FSMContext):
    await query.answer()

    user_id = query.from_user.id

    if prev := tasks.get(user_id):
        prev.cancel()

    async def runner():
        try:
            await process_news_flow(query, state)
        finally:
            tasks.pop(user_id, None)

    task = asyncio.create_task(runner())
    tasks[user_id] = task