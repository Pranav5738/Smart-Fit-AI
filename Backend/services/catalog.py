from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from utils.config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


class CatalogService:
    """Load and query catalog products for smart outfit recommendations."""

    def __init__(self, catalog_path: Path | None = None) -> None:
        settings = get_settings()
        self.catalog_path = catalog_path or settings.catalog_path
        self._products: list[dict[str, Any]] = []
        self.reload_catalog()

    def reload_catalog(self) -> None:
        if not self.catalog_path.exists():
            logger.warning("Catalog file not found at %s", self.catalog_path)
            self._products = []
            return

        products: list[dict[str, Any]] = []
        with self.catalog_path.open("r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                products.append(
                    {
                        "sku": row.get("sku", ""),
                        "brand": row.get("brand", ""),
                        "product_name": row.get("product_name", ""),
                        "category": row.get("category", ""),
                        "occasions": self._split_pipe_values(row.get("occasions", "")),
                        "weather": self._split_pipe_values(row.get("weather", "")),
                        "color": row.get("color", "neutral"),
                        "image_name": row.get("image_name", ""),
                    }
                )

        self._products = products
        logger.info("Loaded %s catalog products", len(products))

    def list_products(
        self,
        categories: list[str] | None = None,
        occasions: list[str] | None = None,
        weather: list[str] | None = None,
        colors: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []

        categories_set = self._to_set(categories)
        occasions_set = self._to_set(occasions)
        weather_set = self._to_set(weather)
        colors_set = self._to_set(colors)

        for product in self._products:
            if categories_set and product["category"].lower() not in categories_set:
                continue

            if occasions_set and not occasions_set.intersection(
                {occasion.lower() for occasion in product["occasions"]}
            ):
                continue

            if weather_set and not weather_set.intersection(
                {item.lower() for item in product["weather"]}
            ):
                continue

            if colors_set and product["color"].lower() not in colors_set:
                continue

            filtered.append(product)
            if len(filtered) >= max(limit, 1):
                break

        return filtered

    def list_brands(self) -> list[str]:
        brands = sorted({product["brand"] for product in self._products if product["brand"]})
        return brands

    @staticmethod
    def _split_pipe_values(raw: str) -> list[str]:
        return [value.strip() for value in raw.split("|") if value.strip()]

    @staticmethod
    def _to_set(values: list[str] | None) -> set[str]:
        return {value.strip().lower() for value in values or [] if value.strip()}
