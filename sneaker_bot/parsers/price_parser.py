import os
import re
import aiohttp
import asyncio
import random
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from sneaker_bot.menu.know_menu import know_menu
from sneaker_bot.services.build_text_parser_price import build_result_text
from sneaker_bot.services.send_messages import record_and_send, send_prompt
from sneaker_bot.tasks import tasks

load_dotenv()
router = Router()

# --- Настройки окружения ---
HEADERS = {"User-Agent": os.getenv("USER_AGENT", "Mozilla/5.0")}
PER_CAT = int(os.getenv("PER_CAT", 5))
BASE = os.getenv("BASE_URL", "")
CATALOGS = [
    urljoin(BASE, os.getenv("CATALOG_MEN_PATH", "")),
    urljoin(BASE, os.getenv("CATALOG_WOMEN_PATH", "")),
]
SNEAKERS = {
    "женские": os.getenv("SNEAKERS_WOMEN_URL", ""),
    "мужские": os.getenv("SNEAKERS_MEN_URL", ""),
}
MAX_PAGES_BUNT = int(os.getenv("MAX_PAGES_BUNT", 1))
MAX_PAGES_SNEAK = int(os.getenv("MAX_PAGES_SNEAK", 1))

SUCCESS_STICKERS = [
    "CAACAgIAAxkBAAEQAAE2aT7hurip0DwMapzkZIF1TGG5hqUAAqIBAAIWQmsKoXd3Y5pOgyE2BA",
]
FAIL_STICKERS = [
    "CAACAgIAAxkBAAEQAAE6aT7ixzphsIWAPUf6O9gnwMdsOdIAArEBAAIWQmsK_Er0l4LrkDE2BA",
]


# -----------------------
# Утилиты для работы с состоянием (prompt_refs, msg_refs, sticker_info)
# -----------------------
async def delete_last_prompt_on_reply(state: FSMContext, bot, chat_id: int) -> bool:
    """
    Удаляет последнюю подсказку из state['prompt_refs'].
    Возвращает True если удаление прошло успешно, False иначе.
    """
    data = await state.get_data()
    prompts = data.get("prompt_refs", [])
    if not prompts:
        return False

    last = prompts.pop()  # удаляем последний prompt
    await state.update_data(prompt_refs=prompts)

    try:
        await bot.delete_message(chat_id=last["chat_id"], message_id=last["message_id"])
        print("Deleted prompt:", last)
        return True
    except Exception as e:
        print("Failed to delete prompt:", last, e)
        return False


async def save_sticker_info(state: FSMContext, sticker_msg: Message):
    """Сохраняет информацию о стикере в state для последующего удаления по back."""
    await state.update_data(sticker_info={"chat_id": sticker_msg.chat.id, "message_id": sticker_msg.message_id})


async def delete_all_prompts_and_sticker(state: FSMContext, bot):
    """
    Удаляет все подсказки prompt_refs и стикер (sticker_info).
    Используется, например, при нажатии кнопки 'back' или при явной очистке.
    """
    data = await state.get_data()
    prompts = data.get("prompt_refs", [])
    sticker_info = data.get("sticker_info")

    for ref in prompts:
        try:
            await bot.delete_message(chat_id=ref["chat_id"], message_id=ref["message_id"])
            print("Deleted prompt:", ref)
        except Exception as e:
            print("Failed to delete prompt:", ref, e)

    if sticker_info:
        try:
            await bot.delete_message(chat_id=sticker_info["chat_id"], message_id=sticker_info["message_id"])
            print("Deleted sticker:", sticker_info)
        except Exception as e:
            print("Failed to delete sticker:", sticker_info, e)

    await state.update_data(prompt_refs=[])
    await state.update_data(sticker_info=None)


# -----------------------
# Парсинг (устойчивый)
# -----------------------
def normalize_price(text: str) -> str:
    if not text:
        return "—"
    m = re.search(r"(\d[\d\s.,]+)\s*(BYN|₽|RUB|USD|€)?", text, flags=re.IGNORECASE)
    if not m:
        return "—"
    amount = m.group(1).replace(",", ".").strip()
    currency = (m.group(2) or "").upper().replace("RUB", "₽")
    return f"{amount} {currency}".strip()


def extract_price(ds: BeautifulSoup) -> str:
    selectors = [
        "p.price",
        "span.price",
        "div.price",
        "div.product-price",
        "span.woocommerce-Price-amount",
        "ins .woocommerce-Price-amount",
        "meta[itemprop='price']",
        "[data-price]",
        "span[class*='cost']",
        "div[class*='price']",
    ]
    for sel in selectors:
        el = ds.select_one(sel)
        if not el:
            continue
        if el.name == "meta":
            return normalize_price(el.get("content", "").strip())
        if el.has_attr("data-price"):
            return normalize_price(el["data-price"])
        txt = el.get_text(" ", strip=True)
        price = normalize_price(txt)
        if price != "—":
            return price
    return normalize_price(ds.get_text(" ", strip=True))


def find_title_and_link(card, base: str):
    """
    Универсальная эвристика для названия и ссылки:
    1) явные <a> с текстом;
    2) img@alt;
    3) title/aria-label;
    4) h1/h2/h3/strong;
    5) data-* атрибуты.
    """
    # 1) явные ссылки с осмысленным текстом
    for a in card.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if text and len(text) >= 3 and not re.fullmatch(r"[\d\s\-]+", text):
            href = a["href"]
            full = urljoin(base, href)
            return text, full

    # 2) img alt
    img = card.find("img", alt=True)
    if img:
        alt = img.get("alt", "").strip()
        if alt and len(alt) >= 3 and not re.fullmatch(r"[\d\s\-]+", alt):
            parent_a = img.find_parent("a", href=True)
            href = parent_a["href"] if parent_a else img.get("data-src") or img.get("src")
            full = urljoin(base, href) if href else base
            return alt, full

    # 3) title / aria-label
    for el in (card.find_all(attrs={"title": True}) + card.find_all(attrs={"aria-label": True})):
        txt = el.get("title") or el.get("aria-label")
        if txt and len(txt.strip()) >= 3 and not re.fullmatch(r"[\d\s\-]+", txt.strip()):
            href = el.get("href") or el.get("data-href") or None
            full = urljoin(base, href) if href else base
            return txt.strip(), full

    # 4) заголовки внутри карточки
    for tag in ("h1", "h2", "h3", "h4", "strong"):
        h = card.select_one(tag)
        if h:
            txt = h.get_text(" ", strip=True)
            if txt and len(txt) >= 3 and not re.fullmatch(r"[\d\s\-]+", txt):
                a = h.find_parent().find("a", href=True) if h.find_parent() else None
                href = a["href"] if a else None
                full = urljoin(base, href) if href else base
                return txt, full

    # 5) data-* атрибуты
    for attr in ("data-name", "data-title", "data-product-name"):
        if card.has_attr(attr):
            txt = card[attr].strip()
            if txt and len(txt) >= 3:
                href = card.get("data-href") or card.get("data-url") or None
                full = urljoin(base, href) if href else base
                return txt, full

    return None


async def fetch_html(session: aiohttp.ClientSession, url: str) -> BeautifulSoup | None:
    try:
        r = await session.get(url, timeout=20, allow_redirects=True)
        if r.status != 200:
            print(f"HTTP {r.status} for {url}")
            return None
        html = await r.text()
        return BeautifulSoup(html, "lxml")
    except Exception as e:
        print(f"Ошибка запроса {url}: {e}")
        return None


# -----------------------
# Основная функция поиска цен
# -----------------------
async def process_price_search(user_id: int, query_ctx: CallbackQuery, state: FSMContext, q: str):
    try:
        temp_to_delete: list[dict] = []

        load_msg = await record_and_send(query_ctx, state, text="Ищем указанную модель кроссовок и схожие модели…")
        temp_to_delete.append({"chat_id": load_msg.chat.id, "message_id": load_msg.message_id})

        raw_bunt = {"muzhskie": [], "zhenskie": []}
        raw_sneaker = {"женские": [], "мужские": []}

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            # bunt.by
            for url in CATALOGS:
                if not url.strip():
                    continue
                key = "muzhskie" if "muzh" in url.lower() else "zhenskie"
                soup = await fetch_html(session, url)
                if soup is None:
                    continue

                cards = soup.select("div[class*='product'], li[class*='product'], article[class*='product']")
                if not cards:
                    cards = soup.select("div, li, article")

                print(f"bunt.by: найдено {len(cards)} карточек на {url}")

                # отладка: превью первой карточки
                if cards:
                    try:
                        print("=== Превью первой карточки (bunt.by) ===")
                        print(cards[0].prettify()[:1000])
                        print("=== Конец превью ===")
                    except Exception:
                        pass

                found_preview = 0
                for card in cards:
                    res = find_title_and_link(card, BASE or url)
                    if not res:
                        continue
                    t, full = res
                    if found_preview < 5:
                        print(f"[bunt.by] title: {t} | url: {full}")
                        found_preview += 1
                    if q and q.strip():
                        if q.lower() not in t.lower():
                            continue
                    raw_bunt[key].append((t, full))
                    if len(raw_bunt[key]) >= PER_CAT:
                        break

                # пагинация bunt.by
                for p in range(2, MAX_PAGES_BUNT + 1):
                    if len(raw_bunt[key]) >= PER_CAT:
                        break
                    next_url = urljoin(url, f"/page/{p}/")
                    sp = await fetch_html(session, next_url)
                    if sp is None:
                        break
                    cards_p = sp.select("div[class*='product'], li[class*='product'], article[class*='product']")
                    if not cards_p:
                        cards_p = sp.select("div, li, article")
                    for card in cards_p:
                        res = find_title_and_link(card, BASE or url)
                        if not res:
                            continue
                        t, full = res
                        if q and q.strip():
                            if q.lower() not in t.lower():
                                continue
                        raw_bunt[key].append((t, full))
                        if len(raw_bunt[key]) >= PER_CAT:
                            break

            # sneakers.by парсинг
            for kind, base in SNEAKERS.items():
                if not base.strip():
                    continue
                for p in range(1, MAX_PAGES_SNEAK + 1):
                    page_url = base if p == 1 else f"{base}?page={p}"
                    soup = await fetch_html(session, page_url)
                    if soup is None:
                        break
                    cards = soup.select("div[class*='product'], li[class*='product'], article[class*='product']")
                    if not cards:
                        cards = soup.select("div, li, article")
                    print(f"sneakers.by: найдено {len(cards)} карточек на {page_url}")
                    found_preview = 0
                    for card in cards:
                        res = find_title_and_link(card, BASE or base)
                        if not res:
                            continue
                        t, full = res
                        if found_preview < 5:
                            print(f"[sneakers.by] title: {t} | url: {full}")
                            found_preview += 1
                        if q and q.strip():
                            if q.lower() not in t.lower():
                                continue
                        raw_sneaker[kind].append((t, full))
                        if len(raw_sneaker[kind]) >= PER_CAT:
                            break
                    if len(raw_sneaker[kind]) >= PER_CAT:
                        break

            async def price_b(item):
                t, u = item
                try:
                    rr = await session.get(u, timeout=20)
                    rr.raise_for_status()
                    ds = BeautifulSoup(await rr.text(), "lxml")
                    price = extract_price(ds)
                    return t, price if price else "—", u
                except Exception as e:
                    print(f"Ошибка получения цены bunt.by: {e} | url: {u}")
                    return t, "ошибка", u

            async def price_s(item):
                t, u = item
                try:
                    rr = await session.get(u, timeout=20)
                    rr.raise_for_status()
                    ds = BeautifulSoup(await rr.text(), "lxml")
                    price = extract_price(ds)
                    return t, price if price else "—", u
                except Exception as e:
                    print(f"Ошибка получения цены sneakers.by: {e} | url: {u}")
                    return t, "ошибка", u

            fb = {k: await asyncio.gather(*[price_b(i) for i in v]) for k, v in raw_bunt.items()}
            fs = {k: await asyncio.gather(*[price_s(i) for i in v]) for k, v in raw_sneaker.items()}

        text = build_result_text(fb, fs)

        no_results = (
            text.strip() == "" or
            (all(len(v) == 0 for v in fb.values()) and all(len(v) == 0 for v in fs.values()))
        )

        # отправляем стикер и сохраняем его в state (чтобы удалить позже по back)
        sticker_id = random.choice(FAIL_STICKERS if no_results else SUCCESS_STICKERS)
        sticker_msg = await query_ctx.bot.send_sticker(chat_id=query_ctx.from_user.id, sticker=sticker_id)
        await save_sticker_info(state, sticker_msg)

        # итоговое сообщение через record_and_send (оно попадёт в state['msg_refs'])
        if no_results:
            await record_and_send(query_ctx, state, text="Ничего не найдено 😔", reply_markup=know_menu)
        else:
            await record_and_send(query_ctx, state, text=text, reply_markup=know_menu, disable_web_page_preview=True)

        # удаляем только временные сообщения (например load_msg)
        for m in temp_to_delete:
            try:
                await query_ctx.bot.delete_message(chat_id=m["chat_id"], message_id=m["message_id"])
            except TelegramBadRequest:
                pass

    except asyncio.CancelledError:
        return
    finally:
        tasks.pop(user_id, None)


# -----------------------
# Примеры хэндлеров ввода (интеграция delete_last_prompt_on_reply + send_prompt)
# -----------------------
# Примечание: эти примеры демонстрационные. Подставь свои фильтры/состояния.

@router.message(lambda m: m.text and m.text.lower() == "start_brand")
async def ask_brand(message: Message, state: FSMContext):
    # отправляем подсказку через send_prompt — она попадёт в state['prompt_refs']
    await send_prompt(message, state, "Введите название бренда")


@router.message(lambda m: m.text and m.text.strip() != "")
async def brand_received(message: Message, state: FSMContext):
    # удаляем предыдущую подсказку (тот самый "Введите бренд")
    await delete_last_prompt_on_reply(state, message.bot, message.chat.id)

    brand = message.text.strip()
    await state.update_data(brand=brand)

    # отправляем следующую подсказку через send_prompt
    await send_prompt(message, state, "Введите модель")


@router.message(lambda m: m.text and m.text.strip() != "")
async def model_received(message: Message, state: FSMContext):
    # удаляем предыдущую подсказку "Введите модель"
    await delete_last_prompt_on_reply(state, message.bot, message.chat.id)

    model = message.text.strip()
    await state.update_data(model=model)

    # отправляем подсказку для размера
    await send_prompt(message, state, "Введите размер")


@router.message(lambda m: m.text and m.text.strip() != "")
async def size_received(message: Message, state: FSMContext):
    # удаляем предыдущую подсказку "Введите размер"
    await delete_last_prompt_on_reply(state, message.bot, message.chat.id)

    size = message.text.strip()
    await state.update_data(size=size)

    # собираем запрос и запускаем поиск (пример)
    data = await state.get_data()
    query = " ".join(filter(None, [data.get("brand"), data.get("model"), data.get("size")]))
    await record_and_send(message, state, f"Запускаю поиск по: {query}")

    # Если у тебя есть CallbackQuery контекст для process_price_search, адаптируй вызов.
    # Здесь демонстрация: можно вызвать process_price_search через имитацию CallbackQuery,
    # либо вынести логику поиска в отдельную функцию, принимающую chat_id и state.
