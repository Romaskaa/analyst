import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from pydantic import HttpUrl

from ...agents import rag
from ...agents.subagents import agent_aio
from ...agents.subagents.utils import parce_site_markups
from ...agents.workflow import agent
from ...database.repos.user import UserSEORepository
from ...schemas import SEOResult
from ..dependencies import get_repo

router_seo = APIRouter()


@router_seo.get("/seo/{user_id}", status_code=status.HTTP_200_OK)
async def get_seo(
    url: HttpUrl, user_id: str, repository: UserSEORepository = Depends(get_repo)
) -> dict:
    url_str = url.encoded_string()
    result = await agent.ainvoke({"url": url_str})  # type: ignore  # noqa: PGH003
    del result["html"]
    del result["markdown"]
    await rag.indexing(
        text=json.dumps(result),
        metadata={
            "tenant_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
    schema = SEOResult(user_id=user_id, result=result)  # type: ignore  # noqa: PGH003
    await repository.create(entity=schema)
    return result


@router_seo.get("/aio/{user_id}", status_code=status.HTTP_200_OK)
async def get_aio(
    url: HttpUrl, user_id: str, repository: UserSEORepository = Depends(get_repo)
) -> dict:
    url_str = url.encoded_string()
    markdown, html = await parce_site_markups(url_str)
    result = await agent_aio.ainvoke(
        {"url": url_str, "html": html, "markdown": markdown}  # type: ignore  # noqa: PGH003
    )  # type: ignore  # noqa: PGH003
    del result["html"]
    del result["markdown"]
    await rag.indexing(
        text=json.dumps(result),
        metadata={
            "tenant_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
    schema = SEOResult(user_id=user_id, result=result)  # type: ignore  # noqa: PGH003
    await repository.create(entity=schema)
    return result
