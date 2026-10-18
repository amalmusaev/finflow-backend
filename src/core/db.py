from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings

# Создание асинхронного движка SQLAlchemy для PostgreSQL (Transaction Mode)
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
    pool_recycle=300,
    pool_timeout=45,
    connect_args={
        "statement_cache_size": 0,
        "timeout": 30,
    },
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
