import json
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Application settings loaded from environment variables when available."""

    app_name: str = "SmartFit AI Backend"
    app_version: str = "1.0.0"
    debug: bool = False

    allowed_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://smart-fit-ai-two.vercel.app",
            "https://smart-fit-ai.onrender.com",
        ]
    )
    cors_allow_origin_regex: Optional[str] = (
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|"
        r"^https://.*\.vercel\.app$|"
        r"^https://.*\.onrender\.com$"
    )

    default_user_height_cm: float = 170.0
    measurement_round_digits: int = 2
    consent_version: str = "v1"
    auto_delete_uploaded_images: bool = True

    auth_token_secret: str = Field(min_length=32)
    auth_access_token_minutes: int = Field(default=20, gt=0)
    auth_refresh_token_days: int = Field(default=14, gt=0)
    auth_max_failed_attempts: int = Field(default=5, gt=0)
    auth_lockout_minutes: int = Field(default=10, gt=0)
    auth_attempt_window_minutes: int = Field(default=15, gt=0)

    model_path: Path = Field(default=BASE_DIR / "models" / "size_model.pkl")
    tryon_assets_dir: Path = Field(default=BASE_DIR / "static" / "clothing")
    catalog_path: Path = Field(default=BASE_DIR / "static" / "catalog" / "products.csv")
    database_url: str = Field(min_length=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        raw = value.strip()
        if not raw:
            return []

        # Allow ALLOWED_ORIGINS to be provided as either JSON array or CSV.
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass

        return [origin.strip() for origin in raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
