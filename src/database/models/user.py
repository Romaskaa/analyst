from typing import Any
from uuid import UUID

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class UserOrm(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool]


class SEOResultOrm(Base):
    __tablename__ = "seo_result"
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), unique=False, nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
