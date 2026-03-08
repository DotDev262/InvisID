import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):

    ADMIN_API_KEY: str = "admin-secret-key"
    EMPLOYEE_API_KEY: str = "employee-secret-key"

    MASTER_SECRET: str = "master-secret-minimum-32-characters"

    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    MAX_FILE_SIZE: int = 10 * 1024 * 1024

    ALLOWED_EXTENSIONS: list = [".png", ".jpg", ".jpeg"]

    UPLOAD_DIR: str = str(BASE_DIR / "app/storage/uploads")

    PROCESSED_DIR: str = str(BASE_DIR / "app/storage/processed")

    RESULT_DIR: str = str(BASE_DIR / "app/storage/results")

    RATE_LIMIT_PER_MINUTE: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


@lru_cache
def get_settings():
    return Settings()