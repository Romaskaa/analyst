from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from ...utils.commons import current_datetime
from .base import Entity


class User(Entity):
    """Пользователь системы"""

    email: EmailStr = Field(..., description="Email пользователя")
    password_hash: str = Field(..., description="Хеш пароля")
    is_active: bool = Field(True, description="Активен ли пользователь")


class RefreshToken(Entity):
    """Схема 'refresh' токена - для ротации"""

    user_id: UUID = Field(..., description="ID пользователя, которому выдан токен")
    token: str = Field(..., description="Refresh токен")
    expires_at: datetime = Field(..., description="Дата истечения")
    revoked: bool = Field(False, description="Отозван ли токен")
    revoked_at: datetime | None = Field(None, description="Время отзыва")

    @property
    def is_valid(self) -> bool:
        """Проверка токена на валидность"""

        return not self.revoked and self.expires_at < current_datetime()
