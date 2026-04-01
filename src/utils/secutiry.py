import logging
from datetime import timedelta
from typing import Any
from uuid import uuid4

import jwt
from passlib.context import CryptContext

from ..core.errors import UnauthorizedError
from ..schemas import TokenType
from ..settings import settings
from .commons import current_datetime

ALGORITHM = "HS256"

# Хеширование паролей
MEMORY_COST = 100  # Размер выделяемой памяти в mb
TIME_COST = 2
PARALLELISM = 2
SALT_SIZE = 16
ROUNDS = 14  # Количество раундов для хеширования

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    argon2__memory_cost=MEMORY_COST,
    argon2__time_cost=TIME_COST,
    argon2__parallelism=PARALLELISM,
    argon2__salt_size=SALT_SIZE,
    bcrypt__rounds=ROUNDS,
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """Создание хеша для пароля"""

    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Сверяет ожидаемый пароль с хэшем пароля"""

    return pwd_context.verify(plain_password, password_hash)


def generate_token(
    token_type: TokenType,
    payload: dict[str, Any],
    expires_in: timedelta,
) -> str:
    """Подписание токена"""

    now = current_datetime()
    expires_at = now + expires_in
    payload.update(
        {
            "exp": expires_at.timestamp(),
            "iat": now.timestamp(),
            "token_type": token_type.value,
            "jti": str(uuid4()),
        }
    )
    return jwt.encode(
        payload=payload,
        key=settings.secret_key,
        algorithm=ALGORITHM,
    )


def validate_token(token: str) -> dict[str, Any]:
    """Декодирование токена"""

    try:
        return jwt.decode(
            token, key=settings.secret_key, algorithms=[ALGORITHM], options={"verify_aud": False}
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token signature expired!") from None
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid token!") from None
