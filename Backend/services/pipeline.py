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
from services.size_predictor import SizePredictorService, get_size_predictor_service
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
        )

        base_size, base_confidence = self.size_predictor.predict(measurements_cm)
        predicted_size = self.size_predictor.apply_fit_preference(base_size, fit_preference)

        confidence = self._adjust_confidence(
            base_confidence=base_confidence,
            fit_preference=fit_preference,
            quality_score=float(quality_report.get("overall_score", 75.0)),
        )

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
        )

        return {
            "measurement_unit": unit_system,
            "measurements": measurements_output,
            "fit_preference": fit_preference,
            "predicted_size": predicted_size,
            "confidence": round(confidence, 4),
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
    def _adjust_confidence(
        base_confidence: float,
        fit_preference: str,
        quality_score: float,
    ) -> float:
        quality_factor = float(np.interp(quality_score, [35.0, 100.0], [0.78, 1.04]))
        fit_penalty = {
            "slim": 0.03,
            "regular": 0.00,
            "relaxed": 0.015,
        }.get(fit_preference, 0.0)

        adjusted = (base_confidence * quality_factor) - fit_penalty
        return float(np.clip(adjusted, 0.5, 0.99))


@lru_cache(maxsize=1)
def get_pipeline() -> SmartFitPipeline:
    settings = get_settings()
    return SmartFitPipeline(
        image_processing=get_image_processing_service(),
        quality_checker=get_capture_quality_service(),
        size_predictor=get_size_predictor_service(settings.model_path),
        virtual_tryon=get_virtual_tryon_service(settings.tryon_assets_dir),
    )
