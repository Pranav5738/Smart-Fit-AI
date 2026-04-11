from pathlib import Path
from functools import lru_cache
from typing import Dict, Tuple

import numpy as np

from utils.logger import get_logger

try:
    import joblib
except ImportError:  # pragma: no cover
    joblib = None

logger = get_logger(__name__)

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
FIT_SHIFTS = {
    "slim": -1,
    "regular": 0,
    "relaxed": 1,
}

PROFILE_SIZE_ORDERS: dict[str, list[str]] = {
    "adult:male": ["XS", "S", "M", "L", "XL", "XXL"],
    "adult:female": ["XS", "S", "M", "L", "XL", "XXL"],
    "adult:unisex": ["XS", "S", "M", "L", "XL", "XXL"],
    "teen:male": ["10Y", "12Y", "14Y", "16Y", "18Y"],
    "teen:female": ["10Y", "12Y", "14Y", "16Y", "18Y"],
    "teen:unisex": ["10Y", "12Y", "14Y", "16Y", "18Y"],
    "child:male": ["3Y", "4Y", "5Y", "6Y", "7Y", "8Y", "10Y", "12Y"],
    "child:female": ["3Y", "4Y", "5Y", "6Y", "7Y", "8Y", "10Y", "12Y"],
    "child:unisex": ["3Y", "4Y", "5Y", "6Y", "7Y", "8Y", "10Y", "12Y"],
}

PROFILE_BANDS: dict[str, dict[str, dict[str, tuple[float, float]]]] = {
    "adult:male": {
        # Based on the provided chart: XS=36in, S=38in, M=40in, L=42in, XL=44in, 2XL=46in.
        # Chest ranges are in centimeters around each 2-inch step; XXL maps to 2XL.
        "XS": {"chest": (89.0, 94.5), "waist": (76.0, 81.0), "shoulder": (40.0, 43.0)},
        "S": {"chest": (94.5, 99.5), "waist": (81.0, 86.0), "shoulder": (42.0, 44.0)},
        "M": {"chest": (99.5, 104.5), "waist": (86.0, 91.0), "shoulder": (44.0, 46.0)},
        "L": {"chest": (104.5, 109.5), "waist": (91.0, 96.0), "shoulder": (46.0, 48.0)},
        "XL": {"chest": (109.5, 114.5), "waist": (96.0, 101.0), "shoulder": (48.0, 50.0)},
        "XXL": {"chest": (114.5, 119.5), "waist": (101.0, 106.0), "shoulder": (50.0, 52.0)},
    },
    "adult:female": {
        "XXS": {"chest": (74.0, 80.0), "waist": (58.0, 64.0), "shoulder": (35.0, 37.0)},
        "XS": {"chest": (80.0, 86.0), "waist": (64.0, 70.0), "shoulder": (36.0, 38.0)},
        "S": {"chest": (86.0, 92.0), "waist": (70.0, 76.0), "shoulder": (37.0, 39.0)},
        "M": {"chest": (92.0, 98.0), "waist": (76.0, 82.0), "shoulder": (38.0, 40.0)},
        "L": {"chest": (98.0, 104.0), "waist": (82.0, 88.0), "shoulder": (39.0, 41.0)},
        "XL": {"chest": (104.0, 112.0), "waist": (88.0, 96.0), "shoulder": (40.0, 42.0)},
        "XXL": {"chest": (112.0, 122.0), "waist": (96.0, 106.0), "shoulder": (41.0, 44.0)},
    },
    "teen:male": {
        "10Y": {"chest": (66.0, 72.0), "waist": (57.0, 62.0), "shoulder": (32.0, 34.0)},
        "12Y": {"chest": (72.0, 78.0), "waist": (62.0, 67.0), "shoulder": (34.0, 36.0)},
        "14Y": {"chest": (78.0, 84.0), "waist": (67.0, 72.0), "shoulder": (36.0, 38.0)},
        "16Y": {"chest": (84.0, 90.0), "waist": (72.0, 77.0), "shoulder": (38.0, 40.0)},
        "18Y": {"chest": (90.0, 96.0), "waist": (77.0, 82.0), "shoulder": (40.0, 42.0)},
    },
    "teen:female": {
        "10Y": {"chest": (64.0, 70.0), "waist": (54.0, 59.0), "shoulder": (31.0, 33.0)},
        "12Y": {"chest": (70.0, 76.0), "waist": (59.0, 64.0), "shoulder": (33.0, 35.0)},
        "14Y": {"chest": (76.0, 82.0), "waist": (64.0, 69.0), "shoulder": (35.0, 37.0)},
        "16Y": {"chest": (82.0, 88.0), "waist": (69.0, 74.0), "shoulder": (37.0, 39.0)},
        "18Y": {"chest": (88.0, 94.0), "waist": (74.0, 79.0), "shoulder": (39.0, 41.0)},
    },
    "child:male": {
        "3Y": {"chest": (52.0, 56.0), "waist": (49.0, 52.0), "shoulder": (25.0, 27.0)},
        "4Y": {"chest": (56.0, 60.0), "waist": (52.0, 55.0), "shoulder": (26.0, 28.0)},
        "5Y": {"chest": (60.0, 64.0), "waist": (55.0, 58.0), "shoulder": (27.0, 29.0)},
        "6Y": {"chest": (64.0, 68.0), "waist": (58.0, 61.0), "shoulder": (28.0, 30.0)},
        "7Y": {"chest": (68.0, 72.0), "waist": (61.0, 64.0), "shoulder": (29.0, 31.0)},
        "8Y": {"chest": (72.0, 76.0), "waist": (64.0, 67.0), "shoulder": (30.0, 32.0)},
        "10Y": {"chest": (76.0, 81.0), "waist": (67.0, 71.0), "shoulder": (32.0, 34.0)},
        "12Y": {"chest": (81.0, 86.0), "waist": (71.0, 75.0), "shoulder": (34.0, 36.0)},
    },
    "child:female": {
        "3Y": {"chest": (50.0, 54.0), "waist": (48.0, 51.0), "shoulder": (24.0, 26.0)},
        "4Y": {"chest": (54.0, 58.0), "waist": (51.0, 54.0), "shoulder": (25.0, 27.0)},
        "5Y": {"chest": (58.0, 62.0), "waist": (54.0, 57.0), "shoulder": (26.0, 28.0)},
        "6Y": {"chest": (62.0, 66.0), "waist": (57.0, 60.0), "shoulder": (27.0, 29.0)},
        "7Y": {"chest": (66.0, 70.0), "waist": (60.0, 63.0), "shoulder": (28.0, 30.0)},
        "8Y": {"chest": (70.0, 74.0), "waist": (63.0, 66.0), "shoulder": (29.0, 31.0)},
        "10Y": {"chest": (74.0, 79.0), "waist": (66.0, 70.0), "shoulder": (31.0, 33.0)},
        "12Y": {"chest": (79.0, 84.0), "waist": (70.0, 74.0), "shoulder": (33.0, 35.0)},
    },
}

for _profile in ["teen:unisex", "child:unisex", "adult:unisex"]:
    if _profile not in PROFILE_BANDS:
        reference = _profile.replace(":unisex", ":male")
        PROFILE_BANDS[_profile] = PROFILE_BANDS[reference]


def infer_size_order(size_label: str) -> list[str]:
    normalized = size_label.upper().strip()
    for order in PROFILE_SIZE_ORDERS.values():
        if normalized in order:
            return order
    return SIZE_ORDER


class SizePredictorService:
    """Predict apparel size using a trained model, with a heuristic fallback."""

    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        if joblib is not None and self.model_path.exists():
            try:
                self.model = joblib.load(self.model_path)
                logger.info("Loaded size model from %s", self.model_path)
                return
            except Exception as exc:  # pragma: no cover
                logger.exception("Failed to load model: %s", exc)
                self.model = None

        # No synthetic training fallback: rely on profile size charts by default.
        self.model = None

    def predict(
        self,
        measurements: Dict[str, float],
        age_group: str = "adult",
        gender: str = "unisex",
    ) -> Tuple[str, float]:
        profile_key = self._profile_key(age_group=age_group, gender=gender)
        profile_bands = PROFILE_BANDS.get(profile_key)
        if profile_bands is not None:
            chart_size, chart_confidence = self._profile_band_predict(
                measurements=measurements,
                size_bands=profile_bands,
            )
        else:
            chart_size, chart_confidence = self._heuristic_predict(measurements)

        features = np.array(
            [[measurements["chest"], measurements["waist"], measurements["shoulder"]]],
            dtype=np.float32,
        )

        if self.model is None:
            return chart_size, chart_confidence

        try:
            raw_prediction = self.model.predict(features)[0]
            predicted_size = self._normalize_prediction(raw_prediction)
            model_confidence = self._predict_confidence(features)

            # Blend model confidence with chart confidence to stay anchored to real fit charts.
            confidence = float(np.clip((model_confidence * 0.55) + (chart_confidence * 0.45), 0.45, 0.98))
            return predicted_size, confidence
        except Exception as exc:  # pragma: no cover
            logger.exception("Model prediction failed. Using chart mapping fallback: %s", exc)
            return chart_size, chart_confidence

    def apply_fit_preference(
        self,
        size_label: str,
        fit_preference: str,
        age_group: str = "adult",
        gender: str = "unisex",
    ) -> str:
        shift = FIT_SHIFTS.get(fit_preference, 0)
        order = PROFILE_SIZE_ORDERS.get(self._profile_key(age_group=age_group, gender=gender))
        return self._shift_size(size_label, shift, size_order=order)

    @staticmethod
    def _profile_key(age_group: str, gender: str) -> str:
        normalized_age = (age_group or "adult").strip().lower()
        normalized_gender = (gender or "unisex").strip().lower()

        if normalized_age not in {"child", "teen", "adult"}:
            normalized_age = "adult"
        if normalized_gender not in {"male", "female", "unisex"}:
            normalized_gender = "unisex"

        return f"{normalized_age}:{normalized_gender}"

    @staticmethod
    def _profile_band_predict(
        measurements: Dict[str, float],
        size_bands: dict[str, dict[str, tuple[float, float]]],
    ) -> Tuple[str, float]:
        chest = float(measurements.get("chest", 0.0))
        waist = float(measurements.get("waist", 0.0))
        shoulder = float(measurements.get("shoulder", 0.0))

        best_size = next(iter(size_bands.keys()))
        best_distance = float("inf")

        for size_label, limits in size_bands.items():
            chest_low, chest_high = limits["chest"]
            waist_low, waist_high = limits["waist"]
            shoulder_low, shoulder_high = limits["shoulder"]

            center_chest = (chest_low + chest_high) / 2.0
            center_waist = (waist_low + waist_high) / 2.0
            center_shoulder = (shoulder_low + shoulder_high) / 2.0

            chest_span = max(chest_high - chest_low, 1.0)
            waist_span = max(waist_high - waist_low, 1.0)
            shoulder_span = max(shoulder_high - shoulder_low, 1.0)

            distance = float(
                np.sqrt(
                    ((chest - center_chest) / chest_span) ** 2
                    + ((waist - center_waist) / waist_span) ** 2
                    + ((shoulder - center_shoulder) / shoulder_span) ** 2
                )
            )

            if distance < best_distance:
                best_distance = distance
                best_size = size_label

        confidence = float(np.clip(0.97 - (best_distance * 0.14), 0.55, 0.97))
        return best_size, confidence

    def _predict_confidence(self, features: np.ndarray) -> float:
        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba(features)[0]
            return float(np.clip(np.max(probabilities), 0.0, 1.0))

        # Conservative default when probabilistic confidence is unavailable.
        return 0.82

    @staticmethod
    def _normalize_prediction(raw_prediction: object) -> str:
        if isinstance(raw_prediction, str):
            candidate = raw_prediction.upper().strip()
            if candidate in SIZE_ORDER:
                return candidate

        try:
            index = int(raw_prediction)
            if 0 <= index < len(SIZE_ORDER):
                return SIZE_ORDER[index]
        except (TypeError, ValueError):
            pass

        return "M"

    @staticmethod
    def _heuristic_predict(measurements: Dict[str, float]) -> Tuple[str, float]:
        chest = measurements["chest"]
        waist = measurements["waist"]

        if chest < 94.5 and waist < 81.0:
            predicted_size = "XS"
        elif chest < 99.5 and waist < 86.0:
            predicted_size = "S"
        elif chest < 104.5 and waist < 91.0:
            predicted_size = "M"
        elif chest < 109.5 and waist < 96.0:
            predicted_size = "L"
        elif chest < 114.5 and waist < 101.0:
            predicted_size = "XL"
        else:
            predicted_size = "XXL"

        band_centers = {
            "XS": (91.4, 78.5),
            "S": (96.5, 83.5),
            "M": (101.6, 88.5),
            "L": (106.7, 93.5),
            "XL": (111.8, 98.5),
            "XXL": (116.8, 103.5),
        }
        target_chest, target_waist = band_centers[predicted_size]

        distance = np.sqrt(
            ((chest - target_chest) / 6.0) ** 2 + ((waist - target_waist) / 5.0) ** 2
        )
        confidence = float(np.clip(0.95 - (distance * 0.08), 0.60, 0.95))

        return predicted_size, confidence

    @staticmethod
    def _shift_size(size_label: str, shift: int, size_order: list[str] | None = None) -> str:
        resolved_order = size_order or infer_size_order(size_label)
        normalized = size_label.upper().strip()
        if normalized not in resolved_order:
            return size_label

        current_index = resolved_order.index(normalized)
        next_index = min(max(current_index + shift, 0), len(resolved_order) - 1)
        return resolved_order[next_index]


@lru_cache(maxsize=1)
def get_size_predictor_service(model_path: Path) -> SizePredictorService:
    return SizePredictorService(model_path=model_path)
