
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Setu"
    APP_ENV: str = "development"
    DEBUG: bool = True

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    
    DATABASE_URL: str
    TEST_DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
