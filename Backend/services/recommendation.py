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
        preferred_brands: list[str] | None = None,
        occasions: list[str] | None = None,
        weather: list[str] | None = None,
        colors: list[str] | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        max_items = max(limit, 1)
        categories_set = self._to_set(categories)
        preferred_brands_set = self._to_set(preferred_brands)
        occasions_set = self._to_set(occasions)
        weather_set = self._to_set(weather)
        colors_set = self._to_set(colors)

        products = self.catalog_service.list_products(limit=500)

        scored_products = sorted(
            products,
            key=lambda product: (
                self._match_score(
                    product=product,
                    categories_set=categories_set,
                    preferred_brands_set=preferred_brands_set,
                    occasions_set=occasions_set,
                    weather_set=weather_set,
                    colors_set=colors_set,
                ),
                str(product.get("sku", "")),
            ),
            reverse=True,
        )

        prioritized: list[dict[str, Any]] = []
        seen_brands: set[str] = set()
        seen_images: set[str] = set()

        for featured_brand in ["nike", "zara"]:
            if featured_brand not in preferred_brands_set:
                continue

            brand_top = next(
                (
                    product
                    for product in scored_products
                    if str(product.get("brand", "")).strip().lower() == featured_brand
                    and str(product.get("category", "")).strip().lower() in {"tees", "jackets"}
                ),
                None,
            )
            brand_bottom = next(
                (
                    product
                    for product in scored_products
                    if str(product.get("brand", "")).strip().lower() == featured_brand
                    and str(product.get("category", "")).strip().lower() == "jeans"
                ),
                None,
            )

            for seeded_product in [brand_top, brand_bottom]:
                if not seeded_product:
                    continue
                if seeded_product in prioritized or len(prioritized) >= max_items:
                    continue

                image_url = self._image_url(str(seeded_product.get("image_name", "")))
                prioritized.append(seeded_product)

                brand = str(seeded_product.get("brand", "")).strip()
                if brand:
                    seen_brands.add(brand)
                if image_url:
                    seen_images.add(image_url)

        # First pass: diversify by brand and image to avoid repetitive cards.
        for product in scored_products:
            if len(prioritized) >= max_items:
                break

            brand = str(product.get("brand", "")).strip()
            image_url = self._image_url(str(product.get("image_name", "")))

            if brand in seen_brands:
                continue
            if image_url and image_url in seen_images:
                continue

            prioritized.append(product)
            if brand:
                seen_brands.add(brand)
            if image_url:
                seen_images.add(image_url)

        # Second pass: fill remaining slots by score while still avoiding exact image repeats.
        if len(prioritized) < max_items:
            for product in scored_products:
                if len(prioritized) >= max_items:
                    break
                if product in prioritized:
                    continue

                image_url = self._image_url(str(product.get("image_name", "")))
                if image_url and image_url in seen_images:
                    continue

                prioritized.append(product)
                if image_url:
                    seen_images.add(image_url)

        recommendations: list[dict[str, Any]] = []
        for product in prioritized:
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
                    "reason": self._reason_for_fit(
                        fit_preference=fit_preference,
                        category=category,
                        product=product,
                        occasions_set=occasions_set,
                        weather_set=weather_set,
                        colors_set=colors_set,
                    ),
                    "image_url": self._image_url(str(product.get("image_name", ""))),
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
                    "image_url": self._image_url("fallback-core-tee.svg"),
                }
            ]

        return recommendations[:max_items]

    @staticmethod
    def _reason_for_fit(
        fit_preference: str,
        category: str,
        product: dict[str, Any],
        occasions_set: set[str],
        weather_set: set[str],
        colors_set: set[str],
    ) -> str:
        if fit_preference == "slim":
            base_reason = f"Selected for a sharper silhouette in {category}."
        elif fit_preference == "relaxed":
            base_reason = f"Selected for comfort-forward relaxed {category} styling."
        else:
            base_reason = f"Balanced fit recommendation for everyday {category}."

        matched_tags: list[str] = []
        product_occasions = {item.strip().lower() for item in product.get("occasions", [])}
        product_weather = {item.strip().lower() for item in product.get("weather", [])}
        product_color = str(product.get("color", "")).strip().lower()

        if occasions_set and occasions_set.intersection(product_occasions):
            matched_tags.append("occasion")
        if weather_set and weather_set.intersection(product_weather):
            matched_tags.append("weather")
        if colors_set and product_color in colors_set:
            matched_tags.append("color")

        if matched_tags:
            return f"{base_reason} Matched on {', '.join(matched_tags)} preferences."

        return base_reason

    @staticmethod
    def _to_set(values: list[str] | None) -> set[str]:
        return {value.strip().lower() for value in values or [] if value.strip()}

    @staticmethod
    def _match_score(
        product: dict[str, Any],
        categories_set: set[str],
        preferred_brands_set: set[str],
        occasions_set: set[str],
        weather_set: set[str],
        colors_set: set[str],
    ) -> int:
        score = 0

        product_category = str(product.get("category", "")).strip().lower()
        product_brand = str(product.get("brand", "")).strip().lower()
        product_occasions = {item.strip().lower() for item in product.get("occasions", [])}
        product_weather = {item.strip().lower() for item in product.get("weather", [])}
        product_color = str(product.get("color", "")).strip().lower()

        if preferred_brands_set:
            score += 5 if product_brand in preferred_brands_set else -2

        if categories_set:
            score += 6 if product_category in categories_set else -4

        if occasions_set:
            matched = len(occasions_set.intersection(product_occasions))
            score += matched * 3
            if matched == 0:
                score -= 2

        if weather_set:
            matched = len(weather_set.intersection(product_weather))
            score += matched * 2
            if matched == 0:
                score -= 1

        if colors_set:
            score += 2 if product_color in colors_set else -1

        return score

    @staticmethod
    def _image_url(image_name: str) -> str:
        if not image_name:
            return ""
        return f"/static/clothing/{image_name}"
