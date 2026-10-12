from datetime import date as dt_date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.schemas.transfers import (
    CashDepositCreate,
    CashWithdrawalCreate,
    TransferCreate,
    TransferListResponse,
    TransferResponse,
    TransferUpdate,
)
from src.services.transfers import TransferService, get_transfer_service

router = APIRouter(prefix="/transfers", tags=["Переводы"])


@router.post(
    "",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать перевод между счетами",
    description="Переводит средства с одного счета на другой с корректировкой балансов обоих счетов.",
)
async def create_transfer(
    transfer_in: TransferCreate,
    service: TransferService = Depends(get_transfer_service),
) -> TransferResponse:
    """Создать новый перевод между счетами."""
    transfer = await service.create_transfer(transfer_in)
    return TransferResponse.model_validate(transfer)


@router.post(
    "/cash-withdrawal",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Обналичивание (снятие наличных)",
    description=(
        "Снимает деньги с карты/банковского счета в наличные. "
        "Если целевой счет наличных (to_account_id) не указан, автоматически используется активный "
        "счет типа 'cash' или создается счет 'Наличные'."
    ),
)
async def cash_withdrawal(
    cash_in: CashWithdrawalCreate,
    service: TransferService = Depends(get_transfer_service),
) -> TransferResponse:
    """Выполнить снятие наличных (обналичивание)."""
    transfer = await service.create_cash_withdrawal(cash_in)
    return TransferResponse.model_validate(transfer)


@router.post(
    "/cash-deposit",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Внесение наличных",
    description=(
        "Вносит наличные деньги на банковскую карту или счет. "
        "Если счет наличных (from_account_id) не указан, автоматически используется активный счет типа 'cash'."
    ),
)
async def cash_deposit(
    cash_in: CashDepositCreate,
    service: TransferService = Depends(get_transfer_service),
) -> TransferResponse:
    """Выполнить внесение наличных на счет/карту."""
    transfer = await service.create_cash_deposit(cash_in)
    return TransferResponse.model_validate(transfer)


@router.get(
    "",
    response_model=TransferListResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить список переводов",
    description="Возвращает список переводов с фильтрацией по счетам, диапазону дат и пагинацией.",
)
async def get_transfers(
    account_id: UUID | None = Query(
        default=None,
        description="Фильтр по счету (где счет участвует как отправитель или получатель)",
    ),
    from_account_id: UUID | None = Query(
        default=None,
        description="Фильтр только по счету списания",
    ),
    to_account_id: UUID | None = Query(
        default=None,
        description="Фильтр только по счету зачисления",
    ),
    from_date: dt_date | None = Query(
        default=None,
        description="Начальная дата диапазона (включительно)",
    ),
    to_date: dt_date | None = Query(
        default=None,
        description="Конечная дата диапазона (включительно)",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Максимальное количество записей",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Смещение для пагинации",
    ),
    service: TransferService = Depends(get_transfer_service),
) -> TransferListResponse:
    """Получить список переводов с фильтрацией и пагинацией."""
    transfers = await service.get_transfers(
        account_id=account_id,
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        from_date=from_date,
        to_date=to_date,
        offset=offset,
        limit=limit,
    )
    return TransferListResponse(
        transfers=[TransferResponse.model_validate(t) for t in transfers]
    )


@router.get(
    "/{transfer_id}",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить перевод по ID",
    description="Возвращает детальную информацию о конкретном переводе.",
)
async def get_transfer_by_id(
    transfer_id: UUID,
    service: TransferService = Depends(get_transfer_service),
) -> TransferResponse:
    """Получить данные перевода по идентификатору."""
    transfer = await service.get_transfer(transfer_id)
    return TransferResponse.model_validate(transfer)


@router.patch(
    "/{transfer_id}",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновить перевод",
    description="Обновляет параметры перевода с автоматическим пересчетом балансов затронутых счетов.",
)
async def update_transfer(
    transfer_id: UUID,
    transfer_update: TransferUpdate,
    service: TransferService = Depends(get_transfer_service),
) -> TransferResponse:
    """Обновить параметры существующего перевода."""
    updated = await service.update_transfer(transfer_id, transfer_update)
    return TransferResponse.model_validate(updated)


@router.delete(
    "/{transfer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить перевод",
    description="Удаляет перевод и откатывает изменения балансов счетов.",
)
async def delete_transfer(
    transfer_id: UUID,
    service: TransferService = Depends(get_transfer_service),
) -> None:
    """Удалить перевод по ID."""
    await service.delete_transfer(transfer_id)
