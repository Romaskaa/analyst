import os
import sqlite3
from uuid import UUID

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ..core.depends import gpt_oss_120b, summarization_middleware
from ..settings import SQLITE_PATH
from .prompts import PROMPT_INFORMANT
from .rag import retrieve

PROMPT = """
Данные из RAG:
{rag_data}

Запрос пользователя:
{user_prompt}

Требования к ответу:
1. Если используешь данные из базы знаний, обязательно указывай источник в формате [Имя файла](ссылка).
2. В конце ответа добавляй блок "Источники" со списком использованных файлов без повторов.
3. Не придумывай источники и не указывай их, если в данных нет полей File и Link.
4. Если в данных нет ответа, честно скажи, что информации недостаточно.
"""


async def call_chatbot(user_id: UUID, user_prompt: str, generation_id: str) -> str:
    """Call chatbot agent for user dialogue within a specific generation context."""

    async with AsyncSqliteSaver.from_conn_string(os.fspath(SQLITE_PATH)) as checkpointer:
        await checkpointer.setup()
        agent = create_agent(
            model=gpt_oss_120b,
            system_prompt=PROMPT_INFORMANT,
            middleware=[summarization_middleware],
            checkpointer=checkpointer,
        )
        rag = await retrieve(
            query=user_prompt,
            metadata_filter={"tenant_id": user_id, "generation_id": generation_id},
        )

        result = await agent.ainvoke(
            {
                "messages": [
                    HumanMessage(content=PROMPT.format(rag_data=rag, user_prompt=user_prompt))
                ],
            },
            config={"configurable": {"thread_id": f"{user_id}"}},
        )
    return result["messages"][-1].content


def reset_chat_history(user_id: UUID) -> None:
    db_path = os.fspath(SQLITE_PATH)
    connection = sqlite3.connect(db_path)
    try:
        thread_id = str(user_id)
        cursor = connection.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        connection.commit()
    finally:
        connection.close()
