from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    dadata_api_key: str | None = None
    dadata_secret: str | None = None
    ais_provider_api_key: str | None = None
    ofac_sdn_csv_url: str | None = "https://www.treasury.gov/ofac/downloads/sdn.csv"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000"

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()
