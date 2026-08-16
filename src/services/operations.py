from collections.abc import Sequence
from datetime import date as dt_date
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_db
from src.core.exceptions import (
    AccountNotFoundError,
    CategoryNotFoundError,
    OperationNotFoundError,
)
from src.models.operation import Operation
from src.repositories.accounts import AccountRepository
from src.repositories.categories import CategoryRepository
from src.repositories.operations import OperationRepository
from src.schemas.enums import OperationType
from src.schemas.operations import OperationCreate, OperationUpdate


class OperationService:
    """Сервис для управления финансовыми операциями и балансом счетов"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.op_repo = OperationRepository(session)
        self.account_repo = AccountRepository(session)
        self.category_repo = CategoryRepository(session)

    async def create_operation(self, operation_in: OperationCreate) -> Operation:
        """Создание новой операции с обновлением баланса счета"""
        account = await self.account_repo.get(operation_in.account_id)
        if not account:
            raise AccountNotFoundError(operation_in.account_id)

        category = await self.category_repo.get(operation_in.category_id)
        if not category:
            raise CategoryNotFoundError(operation_in.category_id)

        # Корректировка баланса счета
        balance_delta = (
            operation_in.amount
            if operation_in.type == OperationType.INCOME
            else -operation_in.amount
        )
        account.balance += balance_delta

        return await self.op_repo.create(operation_in)

    async def get_operations(
        self,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        operation_type: OperationType | None = None,
        from_date: dt_date | None = None,
        to_date: dt_date | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Operation]:
        """Получение списка операций с фильтрацией и пагинацией"""
        return await self.op_repo.list_operations(
            account_id=account_id,
            category_id=category_id,
            operation_type=operation_type,
            from_date=from_date,
            to_date=to_date,
            offset=offset,
            limit=limit,
        )

    async def get_operation(self, operation_id: UUID) -> Operation:
        """Получение конкретной операции по ID"""
        operation = await self.op_repo.get(operation_id)
        if not operation:
            raise OperationNotFoundError(operation_id)
        return operation

    async def update_operation(
        self,
        operation_id: UUID,
        operation_update: OperationUpdate,
    ) -> Operation:
        """Обновление операции с пересчетом баланса счетов при необходимости"""
        operation = await self.get_operation(operation_id)

        # Валидация нового счета
        if (
            operation_update.account_id is not None
            and operation_update.account_id != operation.account_id
        ):
            new_account = await self.account_repo.get(operation_update.account_id)
            if not new_account:
                raise AccountNotFoundError(operation_update.account_id)

        # Валидация новой категории
        if (
            operation_update.category_id is not None
            and operation_update.category_id != operation.category_id
        ):
            new_category = await self.category_repo.get(operation_update.category_id)
            if not new_category:
                raise CategoryNotFoundError(operation_update.category_id)

        # Откат старой суммы с исходного счета
        old_account = await self.account_repo.get(operation.account_id)
        if old_account:
            old_delta = (
                operation.amount
                if operation.type == OperationType.INCOME
                else -operation.amount
            )
            old_account.balance -= old_delta

        updated_op = await self.op_repo.update(operation, operation_update)

        # Применение новой суммы к целевому счету
        target_account = await self.account_repo.get(updated_op.account_id)
        if target_account:
            new_delta = (
                updated_op.amount
                if updated_op.type == OperationType.INCOME
                else -updated_op.amount
            )
            target_account.balance += new_delta

        return updated_op

    async def delete_operation(self, operation_id: UUID) -> None:
        """Удаление операции и откат ее влияния на баланс счета"""
        operation = await self.get_operation(operation_id)

        account = await self.account_repo.get(operation.account_id)
        if account:
            rollback_delta = (
                -operation.amount
                if operation.type == OperationType.INCOME
                else operation.amount
            )
            account.balance += rollback_delta

        await self.op_repo.delete(operation)


async def get_operation_service(
    session: AsyncSession = Depends(get_db),
) -> OperationService:
    """FastAPI Dependency для получения OperationService"""
    return OperationService(session)
