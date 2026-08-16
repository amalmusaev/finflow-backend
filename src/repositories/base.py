from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import BaseModel as DBBaseModel

ModelType = TypeVar("ModelType", bound=DBBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Базовый обобщенный асинхронный репозиторий для CRUD операций"""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get(self, id: UUID) -> ModelType | None:
        """Получить сущность по ID"""
        query = select(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Получить список всех сущностей с пагинацией"""
        query = select(self.model).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, schema: CreateSchemaType | dict[str, Any]) -> ModelType:
        """Создать новую сущность"""
        data = schema.model_dump() if isinstance(schema, BaseModel) else schema
        db_obj = self.model(**data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: ModelType,
        schema: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """Обновить существующую сущность (частичное обновление)"""
        if isinstance(schema, BaseModel):
            update_data = schema.model_dump(exclude_unset=True)
        else:
            update_data = schema

        for field, value in update_data.items():
            if hasattr(db_obj, field) and value is not None:
                setattr(db_obj, field, value)

        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: ModelType) -> None:
        """Удалить сущность"""
        await self.session.delete(db_obj)
        await self.session.flush()
