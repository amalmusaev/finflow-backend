from collections.abc import Sequence
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_db
from src.core.exceptions import CategoryNotFoundError
from src.models.category import Category
from src.repositories.categories import CategoryRepository
from src.schemas.categories import CategoryCreate, CategoryUpdate
from src.schemas.enums import OperationType


class CategoryService:
    """Сервис для управления категориями доходов и расходов"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CategoryRepository(session)

    async def create_category(self, category_in: CategoryCreate) -> Category:
        """Создание новой категории"""
        return await self.repo.create(category_in)

    async def get_categories(
        self,
        category_type: OperationType | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Category]:
        """Получение списка категорий с фильтрацией по типу"""
        return await self.repo.list_categories(
            category_type=category_type,
            offset=offset,
            limit=limit,
        )

    async def get_category(self, category_id: UUID) -> Category:
        """Получение категории по ID"""
        category = await self.repo.get(category_id)
        if not category:
            raise CategoryNotFoundError(category_id)
        return category

    async def update_category(
        self, category_id: UUID, category_update: CategoryUpdate
    ) -> Category:
        """Обновление категории"""
        category = await self.get_category(category_id)
        return await self.repo.update(category, category_update)

    async def delete_category(self, category_id: UUID) -> None:
        """Удаление категории"""
        category = await self.get_category(category_id)
        await self.repo.delete(category)


async def get_category_service(
    session: AsyncSession = Depends(get_db),
) -> CategoryService:
    """FastAPI Dependency для получения CategoryService"""
    return CategoryService(session)
