from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import Account
from src.repositories.base import BaseRepository
from src.schemas.accounts import AccountCreate, AccountUpdate
from src.schemas.enums import AccountType, Currency


class AccountRepository(BaseRepository[Account, AccountCreate, AccountUpdate]):
    """Репозиторий для работы со счетами"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Account, session)

    async def list_accounts(
        self,
        is_active: bool | None = None,
        account_type: AccountType | None = None,
        currency: Currency | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Account]:
        """Получить список счетов с фильтрацией"""
        query = select(Account)

        if is_active is not None:
            query = query.where(Account.is_active == is_active)
        if account_type is not None:
            query = query.where(Account.type == account_type)
        if currency is not None:
            query = query.where(Account.currency == currency)

        query = query.offset(offset).limit(limit).order_by(Account.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_balance(self, account_id: UUID, amount_delta: Decimal) -> Account | None:
        """Изменить баланс счета на заданную величину (+/-)"""
        account = await self.get(account_id)
        if not account:
            return None
        account.balance += amount_delta
        self.session.add(account)
        await self.session.flush()
        await self.session.refresh(account)
        return account
