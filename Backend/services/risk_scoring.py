from __future__ import annotations

from typing import Any

from services.size_predictor import SIZE_ORDER


class ReturnRiskService:
    """Estimate return risk and suggest alternative fit options."""

    def score(
        self,
        predicted_size: str,
        fit_preference: str,
        confidence: float,
        brand_mapping: dict[str, str],
        capture_quality: dict[str, Any] | None,
    ) -> dict[str, Any]:
        confidence_percent = confidence * 100.0 if confidence <= 1.0 else min(confidence, 100.0)
        quality_score = float((capture_quality or {}).get("overall_score", 75.0))

        unique_brand_sizes = {size.upper().strip() for size in brand_mapping.values() if size}
        brand_variance_penalty = 4.0 if len(unique_brand_sizes) <= 1 else 11.0 if len(unique_brand_sizes) == 2 else 18.0

        fit_penalty = {
            "slim": 9.0,
            "regular": 5.0,
            "relaxed": 6.0,
        }.get(fit_preference, 5.0)

        confidence_penalty = max(0.0, 100.0 - confidence_percent) * 0.55
        quality_penalty = max(0.0, 80.0 - quality_score) * 0.6

        score = min(100.0, confidence_penalty + quality_penalty + brand_variance_penalty + fit_penalty)

        level = "low"
        if score >= 60.0:
            level = "high"
        elif score >= 35.0:
            level = "medium"

        reasons: list[str] = []
        if confidence_percent < 80.0:
            reasons.append("Model confidence is moderate, so neighboring sizes may still fit.")
        if quality_score < 70.0:
            reasons.append("Image quality suggests higher measurement uncertainty.")
        if len(unique_brand_sizes) > 1:
            reasons.append("Brand mapping differs across labels, increasing size variance.")
        if fit_preference == "slim":
            reasons.append("Slim fit preference tightens tolerance and increases return sensitivity.")
        if not reasons:
            reasons.append("High confidence and stable brand mapping indicate low return probability.")

        alternatives = {
            "best_fit": predicted_size,
            "comfort_fit": self._shift_size(predicted_size, 1),
            "style_fit": self._style_fit(predicted_size, fit_preference),
        }

        return {
            "score": round(score, 2),
            "level": level,
            "reasons": reasons,
            "alternatives": alternatives,
        }

    @staticmethod
    def _style_fit(base_size: str, fit_preference: str) -> str:
        if fit_preference == "slim":
            return ReturnRiskService._shift_size(base_size, -1)
        if fit_preference == "relaxed":
            return ReturnRiskService._shift_size(base_size, 1)
        return base_size

    @staticmethod
    def _shift_size(base_size: str, shift: int) -> str:
        normalized = base_size.upper().strip()
        if normalized not in SIZE_ORDER:
            return base_size

        start_index = SIZE_ORDER.index(normalized)
        shifted_index = min(max(start_index + shift, 0), len(SIZE_ORDER) - 1)
        return SIZE_ORDER[shifted_index]
