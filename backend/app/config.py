import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./adrobot.db")
    keitaro_mode: str = os.getenv("KEITARO_MODE", "demo")
    keitaro_base_url: str = os.getenv("KEITARO_BASE_URL", "")
    keitaro_api_key: str = os.getenv("KEITARO_API_KEY", "")
    google_redirect_url: str = os.getenv("GOOGLE_REDIRECT_URL", "https://www.google.com/")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")


settings = Settings()
