import os
import time
import asyncio
from urllib.parse import urlparse, parse_qs

import aiohttp
import feedparser
from calendar import timegm
from typing import List, Union

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from functools import wraps

from aiogram.filters.callback_data import CallbackData
from aiogram import Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

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

tasks: dict[int, asyncio.Task] = {}


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

know_menu = back_menu

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()


async def checker(bot: Bot, user_id: int) -> bool:
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

        if not await checker(bot, user_id):
            return await query.answer(
                "Чтобы пользоваться, подпишись на канал",
                show_alert=True,
            )

        return await func(*args, **kwargs)

    return wrapper


async def reply_and_store(
        ctx: Union[Message, CallbackQuery],
        state: FSMContext,
        text: str,
        **kwargs
) -> Message:
    if isinstance(ctx, CallbackQuery):
        await ctx.answer()
        sent = await ctx.message.answer(text, **kwargs)
    else:
        sent = await ctx.answer(text, **kwargs)

    data = await state.get_data()
    msg_ids = data.get("msg_ids", [])
    msg_ids.append(sent.message_id)
    await state.update_data(msg_ids=msg_ids)

    return sent


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

    try:
        await bot.delete_message(chat_id, message.message_id)
    except:
        pass

    await state.clear()

    if not await checker(bot, user_id):
        sent = await reply_and_store(
            message,
            state,
            text="Чтобы пользоваться, подпишись на канал",
            reply_markup=sub_menu,
        )
    else:
        sent = await reply_and_store(
            message,
            state,
            text="Выберите дальнейшее действие:",
            reply_markup=head_menu
        )

    await state.update_data(menu_msg_id=sent.message_id)


@dp.callback_query(lambda c: c.data == "check_button")
@is_sub
async def check_button(query: CallbackQuery, state: CallbackQuery):
    await query.answer()
    await reply_and_store(
        query,
        state,
        text="""
        Привет, спасибо за подписку на канал!
Тут будет публиковаться полезная и интересная информация
Выберите действие:
        """,
        reply_markup=head_menu
    )


class KnowPriceSG(StatesGroup):
    waiting_for_query = State()


@dp.callback_query(lambda c: c.data == "know_button")
@is_sub
async def know_button_start(query: CallbackQuery, state: FSMContext):
    await query.answer()
    await query.message.delete()

    user_id = query.from_user.id
    if prev := tasks.get(user_id):
        prev.cancel()

    await state.set_state(KnowPriceSG.waiting_for_query)

    prompt = await reply_and_store(
        query, state,
        text="Введите название кроссовок:",
        reply_markup=back_menu
    )
    await state.update_data(prompt_id=prompt.message_id)


def build_result_text(fb: dict, fs: dict) -> str:
    parts = []
    shops = [
        ("bunt.by", fb, {"muzhskie": "Мужские", "zhenskie": "Женские"}),
        ("sneakers.by", fs, {"мужские": "Мужские", "женские": "Женские"})
    ]

    for shop_name, data_dict, caps in shops:
        total_found = sum(len(data_dict.get(k, [])) for k in data_dict)

        if total_found == 0:
            parts.append(f"<b>Магазин:</b> {shop_name}")
            parts.append("— Товар не найден.")
            parts.append("")
            continue

        parts.append(f"<b>Магазин:</b> {shop_name}")
        parts.append("")
        for key, title in caps.items():
            items = data_dict.get(key, [])
            if not items:
                continue

            parts.append(f"<b>{title}</b>")
            for idx, (t, price, url) in enumerate(items, start=1):
                parts.append(
                    f"{idx}. {t}\n"
                    f"   Цена: <code>{price}</code>\n"
                    f"   <a href=\"{url}\">Ссылка</a>"
                )
            parts.append("")

        parts.append("")

    return "\n".join(parts).strip()


async def process_price_search(
        user_id: int,
        query_ctx: CallbackQuery,
        state: FSMContext,
        q: str
):
    try:
        load_msg = await reply_and_store(
            query_ctx, state,
            text="Ищем указанную модель кроссовок и схожие модели…"
        )

        raw_bunt = {"muzhskie": [], "zhenskie": []}
        raw_sneaker = {"женские": [], "мужские": []}

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            # bunt.by
            for url in CATALOGS:
                key = "muzhskie" if "muzhskie" in url else "zhenskie"
                r = await session.get(url + "/")
                if r.status != 200:
                    continue
                soup = BeautifulSoup(await r.text(), "lxml")
                nxt = soup.select_one('a.pagination__link[href*="/page/1/"]')
                sid = ""
                if nxt:
                    pr = urlparse(nxt["href"])
                    sid = parse_qs(pr.query).get("srsltid", [""])[0]

                def parse1(sp):
                    for a in sp.select("a.product-title-link"):
                        t = a.get_text(strip=True)
                        if q in t.lower():
                            h = a["href"]
                            full = h if h.startswith("http") else BASE + h
                            raw_bunt[key].append((t, full))
                            if len(raw_bunt[key]) >= PER_CAT:
                                return True
                    return False

                done = parse1(soup)
                for p in range(2, MAX_PAGES_BUNT + 1):
                    if done or len(raw_bunt[key]) >= PER_CAT:
                        break
                    u = f"{url}/page/{p}/" + (f"?srsltid={sid}" if sid else "")
                    rr = await session.get(u)
                    if rr.status != 200:
                        break
                    done = parse1(BeautifulSoup(await rr.text(), "lxml"))

            # sneakers.by
            for kind, base in SNEAKERS.items():
                for p in range(1, MAX_PAGES_SNEAK + 1):
                    if len(raw_sneaker[kind]) >= PER_CAT:
                        break
                    u = f"{base}?page={p}"
                    r = await session.get(u)
                    if r.status != 200:
                        break
                    sp = BeautifulSoup(await r.text(), "lxml")
                    for a in sp.select("a[href*='/katalog/obuv-belarus/']:not(.pagination__link)"):
                        t = a.get_text(strip=True)
                        if q in t.lower():
                            h = a["href"]
                            full = h if h.startswith("http") else a.base_url + h
                            raw_sneaker[kind].append((t, full))
                            if len(raw_sneaker[kind]) >= PER_CAT:
                                break

            async def price_b(item):
                t, u = item
                try:
                    rr = await session.get(u)
                    rr.raise_for_status()
                    ds = BeautifulSoup(await rr.text(), "lxml")
                    pe = ds.select_one("div.product_after_shop_loop_price span.price")
                    return t, pe.get_text(" ", strip=True) if pe else "—", u
                except:
                    return t, "ошибка", u

            async def price_s(item):
                t, u = item
                try:
                    rr = await session.get(u)
                    rr.raise_for_status()
                    ds = BeautifulSoup(await rr.text(), "lxml")
                    pe = ds.select_one("p.price")
                    return t, pe.get_text(" ", strip=True) if pe else "—", u
                except:
                    return t, "ошибка", u

            fb = {
                k: await asyncio.gather(*[price_b(i) for i in v])
                for k, v in raw_bunt.items()
            }
            fs = {
                k: await asyncio.gather(*[price_s(i) for i in v])
                for k, v in raw_sneaker.items()
            }

        try:
            await load_msg.delete()
        except TelegramBadRequest:
            pass

        text = build_result_text(fb, fs)

        await reply_and_store(
            query_ctx, state,
            text=text,
            reply_markup=know_menu,
            disable_web_page_preview=True
        )

    except asyncio.CancelledError:
        return

    finally:
        tasks.pop(user_id, None)


@dp.message(KnowPriceSG.waiting_for_query)
@is_sub
async def know_button_query(message: Message, state: FSMContext):
    data = await state.get_data()
    if prompt := data.get("prompt_id"):
        try:
            await bot.delete_message(message.chat.id, prompt)
        except:
            pass

    try:
        await message.delete()
    except:
        pass

    q = message.text.strip().lower()
    user_id = message.from_user.id

    if prev := tasks.get(user_id):
        prev.cancel()

    task = asyncio.create_task(
        process_price_search(user_id, message, state, q)
    )
    tasks[user_id] = task


@dp.message()
async def default_command(message: Message):
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
async def back_main_button(query: CallbackQuery, state: CallbackQuery):
    await query.answer()
    await query.message.delete()
    await reply_and_store(
        query,
        state,
        text="Выберите дальнейшее действие:",
        reply_markup=head_menu
    )


async def process_news_flow(query: CallbackQuery, state: FSMContext):
    chat_id = query.from_user.id
    try:
        load_msg = await reply_and_store(
            query, state,
            text="Ищем интересные новости..."
        )

        entries = await fetch_entries_last_day()

        try:
            await load_msg.delete()
        except TelegramBadRequest:
            pass

        if not entries:
            await reply_and_store(
                query, state,
                text="За последние сутки новостей не найдено."
            )
            return

        await state.update_data(rss_entries=entries, rss_index=0)
        entry = entries[0]
        kb = make_nav_kb(0, len(entries) - 1)
        await reply_and_store(
            query, state,
            text=f"<b>{entry.title}</b>\n{entry.link}",
            reply_markup=kb
        )

    except asyncio.CancelledError:
        return

    finally:
        tasks.pop(chat_id, None)


@dp.callback_query(lambda c: c.data == "news_button")
@is_sub
async def news_start(query: CallbackQuery, state: FSMContext):
    await query.answer()
    await query.message.delete()

    user_id = query.from_user.id

    if prev := tasks.get(user_id):
        prev.cancel()

    task = asyncio.create_task(process_news_flow(query, state))
    tasks[user_id] = task


@dp.callback_query(RssCb.filter())
async def news_nav(query: CallbackQuery, callback_data: RssCb, state: FSMContext):
    await query.answer()
    data = await state.get_data()
    entries = data.get("rss_entries", [])
    idx = callback_data.idx

    if not entries or not (0 <= idx < len(entries)):
        return await reply_and_store(
            query,
            state,
            text="Ошибка навигации по новостям."
        )

    entry = entries[idx]
    kb = make_nav_kb(idx, len(entries) - 1)
    await query.message.edit_text(
        f"<b>{entry.title}</b>\n{entry.link}",
        reply_markup=kb
    )


@dp.callback_query(lambda c: c.data == "close_news")
async def close_news(query: CallbackQuery, state: FSMContext):
    await query.answer()
    await query.message.delete()

    sent = await reply_and_store(
        query,
        state,
        text="Выберите дальнейшее действие:",
        reply_markup=head_menu
    )
    await state.update_data(menu_msg_id=sent.message_id)


async def main():
    await set_commands(bot)
    await dp.start_polling(bot, skip_updates=False)


if __name__ == '__main__':
    asyncio.run(main())
