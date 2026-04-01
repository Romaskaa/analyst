from fastapi import APIRouter, Depends, status

from ...database.repos.user import UserSEORepository
from ..dependencies import get_repo

router_history = APIRouter()


@router_history.get("/results/{user_id}", status_code=status.HTTP_200_OK)
async def get_results(
    user_id: str, page: int = 1, limit: int = 10, repository: UserSEORepository = Depends(get_repo)
) -> list:
    return await repository.read_paginated(user_id=user_id, page=page, limit=limit)
