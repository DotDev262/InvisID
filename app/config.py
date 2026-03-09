from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# BASE_DIR is 'app/'
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # API Keys (Loaded from .env)
    ADMIN_API_KEY: str = "admin-secret-key"
    EMPLOYEE_API_KEY: str = "employee-secret-key"
    EMPLOYEE_API_KEY_2: str = "employee-secret-2"
    EMPLOYEE_API_KEY_3: str = "employee-secret-3"
    EMPLOYEE_API_KEY_4: str = "contractor-secret-4"
    EMPLOYEE_API_KEY_5: str = "intern-secret-5"
    EMPLOYEE_API_KEY_6: str = "guest-secret-6"
    EMPLOYEE_API_KEY_7: str = "employee-secret-7"
    EMPLOYEE_API_KEY_8: str = "employee-secret-8"

    # Security
    MASTER_SECRET: str = "master-secret-minimum-32-characters"

    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    MAX_FILE_SIZE: int = 10 * 1024 * 1024

    ALLOWED_EXTENSIONS: list = [".png", ".jpg", ".jpeg"]

    UPLOAD_DIR: str = str(BASE_DIR / "storage/uploads")
    PROCESSED_DIR: str = str(BASE_DIR / "storage/processed")
    RESULT_DIR: str = str(BASE_DIR / "storage/results")

    RATE_LIMIT_PER_MINUTE: int = 60
    TRASH_RETENTION_DAYS: int = 30

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), 
        env_file_encoding='utf-8',
        extra="allow"
    )


@lru_cache
def get_settings():
    return Settings()
