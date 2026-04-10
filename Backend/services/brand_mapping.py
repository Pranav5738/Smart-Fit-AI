from __future__ import annotations

from typing import Any

from services.size_predictor import infer_size_order

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


class BrandMappingService:
    """Map predicted size across brands with category and fit-aware offsets."""

    def __init__(self) -> None:
        self.brand_rules: dict[str, dict[str, Any]] = {
            "Nike": {
                "base_offset": 0,
                "category_offsets": {"tees": 0, "jeans": 1, "jackets": 0},
                "fit_adjustments": {"slim": -1, "regular": 0, "relaxed": 1},
            },
            "Zara": {
                "base_offset": 1,
                "category_offsets": {"tees": 0, "jeans": 0, "jackets": 0},
                "fit_adjustments": {"slim": -1, "regular": 0, "relaxed": 0},
            },
            "H&M": {
                "base_offset": 0,
                "category_offsets": {"tees": 0, "jeans": 0, "jackets": 1},
                "fit_adjustments": {"slim": -1, "regular": 0, "relaxed": 1},
            },
            "Adidas": {
                "base_offset": 0,
                "category_offsets": {"tees": 0, "jeans": 1, "jackets": 0},
                "fit_adjustments": {"slim": -1, "regular": 0, "relaxed": 1},
            },
            "Uniqlo": {
                "base_offset": -1,
                "category_offsets": {"tees": 0, "jeans": 0, "jackets": 0},
                "fit_adjustments": {"slim": 0, "regular": 0, "relaxed": 1},
            },
            "Levi's": {
                "base_offset": 0,
                "category_offsets": {"tees": 0, "jeans": 1, "jackets": 0},
                "fit_adjustments": {"slim": -1, "regular": 0, "relaxed": 0},
            },
            "Puma": {
                "base_offset": 0,
                "category_offsets": {"tees": 0, "jeans": 0, "jackets": 0},
                "fit_adjustments": {"slim": -1, "regular": 0, "relaxed": 1},
            },
            "Gap": {
                "base_offset": 1,
                "category_offsets": {"tees": 0, "jeans": 0, "jackets": 0},
                "fit_adjustments": {"slim": -1, "regular": 0, "relaxed": 0},
            },
        }

    def map_size(self, base_size: str, fit_preference: str = "regular") -> dict[str, str]:
        mapping, _ = self.map_with_explanation(
            base_size=base_size,
            fit_preference=fit_preference,
            category="tees",
        )
        return mapping

    def map_with_explanation(
        self,
        base_size: str,
        fit_preference: str = "regular",
        category: str = "tees",
    ) -> tuple[dict[str, str], list[dict[str, Any]]]:
        normalized_base = self._normalize_size(base_size)

        mapping: dict[str, str] = {}
        logic: list[dict[str, Any]] = []

        for brand, rules in self.brand_rules.items():
            brand_size, total_offset = self.map_single(
                base_size=normalized_base,
                brand=brand,
                fit_preference=fit_preference,
                category=category,
                include_offset=True,
            )
            mapping[brand] = brand_size
            logic.append(
                {
                    "brand": brand,
                    "base_size": normalized_base,
                    "mapped_size": brand_size,
                    "category": category,
                    "offset": total_offset,
                    "adjustment_reason": self._adjustment_reason(total_offset),
                }
            )

        return mapping, logic

    def map_single(
        self,
        base_size: str,
        brand: str,
        fit_preference: str = "regular",
        category: str = "tees",
        include_offset: bool = False,
    ) -> Any:
        normalized_base = self._normalize_size(base_size)
        size_order = infer_size_order(normalized_base)
        if normalized_base not in size_order:
            mapped_size = normalized_base
            return (mapped_size, 0) if include_offset else mapped_size

        base_index = size_order.index(normalized_base)

        rules = self.brand_rules.get(brand)
        if rules is None:
            mapped_size = size_order[base_index]
            return (mapped_size, 0) if include_offset else mapped_size

        is_adult_size = normalized_base in SIZE_ORDER
        base_offset = int(rules.get("base_offset", 0)) if is_adult_size else 0
        fit_offset = int(rules.get("fit_adjustments", {}).get(fit_preference, 0))
        category_offset = int(rules.get("category_offsets", {}).get(category, 0)) if is_adult_size else 0
        total_offset = base_offset + fit_offset + category_offset

        mapped_index = min(max(base_index + total_offset, 0), len(size_order) - 1)
        mapped_size = size_order[mapped_index]
        return (mapped_size, total_offset) if include_offset else mapped_size

    @staticmethod
    def _normalize_size(size_label: str) -> str:
        normalized = size_label.upper().strip()
        inferred_order = infer_size_order(normalized)
        return normalized if normalized in inferred_order else normalized

    @staticmethod
    def _adjustment_reason(offset: int) -> str:
        if offset > 0:
            return "Brand tends smaller for this category or preference, mapped one step up."
        if offset < 0:
            return "Brand tends larger for this category or preference, mapped one step down."
        return "Brand baseline closely matches the predicted body size."
