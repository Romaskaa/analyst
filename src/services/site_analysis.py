from __future__ import annotations

import re
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp
import matplotlib
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from ..utils.checkup import get_json_ld, get_llms_data, get_robots_data

matplotlib.use("Agg")
import matplotlib.pyplot as plt

CHARTS_DIR = Path("storage/charts")
SCREENSHOTS_DIR = Path("storage/screenshots")
CHARTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

STOPWORDS = {
    "http",
    "https",
    "www",
    "com",
    "ru",
    "для",
    "это",
    "как",
    "что",
    "или",
    "при",
    "под",
    "the",
    "and",
    "with",
    "from",
    "your",
    "наш",
    "ваш",
    "this",
    "that",
}


async def fetch_page(url: str) -> dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0 SEO-Analyst/1.0"}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        async with session.get(url, ssl=False, allow_redirects=True) as response:
            html = await response.text(errors="ignore")
            return {
                "url": str(response.url),
                "status": response.status,
                "html": html,
                "headers": dict(response.headers),
            }


async def head_request(url: str) -> int | None:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, ssl=False, allow_redirects=True) as response:
                await response.read()
                return response.status
        except aiohttp.ClientError:
            return None


def ensure_absolute_url(url: str) -> str:
    return url if url.startswith(("http://", "https://")) else f"https://{url}"


def visible_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return " ".join(soup.stripped_strings)


_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9-]{3,}")


def normalize_word(word: str) -> str:
    word = word.lower().strip("-_")
    for suffix in (
        "иями",
        "ями",
        "ами",
        "ого",
        "ему",
        "ому",
        "иях",
        "иях",
        "tion",
        "ing",
        "ость",
        "ение",
        "ировать",
        "овать",
        "ать",
        "ять",
        "ия",
        "ий",
        "ый",
        "ой",
        "ая",
        "ое",
        "ые",
        "ые",
        "ам",
        "ям",
        "ах",
        "ях",
        "ов",
        "ев",
        "ом",
        "ем",
        "es",
        "ed",
        "s",
    ):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def extract_keywords(text: str, limit: int = 20) -> list[dict[str, Any]]:
    words = [normalize_word(match.group()) for match in _WORD_RE.finditer(text)]
    filtered = [word for word in words if word not in STOPWORDS and len(word) >= 3]
    total = max(len(filtered), 1)
    counts = Counter(filtered)
    return [
        {
            "keyword": keyword,
            "count": count,
            "density": round(count / total * 100, 2),
        }
        for keyword, count in counts.most_common(limit)
    ]


def cluster_keywords(keywords: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clusters: dict[str, list[str]] = defaultdict(list)
    for item in keywords:
        key = item["keyword"][:5]
        clusters[key].append(item["keyword"])
    result = []
    for root, words in sorted(clusters.items(), key=lambda item: len(item[1]), reverse=True):
        result.append({"cluster": root, "keywords": sorted(set(words))})
    return result


def _save_bar_chart(title: str, labels: list[str], values: list[float], filename: str) -> str:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(labels, values, color="#4F46E5")
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    path = CHARTS_DIR / filename
    fig.savefig(path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def build_semantic_visualizations(keywords: list[dict[str, Any]], score_breakdown: dict[str, int]) -> dict[str, str]:
    keyword_labels = [item["keyword"] for item in keywords[:10]]
    keyword_values = [item["count"] for item in keywords[:10]]
    score_labels = list(score_breakdown.keys())
    score_values = list(score_breakdown.values())
    return {
        "keywords_chart": _save_bar_chart(
            "Топ ключевых слов страницы", keyword_labels, keyword_values, "semantic_keywords.png"
        ),
        "quality_chart": _save_bar_chart(
            "Качество оптимизации", score_labels, score_values, "semantic_quality.png"
        ),
    }


def _title_description_h1(soup: BeautifulSoup) -> tuple[str, str, str]:
    title = soup.title.get_text(strip=True) if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content", "").strip() if description_tag else ""
    h1 = soup.find("h1")
    h1_text = h1.get_text(strip=True) if h1 else ""
    return title, description, h1_text


def generate_json_ld_stub(url: str, soup: BeautifulSoup) -> dict[str, Any]:
    title, description, _ = _title_description_h1(soup)
    page_type = "Article" if soup.find("article") else "WebPage"
    return {
        "@context": "https://schema.org",
        "@type": page_type,
        "url": url,
        "name": title or urlparse(url).netloc,
        "description": description,
    }


def score_semantic_optimization(soup: BeautifulSoup, keywords: list[dict[str, Any]]) -> dict[str, int]:
    title, description, h1 = _title_description_h1(soup)
    top_keywords = {item["keyword"] for item in keywords[:5]}
    checks = {
        "title": 100 if title else 30,
        "description": 100 if description else 30,
        "h1": 100 if h1 else 20,
        "keywords": 90 if top_keywords else 20,
        "structured_data": 100 if get_json_ld(str(soup)) else 35,
    }
    return checks


def semantic_recommendations(soup: BeautifulSoup, keywords: list[dict[str, Any]]) -> list[dict[str, Any]]:
    title, description, h1 = _title_description_h1(soup)
    issues: list[dict[str, Any]] = []
    if not title:
        issues.append(
            {
                "problem": "Отсутствует title",
                "recommendation": "Добавьте title длиной 50–60 символов с основным ключом.",
                "estimated_improvement_percent": 12,
            }
        )
    if not description:
        issues.append(
            {
                "problem": "Отсутствует meta description",
                "recommendation": "Добавьте description длиной 120–160 символов с выгодой для пользователя.",
                "estimated_improvement_percent": 10,
            }
        )
    if not h1:
        issues.append(
            {
                "problem": "Отсутствует H1",
                "recommendation": "Добавьте единственный H1, который отражает интент страницы.",
                "estimated_improvement_percent": 9,
            }
        )
    if not get_json_ld(str(soup)):
        issues.append(
            {
                "problem": "Не найдена JSON-LD разметка",
                "recommendation": "Добавьте JSON-LD для WebPage, Article, Product или Organization в зависимости от типа страницы.",
                "estimated_improvement_percent": 8,
            }
        )
    if not keywords:
        issues.append(
            {
                "problem": "Не удалось выделить ключевые слова",
                "recommendation": "Увеличьте объём уникального текста и добавьте терминологию предметной области.",
                "estimated_improvement_percent": 7,
            }
        )
    return issues


def build_mermaid(clusters: list[dict[str, Any]]) -> str:
    lines = ["graph TD"]
    for index, cluster in enumerate(clusters[:8], start=1):
        cluster_id = f"C{index}"
        lines.append(f"{cluster_id}[{cluster['cluster']}]")
        for word_idx, keyword in enumerate(cluster["keywords"][:5], start=1):
            key_id = f"{cluster_id}_{word_idx}"
            lines.append(f"{cluster_id} --> {key_id}[{keyword}]")
    return "\n".join(lines)


async def analyze_semantics(url: str) -> dict[str, Any]:
    page = await fetch_page(url)
    soup = BeautifulSoup(page["html"], "html.parser")
    text = visible_text_from_html(page["html"])
    keywords = extract_keywords(text)
    clusters = cluster_keywords(keywords)
    scores = score_semantic_optimization(soup, keywords)
    visuals = build_semantic_visualizations(keywords, scores)
    generated_json_ld = generate_json_ld_stub(page["url"], soup)
    issues = semantic_recommendations(soup, keywords)
    return {
        "url": page["url"],
        "semantic_core": keywords,
        "keyword_clusters": clusters,
        "html_optimization": {
            "title": _title_description_h1(soup)[0],
            "description": _title_description_h1(soup)[1],
            "h1": _title_description_h1(soup)[2],
            "recommendations": [issue["recommendation"] for issue in issues],
        },
        "generated_json_ld": generated_json_ld,
        "aio_optimization": {
            "faq_candidates": [item["keyword"] for item in keywords[:5]],
            "snippet_advice": "Добавьте короткие ответы, списки, таблицы и блок FAQ для LLM/AIO и сниппетов.",
        },
        "visualizations": visuals,
        "mermaid": build_mermaid(clusters),
        "issues": issues,
        "optimization_score": round(sum(scores.values()) / len(scores), 1),
    }


async def _collect_page(session: aiohttp.ClientSession, url: str) -> tuple[int | None, str, dict[str, str]]:
    try:
        async with session.get(url, ssl=False, allow_redirects=True) as response:
            return response.status, await response.text(errors="ignore"), dict(response.headers)
    except aiohttp.ClientError:
        return None, "", {}


async def crawl_site(url: str, depth: int = 3, limit: int = 30) -> list[dict[str, Any]]:
    start = ensure_absolute_url(url)
    parsed = urlparse(start)
    queue = deque([(start, 0)])
    visited: set[str] = set()
    pages: list[dict[str, Any]] = []
    timeout = aiohttp.ClientTimeout(total=20)
    headers = {"User-Agent": "Mozilla/5.0 SEO-Analyst/1.0"}

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        while queue and len(visited) < limit:
            current, current_depth = queue.popleft()
            if current in visited or current_depth > depth:
                continue
            visited.add(current)
            status, html, response_headers = await _collect_page(session, current)
            soup = BeautifulSoup(html, "html.parser") if html else BeautifulSoup("", "html.parser")
            title, description, h1 = _title_description_h1(soup)
            links: list[str] = []
            for anchor in soup.find_all("a", href=True):
                target = urljoin(current, anchor["href"])
                parsed_target = urlparse(target)
                normalized = f"{parsed_target.scheme}://{parsed_target.netloc}{parsed_target.path}".rstrip("/")
                if parsed_target.netloc == parsed.netloc and normalized and normalized not in visited:
                    queue.append((normalized, current_depth + 1))
                if parsed_target.netloc == parsed.netloc:
                    links.append(normalized)
            pages.append(
                {
                    "url": current,
                    "depth": current_depth,
                    "status": status,
                    "title": title,
                    "description": description,
                    "h1": h1,
                    "links": sorted(set(link for link in links if link)),
                    "content_type": response_headers.get("Content-Type", ""),
                }
            )
    return pages


def group_technical_issues(pages: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for page in pages:
        status = page["status"]
        if status is None:
            grouped["network"].append({"page": page["url"], "issue": "Не удалось получить страницу"})
        elif 400 <= status < 500:
            grouped["4xx"].append({"page": page["url"], "issue": f"HTTP {status}"})
        elif status >= 500:
            grouped["5xx"].append({"page": page["url"], "issue": f"HTTP {status}"})
        if not page["title"]:
            grouped["meta issues"].append({"page": page["url"], "issue": "Отсутствует title"})
        if not page["description"]:
            grouped["meta issues"].append({"page": page["url"], "issue": "Отсутствует description"})
        if not page["h1"]:
            grouped["heading issues"].append({"page": page["url"], "issue": "Отсутствует H1"})
    return dict(grouped)


def analyze_internal_linking(pages: list[dict[str, Any]]) -> dict[str, Any]:
    inbound: Counter[str] = Counter()
    outbound: dict[str, int] = {}
    for page in pages:
        outbound[page["url"]] = len(page["links"])
        for link in page["links"]:
            inbound[link] += 1
    weak_pages = [
        {"page": page["url"], "inbound_links": inbound.get(page["url"], 0)}
        for page in pages
        if inbound.get(page["url"], 0) <= 1 and page["depth"] > 0
    ]
    return {
        "weak_pages": weak_pages[:15],
        "top_hubs": sorted(
            ({"page": page, "outbound_links": count} for page, count in outbound.items()),
            key=lambda item: item["outbound_links"],
            reverse=True,
        )[:10],
    }


def _resource_status_text(status: int | None) -> str:
    if status is None:
        return "Недоступно"
    if 200 <= status < 300:
        return f"OK ({status})"
    return f"Проблема ({status})"


async def technical_audit(url: str, depth: int = 3) -> dict[str, Any]:
    normalized_url = ensure_absolute_url(url)
    pages = await crawl_site(normalized_url, depth=depth)
    grouped_issues = group_technical_issues(pages)
    robots = await get_robots_data(normalized_url)
    llms = await get_llms_data(normalized_url)
    parsed = urlparse(normalized_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    sitemap_status = await head_request(f"{base}/sitemap.xml")
    relinking = analyze_internal_linking(pages)
    issue_count = sum(len(items) for items in grouped_issues.values())
    projected_gain = min(45, issue_count * 2)
    return {
        "site": normalized_url,
        "scan_depth": depth,
        "pages_scanned": len(pages),
        "resources": {
            "sitemap.xml": _resource_status_text(sitemap_status),
            "robots.txt": "OK" if robots else "Не найден или пустой",
            "llms.txt": "OK" if llms else "Не найден или пустой",
        },
        "grouped_issues": grouped_issues,
        "re_linking": relinking,
        "recommendations": [
            "Исправьте страницы с 4xx/5xx прежде всего — это даст самый быстрый эффект.",
            "Добавьте или обновите sitemap.xml, robots.txt и llms.txt, если они отсутствуют.",
            "Усилите внутренние ссылки на страницы с малым числом входящих ссылок.",
        ],
        "projected_optimization_gain_percent": projected_gain,
        "rescanning_supported": True,
        "pages": pages,
    }


async def capture_uiux_screenshots(url: str) -> dict[str, str]:
    normalized_url = ensure_absolute_url(url)
    desktop_path = SCREENSHOTS_DIR / "uiux_desktop.png"
    mobile_path = SCREENSHOTS_DIR / "uiux_mobile.png"
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            desktop = await browser.new_page(viewport={"width": 1440, "height": 1200})
            await desktop.goto(normalized_url, wait_until="domcontentloaded", timeout=60_000)
            await desktop.screenshot(path=str(desktop_path), full_page=True)
            mobile = await browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
            await mobile.goto(normalized_url, wait_until="domcontentloaded", timeout=60_000)
            await mobile.screenshot(path=str(mobile_path), full_page=True)
        finally:
            await browser.close()
    return {"desktop": str(desktop_path), "mobile": str(mobile_path)}


def _ux_score(value: bool, good: int = 100, bad: int = 35) -> int:
    return good if value else bad


async def uiux_analysis(url: str) -> dict[str, Any]:
    page = await fetch_page(ensure_absolute_url(url))
    soup = BeautifulSoup(page["html"], "html.parser")
    nav = bool(soup.find("nav"))
    ctas = len(soup.find_all(["button"])) + len(
        [a for a in soup.find_all("a") if re.search(r"купить|заказать|contact|demo|trial|консультац", a.get_text(" ", strip=True), re.I)]
    )
    forms = len(soup.find_all("form"))
    inputs_without_label = 0
    for form in soup.find_all("form"):
        for field in form.find_all(["input", "textarea", "select"]):
            field_id = field.get("id")
            if field_id and soup.find("label", attrs={"for": field_id}):
                continue
            if field.get("aria-label"):
                continue
            inputs_without_label += 1
    screenshots = await capture_uiux_screenshots(url)
    score_breakdown = {
        "navigation": _ux_score(nav),
        "cta": 100 if ctas >= 1 else 40,
        "forms": 100 if forms >= 1 else 55,
        "accessibility": 100 if inputs_without_label == 0 else max(30, 100 - inputs_without_label * 15),
        "content_structure": 100 if soup.find("main") and soup.find("h1") else 50,
    }
    average_score = round(sum(score_breakdown.values()) / len(score_breakdown), 1)
    scenarios = [
        "Открыть главную страницу и убедиться, что первый экран содержит понятный оффер и CTA.",
        "Перейти по основному CTA и проверить, что форма или целевая страница открываются без ошибок.",
        "Пройти сценарий заполнения каждой формы: обязательные поля, ошибки валидации, успешная отправка.",
        "Проверить мобильную версию: меню, кнопки и формы доступны без горизонтального скролла.",
    ]
    funnel = [
        {"step": "Landing", "description": "Первый экран и основной оффер"},
        {"step": "CTA click", "description": "Переход на коммерческое действие"},
        {"step": "Form", "description": "Заполнение формы / просмотр контактов"},
        {"step": "Lead", "description": "Успешная отправка заявки"},
    ]
    issues = []
    if not nav:
        issues.append("Не найден семантический блок навигации <nav>.")
    if ctas == 0:
        issues.append("Не найдено явных CTA-кнопок или ссылок действия.")
    if inputs_without_label:
        issues.append(f"Найдено полей без label или aria-label: {inputs_without_label}.")
    return {
        "url": page["url"],
        "uiux_score": average_score,
        "score_breakdown": score_breakdown,
        "issues": issues,
        "test_scenarios": scenarios,
        "funnel": funnel,
        "screenshots": screenshots,
        "metrika_oauth_supported": True,
    }


async def fetch_metrika_report(oauth_token: str, counter_id: str, metrics: str, dimensions: str | None = None) -> dict[str, Any]:
    headers = {"Authorization": f"OAuth {oauth_token}"}
    params = {
        "ids": counter_id,
        "metrics": metrics,
    }
    if dimensions:
        params["dimensions"] = dimensions
    async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.get("https://api-metrika.yandex.net/stat/v1/data", params=params, ssl=False) as response:
            data = await response.json(content_type=None)
            if response.status >= 400:
                raise RuntimeError(f"Yandex Metrika error: {response.status} {data}")
            return data


async def build_metrika_funnels(oauth_token: str, counter_id: str) -> dict[str, Any]:
    report = await fetch_metrika_report(
        oauth_token=oauth_token,
        counter_id=counter_id,
        metrics="ym:s:visits,ym:s:pageviews,ym:s:users,ym:s:bounceRate",
        dimensions="ym:s:startURLPath",
    )
    rows = report.get("data", [])[:10]
    funnel_rows = []
    for row in rows:
        path = row.get("dimensions", [{}])[0].get("name") or row.get("dimensions", [{}])[0].get("id")
        metrics = row.get("metrics", [])
        funnel_rows.append(
            {
                "path": path,
                "visits": metrics[0] if len(metrics) > 0 else 0,
                "pageviews": metrics[1] if len(metrics) > 1 else 0,
                "users": metrics[2] if len(metrics) > 2 else 0,
                "bounce_rate": metrics[3] if len(metrics) > 3 else 0,
            }
        )
    return {
        "counter_id": counter_id,
        "rows": funnel_rows,
        "oauth_used": True,
    }