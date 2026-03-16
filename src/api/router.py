import json
import logging
import pathlib

from fastapi import APIRouter, HTTPException, UploadFile, status
from ..agents.knowledge_base import save_file
from ..agents.prompts import PROMPT_INFORMANT, PROMPT_SUMMARIZE_CHAT
from ..agents.rag import retrieve
from ..agents.workflow import agent
from ..core.depends import gpt_oss_120b
from ..core.depends import rag_stepfun
from ..core.schemas import (
    Chat,
    UploadResponse,
)

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)

messages: list = [
    {"role": "system", "content": PROMPT_INFORMANT},
]
PROMPT = """
Данные из RAG:
{rag_data}

Запрос пользователя:
{data}
"""


async def get_answer(message: dict) -> str:
    retriv = retrieve(
        query=message["content"],
        metadata_filter={"tenant_id": "b77f7b87-2d40-45fa-b653-2ff34d5fd587"},
    )
    print(message)
    print(retriv)
    messages.append(message)
    messages_str = json.dumps(messages, ensure_ascii=False)
    #tokens = gpt_oss_120b.get_num_tokens(messages_str)
    tokens = rag_stepfun.get_num_tokens(messages_str)

    if tokens >= 50000:
        dialog_text = json.dumps(messages[1::], ensure_ascii=False)
        request = PROMPT_SUMMARIZE_CHAT.format(dialog_text=dialog_text)
        #summarize = await gpt_oss_120b.ainvoke(request)
        summarize = await rag_stepfun.ainvoke(request)
        messages.clear()
        messages.append({"role": "assistant", "content": summarize.content})
    #response = await gpt_oss_120b.ainvoke(PROMPT.format(data=message, rag_data=retriv))
    try:
        response = await rag_stepfun.ainvoke(PROMPT.format(data=message, rag_data=retriv))
    except Exception as exc:
        logger.exception("Failed to generate chat completion", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Не удалось получить ответ от LLM-провайдера. "
                "Проверьте OPENROUTER_API_KEY и доступность модели stepfun/step-3.5-flash:free."
            ),
        ) from exc
    print(response)
    messages.append({"role": "assistant", "content": response.content})
    return response.content  # type: ignore  # noqa: PGH003


@router.get("/agent", status_code=status.HTTP_200_OK)
async def analyze(url: str) -> dict:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    data = await agent.ainvoke({"url": url})
    pathlib.Path("refactoring.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data


@router.post("/chat", status_code=status.HTTP_200_OK)
async def answer(chat: Chat) -> dict:
    result = await get_answer(chat.model_dump())
    return {"answer": result}

@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload(file: UploadFile) -> UploadResponse:
    path = save_file(file)
    return UploadResponse(path=path)
