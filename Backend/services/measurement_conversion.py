from typing import Dict, Optional

from utils.exceptions import MeasurementConversionError


class MeasurementConversionService:
    """Convert image-space distances into centimeter measurements."""

    def __init__(self, default_user_height_cm: float = 170.0, round_digits: int = 2) -> None:
        self.default_user_height_cm = default_user_height_cm
        self.round_digits = round_digits

    def convert_to_cm(
        self,
        pixel_measurements: Dict[str, float],
        body_height_px: float,
        user_height_cm: Optional[float] = None,
    ) -> Dict[str, float]:
        if body_height_px <= 1.0:
            raise MeasurementConversionError(
                "Body height in pixels is too small for conversion."
            )

        effective_height_cm = (
            user_height_cm
            if user_height_cm is not None and user_height_cm > 80
            else self.default_user_height_cm
        )

        cm_per_pixel = effective_height_cm / body_height_px

        # Chest and waist are estimated as circumferences from torso widths.
        shoulder_cm = pixel_measurements["shoulder"] * cm_per_pixel
        chest_cm = pixel_measurements["chest"] * cm_per_pixel * 2.05
        waist_cm = pixel_measurements["waist"] * cm_per_pixel * 2.00

        return {
            "chest": round(chest_cm, self.round_digits),
            "waist": round(waist_cm, self.round_digits),
            "shoulder": round(shoulder_cm, self.round_digits),
        }

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
