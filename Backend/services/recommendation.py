from __future__ import annotations

from typing import Any

from services.brand_mapping import BrandMappingService
from services.catalog import CatalogService


class RecommendationService:
    """Generate practical product recommendations from a live catalog."""

    def __init__(self, catalog_service: CatalogService | None = None) -> None:
        self.catalog_service = catalog_service or CatalogService()

    def generate(
        self,
        predicted_size: str,
        fit_preference: str,
        brand_mapper: BrandMappingService,
        categories: list[str] | None = None,
        occasions: list[str] | None = None,
        weather: list[str] | None = None,
        colors: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        products = self.catalog_service.list_products(
            categories=categories,
            occasions=occasions,
            weather=weather,
            colors=colors,
            limit=max(limit * 2, 10),
        )

        recommendations: list[dict[str, Any]] = []
        for product in products:
            category = str(product.get("category", "tees"))
            brand = str(product.get("brand", ""))

            recommended_size = brand_mapper.map_single(
                base_size=predicted_size,
                brand=brand,
                fit_preference=fit_preference,
                category=category,
            )

            recommendations.append(
                {
                    "sku": product.get("sku", ""),
                    "product_name": product.get("product_name", ""),
                    "brand": brand,
                    "category": category,
                    "recommended_size": recommended_size,
                    "occasions": product.get("occasions", []),
                    "weather": product.get("weather", []),
                    "color": product.get("color", "neutral"),
                    "reason": self._reason_for_fit(fit_preference, category),
                    "image_url": self._image_url(product.get("image_name", "")),
                }
            )

        if not recommendations:
            return [
                {
                    "sku": "GEN-001",
                    "product_name": f"Core Tee ({predicted_size})",
                    "brand": "SmartFit Picks",
                    "category": "tees",
                    "recommended_size": predicted_size,
                    "occasions": ["casual"],
                    "weather": ["all-season"],
                    "color": "neutral",
                    "reason": "Fallback recommendation when catalog filters are too strict.",
                    "image_url": self._image_url("tee.png"),
                }
            ]

        return recommendations[: max(limit, 1)]

    @staticmethod
    def _reason_for_fit(fit_preference: str, category: str) -> str:
        if fit_preference == "slim":
            return f"Selected for a sharper silhouette in {category}."
        if fit_preference == "relaxed":
            return f"Selected for comfort-forward relaxed {category} styling."
        return f"Balanced fit recommendation for everyday {category}."

    @staticmethod
    def _image_url(image_name: str) -> str:
        if not image_name:
            return ""
        return f"/static/clothing/{image_name}"
