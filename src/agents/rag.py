import contextlib
import json
import logging
import re
import time
from typing import Any
from uuid import uuid4

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from .knowledge_base import load_knowledge_base_documents

from ..settings import CHROMA_PATH

INDEX_NAME = "main-index"
KB_SOURCE = "knowledge_base"

logger = logging.getLogger(__name__)

hf_model = SentenceTransformer("deepvk/USER-bge-m3")
client = chromadb.PersistentClient(CHROMA_PATH)
splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=50, length_function=len)

def indexing(text: str, metadata: dict[str, Any] | None = None) -> list[str]:
    """Индексация и добавление документа в семантический индекс.

    :param text: Текст документа.
    :param metadata: Мета-информация документа.
    :returns: Идентификаторы чанков в индексе.
    """

    if not text.strip():
        logger.warning("Attempted to index empty text!")
        return []
    start_time = time.monotonic()
    logger.info("Starting index document text, length %s characters", len(text))
    collection = client.get_or_create_collection(INDEX_NAME)
    chunks = splitter.split_text(text)
    ids = [str(uuid4()) for _ in range(len(chunks))]
    embeddings = hf_model.encode_document(chunks, normalize_embeddings=False)
    prepared_metadata = metadata.copy() if metadata else {}
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),  # type: ignore  # noqa: PGH003
        metadatas=[prepared_metadata.copy() for _ in range(len(chunks))],  # type: ignore  # noqa: PGH003
    )
    logger.info("Finished indexing text, time %s seconds", round(time.monotonic() - start_time, 2))
    return ids

def _sync_knowledge_base_index() -> None:
    collection = client.get_or_create_collection(INDEX_NAME)
    kb_docs = load_knowledge_base_documents()

    indexed_files = set()
    existing = collection.get(where={"source": KB_SOURCE}, include=["metadatas"])
    for metadata in existing.get("metadatas", []):
        if not metadata:
            continue
        file_name = metadata.get("kb_file")
        if isinstance(file_name, str):
            indexed_files.add(file_name)

    for file_name, text in kb_docs:
        if file_name in indexed_files:
            continue
        indexing(
            text=text,
            metadata={
                "source": KB_SOURCE,
                "kb_file": file_name,
                "category": "knowledge_base",
            },
        )

def clean_text(text: str) -> str:
    """Очистка текста от экранированных символов и Unicode"""
    if not isinstance(text, str):
        return str(text)

    # Метод 1: Декодирование Unicode escape последовательностей
    with contextlib.suppress(UnicodeDecodeError):
        text = text.encode("utf-8").decode("unicode_escape")

    # Метод 2: Обработка JSON строк
    try:
        # Убираем лишние кавычки в начале и конце если есть
        if text.startswith('"') and text.endswith('"'):
            text = json.loads(text)
        else:
            text = json.loads(f'"{text}"')
    except (json.JSONDecodeError, TypeError):
        pass

    # Декодируем только явные unicode-escape последовательности (\uXXXX),
    # чтобы не ломать уже валидный UTF-8 текст (эффект "Ð..."/"Ñ...").
    if re.search(r"\\u[0-9a-fA-F]{4}", text):
        with contextlib.suppress(UnicodeDecodeError):
            text = text.encode("utf-8").decode("unicode_escape")

    def replace_unicode(match: re.Match[str]) -> str:
        try:
            return chr(int(match.group(1), 16))
        except ValueError:
            return match.group(0)

    return re.sub(r"\\u([0-9a-fA-F]{4})", replace_unicode, text)


def retrieve(
    query: str,
    metadata_filter: dict[str, Any] | None = None,
    search_string: str | None = None,
    n_results: int = 10,
) -> list[str]:
    """Извлечение документов с очисткой текста"""

    _sync_knowledge_base_index()
    collection = client.get_or_create_collection(INDEX_NAME)
    logger.info("Retrieving for query: '%s...'", query[:50])

    embedding = hf_model.encode_query(query, normalize_embeddings=False)
    params = {"query_embeddings": [embedding.tolist()], "n_results": n_results}  # type: ignore  # noqa: PGH003

    if search_string:
        params["where_document"] = {"$contains": search_string}

    queries = []
    if metadata_filter:
        filtered_params = params.copy()
        filtered_params["where"] = metadata_filter
        queries.append(collection.query(**filtered_params, include=["documents", "metadatas", "distances"]))

    kb_params = params.copy()
    kb_params["where"] = {"source": KB_SOURCE}
    queries.append(collection.query(**kb_params, include=["documents", "metadatas", "distances"]))

    combined_rows: list[tuple[str, dict[str, Any], float]] = []
    for query_result in queries:
        for document, metadata, distance in zip(
            query_result["documents"][0],  # type: ignore  # noqa: PGH003
            query_result["metadatas"][0],  # type: ignore  # noqa: PGH003
            query_result["distances"][0],  # type: ignore  # noqa: PGH003
            strict=False,  # type: ignore  # noqa: PGH003
        ):
            combined_rows.append((document, metadata, distance))

    combined_rows.sort(key=lambda row: row[2])

    cleaned_results = []
    for document, metadata, distance in combined_rows[:n_results]:
        # Очищаем документ
        cleaned_doc = clean_text(document)

        # Очищаем метаданные если нужно
        cleaned_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                cleaned_metadata[key] = clean_text(value)
            else:
                cleaned_metadata[key] = value

        cleaned_results.append(
            f"**Relevance score:** {round(distance, 2)}\n"
            f"**Source:** {cleaned_metadata.get('source', '')}\n"
            f"**Category:** {cleaned_metadata.get('category', '')}\n"
            "**Document:**\n"
            f"{cleaned_doc}"
        )

    return cleaned_results