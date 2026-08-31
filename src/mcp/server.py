import argparse
from typing import Any
from uuid import UUID
from datetime import date as dt_date

from mcp.server.mcpserver import MCPServer

from src.core.db import async_session_factory
from src.services.accounts import AccountService
from src.services.categories import CategoryService
from src.services.operations import OperationService
from src.services.analytics import AnalyticsService
from src.schemas.accounts import AccountCreate
from src.schemas.categories import CategoryCreate
from src.schemas.operations import OperationCreate
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_mcp_session():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

mcp = MCPServer("Finflow")

@mcp.tool()
async def get_accounts() -> list[dict[str, Any]]:
    """Получить список всех счетов."""
    async with get_mcp_session() as session:
        service = AccountService(session)
        accounts = await service.get_accounts()
        return [
            {
                "id": str(a.id),
                "name": a.name,
                "type": a.type,
                "currency": a.currency,
                "balance": float(a.balance),
                "is_active": a.is_active,
            }
            for a in accounts
        ]

@mcp.tool()
async def create_account(account_in: AccountCreate) -> dict[str, Any]:
    """Создать новый счет."""
    async with get_mcp_session() as session:
        service = AccountService(session)
        account = await service.create_account(account_in)
        return {
            "id": str(account.id),
            "name": account.name,
            "type": account.type,
            "currency": account.currency,
            "balance": float(account.balance),
            "is_active": account.is_active,
        }

@mcp.tool()
async def get_categories() -> list[dict[str, Any]]:
    """Получить список всех категорий (доходов и расходов)."""
    async with get_mcp_session() as session:
        service = CategoryService(session)
        categories = await service.get_categories()
        return [
            {
                "id": str(c.id),
                "name": c.name,
                "type": c.type,
            }
            for c in categories
        ]

@mcp.tool()
async def create_category(category_in: CategoryCreate) -> dict[str, Any]:
    """Создать новую категорию."""
    async with get_mcp_session() as session:
        service = CategoryService(session)
        category = await service.create_category(category_in)
        return {
            "id": str(category.id),
            "name": category.name,
            "type": category.type,
        }

@mcp.tool()
async def get_operations(limit: int = 100) -> list[dict[str, Any]]:
    """Получить список операций с лимитом (по умолчанию 100)."""
    async with get_mcp_session() as session:
        service = OperationService(session)
        operations = await service.get_operations(limit=limit)
        return [
            {
                "id": str(o.id),
                "account_id": str(o.account_id),
                "category_id": str(o.category_id),
                "amount": float(o.amount),
                "type": o.type,
                "date": o.date.isoformat(),
                "description": o.description,
            }
            for o in operations
        ]

@mcp.tool()
async def create_operation(operation_in: OperationCreate) -> dict[str, Any]:
    """Создать новую операцию (расход или доход)."""
    async with get_mcp_session() as session:
        service = OperationService(session)
        op = await service.create_operation(operation_in)
        return {
            "id": str(op.id),
            "account_id": str(op.account_id),
            "category_id": str(op.category_id),
            "amount": float(op.amount),
            "type": op.type,
            "date": op.date.isoformat(),
            "description": op.description,
        }

@mcp.tool()
async def get_analytics_summary(start_date: dt_date, end_date: dt_date, account_id: UUID | None = None) -> dict[str, Any]:
    """Получить сводную аналитику за период (Cash flow, графики, статистика по категориям)."""
    async with async_session_factory() as session:
        service = AnalyticsService(session)
        summary = await service.get_summary(start_date, end_date, account_id)
        # model_dump with mode="json" converts all Decimal/UUID/Date objects to strings for easy JSON serialization
        return summary.model_dump(mode="json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", default="streamable-http", choices=["stdio", "sse", "streamable-http"], help="Transport protocol")
    parser.add_argument("--sse", action="store_true", help="Run via SSE (legacy)")
    parser.add_argument("--host", default="0.0.0.0", help="Host for HTTP/SSE")
    parser.add_argument("--port", type=int, default=8001, help="Port for HTTP/SSE")
    args = parser.parse_args()

    transport = "sse" if args.sse else args.transport
    if transport in ("sse", "streamable-http"):
        mcp.run(transport=transport, host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")

