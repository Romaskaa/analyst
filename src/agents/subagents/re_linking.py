from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ...services.site_analysis import analyze_internal_linking, crawl_site
from ...core.depends import yandex_gpt
from ..prompts import PROMPT_RE_LINKING


class State(TypedDict):
    start_url: str
    links: list[dict]
    count: int
    result: dict


async def parce_links(state: State) -> dict:
    pages = await crawl_site(state["start_url"], depth=state.get("count", 3) or 3)
    links = [{"url": page["url"], "links": page["links"]} for page in pages]
    return {"links": links, "count": len(pages)}


async def get_advice(state: State) -> dict:
    relinking_stats = analyze_internal_linking(
        [{"url": item["url"], "links": item["links"], "depth": 0} for item in state["links"]]
    )
    request = PROMPT_RE_LINKING.format(pages_json=state["links"], start_url=state["start_url"])
    result = await yandex_gpt.ainvoke(request)
    return {"result": {"summary": result.content, "stats": relinking_stats}}


builder = StateGraph(State)

builder.add_node("parce_links", parce_links)
builder.add_node("get_advice", get_advice)

builder.add_edge(START, "parce_links")
builder.add_edge("parce_links", "get_advice")
builder.add_edge("get_advice", END)

agent_re_linking = builder.compile()
