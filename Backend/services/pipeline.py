from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

import numpy as np

from services.brand_mapping import BrandMappingService
from services.explainability import ExplainabilityService
from services.image_processing import ImageProcessingService, get_image_processing_service
from services.measurement_conversion import MeasurementConversionService
from services.quality_checker import CaptureQualityService, get_capture_quality_service
from services.recommendation import RecommendationService
from services.risk_scoring import ReturnRiskService
from services.size_predictor import SizePredictorService, get_size_predictor_service, infer_size_order
from services.virtual_tryon import VirtualTryOnService
from services.virtual_tryon import get_virtual_tryon_service
from utils.config import get_settings


class SmartFitPipeline:
    """End-to-end orchestration for SmartFit image analysis."""

    def __init__(
        self,
        image_processing: ImageProcessingService | None = None,
        quality_checker: CaptureQualityService | None = None,
        size_predictor: SizePredictorService | None = None,
        virtual_tryon: VirtualTryOnService | None = None,
    ) -> None:
        settings = get_settings()
        self._consent_version = settings.consent_version

        self.image_processing = image_processing or get_image_processing_service()
        self.measurement_conversion = MeasurementConversionService(
            default_user_height_cm=settings.default_user_height_cm,
            round_digits=settings.measurement_round_digits,
        )
        self.quality_checker = quality_checker or get_capture_quality_service()
        self.size_predictor = size_predictor or get_size_predictor_service(settings.model_path)
        self.brand_mapping = BrandMappingService()
        self.recommendation = RecommendationService()
        self.return_risk = ReturnRiskService()
        self.explainability = ExplainabilityService()
        self.virtual_tryon = virtual_tryon or get_virtual_tryon_service(settings.tryon_assets_dir)

    def analyze_image(
        self,
        image_bytes: bytes,
        user_height_cm: Optional[float] = None,
        age_group: str = "adult",
        gender: str = "unisex",
        fit_preference: str = "regular",
        unit_system: str = "cm",
        language: str = "en",
        categories: list[str] | None = None,
        occasions: list[str] | None = None,
        weather: list[str] | None = None,
        colors: list[str] | None = None,
        include_tryon_comparison: bool = True,
        capture_quality: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        image_bgr = self.image_processing.decode_image(image_bytes)
        quality_report = capture_quality or self.quality_checker.assess(image_bgr, language=language)

        pose_result = self.image_processing.extract_measurements(image_bgr)

        measurements_cm = self.measurement_conversion.convert_to_cm(
            pixel_measurements=pose_result.pixel_measurements,
            body_height_px=pose_result.body_height_px,
            user_height_cm=user_height_cm,
            age_group=age_group,
        )

        base_size, base_confidence = self.size_predictor.predict(
            measurements=measurements_cm,
            age_group=age_group,
            gender=gender,
        )
        predicted_size = self.size_predictor.apply_fit_preference(
            size_label=base_size,
            fit_preference=fit_preference,
            age_group=age_group,
            gender=gender,
        )

        confidence_details = self._compute_confidence_details(
            base_confidence=base_confidence,
            pose_quality=pose_result.pose_quality,
            capture_quality=quality_report,
        )
        confidence = confidence_details["final_confidence"]

        brand_mapping_category = categories[0] if categories else "tees"

        brand_mapping, brand_logic = self.brand_mapping.map_with_explanation(
            base_size=predicted_size,
            fit_preference=fit_preference,
            category=brand_mapping_category,
        )

        recommendations = self.recommendation.generate(
            predicted_size=predicted_size,
            fit_preference=fit_preference,
            brand_mapper=self.brand_mapping,
            categories=categories,
            occasions=occasions,
            weather=weather,
            colors=colors,
            limit=8,
        )

        tryon_outputs = self.virtual_tryon.generate_tryon_outputs(
            image_bgr=image_bgr,
            torso_points=pose_result.torso_points,
            include_comparison=include_tryon_comparison,
        )

        measurements_output = self.measurement_conversion.convert_measurements(
            measurements_cm=measurements_cm,
            unit_system=unit_system,
        )

        return_risk = self.return_risk.score(
            predicted_size=predicted_size,
            fit_preference=fit_preference,
            confidence=confidence,
            brand_mapping=brand_mapping,
            capture_quality=quality_report,
        )

        explainability = self.explainability.build(
            measurements=measurements_output,
            measurement_unit=unit_system,
            predicted_size=predicted_size,
            confidence=confidence,
            fit_preference=fit_preference,
            capture_quality=quality_report,
            brand_adjustment_logic=brand_logic,
            age_group=age_group,
            gender=gender,
        )

        confidence_level = self._confidence_level(confidence)
        size_range = self._size_range(predicted_size, span=1) if confidence < 0.65 else None
        prediction_advice = (
            "Retake image with full body visible and enter accurate height for better sizing confidence."
            if confidence < 0.65
            else "Use recommended size with comfort alternative if between sizes."
            if confidence < 0.85
            else "Prediction is stable. Recommended size can be used directly."
        )

        return {
            "measurement_unit": unit_system,
            "age_group": age_group,
            "gender": gender,
            "measurements": measurements_output,
            "measurement_breakdown": {
                "height_cm_used": round(
                    float(user_height_cm)
                    if user_height_cm is not None and user_height_cm > 80
                    else {"child": 125.0, "teen": 155.0, "adult": self.measurement_conversion.default_user_height_cm}.get(age_group, self.measurement_conversion.default_user_height_cm),
                    2,
                ),
                "pixel_debug": pose_result.measurement_debug,
            },
            "fit_preference": fit_preference,
            "predicted_size": predicted_size,
            "confidence": round(confidence, 4),
            "confidence_components": confidence_details,
            "prediction_confidence_level": confidence_level,
            "size_range": size_range,
            "prediction_advice": prediction_advice,
            "brand_mapping": brand_mapping,
            "recommendations": recommendations,
            "capture_quality": quality_report,
            "explainability": explainability,
            "return_risk": return_risk,
            "tryon_image": tryon_outputs["tryon_image"],
            "tryon_comparison": tryon_outputs.get("tryon_comparison"),
            "privacy": {
                "consent_accepted": True,
                "consent_version": self._consent_version,
                "image_auto_deleted": True,
                "data_retention": "Uploaded image bytes are processed in-memory and not persisted.",
            },
        }

    @staticmethod
    def _compute_confidence_details(
        base_confidence: float,
        pose_quality: dict[str, float],
        capture_quality: dict[str, Any],
    ) -> dict[str, float]:
        pose_quality_score = float(np.clip(float(pose_quality.get("overall_score", 70.0)) / 100.0, 0.0, 1.0))
        landmark_visibility = float(np.clip(float(pose_quality.get("visibility_score", 70.0)) / 100.0, 0.0, 1.0))
        measurement_consistency = float(np.clip(float(pose_quality.get("measurement_consistency", 70.0)) / 100.0, 0.0, 1.0))
        demographic_match_confidence = float(np.clip(base_confidence, 0.0, 1.0))

        quality_guard = float(np.clip(float(capture_quality.get("overall_score", 75.0)) / 100.0, 0.0, 1.0))

        weighted = (
            0.4 * pose_quality_score
            + 0.3 * landmark_visibility
            + 0.2 * measurement_consistency
            + 0.1 * demographic_match_confidence
        )
        final_confidence = float(np.clip(weighted * (0.82 + (0.18 * quality_guard)), 0.35, 0.99))

        return {
            "pose_quality": round(pose_quality_score, 4),
            "landmark_visibility": round(landmark_visibility, 4),
            "measurement_consistency": round(measurement_consistency, 4),
            "demographic_match_confidence": round(demographic_match_confidence, 4),
            "quality_guard": round(quality_guard, 4),
            "final_confidence": round(final_confidence, 4),
        }

    @staticmethod
    def _confidence_level(confidence: float) -> str:
        if confidence >= 0.85:
            return "high"
        if confidence >= 0.65:
            return "medium"
        return "low"

    @staticmethod
    def _size_range(size_label: str, span: int = 1) -> str:
        size_order = infer_size_order(size_label)
        normalized = size_label.upper().strip()
        if normalized not in size_order:
            return size_label

        index = size_order.index(normalized)
        low_index = max(0, index - span)
        high_index = min(len(size_order) - 1, index + span)
        if low_index == high_index:
            return size_order[index]
        return f"{size_order[low_index]}-{size_order[high_index]}"


@lru_cache(maxsize=1)
def get_pipeline() -> SmartFitPipeline:
    settings = get_settings()
    return SmartFitPipeline(
        image_processing=get_image_processing_service(),
        quality_checker=get_capture_quality_service(),
        size_predictor=get_size_predictor_service(settings.model_path),
        virtual_tryon=get_virtual_tryon_service(settings.tryon_assets_dir),
    )
