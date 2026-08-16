from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.schemas.categories import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)
from src.schemas.enums import OperationType
from src.services.categories import CategoryService, get_category_service

router = APIRouter(prefix="/categories", tags=["Категории"])


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую категорию",
    description="Создает новую категорию для доходов или расходов.",
)
async def create_category(
    category_in: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """Создать новую категорию."""
    category = await service.create_category(category_in)
    return CategoryResponse.model_validate(category)


@router.get(
    "",
    response_model=CategoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить список категорий",
    description="Возвращает список всех категорий с возможностью фильтрации по типу (доход/расход).",
)
async def get_categories(
    category_type: OperationType | None = Query(
        default=None,
        alias="type",
        description="Фильтр по типу категории (income / expense)",
    ),
    offset: int = Query(default=0, ge=0, description="Смещение списка"),
    limit: int = Query(default=100, ge=1, le=1000, description="Лимит списка"),
    service: CategoryService = Depends(get_category_service),
) -> CategoryListResponse:
    """Получить список категорий."""
    categories = await service.get_categories(
        category_type=category_type,
        offset=offset,
        limit=limit,
    )
    return CategoryListResponse(
        categories=[CategoryResponse.model_validate(c) for c in categories]
    )


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить категорию по ID",
    description="Возвращает детальную информацию о категории по её уникальному идентификатору (UUID).",
)
async def get_category_by_id(
    category_id: UUID,
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """Получить категорию по ее ID."""
    category = await service.get_category(category_id)
    return CategoryResponse.model_validate(category)


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Обновить категорию",
    description="Частично обновляет данные существующей категории (название, тип).",
)
async def update_category(
    category_id: UUID,
    category_update: CategoryUpdate,
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """Обновить существующую категорию."""
    updated = await service.update_category(category_id, category_update)
    return CategoryResponse.model_validate(updated)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить категорию",
    description="Удаляет категорию по её уникальному идентификатору (UUID).",
)
async def delete_category(
    category_id: UUID,
    service: CategoryService = Depends(get_category_service),
) -> None:
    """Удалить категорию по ID."""
    await service.delete_category(category_id)
