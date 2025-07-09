import os
import asyncio

from typing import Union, TYPE_CHECKING

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

from aiogram.filters.callback_data import CallbackData
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from sneaker_bot.parsers.news_parser import fetch_entries_last_day
from sneaker_bot.parsers.price_parser import process_price_search
from sneaker_bot.startup import set_commands
from tasks import tasks
from dependencies import record_and_send, bot, dp

from sneaker_bot.menu.back_menu import back_menu
from sneaker_bot.menu.sub_menu import sub_menu
from sneaker_bot.menu.head_menu import head_menu

from sub_checker import checker_sub, is_sub

if TYPE_CHECKING:
    from aiogram import Bot


from handlers import router as main_router

dp.include_router(main_router)

load_dotenv()
BOT_TOKEN = os.getenv("SECRET_TOKEN_BOT")
ID_CHANNEL = os.getenv("ID_CHANNEL")
NEWS_URL = os.getenv("NEWS_URL")
MAX_PAGES = int(os.getenv("MAX_PAGES"))
LAST_HOURS = int(os.getenv("LAST_HOURS"))
BASE = os.getenv("BASE_URL")
CATALOGS = [
    BASE + os.getenv("CATALOG_MEN_PATH"),
    BASE + os.getenv("CATALOG_WOMEN_PATH"),
]
SNEAKERS = {
    "женские": os.getenv("SNEAKERS_WOMEN_URL"),
    "мужские": os.getenv("SNEAKERS_MEN_URL"),
}
HEADERS = {
    "User-Agent": os.getenv("USER_AGENT")
}
MAX_PAGES_BUNT = int(os.getenv("MAX_PAGES_BUNT", 1))
MAX_PAGES_SNEAK = int(os.getenv("MAX_PAGES_SNEAK", 1))
PER_CAT = int(os.getenv("PER_CAT", 5))


async def send_head_menu(
        source: Union[Message, CallbackQuery],
        state,
        text):
    return await record_and_send(source, state, text, reply_markup=head_menu)


@dp.callback_query(lambda c: c.data == "order_button")
@is_sub
async def order_button(query: CallbackQuery):
    await query.answer(
        text="В будущем тут будет ссылка на наш сайт",
        show_alert=True,
    )
    await query.answer()


class RssCb(CallbackData, prefix="rss"):
    idx: int


def make_nav_kb(idx: int, max_idx: int) -> InlineKeyboardMarkup:
    buttons = []
    if idx > 0:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=RssCb(idx=idx - 1).pack()
            )
        )
    buttons.append(
        InlineKeyboardButton(
            text="Закрыть",
            callback_data="close_news"
        )
    )
    if idx < max_idx:
        buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=RssCb(idx=idx + 1).pack()
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


@dp.callback_query(lambda c: c.data == "back_main")
async def back_head_main_button(query: CallbackQuery, state: CallbackQuery):
    await query.answer()
    await send_head_menu(
        query,
        state,
        text="Выберите дальнейшее действие:"
    )
    await query.message.delete()


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


@dp.callback_query(RssCb.filter())
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


@dp.callback_query(lambda c: c.data == "close_news")
async def close_news_button(query: CallbackQuery, state: FSMContext):
    await query.answer()
    sent = await send_head_menu(
        query,
        state,
        text="Выберите дальнейшее действие:",
    )
    await state.update_data(menu_msg_id=sent.message_id)
    await query.message.delete()


async def main():
    await set_commands(bot)
    await dp.start_polling(bot, skip_updates=False)


if __name__ == '__main__':
    asyncio.run(main())
