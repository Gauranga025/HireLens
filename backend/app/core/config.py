from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration using environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "AI Resume Screening Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Database Configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "resume_screening"
    POSTGRES_USER: str = "resume_user"
    POSTGRES_PASSWORD: str = "resume_dev_password"

    # Explicit, separately configured disposable database for automated tests.
    # This must never fall back to DATABASE_URL.
    TEST_DATABASE_URL: Optional[str] = None

    # Local directory for uploaded resume files. In containers, point this at a
    # mounted persistent volume; otherwise it stays relative to process CWD.
    UPLOAD_STORAGE_DIR: str = "storage/uploads"

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components."""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
