from uuid import UUID
from datetime import date as dt_date
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict

from src.schemas.enums import OperationType


class OperationBase(BaseModel):
    """Базовая схема операции"""
    description: str = Field(..., min_length=1, max_length=255, description="Описание операции")
    amount: Decimal = Field(..., ge=Decimal(0), description="Сумма операции")
    type: OperationType = Field(..., description="Тип операции")
    date: dt_date = Field(..., description="Дата операции")


class OperationCreate(OperationBase):
    category_id: UUID = Field(..., description="ID категории операции")
    account_id: UUID = Field(..., description="ID счета операции")


class OperationResponse(OperationBase):
    """Схема для ответа с операцией"""
    id: UUID = Field(..., description="ID операции")
    category_id: UUID = Field(..., description="ID категории операции")
    account_id: UUID = Field(..., description="ID счета операции")

    model_config = ConfigDict(from_attributes=True)


class OperationUpdate(BaseModel):
    """Схема для обновления операции"""
    description: str | None = Field(None, min_length=1, max_length=255, description="Описание операции")
    amount: Decimal | None = Field(None, ge=Decimal(0), description="Сумма операции")
    type: OperationType | None = Field(None, description="Тип операции")
    category_id: UUID | None = Field(None, description="ID категории операции")
    account_id: UUID | None = Field(None, description="ID счета операции")
    date: dt_date | None = Field(None, description="Дата операции")


class OperationListResponse(BaseModel):
    """Схема для ответа со списком операций"""
    operations: list[OperationResponse] = Field(..., description="Список операций")
