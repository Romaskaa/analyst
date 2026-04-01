import json
import os
import pathlib
import sys
from asyncio import run, sleep
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from retry.conditions import stop_after_attempt
from retry.retry import Retry


from ..utils.web_parser import get_html_content



def normalize_url(url: str, base: str) -> str:
    # Если ссылка уже абсолютная, base не повлияет
    full = urljoin(base, url)
    # Удаляем фрагмент
    full, _ = urldefrag(full)

    # Убираем конечный слеш, кроме корня
    parsed = urlparse(full)
    if parsed.path.endswith("/") and parsed.path != "/":
        full = full.rstrip("/")
    return full


@Retry(stop_condition=stop_after_attempt(3))
async def get_links(url: str) -> list:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        try:
            html = await get_html_content(browser, url)
            soup = BeautifulSoup(html, "html.parser")
            all_links = soup.find_all("a")
            links: list = []
            for href in all_links:
                link = href.get("href", "")
                if link.find("/") != 0 or link == "/":  # type: ignore  # noqa: PGH003
                    continue
                links.append(link)
            return links

        finally:
            await browser.close()

links: list = []

for i in range(1,6):



