from __future__ import annotations

import contextlib
import json
import logging
import re
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from ..settings import CHROMA_PATH
from .knowledge_base import (
    UPLOAD_DIR,
    load_knowledge_base_documents,
    normalize_filename,
    remove_uploaded_file,
)

INDEX_NAME = "main-index"
KB_SOURCE = "knowledge_base"

logger = logging.getLogger(__name__)

splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=50, length_function=len)
hf_model: SentenceTransformer | None = None
client: chromadb.PersistentClient | None = None


def get_embedding_model() -> SentenceTransformer:
    global hf_model
    if hf_model is None:
        hf_model = SentenceTransformer("deepvk/USER-bge-m3")
    return hf_model


def get_chroma_client() -> chromadb.PersistentClient:
    global client
    if client is not None:
        return client

    try:
        client = chromadb.PersistentClient(CHROMA_PATH)
    except Exception:
        fallback_path = Path("storage/chroma_runtime")
        fallback_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(fallback_path)
        logger.exception("Failed to open default Chroma path, switched to %s", fallback_path)

    return client


async def indexing(text: str, metadata: dict[str, Any] | None = None) -> list[str]:
    if not text.strip():
        logger.warning("Attempted to index empty text!")
        return []

    start_time = time.monotonic()
    logger.info("Starting index document text, length %s characters", len(text))
    collection = get_chroma_client().get_or_create_collection(INDEX_NAME)
    chunks = splitter.split_text(text)
    ids = [str(uuid4()) for _ in range(len(chunks))]
    embeddings = get_embedding_model().encode_document(chunks, normalize_embeddings=False)
    prepared_metadata = metadata.copy() if metadata else {}
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=[prepared_metadata.copy() for _ in range(len(chunks))],
    )
    logger.info("Finished indexing text, time %s seconds", round(time.monotonic() - start_time, 2))
    return ids


def _sync_knowledge_base_index() -> None:
    collection = get_chroma_client().get_or_create_collection(INDEX_NAME)
    kb_docs = load_knowledge_base_documents()

    indexed_files: set[str] = set()
    existing = collection.get(where={"source": KB_SOURCE}, include=["metadatas"])
    for metadata in existing.get("metadatas", []):
        if not isinstance(metadata, dict):
            continue
        file_name = metadata.get("kb_file")
        if isinstance(file_name, str):
            indexed_files.add(normalize_filename(file_name))

    for file_name, text in kb_docs:
        normalized_file_name = normalize_filename(file_name)
        file_path = UPLOAD_DIR / file_name
        if normalized_file_name in indexed_files:
            remove_uploaded_file(file_path)
            continue

        chunks = splitter.split_text(text)
        if not chunks:
            remove_uploaded_file(file_path)
            continue

        embeddings = get_embedding_model().encode_document(chunks, normalize_embeddings=False)
        ids = [str(uuid4()) for _ in range(len(chunks))]
        metadata = {
            "source": KB_SOURCE,
            "kb_file": normalized_file_name,
            "kb_link": f"kb://{normalized_file_name}",
            "category": "knowledge_base",
        }
        collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings.tolist(),
            metadatas=[metadata.copy() for _ in range(len(chunks))],
        )
        remove_uploaded_file(file_path)


def list_knowledge_base_files() -> list[dict[str, str]]:
    _sync_knowledge_base_index()
    collection = get_chroma_client().get_or_create_collection(INDEX_NAME)
    existing = collection.get(where={"source": KB_SOURCE}, include=["metadatas"])

    seen: set[str] = set()
    files: list[dict[str, str]] = []
    for metadata in existing.get("metadatas", []):
        if not isinstance(metadata, dict):
            continue
        file_name = metadata.get("kb_file")
        if not isinstance(file_name, str):
            continue
        normalized_file_name = normalize_filename(file_name)
        if normalized_file_name in seen:
            continue
        seen.add(normalized_file_name)
        files.append(
            {
                "name": normalized_file_name,
                "link": str(metadata.get("kb_link", f"kb://{normalized_file_name}")).replace(
                    file_name,
                    normalized_file_name,
                ),
            }
        )

    files.sort(key=lambda item: item["name"].lower())
    return files


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return str(text)

    with contextlib.suppress(UnicodeDecodeError):
        text = text.encode("utf-8").decode("unicode_escape")

    try:
        if text.startswith('"') and text.endswith('"'):
            text = json.loads(text)
        else:
            text = json.loads(f'"{text}"')
    except (json.JSONDecodeError, TypeError):
        pass

    if re.search(r"\\u[0-9a-fA-F]{4}", text):
        with contextlib.suppress(UnicodeDecodeError):
            text = text.encode("utf-8").decode("unicode_escape")

    def replace_unicode(match: re.Match[str]) -> str:
        try:
            return chr(int(match.group(1), 16))
        except ValueError:
            return match.group(0)

    return re.sub(r"\\u([0-9a-fA-F]{4})", replace_unicode, text)


async def retrieve(
    query: str,
    metadata_filter: dict[str, Any] | None = None,
    search_string: str | None = None,
    n_results: int = 10,
) -> list[str]:
    _sync_knowledge_base_index()
    collection = get_chroma_client().get_or_create_collection(INDEX_NAME)
    logger.info("Retrieving for query: '%s...'", query[:50])

    embedding = get_embedding_model().encode_query(query, normalize_embeddings=False)
    params = {"query_embeddings": [embedding.tolist()], "n_results": n_results}

    if search_string:
        params["where_document"] = {"$contains": search_string}

    queries = []
    if metadata_filter:
        if len(metadata_filter) == 0:
            pass  # пустой фильтр не передаём
        elif len(metadata_filter) == 1:
            params["where"] = metadata_filter
        else:
            # Несколько полей → оборачиваем в $and
            params["where"] = {"$and": [{k: v} for k, v in metadata_filter.items()]}
            
    kb_params = params.copy()
    kb_params["where"] = {"source": KB_SOURCE}
    queries.append(collection.query(**kb_params, include=["documents", "metadatas", "distances"]))

    combined_rows: list[tuple[str, dict[str, Any] | None, float]] = []
    for query_result in queries:
        documents = query_result.get("documents") or []
        metadatas = query_result.get("metadatas") or []
        distances = query_result.get("distances") or []
        if not documents or not metadatas or not distances:
            continue
        for document, metadata, distance in zip(documents[0], metadatas[0], distances[0], strict=False):
            combined_rows.append((document, metadata, distance))

    combined_rows.sort(key=lambda row: row[2])

    cleaned_results = []
    for document, metadata, distance in combined_rows[:n_results]:
        cleaned_doc = clean_text(document)

        cleaned_metadata: dict[str, Any] = {}
        safe_metadata = metadata if isinstance(metadata, dict) else {}
        for key, value in safe_metadata.items():
            if isinstance(value, str):
                cleaned_metadata[key] = clean_text(value)
            else:
                cleaned_metadata[key] = value

        raw_file_name = str(cleaned_metadata.get("kb_file", ""))
        file_name = normalize_filename(raw_file_name)
        file_link = str(cleaned_metadata.get("kb_link", "")).replace(raw_file_name, file_name)
        cleaned_results.append(
            f"**Relevance score:** {round(distance, 2)}\n"
            f"**Source:** {cleaned_metadata.get('source', '')}\n"
            f"**Category:** {cleaned_metadata.get('category', '')}\n"
            f"**File:** {file_name}\n"
            f"**Link:** {file_link}\n"
            "**Document:**\n"
            f"{cleaned_doc}"
        )

    return cleaned_results


def delete_old_data(max_age_hours: int = 3) -> None:
    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
    cutoff_str = cutoff.isoformat()
    collection = get_chroma_client().get_or_create_collection(INDEX_NAME)
    old_docs = collection.get(where={"timestamp": {"$lt": cutoff_str}})
    if old_docs["ids"]:
        collection.delete(ids=old_docs["ids"])
        logger.info("Removed %s outdated RAG results", len(old_docs["ids"]))
