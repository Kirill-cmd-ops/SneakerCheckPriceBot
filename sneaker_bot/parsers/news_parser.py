import asyncio
import os
import time
from calendar import timegm
from typing import List
from dotenv import load_dotenv

import aiohttp
import feedparser


load_dotenv()
LAST_HOURS = int(os.getenv("LAST_HOURS"))
MAX_PAGES = int(os.getenv("MAX_PAGES"))
NEWS_URL = os.getenv("NEWS_URL")


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