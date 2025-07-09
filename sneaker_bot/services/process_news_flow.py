import asyncio

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from sneaker_bot.menu.watching_news_menu import make_nav_kb
from sneaker_bot.parsers.news_parser import fetch_entries_last_day
from sneaker_bot.services.send_messages import record_and_send
from sneaker_bot.tasks import tasks


async def process_news_flow(query: CallbackQuery, state: FSMContext):
    chat_id = query.from_user.id
    try:
        load_msg = await record_and_send(query, state, text="Ищем интересные новости...")

        menu_msg = query.message
        try:
            await menu_msg.delete()
        except TelegramBadRequest:
            pass

        entries = await fetch_entries_last_day()

        if not entries:
            await record_and_send(query, state, text="За последние сутки новостей не найдено.")
            return

        await state.update_data(rss_entries=entries, rss_index=0)
        entry = entries[0]
        kb = make_nav_kb(0, len(entries) - 1)
        await record_and_send(query, state, text=f"<b>{entry.title}</b>\n{entry.link}", reply_markup=kb)

        try:
            await load_msg.delete()
        except TelegramBadRequest:
            pass

    except asyncio.CancelledError:
        return

    finally:
        tasks.pop(chat_id, None)
