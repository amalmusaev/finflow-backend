from collections.abc import Sequence
from datetime import date as dt_date
from decimal import Decimal
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_db
from src.core.exceptions import (
    AccountNotFoundError,
    TransferNotFoundError,
    ValidationError,
)
from src.models.transfer import Transfer
from src.repositories.accounts import AccountRepository
from src.repositories.transfers import TransferRepository
from src.schemas.accounts import AccountCreate
from src.schemas.enums import AccountType
from src.schemas.transfers import (
    CashDepositCreate,
    CashWithdrawalCreate,
    TransferCreate,
    TransferUpdate,
)


class TransferService:
    """Сервис для управления переводами между счетами и обналичиванием"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transfer_repo = TransferRepository(session)
        self.account_repo = AccountRepository(session)

    async def create_transfer(self, transfer_in: TransferCreate) -> Transfer:
        """Создание перевода между счетами с корректировкой балансов"""
        if transfer_in.from_account_id == transfer_in.to_account_id:
            raise ValidationError("Счет списания и счет зачисления не могут совпадать")

        from_account = await self.account_repo.get(transfer_in.from_account_id)
        if not from_account:
            raise AccountNotFoundError(transfer_in.from_account_id)
        if not from_account.is_active:
            raise ValidationError(f"Счет списания '{from_account.name}' деактивирован")

        to_account = await self.account_repo.get(transfer_in.to_account_id)
        if not to_account:
            raise AccountNotFoundError(transfer_in.to_account_id)
        if not to_account.is_active:
            raise ValidationError(f"Счет зачисления '{to_account.name}' деактивирован")

        # Определение суммы зачисления
        to_amount = transfer_in.to_amount
        if to_amount is None:
            if from_account.currency != to_account.currency:
                raise ValidationError(
                    f"Валюты счетов не совпадают ({from_account.currency} -> {to_account.currency}). "
                    "Укажите сумму зачисления 'to_amount'."
                )
            to_amount = transfer_in.amount

        # Корректировка балансов счетов
        from_account.balance -= (transfer_in.amount + transfer_in.fee)
        to_account.balance += to_amount

        # Сохранение перевода в БД
        transfer_data = transfer_in.model_dump()
        transfer_data["to_amount"] = to_amount
        return await self.transfer_repo.create(transfer_data)

    async def create_cash_withdrawal(self, cash_in: CashWithdrawalCreate) -> Transfer:
        """Снятие наличных (обналичивание с карты/банка в наличные)"""
        from_account = await self.account_repo.get(cash_in.from_account_id)
        if not from_account:
            raise AccountNotFoundError(cash_in.from_account_id)
        if not from_account.is_active:
            raise ValidationError(f"Счет списания '{from_account.name}' деактивирован")

        to_account_id = cash_in.to_account_id
        if to_account_id is not None:
            to_account = await self.account_repo.get(to_account_id)
            if not to_account:
                raise AccountNotFoundError(to_account_id)
            if to_account.type != AccountType.CASH:
                raise ValidationError(f"Целевой счет '{to_account.name}' не является счетом наличных (cash)")
        else:
            # Ищем активный счет наличных в соответствующей валюте
            cash_accounts = await self.account_repo.list_accounts(
                is_active=True,
                account_type=AccountType.CASH,
                currency=from_account.currency,
            )
            if cash_accounts:
                to_account = cash_accounts[0]
                to_account_id = to_account.id
            else:
                # Автоматически создаем счет "Наличные"
                new_cash_account = await self.account_repo.create(
                    AccountCreate(
                        name="Наличные",
                        type=AccountType.CASH,
                        currency=from_account.currency,
                        balance=Decimal("0.00"),
                    )
                )
                to_account_id = new_cash_account.id

        transfer_create = TransferCreate(
            from_account_id=cash_in.from_account_id,
            to_account_id=to_account_id,
            amount=cash_in.amount,
            to_amount=cash_in.amount,
            fee=cash_in.fee,
            date=cash_in.date,
            description=cash_in.description or "Снятие наличных",
        )
        return await self.create_transfer(transfer_create)

    async def create_cash_deposit(self, cash_in: CashDepositCreate) -> Transfer:
        """Внесение наличных на счет/карту"""
        to_account = await self.account_repo.get(cash_in.to_account_id)
        if not to_account:
            raise AccountNotFoundError(cash_in.to_account_id)
        if not to_account.is_active:
            raise ValidationError(f"Счет зачисления '{to_account.name}' деактивирован")

        from_account_id = cash_in.from_account_id
        if from_account_id is not None:
            from_account = await self.account_repo.get(from_account_id)
            if not from_account:
                raise AccountNotFoundError(from_account_id)
            if from_account.type != AccountType.CASH:
                raise ValidationError(f"Счет списания '{from_account.name}' не является счетом наличных (cash)")
        else:
            # Ищем активный счет наличных в соответствующей валюте
            cash_accounts = await self.account_repo.list_accounts(
                is_active=True,
                account_type=AccountType.CASH,
                currency=to_account.currency,
            )
            if not cash_accounts:
                raise ValidationError(
                    f"Не найден счет наличных с валютой {to_account.currency}. "
                    "Создайте счет наличных или укажите from_account_id."
                )
            from_account = cash_accounts[0]
            from_account_id = from_account.id

        transfer_create = TransferCreate(
            from_account_id=from_account_id,
            to_account_id=cash_in.to_account_id,
            amount=cash_in.amount,
            to_amount=cash_in.amount,
            fee=cash_in.fee,
            date=cash_in.date,
            description=cash_in.description or "Внесение наличных",
        )
        return await self.create_transfer(transfer_create)

    async def get_transfers(
        self,
        account_id: UUID | None = None,
        from_account_id: UUID | None = None,
        to_account_id: UUID | None = None,
        from_date: dt_date | None = None,
        to_date: dt_date | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Transfer]:
        """Получение списка переводов с фильтрацией и пагинацией"""
        return await self.transfer_repo.list_transfers(
            account_id=account_id,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            from_date=from_date,
            to_date=to_date,
            offset=offset,
            limit=limit,
        )

    async def get_transfer(self, transfer_id: UUID) -> Transfer:
        """Получение конкретного перевода по ID"""
        transfer = await self.transfer_repo.get(transfer_id)
        if not transfer:
            raise TransferNotFoundError(transfer_id)
        return transfer

    async def update_transfer(
        self,
        transfer_id: UUID,
        transfer_update: TransferUpdate,
    ) -> Transfer:
        """Обновление параметров перевода с пересчетом балансов счетов"""
        transfer = await self.get_transfer(transfer_id)

        # 1. Откат старого перевода с балансов
        old_from_account = await self.account_repo.get(transfer.from_account_id)
        if old_from_account:
            old_from_account.balance += (transfer.amount + transfer.fee)

        old_to_account = await self.account_repo.get(transfer.to_account_id)
        if old_to_account:
            old_to_account.balance -= transfer.to_amount

        # 2. Вычисление новых параметров
        new_from_account_id = (
            transfer_update.from_account_id
            if transfer_update.from_account_id is not None
            else transfer.from_account_id
        )
        new_to_account_id = (
            transfer_update.to_account_id
            if transfer_update.to_account_id is not None
            else transfer.to_account_id
        )

        if new_from_account_id == new_to_account_id:
            raise ValidationError("Счет списания и счет зачисления не могут совпадать")

        new_from_account = await self.account_repo.get(new_from_account_id)
        if not new_from_account:
            raise AccountNotFoundError(new_from_account_id)

        new_to_account = await self.account_repo.get(new_to_account_id)
        if not new_to_account:
            raise AccountNotFoundError(new_to_account_id)

        new_amount = (
            transfer_update.amount
            if transfer_update.amount is not None
            else transfer.amount
        )
        new_fee = (
            transfer_update.fee
            if transfer_update.fee is not None
            else transfer.fee
        )

        if transfer_update.to_amount is not None:
            new_to_amount = transfer_update.to_amount
        elif transfer_update.amount is not None:
            if new_from_account.currency == new_to_account.currency:
                new_to_amount = new_amount
            else:
                new_to_amount = transfer.to_amount
        else:
            new_to_amount = transfer.to_amount

        # 3. Применение новых сумм к балансам
        new_from_account.balance -= (new_amount + new_fee)
        new_to_account.balance += new_to_amount

        # 4. Сохранение изменений в объекте
        update_dict = transfer_update.model_dump(exclude_unset=True)
        if "to_amount" not in update_dict and new_to_amount != transfer.to_amount:
            update_dict["to_amount"] = new_to_amount

        return await self.transfer_repo.update(transfer, update_dict)

    async def delete_transfer(self, transfer_id: UUID) -> None:
        """Удаление перевода с возвратом сумм на балансы счетов"""
        transfer = await self.get_transfer(transfer_id)

        from_account = await self.account_repo.get(transfer.from_account_id)
        if from_account:
            from_account.balance += (transfer.amount + transfer.fee)

        to_account = await self.account_repo.get(transfer.to_account_id)
        if to_account:
            to_account.balance -= transfer.to_amount

        await self.transfer_repo.delete(transfer)


async def get_transfer_service(
    session: AsyncSession = Depends(get_db),
) -> TransferService:
    """FastAPI Dependency для получения TransferService"""
    return TransferService(session)
