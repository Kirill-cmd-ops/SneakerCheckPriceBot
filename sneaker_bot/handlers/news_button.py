import asyncio

from aiogram import Router

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from sneaker_bot.menu.watching_news_menu import RssCb, make_nav_kb
from sneaker_bot.services.process_news_flow import process_news_flow
from sneaker_bot.services.send_head_menu import send_head_menu
from sneaker_bot.services.send_messages import record_and_send
from sneaker_bot.sub_checker import is_sub
from sneaker_bot.tasks import tasks


router = Router()

@router.callback_query(lambda c: c.data == "news_button")
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


@router.callback_query(RssCb.filter())
async def news_nav(query: CallbackQuery, callback_data: RssCb, state: FSMContext):
    await query.answer()
    data = await state.get_data()
    entries = data.get("rss_entries", [])
    idx = callback_data.idx

    if not entries or not (0 <= idx < len(entries)):
        return await record_and_send(query, state, text="Ошибка навигации по новостям.")

    entry = entries[idx]
    kb = make_nav_kb(idx, len(entries) - 1)
    await query.message.edit_text(
        f"<b>{entry.title}</b>\n{entry.link}",
        reply_markup=kb
    )


@router.callback_query(lambda c: c.data == "close_news")
async def close_news_button(query: CallbackQuery, state: FSMContext):
    await query.answer()
    sent = await send_head_menu(
        query,
        state,
        text="📩Выберите дальнейшее действие:📩",
    )
    await state.update_data(menu_msg_id=sent.message_id)
    await query.message.delete()