from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict

from src.schemas.enums import AccountType, Currency


class AccountBase(BaseModel):
    """Базовая схема счета"""
    name: str = Field(..., min_length=1, max_length=128, description="Название счета")
    type: AccountType = Field(..., description="Тип счета")
    currency: Currency = Field(Currency.RUB, description="Валюта счета")


class AccountCreate(AccountBase):
    """Схема для создания счета"""
    balance: Decimal = Field(Decimal(0.0), description="Баланс счета")


class AccountResponse(AccountBase):
    """Схема для ответа с счетом"""
    id: UUID = Field(..., description="ID счета")
    balance: Decimal = Field(..., description="Текущий баланс счета")
    is_active: bool = Field(..., description="Статус активности счета")

    model_config = ConfigDict(from_attributes=True)


class AccountUpdate(BaseModel):
    """Схема для обновления счета"""
    name: str | None = Field(default=None, min_length=1, max_length=128, description="Название счета")
    type: AccountType | None = Field(default=None, description="Тип счета")
    currency: Currency | None = Field(default=None, description="Валюта счета")
    is_active: bool | None = Field(default=None, description="Активен ли счет")


class AccountListResponse(BaseModel):
    """Схема для ответа со списком счетов"""
    accounts: list[AccountResponse] = Field(..., description="Список счетов")
