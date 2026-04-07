import base64
import json

import aiohttp

from ...core.constants import BATCH_SIZE, REQUEST_TIMEOUT, STATUS_OK
from ...core.depends import (
    gemma_3_27b_it,
    gpt_oss_120b,
    parser_generated_alt,
    parser_markdown,
    yandex_gpt,
)
from ...schemas import SEOAnalysisReport
from ..prompts import (
    PROMPT_ANALYZE_JSON_LD,
    PROMPT_ANALYZE_LLMS_TXT,
    PROMPT_GENERATE_ALT,
    PROMPT_GENERATE_JSON_LD,
    PROMPT_GENERATE_LLMS_TXT,
    PROMPT_MARKDOWN,
    PROMPT_SUMMARIZE,
)
from .utils import count_tokens, count_tokens_with_ai_message, get_mime, is_image


async def analyze_json_ld(ld: list) -> dict:
    request = PROMPT_ANALYZE_JSON_LD.format(json_ld=ld)
    result = await yandex_gpt.ainvoke(request)
    total_tokens = await count_tokens_with_ai_message(request, result)
    return {"json_ld": result.content, "total_tokens": total_tokens}


async def generate_json_ld(markdown: list) -> dict:
    request = PROMPT_GENERATE_JSON_LD.format(data=markdown)
    result = await gpt_oss_120b.ainvoke(request)
    total_tokens = await count_tokens_with_ai_message(request, result)
    return {"json_ld": result.content, "total_tokens": total_tokens}


async def analyze_llms_txt(txt: str) -> dict:
    request = PROMPT_ANALYZE_LLMS_TXT.format(data=txt)
    result = await yandex_gpt.ainvoke(request)
    total_tokens = await count_tokens_with_ai_message(request, result)
    return {"llms_txt": result.content, "total_tokens": total_tokens}


async def generate_llms_txt(markdown: list[str], url: str) -> dict:
    total_tokens = 0
    request_summarize = PROMPT_SUMMARIZE.format(data=markdown)
    summarize = await gpt_oss_120b.ainvoke(request_summarize)
    tokens = await count_tokens_with_ai_message(request_summarize, summarize)
    total_tokens += tokens
    request = PROMPT_GENERATE_LLMS_TXT.format(data={"url": url, "data": summarize.content})
    result = await yandex_gpt.ainvoke(request)
    count = await count_tokens_with_ai_message(request, result)
    total_tokens += count
    return {"llms_txt": result.content, "total_tokens": total_tokens}


async def analyze_markdown(markdown: list[str]) -> tuple:
    request = PROMPT_MARKDOWN.format(
        query=markdown, format_instructions=parser_markdown.get_format_instructions()
    )  # noqa: E501, RUF100
    chain = gpt_oss_120b | parser_markdown
    result: SEOAnalysisReport = await chain.ainvoke(request)
    total_tokens = await count_tokens(request, result.model_dump_json())
    return result.model_dump(), total_tokens


async def _process_image_chunk(links: list[str]) -> tuple[list, int]:
    """
    Обрабатывает один чанк ссылок: скачивает изображения, группирует по BATCH_SIZE,
    вызывает generate_alt для каждой группы и возвращает список alt-текстов и общее число токенов.
    """
    alt_texts = []
    total_tokens = 0
    batch = []
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
        for link in links:
            if not is_image(link):
                continue
            async with session.get(link, ssl=False) as response:
                if response.status != STATUS_OK:
                    continue
                data = await response.read()
                mime = await get_mime(link, data)
                if mime == "image/svg+xml":
                    continue
                base64_str = base64.b64encode(data).decode("utf-8")
                batch.append({"image": base64_str, "type": mime, "url": link})

                if len(batch) == BATCH_SIZE:
                    alt, tokens = await _generate_alt(batch)
                    alt_texts.append(alt)
                    total_tokens += tokens
                    batch.clear()

        if batch:
            alt, tokens = await _generate_alt(batch)
            alt_texts.append(alt)
            total_tokens += tokens
    return alt_texts, total_tokens


async def process_all_images(all_links: list[str]) -> tuple[list[str], int]:
    """Разбивает все ссылки на три части и обрабатывает их параллельно."""
    all_alts, total_tokens = await _process_image_chunk(all_links[:3])
    # Разделение на три примерно равные части без numpy
    # n = len(all_links)
    # part_size = n // 3
    # remainder = n % 3
    # parts = []
    # start = 0
    # for i in range(3):
    #     end = start + part_size + (1 if i < remainder else 0)
    #     parts.append(all_links[start:end])
    #     start = end
    # # Параллельный запуск трёх задач

    # results = await asyncio.gather(
    #     *[_process_image_chunk(parts[i]) for i in range(3) if parts[i]],
    # )

    # all_alts: list = []
    # total_tokens = 0
    # for res in results:
    #     if isinstance(res, BaseException):
    #         continue
    #     alts, tokens = res
    #     all_alts.extend(alts)
    #     total_tokens += tokens

    return all_alts, total_tokens


async def _generate_alt(images_batch: list[dict]) -> tuple[list, int]:
    chain = gemma_3_27b_it | parser_generated_alt
    request = PROMPT_GENERATE_ALT.format(
        urls=[img["url"] for img in images_batch],
        format_instructions=parser_generated_alt.get_format_instructions(),
    )

    content: list[dict] = [{"type": "text", "text": request}]
    for img in images_batch:
        content.extend(
            [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{img['type']};base64,{img['image']}"},
                }
            ]
        )

    count_request = gemma_3_27b_it.get_num_tokens(json.dumps(content))
    response = await chain.ainvoke(
        [
            {
                "role": "user",
                "content": content,
            }
        ]
    )
    result = [i.model_dump() for i in response.result]
    count_response = gemma_3_27b_it.get_num_tokens(json.dumps(result))
    return result, count_request + count_response