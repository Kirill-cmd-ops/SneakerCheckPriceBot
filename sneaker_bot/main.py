import os
import time
import asyncio
import aiohttp
import feedparser
from calendar import timegm
from typing import List
from dotenv import load_dotenv

from aiogram.filters.callback_data import CallbackData
from aiogram import Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

load_dotenv()
BOT_TOKEN = os.getenv("SECRET_TOKEN_BOT")
ID_CHANNEL = os.getenv("ID_CHANNEL")
NEWS_URL = os.getenv("NEWS_URL")
MAX_PAGES = int(os.getenv("MAX_PAGES"))
LAST_HOURS = int(os.getenv("LAST_HOURS"))

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
                text="Избранное",
                callback_data="favorite_button"
            )
        ],
        [
            InlineKeyboardButton(
                text="Новости",
                callback_data="news_button"
            ),
            InlineKeyboardButton(
                text="Помощь",
                url="tg://resolve?domain=SkForbes"
            )
        ],
        [
            InlineKeyboardButton(
                text="Заказать кроссовки",
                callback_data="order_button"
            )
        ]
    ]
)

back_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data="back_main"
            )
        ]
    ]
)

know_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Добавить в избранное",
                callback_data="back_main"
            )
        ],
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data="back_main"
            )
        ]
    ]
)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()


async def is_sub(bot: Bot, user_id: int) -> bool:
    member = await bot.get_chat_member(
        chat_id=ID_CHANNEL,
        user_id=user_id,
    )
    return member.status not in ("left", "kicked")


@dp.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id

    data = await state.get_data()
    old_menu_id = data.get("menu_msg_id")
    if old_menu_id:
        try:
            await bot.delete_message(message.chat.id, old_menu_id)
        except Exception:
            pass

    if not await is_sub(bot, user_id):
        sent = await message.answer(
            "Чтобы пользоваться, подпишись на канал",
            reply_markup=sub_menu,
        )
    else:
        sent = await message.answer(
            text="Выберите интересующий пункт меню:",
            reply_markup=head_menu
        )

    # 3) сохраняем ID этого меню в FSM
    await state.update_data(menu_msg_id=sent.message_id)


# проверка на подписку
@dp.callback_query(lambda c: c.data == "check_button")
async def check_button(query: CallbackQuery):
    if not await is_sub(bot, query.from_user.id):
        return await query.answer(
            text="Вы не подписаны на канал",
            show_alert=True,
        )
    await query.message.delete()
    await query.answer()
    await query.message.answer(
        text="Привет",
        reply_markup=head_menu
    )


# обработчик кнопки узнать цены
@dp.callback_query(lambda c: c.data == "know_button")
async def know_button(query: CallbackQuery):
    await query.message.delete()
    await query.answer()
    await query.message.answer(
        text="Узнаем цены..."
    )

    await query.message.answer(
        text="""
        Цены вашего товара:
        ...
        ...
        ...""",
        reply_markup=know_menu,
    )


# обработчик кнопки заказать кроссовки
@dp.callback_query(lambda c: c.data == "order_button")
async def order_button(query: CallbackQuery):
    await query.answer(
        text="В будущем тут будет ссылка на наш сайт",
        show_alert=True,
    )
    await query.answer()


class RssCb(CallbackData, prefix="rss"):
    idx: int


async def fetch_rss_page(session: aiohttp.ClientSession, page: int):
    url = NEWS_URL if page == 1 else f"{NEWS_URL}?paged={page}"
    async with session.get(url, timeout=5) as resp:
        if resp.status == 404:
            return []
        resp.raise_for_status()
        txt = await resp.text()
    return feedparser.parse(txt).entries


async def fetch_entries_last_day() -> List[feedparser.FeedParserDict]:
    cutoff_ts = time.time() - LAST_HOURS * 3600
    recent = []

    async with aiohttp.ClientSession() as session:
        for page in range(1, MAX_PAGES + 1):
            entries = await fetch_rss_page(session, page)
            if not entries:
                break

            for entry in entries:
                if not entry.get("published_parsed"):
                    continue
                ts = timegm(entry.published_parsed)
                if ts >= cutoff_ts:
                    recent.append(entry)
                else:
                    break
            else:
                await asyncio.sleep(1)
                continue
            break

    return recent


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
async def back_main_button(query: CallbackQuery):
    await query.answer()
    await query.message.answer(
        text="Выберите пункт меню:",
        reply_markup=head_menu
    )


@dp.callback_query(lambda c: c.data == "news_button")
async def news_start(query: CallbackQuery, state: FSMContext):
    await query.answer()
    load_msg = await query.message.answer("Ищем интересные новости...")
    entries = await fetch_entries_last_day()

    try:
        await load_msg.delete()
    except:
        pass

    if not entries:
        return await query.message.answer("За последние сутки новостей не найдено.")

    await state.update_data(rss_entries=entries)

    idx = 0
    entry = entries[idx]
    kb = make_nav_kb(idx, len(entries) - 1)
    await query.message.edit_text(
        f"<b>{entry.title}</b>\n{entry.link}",
        reply_markup=kb
    )


@dp.callback_query(RssCb.filter())
async def news_nav(query: CallbackQuery, callback_data: RssCb, state: FSMContext):
    await query.answer()
    data = await state.get_data()
    entries = data.get("rss_entries", [])
    idx = callback_data.idx

    if not entries or not (0 <= idx < len(entries)):
        return await query.message.answer("Ошибка навигации по новостям.")

    entry = entries[idx]
    kb = make_nav_kb(idx, len(entries) - 1)
    await query.message.edit_text(
        f"<b>{entry.title}</b>\n{entry.link}",
        reply_markup=kb
    )


@dp.callback_query(lambda c: c.data == "close_news")
async def close_news(query: CallbackQuery, state: FSMContext):
    await query.answer("Закрыто")
    await query.message.delete()

    # вернуть главное меню
    sent = await query.message.answer(
        text="Выберите пункт меню:",
        reply_markup=head_menu
    )
    await state.update_data(menu_msg_id=sent.message_id)


async def main():
    await dp.start_polling(bot, skip_updates=False)


if __name__ == '__main__':
    asyncio.run(main())
