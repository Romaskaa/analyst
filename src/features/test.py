import asyncio
import base64
import mimetypes
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
from langchain_core.messages import HumanMessage
from playwright.async_api import async_playwright

from ..agents.prompts import PROMPT_GENERATE_ALT
from ..core.depends import gemma_3_27b_it, parser_generated_alt
from ..utils.web_parser import get_html_content

# Константы для настройки
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)  # таймаут 30 секунд
BATCH_SIZE = 3  # размер батча для генерации alt


async def get_images(url: str) -> list[str]:
    """Извлекает все ссылки на изображения со страницы, у которых отсутствует alt."""
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
            # Попытка найти базовый URL в теге <base>
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            all_images = soup.find_all("img")
            links: list[str] = []
            for img in all_images:
                alt = img.get("alt", "")
                src = img.get("src")
                if not src:
                    continue
                if alt == "":
                    # Преобразуем относительный URL в абсолютный
                    full_url: str = urljoin(base_url, src)  # type: ignore  # noqa: PGH003
                    links.append(full_url)
            return links
        finally:
            await browser.close()

