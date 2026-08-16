from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings

# Гарантируем существование директории для локальной базы данных SQLite
if "sqlite" in settings.database_url:
    db_path = settings.database_url.split("///")[-1]
    if db_path and not db_path.startswith(":memory:"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

# Создание асинхронного движка SQLAlchemy
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Фабрика асинхронных сессий
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(AsyncAttrs, DeclarativeBase):
    """Базовый декларативный класс для всех моделей SQLAlchemy"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для FastAPI для получения асинхронной сессии БД"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
