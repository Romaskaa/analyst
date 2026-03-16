import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ...core.depends import parser_expertise, parser_sc, parser_specialization, yandex_gpt
from ...core.schemas import ExpertiseSite, SemanticCore, SpecializationSite
from ..prompts import PROMPT_EXPERTISE, PROMPT_SEMANTIC_CORE, PROMPT_SPECIALIZATION
from .utils import count_tokens, one_bit_queries

logger = logging.getLogger(__name__)


class State(TypedDict):
    url: str
    markdown: str
    specialization: dict
    expertise: dict
    semantic_core: dict
    total_tokens: int


async def get_specialization(state: State) -> dict:
    request = PROMPT_SPECIALIZATION.format(
        format_instructions=parser_specialization.get_format_instructions(), data=state["markdown"]
    )
    chain = yandex_gpt | parser_specialization
    result: SpecializationSite = await chain.ainvoke(request)
    total_tokens = await count_tokens(request, result.model_dump_json())
    logger.info("Получения специализации компании")
    return {
        "specialization": result.model_dump(),
        "total_tokens": total_tokens,
    }


async def get_expertise(state: State) -> dict:
    chain = yandex_gpt | parser_expertise
    request = PROMPT_EXPERTISE.format(
        data=state["markdown"],
        format_instructions=parser_expertise.get_format_instructions(),
    )
    result: ExpertiseSite = await chain.ainvoke(request)
    tokens = await count_tokens(request, result.model_dump_json())
    total_tokens = tokens + state["total_tokens"]
    logger.info("Получения экспертизы компании")
    return {"total_tokens": total_tokens, "expertise": result.model_dump()}


async def get_semantic_core(state: State) -> dict:
    request = PROMPT_SEMANTIC_CORE.format(
        data=one_bit_queries, format_instructions=parser_sc.get_format_instructions()
    )
    chain = yandex_gpt | parser_sc
    result: SemanticCore = await chain.ainvoke(request)
    tokens = await count_tokens(request, result.model_dump_json())
    total_tokens = tokens + state["total_tokens"]
    logger.info("Получения семантического ядра компании")
    return {"total_tokens": total_tokens, "semantic_core": result.model_dump()}


builder = StateGraph(State)

builder.add_node("get_specialization", get_specialization)
builder.add_node("get_expertise", get_expertise)
builder.add_node("get_semantic_core", get_semantic_core)

builder.add_edge(START, "get_specialization")
builder.add_edge("get_specialization", "get_expertise")
builder.add_edge("get_expertise", "get_semantic_core")
builder.add_edge("get_semantic_core", END)

agent_analyst = builder.compile()
