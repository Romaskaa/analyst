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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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


async def rekurs(
    start_url: str,
    urls: list[str],
    deep: int,
    base_url: str,
    data: list,
    passed_urls: set,
    count: int,
) -> list:
    print(f"Глубина: {deep}, URL-ов для обработки: {len(urls)}")
    if deep == 0:
        return data

    next_links = set()
    for url in urls:
        count += 1
        # Нормализуем текущий URL для проверки
        full_current = normalize_url(url, base_url)
        if full_current in passed_urls:
            continue
        passed_urls.add(full_current)

        await sleep(1.5)

        hrefs = await get_links(full_current)  # full_current уже абсолютный
        # Преобразуем найденные ссылки в абсолютные и нормализуем
        new_abs_links = {normalize_url(link, base_url) for link in hrefs if link}
        if (start_url in new_abs_links) and start_url != full_current:
            data.append({"url": url, "links": list(new_abs_links)})
            return data
        # Оставляем только те, которых ещё не было
        unique_new = new_abs_links - passed_urls

        data.append(
            {"url": url, "links": list(unique_new)}
        )  # сохраняем относительный исходный url или можно full_current
        next_links.update(unique_new)
    print(count)
    return await rekurs(
        start_url=start_url,
        urls=list(next_links),
        deep=deep - 1,
        base_url=base_url,
        data=data,
        passed_urls=passed_urls,
        count=count,
    )


async def orkestrator(url: str, base_url: str):
    hrefs = await get_links(url)  # full_current уже абсолютный
    # Преобразуем найденные ссылки в абсолютные и нормализуем
    new_abs_links = {normalize_url(link, base_url) for link in hrefs if link}


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


result = run(
    rekurs(
        start_url="https://arsplus.ru/catalog/oborudovanie_intel/optsiya_intel_raid_maintenance_free_backup_axxrmfbu4_/",
        urls=[
            "https://arsplus.ru/catalog/oborudovanie_intel/optsiya_intel_raid_maintenance_free_backup_axxrmfbu4_/"
        ],
        deep=4,
        base_url="https://arsplus.ru",
        data=[],
        passed_urls=set(),
        count=0,
    )
)

pathlib.Path("check1.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
