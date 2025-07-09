import os
import asyncio

from typing import Union

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
from functools import wraps

from aiogram.filters.callback_data import CallbackData
from aiogram import Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from sneaker_bot.parsers.news_parser import fetch_entries_last_day
from sneaker_bot.parsers.price_parser import process_price_search
from tasks import tasks
from dependencies import record_and_send
from sneaker_bot.menu.back_menu import back_menu


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


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запуск бота")
    ]
    await bot.set_my_commands(commands)


sub_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Подписаться на канал",
                url="https://t.me/SneakerPriceCheck"
            )
        ],
        [
            InlineKeyboardButton(
                text="Проверить",
                callback_data="check_button"
            )
        ]
    ]
)

head_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Узнать цены",
                callback_data="know_button"
            ),
            InlineKeyboardButton(
                text="Новости",
                callback_data="news_button"
            )
        ],
        [
            InlineKeyboardButton(
                text="Заказать кроссовки",
                callback_data="order_button"
            )
        ],
        [
            InlineKeyboardButton(
                text="Помощь",
                url="tg://resolve?domain=SkForbes"
            )
        ],
    ]
)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()


async def checker_sub(bot: Bot, user_id: int) -> bool:
    member = await bot.get_chat_member(
        chat_id=ID_CHANNEL,
        user_id=user_id,
    )
    return member.status not in ("left", "kicked")


def is_sub(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        msg = None
        query = None
        for arg in args:
            if isinstance(arg, Message):
                msg = arg
            elif isinstance(arg, CallbackQuery):
                query = arg

        if query:
            user_id = query.from_user.id

        elif msg:
            user_id = msg.from_user.id

        else:
            return await func(*args, **kwargs)

        if not await checker_sub(bot, user_id):
            return await query.answer(
                "Чтобы пользоваться, подпишись на канал",
                show_alert=True,
            )

        return await func(*args, **kwargs)

    return wrapper


async def send_head_menu(
        source: Union[Message, CallbackQuery],
        state,
        text):
    return await record_and_send(source, state, text, reply_markup=head_menu)


@dp.message(Command("start"))
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


@dp.callback_query(lambda c: c.data == "check_button")
@is_sub
async def check_button(query: CallbackQuery, state: CallbackQuery):
    await query.answer()
    await record_and_send(query, state, text="""
            Привет, спасибо за подписку на канал!
    Тут будет публиковаться полезная и интересная информация
    Выберите действие:
            """)
    await query.message.delete()


class KnowPriceSG(StatesGroup):
    waiting_for_query = State()


@dp.callback_query(lambda c: c.data == "know_button")
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


@dp.message(KnowPriceSG.waiting_for_query)
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


@dp.message()
async def default_text(message: Message):
    try:
        await message.delete()
    except:
        pass


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
