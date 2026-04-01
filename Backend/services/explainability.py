from __future__ import annotations

from typing import Any


class ExplainabilityService:
    """Build human-readable explanations for prediction outcomes."""

    def build(
        self,
        measurements: dict[str, float],
        measurement_unit: str,
        predicted_size: str,
        confidence: float,
        fit_preference: str,
        capture_quality: dict[str, Any],
        brand_adjustment_logic: list[dict[str, Any]],
    ) -> dict[str, Any]:
        confidence_percent = confidence * 100.0 if confidence <= 1.0 else confidence

        key_measurements = [
            {
                "metric": "chest",
                "value": measurements.get("chest", 0.0),
                "unit": measurement_unit,
                "impact": "Primary upper-body fit anchor.",
            },
            {
                "metric": "waist",
                "value": measurements.get("waist", 0.0),
                "unit": measurement_unit,
                "impact": "Determines torso comfort and silhouette.",
            },
            {
                "metric": "shoulder",
                "value": measurements.get("shoulder", 0.0),
                "unit": measurement_unit,
                "impact": "Controls jacket and shirt alignment.",
            },
        ]

        confidence_reasoning = [
            f"Model confidence score is {round(confidence_percent, 1)}% based on learned size boundaries.",
            f"Fit preference '{fit_preference}' adjusts baseline size to better match style intent.",
        ]

        quality_score = float(capture_quality.get("overall_score", 75.0))
        if quality_score < 70.0:
            confidence_reasoning.append(
                "Capture quality reduced confidence due to pose, lighting, or framing uncertainty."
            )
        else:
            confidence_reasoning.append(
                "Capture quality is strong, improving measurement trustworthiness."
            )

        size_reasoning = (
            f"Size {predicted_size} best matches chest, waist, and shoulder proportions "
            f"for the selected {fit_preference} preference."
        )

        return {
            "size_reasoning": size_reasoning,
            "key_measurements": key_measurements,
            "confidence_reasoning": confidence_reasoning,
            "brand_adjustment_logic": brand_adjustment_logic,
        }
