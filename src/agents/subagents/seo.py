import json
import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ...core.depends import (
    cwv_prompt_template,
    parser_cwv,
    parser_result,
    text_splitter,
    yandex_gpt,
)
from ...core.schemas import CWVReport, SiteAnalysisReport
from ...integrations.google_psi_api import run_page_speed
from ...utils.psi_charts import generate_psi_charts
from ..prompts import PROMPT_RESULT
from .process import analyze_markdown
from .utils import get_seo_issues

logger = logging.getLogger(__name__)


class State(TypedDict):
    url: str
    markdown: str
    html: str
    analyze_md: dict
    seo_issue: list[dict]
    cwv: CWVReport
    charts: dict[str, str]
    result: SiteAnalysisReport
    total_tokens: int


async def analyze_markups(state: State) -> dict:
    result, tokens = await analyze_markdown(state["markdown"])
    seo_issue = await get_seo_issues(state["html"])
    logger.info("Анализ разметки сайта")
    return {
        "analyze_md": result,
        "seo_issue": seo_issue,
        "total_tokens": tokens,
    }


async def get_core_web_vitals(state: State) -> dict:
    cwv = await run_page_speed(state["url"])
    charts = generate_psi_charts(cwv)
    chain = cwv_prompt_template | yandex_gpt | parser_cwv
    count_cwv = yandex_gpt.get_num_tokens(str(cwv))
    result: CWVReport = await chain.ainvoke({"query": cwv})
    count_result = yandex_gpt.get_num_tokens(str(result))
    tokens = count_cwv + count_result
    total_tokens = state["total_tokens"] + tokens
    logger.info("Получение CWV")
    return {"cwv": result.model_dump(), "charts": charts, "total_tokens": total_tokens}


async def final_result(state: State) -> dict:
    chain = yandex_gpt | parser_result
    dumps_markdown = json.dumps(state["analyze_md"])
    dumps_issue = json.dumps(state["seo_issue"])
    split_markdown = text_splitter.split_text(dumps_markdown)
    split_issue = text_splitter.split_text(dumps_issue)
    request = PROMPT_RESULT.format(
        markdown=split_markdown,
        seo_issue=split_issue,
        cwv=state["cwv"],
        format_instructions=parser_result.get_format_instructions(),
    )
    count_data = yandex_gpt.get_num_tokens(request)

    result: SiteAnalysisReport = await chain.ainvoke(request)
    count_result = yandex_gpt.get_num_tokens(result.model_dump_json())
    tokens = count_data + count_result
    total_tokens = state["total_tokens"] + tokens
    logger.info("Результат SEO")
    result_data = result.to_dict
    result_data["charts"] = state["charts"]
    return {"result": result_data, "total_tokens": total_tokens}


builder = StateGraph(State)

builder.add_node("analyze_markups", analyze_markups)
builder.add_node("get_core_web_vitals", get_core_web_vitals)
builder.add_node("final_result", final_result)

builder.add_edge(START, "analyze_markups")
builder.add_edge("analyze_markups", "get_core_web_vitals")
builder.add_edge("get_core_web_vitals", "final_result")
builder.add_edge("final_result", END)

agent_seo = builder.compile()
