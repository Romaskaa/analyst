from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.entities.base import Entity
from ..base import Base


class SqlAlchemyRepository[EntityT: Entity, ModelT: Base]:
    entity: type[EntityT]
    model: type[ModelT]

    def __init__(self, session: AsyncSession, autocommit: bool = False) -> None:
        self.session = session
        self.autocommit = autocommit

    async def create(self, entity: EntityT) -> EntityT:
        stmt = insert(self.model).values(**entity.model_dump()).returning(self.model)
        result = await self.session.execute(stmt)
        model = result.scalar_one()
        await self.session.flush()
        if self.autocommit:
            await self.session.commit()
        return self.entity.model_validate(model)

    async def read(self, uid: UUID) -> EntityT | None:
        stmt = select(self.model).where(self.model.id == uid)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.entity.model_validate(model)

    async def read_all(self, page: int, limit: int) -> list[EntityT]:
        offset = (page - 1) * limit
        stmt = select(self.model).offset(offset).limit(limit)
        results = await self.session.execute(stmt)
        models = results.scalars().all()
        return [self.entity.model_validate(model) for model in models]

    async def update(self, uid: UUID, **kwargs) -> EntityT | None:
        stmt = (
            update(self.model)
            .where(self.model.id == uid)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        if self.autocommit:
            await self.session.commit()
        model = result.scalar_one_or_none()
        return None if model is None else self.entity.model_validate(model)

    async def upsert(self, entity: EntityT) -> None:
        model = self.model(**entity.model_dump())
        await self.session.merge(model)

    async def delete(self, uid: UUID) -> None:
        stmt = delete(self.model).where(self.model.id == uid)
        await self.session.execute(stmt)
        if self.autocommit:
            await self.session.commit()
