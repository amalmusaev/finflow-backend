from datetime import date as dt_date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.schemas.analytics import AnalyticsSummaryResponse
from src.services.analytics import AnalyticsService, get_analytics_service

router = APIRouter(prefix="/analytics", tags=["Аналитика"])


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить сводную аналитику для дашборда",
    description=(
        "Возвращает агрегированные данные для дашборда за указанный период времени. "
        "Включает общие метрики (доходы, расходы), сравнение с предыдущим периодом "
        "и данные для графиков (timeline и разбивка по категориям)."
    ),
)
async def get_analytics_summary(
    start_date: dt_date = Query(
        ...,
        description="Начальная дата периода (YYYY-MM-DD)",
    ),
    end_date: dt_date = Query(
        ...,
        description="Конечная дата периода (YYYY-MM-DD)",
    ),
    account_id: UUID | None = Query(
        default=None,
        description="Опциональный фильтр по ID счета",
    ),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsSummaryResponse:
    """Получить сводку аналитики за период."""
    return await service.get_summary(
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
    )
