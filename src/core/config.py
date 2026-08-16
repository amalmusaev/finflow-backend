from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения"""
    app_name: str = "FinFlow"
    app_version: str = "0.1.0"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./database/app.db"


settings = Settings()