from fastapi import APIRouter, UploadFile, status

from ...agents import chatbot
from ...agents.knowledge_base import save_file
from ...agents.rag import list_knowledge_base_files
from ...schemas import Chat, Role, UploadResponse
from ..dependencies import CurrentUserDep

router_chat = APIRouter()


@router_chat.post("/chat", status_code=status.HTTP_200_OK)
async def answer(chat: Chat, current_user: CurrentUserDep) -> Chat:
    result = await chatbot.call_chatbot(
        user_id=current_user.user_id,
        user_prompt=chat.text,
        generation_id=chat.generation_id,
    )
    return Chat(role=Role.AI, text=result, generation_id=chat.generation_id)


@router_chat.post("/chat/reset", status_code=status.HTTP_200_OK)
async def reset_chat(current_user: CurrentUserDep) -> dict[str, str]:
    chatbot.reset_chat_history(user_id=current_user.user_id)
    return {"status": "ok"}


@router_chat.get("/knowledge-base/files", status_code=status.HTTP_200_OK)
async def knowledge_base_files(_current_user: CurrentUserDep) -> dict[str, list[dict[str, str]]]:
    return {"files": list_knowledge_base_files()}


@router_chat.post("/upload", status_code=status.HTTP_200_OK)
async def upload(file: UploadFile, _current_user: CurrentUserDep) -> UploadResponse:
    path = save_file(file)
    return UploadResponse(path=path)
