import os
import time
import asyncio
from urllib.parse import urlparse, parse_qs

import aiohttp
import feedparser
from calendar import timegm
from typing import List

from aiogram.fsm.state import State, StatesGroup
from bs4 import BeautifulSoup
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
            text="Выберите действие:",
            reply_markup=head_menu
        )

    await state.update_data(menu_msg_id=sent.message_id)


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
async def know_button_start(query: CallbackQuery, state: FSMContext):
    await query.answer()
    await query.message.delete()
    await state.set_state(KnowPriceSG.waiting_for_query)
    await bot.send_message(query.from_user.id, "Введите часть названия кроссовок:", reply_markup=back_menu)


@dp.message(KnowPriceSG.waiting_for_query)
async def know_button_query(message: Message, state: FSMContext):
    q = message.text.strip().lower()
    loading = await message.answer("Ищем…")
    raw_bunt = {"muzhskie": [], "zhenskie": []}
    raw_snk = {"женские": [], "мужские": []}

    async with aiohttp.ClientSession(headers=HEADERS) as s:
        # bunt.by
        for url0 in CATALOGS:
            key = "muzhskie" if "muzhskie" in url0 else "zhenskie"
            r = await s.get(url0 + "/")
            if r.status != 200: continue
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
                        if len(raw_bunt[key]) >= PER_CAT: return True
                return False

            done = parse1(soup)
            for p in range(2, MAX_PAGES_BUNT + 1):
                if done or len(raw_bunt[key]) >= PER_CAT: break
                u = f"{url0}/page/{p}/"
                if sid: u += f"?srsltid={sid}"
                rr = await s.get(u)
                if rr.status != 200: break
                done = parse1(BeautifulSoup(await rr.text(), "lxml"))

        # sneakers.by
        for kind, base in SNEAKERS.items():
            for p in range(1, MAX_PAGES_SNEAK + 1):
                if len(raw_snk[kind]) >= PER_CAT: break
                u = f"{base}?page={p}"
                r = await s.get(u)
                if r.status != 200: break
                sp = BeautifulSoup(await r.text(), "lxml")
                for a in sp.select("a[href*='/katalog/obuv-belarus/']:not(.pagination__link)"):
                    t = a.get_text(strip=True)
                    if q in t.lower():
                        h = a["href"]
                        full = h if h.startswith("http") else a.base_url + h
                        raw_snk[kind].append((t, full))
                        if len(raw_snk[kind]) >= PER_CAT: break

        async def price_b(item):
            t, u = item
            try:
                r = await s.get(u);
                r.raise_for_status()
                ds = BeautifulSoup(await r.text(), "lxml")
                pe = ds.select_one("div.product_after_shop_loop_price span.price")
                return t, pe.get_text(" ", strip=True) if pe else "—", u
            except:
                return t, "ошибка", u

        async def price_s(item):
            t, u = item
            try:
                r = await s.get(u);
                r.raise_for_status()
                ds = BeautifulSoup(await r.text(), "lxml")
                pe = ds.select_one("p.price")
                return t, pe.get_text(" ", strip=True) if pe else "—", u
            except:
                return t, "ошибка", u

        fb = {k: await asyncio.gather(*[price_b(i) for i in v]) for k, v in raw_bunt.items()}
        fs = {k: await asyncio.gather(*[price_s(i) for i in v]) for k, v in raw_snk.items()}

    await loading.delete()
    parts = []
    for shop, data, caps in [
        ("bunt.by", fb, {"muzhskie": "Мужские", "zhenskie": "Женские"}),
        ("sneakers.by", fs, {"мужские": "Мужские", "женские": "Женские"})
    ]:
        parts.append(f"<b>Магазин:</b> {shop}");
        parts.append("")
        for k, cap in caps.items():
            blk = data.get(k, [])
            if not blk: continue
            parts.append(f"<b>{cap}</b>")
            for i, (t, p, u) in enumerate(blk, 1):
                parts.append(f"{i}. {t}\n   Цена: <code>{p}</code>\n   <a href=\"{u}\">Ссылка</a>")
            parts.append("")

    text = "\n".join(parts).strip()
    await message.answer(text or "Ничего не найдено.", reply_markup=know_menu, disable_web_page_preview=True)
    await state.clear()


@dp.callback_query(lambda c: c.data == "back_main")
async def back_main(query: CallbackQuery, state: FSMContext):
    await query.answer()
    await state.clear()
    await query.message.edit_text("Выберите действие:", reply_markup=head_menu)


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
        text="Выберите действие:",
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

    sent = await query.message.answer(
        text="Выберите действие:",
        reply_markup=head_menu
    )
    await state.update_data(menu_msg_id=sent.message_id)


async def main():
    await dp.start_polling(bot, skip_updates=False)


if __name__ == '__main__':
    asyncio.run(main())
