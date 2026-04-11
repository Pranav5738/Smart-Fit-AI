import math
from typing import Dict, Optional

from utils.exceptions import MeasurementConversionError


class MeasurementConversionService:
    """Convert image-space distances into centimeter measurements."""

    def __init__(self, default_user_height_cm: float = 170.0, round_digits: int = 2) -> None:
        self.default_user_height_cm = default_user_height_cm
        self.round_digits = round_digits

    def convert_to_cm(
        self,
        front_pixel_measurements: Dict[str, float],
        side_pixel_measurements: Dict[str, float],
        front_body_height_px: float,
        side_body_height_px: float,
        user_height_cm: Optional[float] = None,
        age_group: str = "adult",
        front_debug: Optional[Dict[str, float]] = None,
        side_debug: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        if front_body_height_px <= 1.0 or side_body_height_px <= 1.0:
            raise MeasurementConversionError(
                "Body height in pixels is too small for conversion."
            )

        age_group_defaults = {
            "child": 125.0,
            "teen": 155.0,
            "adult": self.default_user_height_cm,
        }
        normalized_age_group = (age_group or "adult").strip().lower()
        fallback_height = age_group_defaults.get(normalized_age_group, self.default_user_height_cm)

        effective_height_cm = (
            user_height_cm
            if user_height_cm is not None and user_height_cm > 80
            else fallback_height
        )

        front_debug = front_debug or {}
        side_debug = side_debug or {}

        front_cm_per_pixel = effective_height_cm / front_body_height_px
        side_cm_per_pixel = effective_height_cm / side_body_height_px

        shoulder_width_cm = float(front_pixel_measurements["shoulder"]) * front_cm_per_pixel
        chest_width_cm = float(front_pixel_measurements["chest"]) * front_cm_per_pixel
        waist_width_cm = float(front_pixel_measurements["waist"]) * front_cm_per_pixel

        chest_depth_cm = float(side_pixel_measurements["chest"]) * side_cm_per_pixel
        waist_depth_cm = float(side_pixel_measurements["waist"]) * side_cm_per_pixel

        # Dynamic shape-aware depth adaptation from shoulder-to-waist ratio.
        shoulder_to_waist_ratio = shoulder_width_cm / max(waist_width_cm, 1.0)
        depth_shape_adjust = float(min(max(1.0 + ((1.15 - shoulder_to_waist_ratio) * 0.18), 0.86), 1.14))
        chest_depth_cm *= depth_shape_adjust
        waist_depth_cm *= (2.0 - depth_shape_adjust)

        # Normalize scale with anthropometric shoulder anchor and hip/shoulder proportion.
        shoulder_anchor_cm = {
            "child": 31.0,
            "teen": 38.0,
            "adult": 44.0,
        }.get(normalized_age_group, 44.0)

        observed_hip_to_shoulder = float(front_debug.get("hip_to_shoulder_ratio", 0.9))
        expected_hip_to_shoulder = {
            "child": 0.95,
            "teen": 0.90,
            "adult": 0.86,
        }.get(normalized_age_group, 0.86)

        shoulder_ratio_factor = float(
            min(max(shoulder_anchor_cm / max(shoulder_width_cm, 1.0), 0.90), 1.10)
        )
        proportion_factor = float(
            min(max(expected_hip_to_shoulder / max(observed_hip_to_shoulder, 0.1), 0.92), 1.08)
        )
        perspective_factor = float(
            min(max(float(front_debug.get("perspective_factor", 1.0)), 0.92), 1.12)
        )

        global_scale_correction = (0.5 * shoulder_ratio_factor) + (0.3 * proportion_factor) + (0.2 * perspective_factor)

        shoulder_cm = shoulder_width_cm * global_scale_correction
        chest_cm = self._ellipse_circumference(chest_width_cm * global_scale_correction, chest_depth_cm * global_scale_correction)
        waist_cm = self._ellipse_circumference(waist_width_cm * global_scale_correction, waist_depth_cm * global_scale_correction)

        return {
            "chest": round(chest_cm, self.round_digits),
            "waist": round(waist_cm, self.round_digits),
            "shoulder": round(shoulder_cm, self.round_digits),
        }

    @staticmethod
    def _ellipse_circumference(width_cm: float, depth_cm: float) -> float:
        major = max(width_cm, 1.0) / 2.0
        minor = max(depth_cm, 1.0) / 2.0
        h = ((major - minor) ** 2) / max((major + minor) ** 2, 1e-6)
        # Ramanujan approximation (accurate and efficient for ellipse circumference).
        return math.pi * (major + minor) * (1.0 + ((3.0 * h) / (10.0 + math.sqrt(max(4.0 - (3.0 * h), 1e-6)))))

    def convert_measurements(
        self,
        measurements_cm: Dict[str, float],
        unit_system: str = "cm",
    ) -> Dict[str, float]:
        if unit_system.lower() == "cm":
            return {
                key: round(float(value), self.round_digits)
                for key, value in measurements_cm.items()
            }

        inch_factor = 0.3937007874
        return {
            key: round(float(value) * inch_factor, self.round_digits)
            for key, value in measurements_cm.items()
        }
