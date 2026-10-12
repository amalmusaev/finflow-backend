from datetime import date as dt_date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TransferBase(BaseModel):
    """Базовая схема перевода между счетами"""
    from_account_id: UUID = Field(..., description="ID счета списания")
    to_account_id: UUID = Field(..., description="ID счета зачисления")
    amount: Decimal = Field(..., gt=Decimal("0"), description="Сумма списания со счета-источника")
    to_amount: Decimal | None = Field(None, gt=Decimal("0"), description="Сумма зачисления на счет-получатель (по умолчанию равна amount)")
    fee: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), description="Комиссия за перевод")
    date: dt_date = Field(..., description="Дата перевода")
    description: str | None = Field(None, max_length=255, description="Комментарий/описание перевода")


class TransferCreate(TransferBase):
    @model_validator(mode="after")
    def validate_different_accounts(self) -> "TransferCreate":
        if self.from_account_id == self.to_account_id:
            raise ValueError("Счет списания и счет зачисления не могут совпадать")
        return self


class CashWithdrawalCreate(BaseModel):
    """Схема для операции обналичивания (снятие наличных)"""
    from_account_id: UUID = Field(..., description="Счет списания (карта, банк и т.д.)")
    to_account_id: UUID | None = Field(
        None,
        description="Счет наличных (если не указан, используется активный счет типа 'cash' или создается 'Наличные')",
    )
    amount: Decimal = Field(..., gt=Decimal("0"), description="Сумма снятия наличных")
    fee: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), description="Комиссия за снятие (если есть)")
    date: dt_date = Field(..., description="Дата операции")
    description: str | None = Field(default="Снятие наличных", max_length=255, description="Комментарий к операции")


class CashDepositCreate(BaseModel):
    """Схема для операции внесения наличных на счет/карту"""
    to_account_id: UUID = Field(..., description="Счет зачисления (карта, банк и т.д.)")
    from_account_id: UUID | None = Field(
        None,
        description="Счет наличных (если не указан, используется активный счет типа 'cash')",
    )
    amount: Decimal = Field(..., gt=Decimal("0"), description="Сумма внесения наличных")
    fee: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"), description="Комиссия за внесение (если есть)")
    date: dt_date = Field(..., description="Дата операции")
    description: str | None = Field(default="Внесение наличных", max_length=255, description="Комментарий к операции")


class TransferResponse(BaseModel):
    """Схема ответа с данными перевода"""
    id: UUID = Field(..., description="ID перевода")
    from_account_id: UUID = Field(..., description="ID счета списания")
    to_account_id: UUID = Field(..., description="ID счета зачисления")
    amount: Decimal = Field(..., description="Сумма списания")
    to_amount: Decimal = Field(..., description="Сумма зачисления")
    fee: Decimal = Field(..., description="Комиссия")
    date: dt_date = Field(..., description="Дата перевода")
    description: str | None = Field(None, description="Описание перевода")

    model_config = ConfigDict(from_attributes=True)


class TransferUpdate(BaseModel):
    """Схема обновления перевода"""
    from_account_id: UUID | None = Field(None, description="ID счета списания")
    to_account_id: UUID | None = Field(None, description="ID счета зачисления")
    amount: Decimal | None = Field(None, gt=Decimal("0"), description="Сумма списания")
    to_amount: Decimal | None = Field(None, gt=Decimal("0"), description="Сумма зачисления")
    fee: Decimal | None = Field(None, ge=Decimal("0"), description="Комиссия")
    date: dt_date | None = Field(None, description="Дата перевода")
    description: str | None = Field(None, max_length=255, description="Описание перевода")


class TransferListResponse(BaseModel):
    """Схема ответа со списком переводов"""
    transfers: list[TransferResponse] = Field(..., description="Список переводов")
