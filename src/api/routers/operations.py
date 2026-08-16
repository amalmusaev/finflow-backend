from datetime import date as dt_date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.schemas.enums import OperationType
from src.schemas.operations import (
    OperationCreate,
    OperationListResponse,
    OperationResponse,
    OperationUpdate,
)
from src.services.operations import OperationService, get_operation_service

router = APIRouter(prefix="/operations", tags=["Операции"])


@router.post(
    "",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую финансовую операцию",
    description="Создает новую операцию (доход или расход), привязанную к счету и категории, и обновляет баланс счета.",
)
async def create_operation(
    operation_in: OperationCreate,
    service: OperationService = Depends(get_operation_service),
) -> OperationResponse:
    """Создать новую операцию с автоматическим пересчетом баланса счета."""
    operation = await service.create_operation(operation_in)
    return OperationResponse.model_validate(operation)


@router.get(
    "",
    response_model=OperationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить список операций с фильтрацией",
    description=(
        "Возвращает список финансовых операций с возможностью фильтрации по счету, "
        "категории, типу операции, диапазону дат, а также пагинацией (limit/offset)."
    ),
)
async def get_operations(
    account_id: UUID | None = Query(
        default=None,
        description="Фильтр по идентификатору счета",
    ),
    category_id: UUID | None = Query(
        default=None,
        description="Фильтр по идентификатору категории",
    ),
    operation_type: OperationType | None = Query(
        default=None,
        alias="type",
        description="Фильтр по типу операции (income / expense)",
    ),
    from_date: dt_date | None = Query(
        default=None,
        description="Начальная дата диапазона операций (включительно)",
    ),
    to_date: dt_date | None = Query(
        default=None,
        description="Конечная дата диапазона операций (включительно)",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Максимальное количество возвращаемых записей",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Смещение для пагинации",
    ),
    service: OperationService = Depends(get_operation_service),
) -> OperationListResponse:
    """Получить список операций с фильтрацией и пагинацией."""
    operations = await service.get_operations(
        account_id=account_id,
        category_id=category_id,
        operation_type=operation_type,
        from_date=from_date,
        to_date=to_date,
        offset=offset,
        limit=limit,
    )
    return OperationListResponse(
        operations=[OperationResponse.model_validate(op) for op in operations]
    )


@router.get(
    "/{operation_id}",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить операцию по ID",
    description="Возвращает детальную информацию об операции по её уникальному идентификатору (UUID).",
)
async def get_operation_by_id(
    operation_id: UUID,
    service: OperationService = Depends(get_operation_service),
) -> OperationResponse:
    """Получить операцию по ее ID."""
    operation = await service.get_operation(operation_id)
    return OperationResponse.model_validate(operation)


@router.patch(
    "/{operation_id}",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновить операцию",
    description="Частично обновляет данные существующей операции (описание, сумма, тип, категория, счет, дата).",
)
async def update_operation(
    operation_id: UUID,
    operation_update: OperationUpdate,
    service: OperationService = Depends(get_operation_service),
) -> OperationResponse:
    """Обновить существующую операцию."""
    updated = await service.update_operation(operation_id, operation_update)
    return OperationResponse.model_validate(updated)


@router.delete(
    "/{operation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить операцию",
    description="Удаляет финансовую операцию по её уникальному идентификатору (UUID) и корректирует баланс счета.",
)
async def delete_operation(
    operation_id: UUID,
    service: OperationService = Depends(get_operation_service),
) -> None:
    """Удалить операцию по ID."""
    await service.delete_operation(operation_id)
