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
        front_image_bytes: bytes,
        side_image_bytes: bytes,
        user_height_cm: Optional[float] = None,
        age_group: str = "adult",
        gender: str = "unisex",
        fit_preference: str = "regular",
        unit_system: str = "cm",
        language: str = "en",
        categories: list[str] | None = None,
        preferred_brands: list[str] | None = None,
        occasions: list[str] | None = None,
        weather: list[str] | None = None,
        colors: list[str] | None = None,
        include_tryon_comparison: bool = True,
        extra_front_image_bytes: list[bytes] | None = None,
        extra_side_image_bytes: list[bytes] | None = None,
        capture_quality: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        front_images = [front_image_bytes] + list(extra_front_image_bytes or [])
        side_images = [side_image_bytes] + list(extra_side_image_bytes or [])

        front_results = [
            self.image_processing.extract_measurements(
                self.image_processing.decode_image(image_bytes),
                view="front",
            )
            for image_bytes in front_images
        ]
        side_results = [
            self.image_processing.extract_measurements(
                self.image_processing.decode_image(image_bytes),
                view="side",
            )
            for image_bytes in side_images
        ]

        front_result = self._aggregate_pose_results(front_results)
        side_result = self._aggregate_pose_results(side_results)

        primary_front_bgr = self.image_processing.decode_image(front_image_bytes)
        quality_report = capture_quality or self.quality_checker.assess(primary_front_bgr, language=language)

        measurements_cm = self.measurement_conversion.convert_to_cm(
            front_pixel_measurements=front_result.pixel_measurements,
            side_pixel_measurements=side_result.pixel_measurements,
            front_body_height_px=front_result.body_height_px,
            side_body_height_px=side_result.body_height_px,
            user_height_cm=user_height_cm,
            age_group=age_group,
            front_debug=front_result.measurement_debug,
            side_debug=side_result.measurement_debug,
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
            front_pose_quality=front_result.pose_quality,
            side_pose_quality=side_result.pose_quality,
            capture_quality=quality_report,
            front_frame_count=len(front_results),
            side_frame_count=len(side_results),
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
            preferred_brands=preferred_brands,
            occasions=occasions,
            weather=weather,
            colors=colors,
            limit=8,
        )

        preferred_brand_set = {brand.strip().lower() for brand in preferred_brands or [] if brand.strip()}
        nike_size_suggestions = (
            self.brand_mapping.nike_top_bottom_suggestions(
                measurements_cm=measurements_cm,
                fit_preference=fit_preference,
                gender=gender,
            )
            if "nike" in preferred_brand_set
            else None
        )
        zara_size_suggestions = (
            self.brand_mapping.zara_top_bottom_suggestions(
                measurements_cm=measurements_cm,
                fit_preference=fit_preference,
                gender=gender,
            )
            if "zara" in preferred_brand_set
            else None
        )

        tryon_outputs = self.virtual_tryon.generate_tryon_outputs(
            image_bgr=primary_front_bgr,
            torso_points=front_result.torso_points,
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
                "pixel_debug": front_result.measurement_debug,
                "front_pixel_debug": front_result.measurement_debug,
                "side_pixel_debug": side_result.measurement_debug,
                "front_frames_used": len(front_results),
                "side_frames_used": len(side_results),
            },
            "fit_preference": fit_preference,
            "predicted_size": predicted_size,
            "confidence": round(confidence, 4),
            "confidence_components": confidence_details,
            "prediction_confidence_level": confidence_level,
            "size_range": size_range,
            "prediction_advice": prediction_advice,
            "brand_mapping": brand_mapping,
            "nike_size_suggestions": nike_size_suggestions,
            "zara_size_suggestions": zara_size_suggestions,
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
        front_pose_quality: dict[str, float],
        side_pose_quality: dict[str, float],
        capture_quality: dict[str, Any],
        front_frame_count: int,
        side_frame_count: int,
    ) -> dict[str, float]:
        front_pose_score = float(np.clip(float(front_pose_quality.get("overall_score", 70.0)) / 100.0, 0.0, 1.0))
        side_pose_score = float(np.clip(float(side_pose_quality.get("overall_score", 65.0)) / 100.0, 0.0, 1.0))
        pose_quality_score = (front_pose_score * 0.65) + (side_pose_score * 0.35)

        landmark_visibility = float(
            np.clip(
                (
                    float(front_pose_quality.get("visibility_score", 70.0)) * 0.65
                    + float(side_pose_quality.get("visibility_score", 65.0)) * 0.35
                )
                / 100.0,
                0.0,
                1.0,
            )
        )
        measurement_consistency = float(
            np.clip(
                (
                    float(front_pose_quality.get("measurement_consistency", 70.0)) * 0.6
                    + float(side_pose_quality.get("measurement_consistency", 65.0)) * 0.4
                )
                / 100.0,
                0.0,
                1.0,
            )
        )
        demographic_match_confidence = float(np.clip(base_confidence, 0.0, 1.0))

        quality_guard = float(np.clip(float(capture_quality.get("overall_score", 75.0)) / 100.0, 0.0, 1.0))
        low_resolution_penalty = float(
            np.clip(1.0 - (float(front_pose_quality.get("resolution_score", 75.0)) / 100.0), 0.0, 0.22)
        )
        side_pose_penalty = float(np.clip(1.0 - side_pose_score, 0.0, 0.24))
        missing_side_penalty = 0.18 if side_frame_count <= 0 else 0.0

        frame_bonus = 0.0
        if front_frame_count > 1:
            frame_bonus += min(0.03, (front_frame_count - 1) * 0.01)
        if side_frame_count > 1:
            frame_bonus += min(0.03, (side_frame_count - 1) * 0.01)

        weighted = (
            0.4 * pose_quality_score
            + 0.3 * landmark_visibility
            + 0.2 * measurement_consistency
            + 0.1 * demographic_match_confidence
        )
        final_confidence = float(
            np.clip(
                (weighted * (0.82 + (0.18 * quality_guard))) - low_resolution_penalty - side_pose_penalty + frame_bonus,
                0.30,
                0.99,
            )
        )
        final_confidence = float(
            np.clip(
                final_confidence - missing_side_penalty,
                0.30,
                0.99,
            )
        )

        return {
            "pose_quality": round(pose_quality_score, 4),
            "landmark_visibility": round(landmark_visibility, 4),
            "measurement_consistency": round(measurement_consistency, 4),
            "demographic_match_confidence": round(demographic_match_confidence, 4),
            "quality_guard": round(quality_guard, 4),
            "low_resolution_penalty": round(low_resolution_penalty, 4),
            "side_pose_penalty": round(side_pose_penalty, 4),
            "missing_side_penalty": round(missing_side_penalty, 4),
            "frame_bonus": round(frame_bonus, 4),
            "final_confidence": round(final_confidence, 4),
        }

    @staticmethod
    def _aggregate_pose_results(results: list[Any]) -> Any:
        if not results:
            raise ValueError("No pose extraction results available for aggregation.")
        if len(results) == 1:
            return results[0]

        base = results[0]
        keys = set(base.pixel_measurements.keys())
        averaged_measurements = {
            key: float(np.mean([result.pixel_measurements.get(key, 0.0) for result in results]))
            for key in keys
        }
        averaged_pose_quality = {
            key: float(np.mean([result.pose_quality.get(key, 0.0) for result in results]))
            for key in base.pose_quality.keys()
        }
        averaged_debug = {
            key: float(np.mean([result.measurement_debug.get(key, 0.0) for result in results]))
            for key in base.measurement_debug.keys()
        }

        base.pixel_measurements = averaged_measurements
        base.body_height_px = float(np.mean([result.body_height_px for result in results]))
        base.pose_quality = averaged_pose_quality
        base.measurement_debug = averaged_debug
        return base

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
