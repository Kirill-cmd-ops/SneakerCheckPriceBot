from urllib.parse import urlparse, parse_qs

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

import os
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from tasks import tasks
from dependencies import record_and_send, build_result_text
from sneaker_bot.menu.know_menu import know_menu


load_dotenv()
HEADERS = {
    "User-Agent": os.getenv("USER_AGENT")
}
PER_CAT = int(os.getenv("PER_CAT", 5))
BASE = os.getenv("BASE_URL")
CATALOGS = [
    BASE + os.getenv("CATALOG_MEN_PATH"),
    BASE + os.getenv("CATALOG_WOMEN_PATH"),
]
MAX_PAGES = int(os.getenv("MAX_PAGES"))
SNEAKERS = {
    "женские": os.getenv("SNEAKERS_WOMEN_URL"),
    "мужские": os.getenv("SNEAKERS_MEN_URL"),
}
MAX_PAGES_BUNT = int(os.getenv("MAX_PAGES_BUNT", 1))
MAX_PAGES_SNEAK = int(os.getenv("MAX_PAGES_SNEAK", 1))


async def process_price_search(
        user_id: int,
        query_ctx: CallbackQuery,
        state: FSMContext,
        q: str
):
    try:
        load_msg = await record_and_send(query_ctx, state, text="Ищем указанную модель кроссовок и схожие модели…")

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

        text = build_result_text(fb, fs)

        await record_and_send(query_ctx, state, text=text, reply_markup=know_menu, disable_web_page_preview=True)
        try:
            await load_msg.delete()
        except TelegramBadRequest:
            pass

    except asyncio.CancelledError:
        return

    finally:
        tasks.pop(user_id, None)
