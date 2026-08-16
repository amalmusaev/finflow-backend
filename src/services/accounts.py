from collections.abc import Sequence
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_db
from src.core.exceptions import AccountNotFoundError
from src.models.account import Account
from src.repositories.accounts import AccountRepository
from src.schemas.accounts import AccountCreate, AccountUpdate
from src.schemas.enums import AccountType, Currency


class AccountService:
    """Сервис для управления финансовыми счетами пользователя"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AccountRepository(session)

    async def create_account(self, account_in: AccountCreate) -> Account:
        """Создание нового счета"""
        return await self.repo.create(account_in)

    async def get_accounts(
        self,
        is_active: bool | None = None,
        account_type: AccountType | None = None,
        currency: Currency | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Account]:
        """Получение списка счетов с фильтрацией и пагинацией"""
        return await self.repo.list_accounts(
            is_active=is_active,
            account_type=account_type,
            currency=currency,
            offset=offset,
            limit=limit,
        )

    async def get_account(self, account_id: UUID) -> Account:
        """Получение конкретного счета по ID"""
        account = await self.repo.get(account_id)
        if not account:
            raise AccountNotFoundError(account_id)
        return account

    async def update_account(
        self, account_id: UUID, account_update: AccountUpdate
    ) -> Account:
        """Обновление счета"""
        account = await self.get_account(account_id)
        return await self.repo.update(account, account_update)

    async def delete_account(self, account_id: UUID) -> None:
        """Удаление счета"""
        account = await self.get_account(account_id)
        await self.repo.delete(account)


async def get_account_service(
    session: AsyncSession = Depends(get_db),
) -> AccountService:
    """FastAPI Dependency для получения AccountService"""
    return AccountService(session)
