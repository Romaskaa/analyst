import json
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from playwright.async_api import async_playwright

from ..utils.web_parser import get_html_content, get_markdown_content
from . import rag
from .subagents import agent_aio, agent_analyst, agent_seo


class State(TypedDict):
    url: str
    html: str
    markdown: str
    analyst_result: dict
    aio_result: dict
    seo_result: dict
    rag_result: str
    total_tokens: int
    total_money: float


async def get_site_markups(state: State) -> dict:
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
            markdown = await get_markdown_content(browser, state["url"])
            html = await get_html_content(browser, state["url"])
            return {"markdown": markdown, "html": html}
        finally:
            await browser.close()


async def get_analyst_result(state: State) -> dict:
    result = await agent_analyst.ainvoke({"url": state["url"], "markdown": state["markdown"]})  # type: ignore  # noqa: PGH003
    total_money = (result["total_tokens"] / 1000) * 0.41
    total_tokens = result["total_tokens"]
    del result["url"]
    del result["markdown"]
    del result["total_tokens"]
    return {
        "analyst_result": result,
        "total_tokens": total_tokens,
        "total_money": total_money,
    }


async def get_aio_result(state: State) -> dict:
    result = await agent_aio.ainvoke(
        {
            "url": state["url"],
            "markdown": state["markdown"],
            "html": state["html"],
        }  # type: ignore  # noqa: PGH003
    )
    total_tokens = state["total_tokens"] + result["total_tokens"]
    money = (result["total_tokens"] / 1000) * 0.41
    total_money = money + state["total_money"]
    del result["url"]
    del result["markdown"]
    del result["html"]
    del result["total_tokens"]
    return {"aio_result": result, "total_tokens": total_tokens, "total_money": total_money}


async def get_seo_result(state: State) -> dict:
    result = await agent_seo.ainvoke(
        {
            "url": state["url"],
            "markdown": state["markdown"],
            "html": state["html"],
        }  # type: ignore  # noqa: PGH003
    )
    total_tokens = state["total_tokens"] + result["total_tokens"]
    money = (result["total_tokens"] / 1000) * 0.41
    total_money = money + state["total_money"]
    return {
        "seo_result": result["result"],
        "total_tokens": total_tokens,
        "total_money": total_money,
    }


async def save_in_rag(state: State) -> dict:
    result = state.copy()
    result["markdown"] = ""
    result["html"] = ""
    rag.indexing(
        text=json.dumps(result), metadata={"tenant_id": "b77f7b87-2d40-45fa-b653-2ff34d5fd587"}
    )
    return {"rag_result": "saved"}


builder = StateGraph(State)

builder.add_node("get_site_markups", get_site_markups)
builder.add_node("get_analyst_result", get_analyst_result)
builder.add_node("get_aio_result", get_aio_result)
builder.add_node("get_seo_result", get_seo_result)
builder.add_node("save_in_rag", save_in_rag)
builder.add_edge(START, "get_site_markups")
builder.add_edge("get_site_markups", "get_analyst_result")
builder.add_edge("get_analyst_result", "get_aio_result")
builder.add_edge("get_aio_result", "get_seo_result")
builder.add_edge("get_seo_result", "save_in_rag")
builder.add_edge("save_in_rag", END)
agent = builder.compile()
