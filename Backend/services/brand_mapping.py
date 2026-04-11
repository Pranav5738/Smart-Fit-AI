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
        }

    def map_size(self, base_size: str, fit_preference: str = "regular") -> dict[str, str]:
        mapping, _ = self.map_with_explanation(
            base_size=base_size,
            fit_preference=fit_preference,
            category="tees",
        )
        return mapping

    def nike_top_bottom_suggestions(
        self,
        measurements_cm: dict[str, float],
        fit_preference: str = "regular",
        gender: str = "unisex",
    ) -> dict[str, Any]:
        chest_cm = float(measurements_cm.get("chest", 0.0) or 0.0)
        waist_cm = float(measurements_cm.get("waist", 0.0) or 0.0)

        chest_in = chest_cm / 2.54 if chest_cm > 0 else 0.0
        waist_in = waist_cm / 2.54 if waist_cm > 0 else 0.0

        nike_top_chart = self._nike_top_chart(gender)
        nike_bottom_chart = self._nike_bottom_chart(gender)

        top_size = self._size_from_chart(chest_in, nike_top_chart)
        bottom_size = self._size_from_chart(waist_in, nike_bottom_chart)

        top_size = self._apply_fit_preference(top_size, fit_preference)
        bottom_size = self._apply_fit_preference(bottom_size, fit_preference)

        return {
            "brand": "Nike",
            "tops_size": top_size,
            "bottoms_size": bottom_size,
            "measurement_basis": {
                "chest_cm": round(chest_cm, 2),
                "waist_cm": round(waist_cm, 2),
                "chest_in": round(chest_in, 2),
                "waist_in": round(waist_in, 2),
            },
        }

    def zara_top_bottom_suggestions(
        self,
        measurements_cm: dict[str, float],
        fit_preference: str = "regular",
        gender: str = "unisex",
    ) -> dict[str, Any]:
        chest_cm = float(measurements_cm.get("chest", 0.0) or 0.0)
        waist_cm = float(measurements_cm.get("waist", 0.0) or 0.0)
        chest_in = chest_cm / 2.54 if chest_cm > 0 else 0.0
        waist_in = waist_cm / 2.54 if waist_cm > 0 else 0.0

        normalized_gender = gender.strip().lower()

        if normalized_gender == "female":
            # Women's chart from provided Zara reference where top sizing is bust-driven and bottoms are waist-driven.
            women_top_bust_in = [
                (31.5, "XXS"),
                (32.5, "XS"),
                (34.0, "S"),
                (35.5, "M"),
                (37.75, "L"),
                (40.25, "XL"),
            ]
            women_bottom_waist_in = [
                (22.75, "XXS"),
                (24.5, "XS"),
                (26.0, "S"),
                (27.5, "M"),
                (30.0, "L"),
                (32.25, "XL"),
            ]

            top_size = self._nearest_size(chest_in, women_top_bust_in)
            bottom_size = self._nearest_size(waist_in, women_bottom_waist_in)
        else:
            men_top_chart_cm = [
                (89.0, 93.0, "S"),
                (94.0, 98.0, "M"),
                (99.0, 103.0, "L"),
                (104.0, 108.0, "XL"),
                (112.0, 116.0, "XXL"),
            ]
            men_bottom_chart_cm = [
                (76.0, 80.0, "S"),
                (80.0, 88.0, "M"),
                (89.0, 91.0, "L"),
                (95.0, 101.0, "XL"),
                (105.0, 111.0, "XXL"),
            ]

            top_size = self._size_from_chart(chest_cm, men_top_chart_cm)
            bottom_size = self._size_from_chart(waist_cm, men_bottom_chart_cm)

        top_size = self._apply_fit_preference(top_size, fit_preference)
        bottom_size = self._apply_fit_preference(bottom_size, fit_preference)

        return {
            "brand": "Zara",
            "tops_size": top_size,
            "bottoms_size": bottom_size,
            "measurement_basis": {
                "chest_cm": round(chest_cm, 2),
                "waist_cm": round(waist_cm, 2),
                "chest_in": round(chest_in, 2),
                "waist_in": round(waist_in, 2),
            },
        }

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
    def _apply_fit_preference(size_label: str, fit_preference: str) -> str:
        size_order = infer_size_order(size_label)
        if size_label not in size_order:
            return size_label

        fit_offsets = {"slim": -1, "regular": 0, "relaxed": 1}
        offset = int(fit_offsets.get(fit_preference, 0))
        idx = size_order.index(size_label)
        mapped_idx = min(max(idx + offset, 0), len(size_order) - 1)
        return size_order[mapped_idx]

    @staticmethod
    def _size_from_chart(value_in: float, chart: list[tuple[float, float, str]]) -> str:
        if value_in <= 0:
            return "M"

        for low, high, size_label in chart:
            if low <= value_in < high:
                return size_label

        if value_in < chart[0][0]:
            return chart[0][2]
        return chart[-1][2]

    @staticmethod
    def _nearest_size(value: float, points: list[tuple[float, str]]) -> str:
        if value <= 0 or not points:
            return "M"

        nearest = min(points, key=lambda item: abs(item[0] - value))
        return nearest[1]

    @staticmethod
    def _nike_top_chart(gender: str) -> list[tuple[float, float, str]]:
        normalized = gender.strip().lower()
        if normalized == "female":
            return [
                (29.5, 32.5, "XS"),
                (32.5, 35.5, "S"),
                (35.5, 38.0, "M"),
                (38.0, 41.0, "L"),
                (41.0, 44.5, "XL"),
                (44.5, 49.5, "XXL"),
            ]

        return [
            (32.5, 35.0, "XS"),
            (35.0, 37.5, "S"),
            (37.5, 41.0, "M"),
            (41.0, 44.0, "L"),
            (44.0, 48.5, "XL"),
            (48.5, 53.5, "XXL"),
        ]

    @staticmethod
    def _nike_bottom_chart(gender: str) -> list[tuple[float, float, str]]:
        normalized = gender.strip().lower()
        if normalized == "female":
            return [
                (23.5, 26.0, "XS"),
                (26.0, 29.0, "S"),
                (29.0, 31.5, "M"),
                (31.5, 35.0, "L"),
                (35.0, 38.5, "XL"),
                (38.5, 43.5, "XXL"),
            ]

        return [
            (26.0, 29.0, "XS"),
            (29.0, 32.0, "S"),
            (32.0, 35.0, "M"),
            (35.0, 38.0, "L"),
            (38.0, 43.0, "XL"),
            (43.0, 47.5, "XXL"),
        ]

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
