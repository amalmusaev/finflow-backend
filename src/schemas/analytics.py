from datetime import date as dt_date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.enums import OperationType


class OperationMinimal(BaseModel):
    """Минимальная информация об операции для дашборда"""
    id: UUID
    description: str
    amount: Decimal
    date: dt_date
    category_id: UUID
    type: OperationType
    account_id: UUID


class SummaryMetrics(BaseModel):
    """Сводные метрики за период"""
    total_income: Decimal = Field(default=Decimal("0.00"))
    total_expense: Decimal = Field(default=Decimal("0.00"))
    net_flow: Decimal = Field(default=Decimal("0.00"))
    savings_rate: Decimal = Field(default=Decimal("0.00"))
    avg_daily_expense: Decimal = Field(default=Decimal("0.00"))
    max_expense_operation: Optional[OperationMinimal] = None


class Comparisons(BaseModel):
    """Сравнение с предыдущим периодом"""
    has_previous_period: bool = Field(default=False)
    income_growth_percent: Decimal = Field(default=Decimal("0.00"))
    expense_growth_percent: Decimal = Field(default=Decimal("0.00"))


class TimelinePoint(BaseModel):
    """Точка на графике доходов и расходов по дням"""
    date: dt_date
    income: Decimal = Field(default=Decimal("0.00"))
    expense: Decimal = Field(default=Decimal("0.00"))


class CategoryGroup(BaseModel):
    """Сгруппированные данные по категории"""
    category_id: UUID
    amount: Decimal
    count: int


class AnalyticsSummaryResponse(BaseModel):
    """Полный ответ эндпоинта аналитики"""
    summary: SummaryMetrics
    comparisons: Comparisons
    timeline: list[TimelinePoint]
    expenses_by_category: list[CategoryGroup]
    incomes_by_category: list[CategoryGroup]
