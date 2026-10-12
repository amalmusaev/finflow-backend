from datetime import date as dt_date
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_db
from src.models.operation import Operation
from src.models.transfer import Transfer
from src.schemas.analytics import (
    AnalyticsSummaryResponse,
    CategoryGroup,
    Comparisons,
    OperationMinimal,
    SummaryMetrics,
    TimelinePoint,
)
from src.schemas.enums import OperationType


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_summary(
        self,
        start_date: dt_date,
        end_date: dt_date,
        account_id: UUID | None = None,
    ) -> AnalyticsSummaryResponse:
        # Calculate days in current period
        days = (end_date - start_date).days + 1
        
        # Previous period range
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=days - 1)
        
        # Query current period operations
        query = select(Operation).where(
            Operation.date >= start_date,
            Operation.date <= end_date
        )
        if account_id:
            query = query.where(Operation.account_id == account_id)
            
        result = await self.session.execute(query.order_by(Operation.date))
        operations = result.scalars().all()

        # Query current period transfers
        transfers_query = select(Transfer).where(
            Transfer.date >= start_date,
            Transfer.date <= end_date,
        )
        if account_id:
            transfers_query = transfers_query.where(
                or_(Transfer.from_account_id == account_id, Transfer.to_account_id == account_id)
            )
        transfers_result = await self.session.execute(transfers_query)
        transfers = transfers_result.scalars().all()
        total_transfers = sum((t.amount for t in transfers), Decimal("0.00"))
        transfers_count = len(transfers)
        
        # Query previous period operations
        prev_query = select(Operation).where(
            Operation.date >= prev_start_date,
            Operation.date <= prev_end_date
        )
        if account_id:
            prev_query = prev_query.where(Operation.account_id == account_id)
            
        prev_result = await self.session.execute(prev_query)
        prev_operations = prev_result.scalars().all()
        
        # Calculate current period metrics (переводы не входят в доходы/расходы)
        total_income = sum((op.amount for op in operations if op.type == OperationType.INCOME), Decimal("0.00"))
        total_expense = sum((op.amount for op in operations if op.type == OperationType.EXPENSE), Decimal("0.00"))
        net_flow = total_income - total_expense
        
        savings_rate = Decimal("0.00")
        if total_income > 0:
            savings_rate = (net_flow / total_income) * Decimal("100")
            
        avg_daily_expense = total_expense / Decimal(str(days)) if days > 0 else Decimal("0.00")
        
        max_expense_op = None
        expense_ops = [op for op in operations if op.type == OperationType.EXPENSE]
        if expense_ops:
            max_op = max(expense_ops, key=lambda x: x.amount)
            max_expense_op = OperationMinimal(
                id=max_op.id,
                description=max_op.description,
                amount=max_op.amount,
                date=max_op.date,
                category_id=max_op.category_id,
                type=max_op.type,
                account_id=max_op.account_id,
            )
            
        # Calculate previous period metrics for comparisons
        prev_total_income = sum((op.amount for op in prev_operations if op.type == OperationType.INCOME), Decimal("0.00"))
        prev_total_expense = sum((op.amount for op in prev_operations if op.type == OperationType.EXPENSE), Decimal("0.00"))
        
        has_prev_period = len(prev_operations) > 0
        
        income_growth_percent = Decimal("0.00")
        if prev_total_income > 0:
            income_growth_percent = ((total_income - prev_total_income) / prev_total_income) * Decimal("100")
        elif total_income > 0:
            income_growth_percent = Decimal("100.00")
            
        expense_growth_percent = Decimal("0.00")
        if prev_total_expense > 0:
            expense_growth_percent = ((total_expense - prev_total_expense) / prev_total_expense) * Decimal("100")
        elif total_expense > 0:
            expense_growth_percent = Decimal("100.00")
            
        # Group by date for timeline
        timeline_dict: dict[dt_date, TimelinePoint] = {}
        # Pre-fill timeline with all dates in range to ensure continuous chart
        curr_date = start_date
        while curr_date <= end_date:
            timeline_dict[curr_date] = TimelinePoint(
                date=curr_date,
                income=Decimal("0.00"),
                expense=Decimal("0.00"),
                transfers=Decimal("0.00"),
            )
            curr_date += timedelta(days=1)
            
        for op in operations:
            if op.type == OperationType.INCOME:
                timeline_dict[op.date].income += op.amount
            elif op.type == OperationType.EXPENSE:
                timeline_dict[op.date].expense += op.amount

        for t in transfers:
            if t.date in timeline_dict:
                timeline_dict[t.date].transfers += t.amount
                
        timeline = sorted(timeline_dict.values(), key=lambda x: x.date)
        
        # Group by category
        expenses_by_category_dict: dict[UUID, CategoryGroup] = {}
        incomes_by_category_dict: dict[UUID, CategoryGroup] = {}
        
        for op in operations:
            if op.type == OperationType.EXPENSE:
                if op.category_id not in expenses_by_category_dict:
                    expenses_by_category_dict[op.category_id] = CategoryGroup(
                        category_id=op.category_id, amount=Decimal("0.00"), count=0
                    )
                expenses_by_category_dict[op.category_id].amount += op.amount
                expenses_by_category_dict[op.category_id].count += 1
            elif op.type == OperationType.INCOME:
                if op.category_id not in incomes_by_category_dict:
                    incomes_by_category_dict[op.category_id] = CategoryGroup(
                        category_id=op.category_id, amount=Decimal("0.00"), count=0
                    )
                incomes_by_category_dict[op.category_id].amount += op.amount
                incomes_by_category_dict[op.category_id].count += 1
                
        expenses_by_category = sorted(expenses_by_category_dict.values(), key=lambda x: x.amount, reverse=True)
        incomes_by_category = sorted(incomes_by_category_dict.values(), key=lambda x: x.amount, reverse=True)
        
        return AnalyticsSummaryResponse(
            summary=SummaryMetrics(
                total_income=total_income,
                total_expense=total_expense,
                net_flow=net_flow,
                savings_rate=round(savings_rate, 2),
                avg_daily_expense=round(avg_daily_expense, 2),
                max_expense_operation=max_expense_op,
                total_transfers=total_transfers,
                transfers_count=transfers_count,
            ),
            comparisons=Comparisons(
                has_previous_period=has_prev_period,
                income_growth_percent=round(income_growth_percent, 2),
                expense_growth_percent=round(expense_growth_percent, 2),
            ),
            timeline=timeline,
            expenses_by_category=expenses_by_category,
            incomes_by_category=incomes_by_category,
        )


async def get_analytics_service(
    session: AsyncSession = Depends(get_db),
) -> AnalyticsService:
    """FastAPI Dependency для получения AnalyticsService"""
    return AnalyticsService(session)
