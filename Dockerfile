FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

# Настройка переменных окружения Python и uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

# Установка зависимостей
RUN uv sync --frozen --no-install-project --no-cache

# Копирование конфигурации миграций и исходного кода
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src


# Порт бэкенда
EXPOSE 8000

# Автоматическое применение миграций и запуск ASGI сервера
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000"]
