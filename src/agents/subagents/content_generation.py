import logging
from typing import TypedDict
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from langgraph.graph import END, START, StateGraph

from ...core.depends import gpt_oss_120b
from ...utils.layout_structure import (
    validate_description,
    validate_heading,
    validate_images,
    validate_title,
)
from ..prompts import (
    PROMPT_GENERATE_DESCRIPTION,
    PROMPT_GENERATE_H1,
    PROMPT_GENERATE_TITLE,
)
from .process import process_all_images
from .utils import count_tokens_with_ai_message

logger = logging.getLogger(__name__)


class State(TypedDict):
    url: str
    html: str
    markdown: list[str]
    title: str
    description: str
    h1: str
    alt_tags: list[str] | str
    total_tokens: int
    total_money: float


async def create_title(state: State) -> dict:
    soup = BeautifulSoup(state["html"], "html.parser")
    validate = validate_title(soup)
    logger.info("Генерация title")
    if validate != []:
        request = PROMPT_GENERATE_TITLE.format(
            data=state["markdown"], analyze=validate[0].model_dump()
        )
        result = await gpt_oss_120b.ainvoke(request)
        total_tokens = await count_tokens_with_ai_message(request, result)
        total_money = total_tokens / 1000 * 0.30
        return {"title": result.content, "total_tokens": total_tokens, "total_money": total_money}

    return {"title": "У вас правильно написан заголовок", "total_tokens": 0, "total_money": 0}


async def create_description(state: State) -> dict:
    soup = BeautifulSoup(state["html"], "html.parser")
    validate = validate_description(soup)
    logger.info("Генерация description")
    if validate != []:
        request = PROMPT_GENERATE_DESCRIPTION.format(
            data=state["markdown"], analyze=validate[0].model_dump()
        )
        result = await gpt_oss_120b.ainvoke(request)
        tokens = await count_tokens_with_ai_message(request, result)
        total_tokens = state["total_tokens"] + tokens
        total_money = (tokens / 1000 * 0.30) + state["total_money"]
        return {
            "description": result.content,
            "total_tokens": total_tokens,
            "total_money": total_money,
        }
    return {"description": "У вас правильное описание страницы"}


async def create_h1(state: State) -> dict:
    soup = BeautifulSoup(state["html"], "html.parser")
    validate = validate_heading(soup)
    logger.info("Генерация h1")
    if validate != []:
        analyze = [i.model_dump() for i in validate]
        request = PROMPT_GENERATE_H1.format(data=state["markdown"], analyze=analyze)
        result = await gpt_oss_120b.ainvoke(request)
        tokens = await count_tokens_with_ai_message(request, result)
        total_tokens = state["total_tokens"] + tokens
        total_money = (tokens / 1000 * 0.30) + state["total_money"]
        return {"h1": result.content, "total_tokens": total_tokens, "total_money": total_money}
    return {"h1": "Тег H1 правильно написан"}


async def create_alts(state: State) -> dict:
    parsed = urlparse(state["url"])
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    soup = BeautifulSoup(state["html"], "html.parser")
    validate = validate_images(soup)
    logger.info("Генерация alts")
    if isinstance(validate, tuple):
        modified_urls: list = []
        unique_urls = list(set(validate[1]))
        for url in unique_urls:
            if not url:
                continue
            if url.startswith(("http://", "https://")):
                modified_urls.append(url)
            else:
                absolute_url = urljoin(base_url, url)
                modified_urls.append(absolute_url)
        tags, tokens = await process_all_images(modified_urls)
        total_tokens = state["total_tokens"] + tokens
        total_money = (tokens / 1000 * 0.40) + state["total_money"]
        return {"alt_tags": tags, "total_tokens": total_tokens, "total_money": total_money}
    return {"alt_tags": "Изображений на сайте нету либо они определены в неправильном теге"}


builder = StateGraph(State)

builder.add_node("create_title", create_title)
builder.add_node("create_description", create_description)
builder.add_node("create_h1", create_h1)
builder.add_node("create_alts", create_alts)

builder.add_edge(START, "create_title")
builder.add_edge("create_title", "create_description")
builder.add_edge("create_description", "create_h1")
builder.add_edge("create_h1", "create_alts")
builder.add_edge("create_alts", END)

agent_content_generation_result = builder.compile()
