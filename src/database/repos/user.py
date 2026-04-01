from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.entities import User
from ...schemas import SEOResult
from ..models import SEOResultOrm, UserOrm
from .base import SqlAlchemyRepository


class UserRepository(SqlAlchemyRepository[User, UserOrm]):
    entity = User
    model = UserOrm

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(self.model).where(self.model.email == email)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.entity.model_validate(model)


class UserSEORepository:
    model = SEOResultOrm
    schema = SEOResult

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, entity: SEOResult) -> None:
        stmt = insert(self.model).values(**entity.model_dump())
        await self.session.execute(stmt)
        await self.session.flush()
        await self.session.commit()

    async def read_paginated(self, user_id: str, limit: int, page: int) -> list:
        offset = (page - 1) * limit
        stmt = select(self.model).where(self.model.user_id == user_id).offset(offset).limit(limit)
        results = await self.session.execute(stmt)
        models = results.scalars().all()
        return [self.schema.model_validate(model) for model in models]
