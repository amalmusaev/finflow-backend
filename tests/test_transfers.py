from datetime import date
from decimal import Decimal
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.db import async_session_factory
from src.main import app
from src.models.account import Account
from src.models.transfer import Transfer
from src.schemas.enums import AccountType, Currency


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def setup_accounts():
    """Создание двух тестовых счетов (карта и наличные) для тестов"""
    async with async_session_factory() as session:
        card_acc = Account(
            name="Тест Карта",
            type=AccountType.CARD,
            currency=Currency.RUB,
            balance=Decimal("10000.00"),
            is_active=True,
        )
        cash_acc = Account(
            name="Тест Наличные",
            type=AccountType.CASH,
            currency=Currency.RUB,
            balance=Decimal("2000.00"),
            is_active=True,
        )
        session.add_all([card_acc, cash_acc])
        await session.commit()
        await session.refresh(card_acc)
        await session.refresh(cash_acc)

        card_id = card_acc.id
        cash_id = cash_acc.id

    yield card_id, cash_id

    # Очистка тестовых данных
    async with async_session_factory() as session:
        card = await session.get(Account, card_id)
        if card:
            await session.delete(card)
        cash = await session.get(Account, cash_id)
        if cash:
            await session.delete(cash)
        await session.commit()


@pytest.mark.asyncio
async def test_create_transfer(async_client: AsyncClient, setup_accounts):
    card_id, cash_id = setup_accounts

    transfer_data = {
        "from_account_id": str(card_id),
        "to_account_id": str(cash_id),
        "amount": "3000.00",
        "fee": "50.00",
        "date": "2026-10-12",
        "description": "Тестовый перевод",
    }

    res = await async_client.post("/api/v1/transfers", json=transfer_data)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["amount"] == "3000.00"
    assert data["fee"] == "50.00"
    assert data["description"] == "Тестовый перевод"

    # Проверка балансов
    res_card = await async_client.get(f"/api/v1/accounts/{card_id}")
    assert res_card.status_code == 200
    assert Decimal(res_card.json()["balance"]) == Decimal("6950.00")  # 10000 - (3000 + 50)

    res_cash = await async_client.get(f"/api/v1/accounts/{cash_id}")
    assert res_cash.status_code == 200
    assert Decimal(res_cash.json()["balance"]) == Decimal("5000.00")  # 2000 + 3000


@pytest.mark.asyncio
async def test_transfer_same_account_validation(async_client: AsyncClient, setup_accounts):
    card_id, _ = setup_accounts
    transfer_data = {
        "from_account_id": str(card_id),
        "to_account_id": str(card_id),
        "amount": "1000.00",
        "date": "2026-10-12",
    }
    res = await async_client.post("/api/v1/transfers", json=transfer_data)
    assert res.status_code == 422 or res.status_code == 400


@pytest.mark.asyncio
async def test_cash_withdrawal_convenience(async_client: AsyncClient, setup_accounts):
    card_id, cash_id = setup_accounts

    res = await async_client.post(
        "/api/v1/transfers/cash-withdrawal",
        json={
            "from_account_id": str(card_id),
            "amount": "1500.00",
            "date": "2026-10-12",
            "description": "Снятие в банкомате",
        },
    )
    assert res.status_code == 201, res.text

    # Проверка, что баланс карты уменьшился
    res_card = await async_client.get(f"/api/v1/accounts/{card_id}")
    assert Decimal(res_card.json()["balance"]) == Decimal("8500.00")


@pytest.mark.asyncio
async def test_analytics_transfer_isolation(async_client: AsyncClient, setup_accounts):
    card_id, cash_id = setup_accounts

    # Делаем перевод
    res = await async_client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(card_id),
            "to_account_id": str(cash_id),
            "amount": "4000.00",
            "date": "2026-10-12",
            "description": "Перевод для аналитики",
        },
    )
    assert res.status_code == 201

    # Запрашиваем аналитику
    analytics_res = await async_client.get(
        "/api/v1/analytics/summary",
        params={"start_date": "2026-10-12", "end_date": "2026-10-12"},
    )
    assert analytics_res.status_code == 200
    summary = analytics_res.json()["summary"]

    # Перевод не должен увеличивать total_expense
    assert Decimal(summary["total_transfers"]) >= Decimal("4000.00")
    assert summary["transfers_count"] >= 1


@pytest.mark.asyncio
async def test_update_and_delete_transfer(async_client: AsyncClient, setup_accounts):
    card_id, cash_id = setup_accounts

    # 1. Создаем перевод на 2000
    create_res = await async_client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(card_id),
            "to_account_id": str(cash_id),
            "amount": "2000.00",
            "date": "2026-10-12",
            "description": "Перевод для теста обновления",
        },
    )
    assert create_res.status_code == 201
    transfer_id = create_res.json()["id"]

    # Проверяем баланс после создания: Карта 8000, Наличные 4000
    res_card = await async_client.get(f"/api/v1/accounts/{card_id}")
    assert Decimal(res_card.json()["balance"]) == Decimal("8000.00")

    # 2. Обновляем сумму на 3000
    update_res = await async_client.patch(
        f"/api/v1/transfers/{transfer_id}",
        json={"amount": "3000.00"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["amount"] == "3000.00"

    # Балансы должны скорректироваться: Карта 7000, Наличные 5000
    res_card = await async_client.get(f"/api/v1/accounts/{card_id}")
    assert Decimal(res_card.json()["balance"]) == Decimal("7000.00")
    res_cash = await async_client.get(f"/api/v1/accounts/{cash_id}")
    assert Decimal(res_cash.json()["balance"]) == Decimal("5000.00")

    # 3. Удаляем перевод
    del_res = await async_client.delete(f"/api/v1/transfers/{transfer_id}")
    assert del_res.status_code == 204

    # Балансы должны полностью откатиться: Карта 10000, Наличные 2000
    res_card = await async_client.get(f"/api/v1/accounts/{card_id}")
    assert Decimal(res_card.json()["balance"]) == Decimal("10000.00")
    res_cash = await async_client.get(f"/api/v1/accounts/{cash_id}")
    assert Decimal(res_cash.json()["balance"]) == Decimal("2000.00")
