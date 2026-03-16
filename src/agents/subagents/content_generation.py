from typing import TypedDict

from .process import process_all_images


class State(TypedDict):
    url: str
    html: str
    title: str
    description: str
    keywords: list[str]
    alt_tags: list[str]
    total_tokens: int


async def create_alts(state: State) -> dict:
    # src = await get_src_images(state["url"])
    tags, tokens = await process_all_images(src)
    return {"alt_tags": tags, "total_tokens": tokens}
