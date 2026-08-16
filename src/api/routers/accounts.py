from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.schemas.accounts import (
    AccountCreate,
    AccountListResponse,
    AccountResponse,
    AccountUpdate,
)
from src.schemas.enums import AccountType, Currency
from src.services.accounts import AccountService, get_account_service

router = APIRouter(prefix="/accounts", tags=["Счета"])


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый счет",
    description="Создает новый финансовый счет пользователя с начальным балансом.",
)
async def create_account(
    account_in: AccountCreate,
    service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """Создать новый счет."""
    account = await service.create_account(account_in)
    return AccountResponse.model_validate(account)


@router.get(
    "",
    response_model=AccountListResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить список счетов",
    description="Возвращает список всех счетов с возможностью фильтрации по статусу активности, типу счета и валюте.",
)
async def get_accounts(
    is_active: bool | None = Query(
        default=None,
        description="Фильтр по статусу активности счета (активен/заблокирован)",
    ),
    account_type: AccountType | None = Query(
        default=None,
        alias="type",
        description="Фильтр по типу счета (cash, card, bank, deposit)",
    ),
    currency: Currency | None = Query(
        default=None,
        description="Фильтр по валюте счета (RUB, USD, EUR и т.д.)",
    ),
    offset: int = Query(default=0, ge=0, description="Смещение списка"),
    limit: int = Query(default=100, ge=1, le=1000, description="Лимит списка"),
    service: AccountService = Depends(get_account_service),
) -> AccountListResponse:
    """Получить список счетов."""
    accounts = await service.get_accounts(
        is_active=is_active,
        account_type=account_type,
        currency=currency,
        offset=offset,
        limit=limit,
    )
    return AccountListResponse(
        accounts=[AccountResponse.model_validate(acc) for acc in accounts]
    )


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить счет по ID",
    description="Возвращает детальную информацию о счете по его уникальному идентификатору (UUID).",
)
async def get_account_by_id(
    account_id: UUID,
    service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """Получить информацию о счете по его ID."""
    account = await service.get_account(account_id)
    return AccountResponse.model_validate(account)


@router.patch(
    "/{account_id}",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновить счет",
    description="Частично обновляет данные существующего счета (название, тип, валюта, статус активности).",
)
async def update_account(
    account_id: UUID,
    account_update: AccountUpdate,
    service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """Обновить существующий счет."""
    updated_account = await service.update_account(account_id, account_update)
    return AccountResponse.model_validate(updated_account)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить счет",
    description="Удаляет счет по его уникальному идентификатору (UUID).",
)
async def delete_account(
    account_id: UUID,
    service: AccountService = Depends(get_account_service),
) -> None:
    """Удалить счет по ID."""
    await service.delete_account(account_id)
