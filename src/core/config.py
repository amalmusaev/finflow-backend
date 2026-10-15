from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FinFlow"
    app_version: str = "0.1.0"
    debug: bool = False

    # Параметры подключения к PostgreSQL
    host: str = "localhost"
    port: int = 6543
    session_port: int = 5432
    database: str = "postgres"
    user: str = "postgres"
    password: str = ""

    def _build_db_url(self, port: int) -> str:
        encoded_user = quote_plus(self.user)
        encoded_password = quote_plus(self.password) if self.password else ""
        auth = f"{encoded_user}:{encoded_password}" if encoded_password else encoded_user
        return f"postgresql+asyncpg://{auth}@{self.host}:{port}/{self.database}"

    @property
    def database_url(self) -> str:
        """Формирование асинхронной строки подключения postgresql+asyncpg (Transaction Pooler)"""
        return self._build_db_url(self.port)

    @property
    def session_database_url(self) -> str:
        """Формирование асинхронной строки подключения для миграций Alembic (Session Pooler)"""
        return self._build_db_url(self.session_port)


settings = Settings()