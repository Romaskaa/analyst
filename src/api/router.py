import json
import pathlib

from fastapi import APIRouter, status

from ..agents.prompts import PROMPT_INFORMANT, PROMPT_SUMMARIZE_CHAT
from ..agents.rag import retrieve
from ..agents.workflow import agent
from ..core.depends import gpt_oss_120b
from ..core.schemas import Chat

router = APIRouter(prefix="/api/v1")

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
    tokens = gpt_oss_120b.get_num_tokens(messages_str)

    if tokens >= 50000:
        dialog_text = json.dumps(messages[1::], ensure_ascii=False)
        request = PROMPT_SUMMARIZE_CHAT.format(dialog_text=dialog_text)
        summarize = await gpt_oss_120b.ainvoke(request)
        messages.clear()
        messages.append({"role": "assistant", "content": summarize.content})
    response = await gpt_oss_120b.ainvoke(PROMPT.format(data=message, rag_data=retriv))
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
