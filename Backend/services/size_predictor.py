from pathlib import Path
from typing import Dict, Tuple

import numpy as np

from utils.logger import get_logger

try:
    import joblib
except ImportError:  # pragma: no cover
    joblib = None

try:
    from sklearn.ensemble import RandomForestClassifier
except ImportError:  # pragma: no cover
    RandomForestClassifier = None

logger = get_logger(__name__)

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
FIT_SHIFTS = {
    "slim": -1,
    "regular": 0,
    "relaxed": 1,
}


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

        self.model = self._bootstrap_model()

        if self.model is not None and joblib is not None:
            try:
                self.model_path.parent.mkdir(parents=True, exist_ok=True)
                joblib.dump(self.model, self.model_path)
                logger.info("Bootstrapped and saved fallback model to %s", self.model_path)
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed to persist fallback model: %s", exc)

    def predict(self, measurements: Dict[str, float]) -> Tuple[str, float]:
        features = np.array(
            [[measurements["chest"], measurements["waist"], measurements["shoulder"]]],
            dtype=np.float32,
        )

        if self.model is None:
            return self._heuristic_predict(measurements)

        try:
            raw_prediction = self.model.predict(features)[0]
            predicted_size = self._normalize_prediction(raw_prediction)
            confidence = self._predict_confidence(features)
            return predicted_size, confidence
        except Exception as exc:  # pragma: no cover
            logger.exception("Model prediction failed. Using fallback heuristic: %s", exc)
            return self._heuristic_predict(measurements)

    def apply_fit_preference(self, size_label: str, fit_preference: str) -> str:
        shift = FIT_SHIFTS.get(fit_preference, 0)
        return self._shift_size(size_label, shift)

    def _bootstrap_model(self):
        if RandomForestClassifier is None:
            logger.warning(
                "scikit-learn is not installed. Falling back to heuristic size prediction."
            )
            return None

        # Synthetic training data provides a robust default when no artifact is available.
        rng = np.random.default_rng(42)
        size_bands = {
            "XS": {"chest": (78.0, 86.0), "waist": (66.0, 74.0), "shoulder": (38.0, 42.0)},
            "S": {"chest": (86.0, 94.0), "waist": (74.0, 82.0), "shoulder": (41.0, 44.0)},
            "M": {"chest": (94.0, 102.0), "waist": (82.0, 90.0), "shoulder": (43.0, 46.0)},
            "L": {"chest": (102.0, 110.0), "waist": (90.0, 98.0), "shoulder": (45.0, 48.0)},
            "XL": {"chest": (110.0, 118.0), "waist": (98.0, 106.0), "shoulder": (47.0, 50.0)},
            "XXL": {"chest": (118.0, 128.0), "waist": (106.0, 116.0), "shoulder": (49.0, 53.0)},
        }

        features = []
        labels = []

        for size, limits in size_bands.items():
            chest_low, chest_high = limits["chest"]
            waist_low, waist_high = limits["waist"]
            shoulder_low, shoulder_high = limits["shoulder"]

            chest_values = rng.normal(
                loc=(chest_low + chest_high) / 2.0,
                scale=(chest_high - chest_low) / 5.5,
                size=260,
            )
            waist_values = rng.normal(
                loc=(waist_low + waist_high) / 2.0,
                scale=(waist_high - waist_low) / 5.5,
                size=260,
            )
            shoulder_values = rng.normal(
                loc=(shoulder_low + shoulder_high) / 2.0,
                scale=(shoulder_high - shoulder_low) / 5.5,
                size=260,
            )

            for chest, waist, shoulder in zip(chest_values, waist_values, shoulder_values):
                features.append([float(chest), float(waist), float(shoulder)])
                labels.append(size)

        X = np.asarray(features, dtype=np.float32)
        y = np.asarray(labels)

        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=2,
            random_state=42,
            class_weight="balanced_subsample",
        )
        model.fit(X, y)
        logger.info("Bootstrapped fallback RandomForest model for size prediction.")
        return model

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

        if chest < 84 and waist < 72:
            predicted_size = "XS"
        elif chest < 92 and waist < 80:
            predicted_size = "S"
        elif chest < 100 and waist < 88:
            predicted_size = "M"
        elif chest < 108 and waist < 96:
            predicted_size = "L"
        elif chest < 116 and waist < 104:
            predicted_size = "XL"
        else:
            predicted_size = "XXL"

        band_centers = {
            "XS": (82.0, 70.0),
            "S": (88.0, 76.0),
            "M": (96.0, 84.0),
            "L": (104.0, 92.0),
            "XL": (112.0, 100.0),
            "XXL": (120.0, 108.0),
        }
        target_chest, target_waist = band_centers[predicted_size]

        distance = np.sqrt(
            ((chest - target_chest) / 6.0) ** 2 + ((waist - target_waist) / 5.0) ** 2
        )
        confidence = float(np.clip(0.95 - (distance * 0.08), 0.60, 0.95))

        return predicted_size, confidence

    @staticmethod
    def _shift_size(size_label: str, shift: int) -> str:
        normalized = size_label.upper().strip()
        if normalized not in SIZE_ORDER:
            return size_label

        current_index = SIZE_ORDER.index(normalized)
        next_index = min(max(current_index + shift, 0), len(SIZE_ORDER) - 1)
        return SIZE_ORDER[next_index]
