from collections.abc import AsyncIterable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import UnauthorizedError
from ..database.conn import session_factory
from ..database.repos.user import UserSEORepository
from ..services.auth import AuthService
from ..services.invitation import InvitationService
from ..utils.secutiry import validate_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="JWT Bearer",
    description="Вставьте JWT-токен (access token)",
)


async def get_db() -> AsyncIterable[AsyncSession]:
    async with session_factory() as session:
        yield session


def get_repo(session: AsyncSession = Depends(get_db)) -> UserSEORepository:
    return UserSEORepository(session)


def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(session)


def get_invitation_service(session: AsyncSession = Depends(get_db)) -> InvitationService:
    return InvitationService(session)


class CurrentUser(BaseModel):
    """Авторизованный пользователь, который делает запрос к сервису"""

    user_id: UUID
    email: EmailStr


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> CurrentUser:
    """Получение текущего авторизованного пользователя"""

    payload = validate_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Invalid token: missing sub claim")
    return CurrentUser(
        user_id=user_id,
        email=payload.get("email"),  # type: ignore  # noqa: PGH003
        role=payload.get("role"),  # type: ignore  # noqa: PGH003
    )
