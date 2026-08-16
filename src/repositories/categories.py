from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.category import Category
from src.repositories.base import BaseRepository
from src.schemas.categories import CategoryCreate, CategoryUpdate
from src.schemas.enums import OperationType


class CategoryRepository(BaseRepository[Category, CategoryCreate, CategoryUpdate]):
    """Репозиторий для работы с категориями доходов и расходов"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Category, session)

    async def list_categories(
        self,
        category_type: OperationType | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Category]:
        """Получить список категорий с фильтрацией по типу"""
        query = select(Category)

        if category_type is not None:
            query = query.where(Category.type == category_type)

        query = query.offset(offset).limit(limit).order_by(Category.name.asc())
        result = await self.session.execute(query)
        return result.scalars().all()
