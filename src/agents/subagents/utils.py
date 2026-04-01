import logging
import mimetypes
import os
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from langchain.messages import AIMessage
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from ...core.constants import ALLOWED_EXT
from ...core.depends import (
    text_splitter,
    yandex_gpt,
)
from ...settings import settings
from ...utils.layout_structure import find_seo_issues
from ...utils.web_parser import get_html_content, get_markdown_content

logger = logging.getLogger(__name__)


async def get_mime(url: str, data: bytes) -> str:
    """Определяет MIME-тип изображения по URL и содержимому."""
    mime_type, _ = mimetypes.guess_type(url)
    if mime_type:
        return mime_type

    # Проверка сигнатур
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    # Неизвестный тип
    raise ValueError(f"Не удалось определить MIME-тип для {url}")


def is_image(url):
    path = urlparse(url).path
    path = unquote(path)
    ext = os.path.splitext(path)[1].lower()
    return ext in ALLOWED_EXT


async def count_tokens_with_ai_message(request: str, result: AIMessage) -> int:
    count_request = yandex_gpt.get_num_tokens(request)
    count_result = yandex_gpt.get_num_tokens(str(result.content))
    return count_request + count_result


async def count_tokens(request: str, result: str) -> int:
    count_request = yandex_gpt.get_num_tokens(request)
    count_result = yandex_gpt.get_num_tokens(result)
    return count_request + count_result


async def get_seo_issues(html: str) -> list:
    bs = BeautifulSoup(html, "html.parser")
    issue = find_seo_issues(bs)
    result: list = []
    for i in issue:
        if isinstance(i, tuple):
            result.append(i[0].model_dump())
        else:
            result.append(i.model_dump())

    return result


async def parce_site_markups(url: str) -> tuple:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect(ws_endpoint=settings.chromium_ws_endpoint)
        try:
            markdown = await get_markdown_content(browser, url)
            html = await get_html_content(browser, url)
            splited_markdown = text_splitter.split_text(markdown)
        except PlaywrightTimeoutError:
            # Fallback в случае неудачного ожидания загрузки страницы
            logger.warning(
                "Fallback networkidle timeout for `%s` page, using domcontentloaded", url
            )

        splited_markdown = text_splitter.split_text(markdown)
        return splited_markdown, html
