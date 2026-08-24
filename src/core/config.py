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
    port: int = 5432
    database: str = "postgres"
    user: str = "postgres"
    password: str = ""

    @property
    def database_url(self) -> str:
        """Формирование асинхронной строки подключения postgresql+asyncpg"""
        encoded_user = quote_plus(self.user)
        encoded_password = quote_plus(self.password) if self.password else ""
        auth = f"{encoded_user}:{encoded_password}" if encoded_password else encoded_user
        return f"postgresql+asyncpg://{auth}@{self.host}:{self.port}/{self.database}"


settings = Settings()