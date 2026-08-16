from collections.abc import Sequence
from datetime import date as dt_date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.operation import Operation
from src.repositories.base import BaseRepository
from src.schemas.enums import OperationType
from src.schemas.operations import OperationCreate, OperationUpdate


class OperationRepository(BaseRepository[Operation, OperationCreate, OperationUpdate]):
    """Репозиторий для работы с финансовыми операциями"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Operation, session)

    async def list_operations(
        self,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        operation_type: OperationType | None = None,
        from_date: dt_date | None = None,
        to_date: dt_date | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Operation]:
        """Получить список операций с фильтрацией и пагинацией"""
        query = select(Operation)

        if account_id is not None:
            query = query.where(Operation.account_id == account_id)
        if category_id is not None:
            query = query.where(Operation.category_id == category_id)
        if operation_type is not None:
            query = query.where(Operation.type == operation_type)
        if from_date is not None:
            query = query.where(Operation.date >= from_date)
        if to_date is not None:
            query = query.where(Operation.date <= to_date)

        query = query.offset(offset).limit(limit).order_by(Operation.date.desc(), Operation.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()
