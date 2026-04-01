from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ...core.depends import (
    yandex_gpt,
)
from ..prompts import PROMPT_RE_LINKING


class State(TypedDict):
    start_url: str
    links: list[dict]
    count: int
    result: dict


async def parce_links(state: State) -> dict:
    return {"links": ..., "count": ...}


async def get_advice(state: State) -> dict:
    request = PROMPT_RE_LINKING.format(pages_json=state["links"], start_url=state["start_url"])
    result = yandex_gpt.ainvoke(request)
    return {"result": result}


builder = StateGraph(State)

builder.add_node("parce_links", parce_links)
builder.add_node("get_advice", get_advice)

builder.add_edge(START, "parce_links")
builder.add_edge("parce_links", "get_advice")
builder.add_edge("get_advice", END)

agent_re_linking = builder.compile()
