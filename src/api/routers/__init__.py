from fastapi import APIRouter

from src.api.routers.accounts import router as accounts_router
from src.api.routers.categories import router as categories_router
from src.api.routers.operations import router as operations_router
from src.api.routers.analytics import router as analytics_router

api_router = APIRouter()

api_router.include_router(accounts_router)
api_router.include_router(categories_router)
api_router.include_router(operations_router)
api_router.include_router(analytics_router)

__all__ = [
    "api_router",
    "accounts_router",
    "categories_router",
    "operations_router",
    "analytics_router",
]
