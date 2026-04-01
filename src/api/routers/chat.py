from typing import Any

from fastapi import APIRouter, Request, UploadFile, status

from ...agents import chatbot
from ...agents.knowledge_base import save_file
from ...agents.rag import list_knowledge_base_files
from ...schemas import Chat, Role, UploadResponse

router_chat = APIRouter()


@router_chat.post("/chat", status_code=status.HTTP_200_OK)
async def answer(request: Request) -> Chat | dict[str, str]:
    payload: dict[str, Any] = await request.json()
    user_id = str(payload.get("user_id") or "public")
    user_prompt = str(payload.get("text") or payload.get("content") or "").strip()
    result = await chatbot.call_chatbot(user_id=user_id, user_prompt=user_prompt)

    if "content" in payload and "text" not in payload:
        return {"answer": result}

    return Chat(user_id=user_id, role=Role.AI, text=result)


@router_chat.post("/chat/reset", status_code=status.HTTP_200_OK)
async def reset_chat() -> dict[str, str]:
    chatbot.reset_chat_history()
    return {"status": "ok"}


@router_chat.get("/knowledge-base/files", status_code=status.HTTP_200_OK)
async def knowledge_base_files() -> dict[str, list[dict[str, str]]]:
    return {"files": list_knowledge_base_files()}


@router_chat.post("/upload", status_code=status.HTTP_200_OK)
async def upload(file: UploadFile) -> UploadResponse:
    path = save_file(file)
    return UploadResponse(path=path)
