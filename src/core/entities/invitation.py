import secrets
from datetime import datetime

from pydantic import EmailStr, Field

from ...utils.commons import current_datetime
from .base import Entity


def generate_invite_token(length: int = 32) -> str:
    """Генерация токена для активации приглашения"""

    return secrets.token_urlsafe(length)


class Invitation(Entity):
    """Приглашение пользователя в тикет-систему"""

    email: EmailStr = Field(..., description="Email пользователя")
    token: str = Field(
        default_factory=generate_invite_token,
        description="Уникальный токен для ссылки-приглашения",
    )
    expires_at: datetime = Field(..., description="Время истечения приглашения")
    is_used: bool = Field(False, description="Использовано ли приглашение")

    @property
    def is_valid(self) -> bool:
        """Актуально ли приглашение"""

        return not self.is_used and self.expires_at > current_datetime()

    def mark_as_used(self) -> None:
        """Пометить, как использованное"""

        self.is_used = True
