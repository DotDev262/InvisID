import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    # API Keys
    ADMIN_API_KEY: str = "admin-secret-key"
    EMPLOYEE_API_KEY: str = "employee-secret-key"

    # Security
    MASTER_SECRET: str = "master-secret-minimum-32-characters"

    # App settings
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # File settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = [".png", ".jpg", ".jpeg"]
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "storage/uploads")
    PROCESSED_DIR: str = os.path.join(BASE_DIR, "storage/processed")
    RESULT_DIR: str = os.path.join(BASE_DIR, "storage/results")

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
