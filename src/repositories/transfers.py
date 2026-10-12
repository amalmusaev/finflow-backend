from collections.abc import Sequence
from datetime import date as dt_date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transfer import Transfer
from src.repositories.base import BaseRepository
from src.schemas.transfers import TransferCreate, TransferUpdate


class TransferRepository(BaseRepository[Transfer, TransferCreate, TransferUpdate]):
    """Репозиторий для работы с переводами между счетами"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Transfer, session)

    async def list_transfers(
        self,
        account_id: UUID | None = None,
        from_account_id: UUID | None = None,
        to_account_id: UUID | None = None,
        from_date: dt_date | None = None,
        to_date: dt_date | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Transfer]:
        """Получить список переводов с фильтрацией и пагинацией"""
        query = select(Transfer)

        if account_id is not None:
            query = query.where(
                or_(Transfer.from_account_id == account_id, Transfer.to_account_id == account_id)
            )
        if from_account_id is not None:
            query = query.where(Transfer.from_account_id == from_account_id)
        if to_account_id is not None:
            query = query.where(Transfer.to_account_id == to_account_id)
        if from_date is not None:
            query = query.where(Transfer.date >= from_date)
        if to_date is not None:
            query = query.where(Transfer.date <= to_date)

        query = query.offset(offset).limit(limit).order_by(Transfer.date.desc(), Transfer.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()
