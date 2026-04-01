from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Application settings loaded from environment variables when available."""

    app_name: str = "SmartFit AI Backend"
    app_version: str = "1.0.0"
    debug: bool = False

    allowed_origins: List[str] = Field(default_factory=lambda: ["*"])

    default_user_height_cm: float = 170.0
    measurement_round_digits: int = 2
    consent_version: str = "v1"
    auto_delete_uploaded_images: bool = True

    model_path: Path = Field(default=BASE_DIR / "models" / "size_model.pkl")
    tryon_assets_dir: Path = Field(default=BASE_DIR / "static" / "clothing")
    catalog_path: Path = Field(default=BASE_DIR / "static" / "catalog" / "products.csv")
    data_store_path: Path = Field(default=BASE_DIR / "model_artifacts" / "profile_store.db")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
