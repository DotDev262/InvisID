from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API Keys
    ADMIN_API_KEY: str = "admin-secret-key"
    EMPLOYEE_API_KEY: str = "employee-secret-key"

    # Security
    MASTER_SECRET: str = "master-secret-minimum-32-characters"

    # App settings
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # File settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list = [".png", ".jpg", ".jpeg"]

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 10

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
