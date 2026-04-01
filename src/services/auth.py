from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.entities import User
from ..core.errors import (
    InvitationExpiredError,
    NotFoundError,
    UnauthorizedError,
    UserAlreadyExistsError,
)
from ..database.repos import InvitationRepository, UserRepository
from ..schemas import TokensPair, TokenType, UserCreateForm
from ..settings import settings
from ..utils.commons import get_expiration_timestamp
from ..utils.secutiry import generate_token, hash_password, verify_password


def create_tokens_pair(payload: dict[str, Any]) -> TokensPair:
    """Создаёт пару токенов 'access' и 'refresh'"""

    access_token_expires_in = timedelta(minutes=settings.jwt.access_token_expires_in_minutes)
    refresh_token_expires_in = timedelta(days=settings.jwt.refresh_token_expires_in_days)
    access_token = generate_token(
        token_type=TokenType.ACCESS,
        payload=payload,
        expires_in=access_token_expires_in,
    )
    refresh_token = generate_token(
        token_type=TokenType.REFRESH, payload=payload, expires_in=refresh_token_expires_in
    )
    return TokensPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=get_expiration_timestamp(access_token_expires_in),
    )


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.invitation_repo = InvitationRepository(session)

    async def register(self, token: str, form_data: UserCreateForm) -> TokensPair:
        """Регистрация нового пользователя"""

        invitation = await self.invitation_repo.get_by_token(token)
        if invitation is None:
            raise NotFoundError("Invitation not found")
        if not invitation.is_valid:
            raise InvitationExpiredError("Invitation expired or already used")
        existing_user = await self.user_repo.get_by_email(invitation.email)
        if existing_user is not None:
            raise UserAlreadyExistsError(f"User with email - '{invitation.email}' already exists'")

        user = User(
            email=invitation.email,
            password_hash=hash_password(form_data.password),
        )  # type: ignore  # noqa: PGH003
        await self.user_repo.create(user)
        invitation.mark_as_used()
        await self.invitation_repo.upsert(invitation)

        tokens = await self._create_tokens_for_user(user)
        await self.session.commit()
        return tokens

    async def authenticate(self, email: str, password: str) -> TokensPair:
        """Аутентификация пользователя по логин + пароль"""

        user = await self.user_repo.get_by_email(email)
        if user is None:
            raise UnauthorizedError(f"User not found by email - '{email}'")
        if not verify_password(password, user.password_hash) and not user.is_active:
            raise UnauthorizedError("Invalid password or user is not active")

        tokens = await self._create_tokens_for_user(user)
        await self.session.commit()
        return tokens

    async def _create_tokens_for_user(self, user: User) -> TokensPair:
        """Выпуск пары токенов + сохранение 'refresh' токена для возможности ротации"""

        payload = {
            "iss": settings.app.url,
            "sub": f"{user.id}",
            "email": user.email,
        }
        return create_tokens_pair(payload)
