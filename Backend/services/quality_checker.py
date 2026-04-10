from __future__ import annotations

from functools import lru_cache
from typing import Any

import cv2
import numpy as np

from utils.logger import get_logger

logger = get_logger(__name__)


class CaptureQualityService:
    """Score upload quality to improve downstream model reliability."""

    def __init__(
        self,
        min_detection_confidence: float = 0.45,
        min_tracking_confidence: float = 0.45,
    ) -> None:
        import mediapipe as mp

        self._mp_pose = mp.solutions.pose
        self._pose = self._mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def assess(self, image_bgr: np.ndarray, language: str = "en") -> dict[str, Any]:
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        brightness = float(np.mean(gray))
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        lighting_score = self._clamp(100.0 - abs(brightness - 145.0) * 0.9)
        sharpness_score = self._clamp((sharpness / 220.0) * 100.0)

        results = self._pose.process(image_rgb)
        pose_score, framing_score, raw_hints = self._pose_and_framing_scores(results)

        if lighting_score < 55:
            raw_hints.append("better_light")
        if sharpness_score < 55:
            raw_hints.append("steady_camera")

        overall_score = self._clamp(
            (lighting_score * 0.30)
            + (pose_score * 0.30)
            + (framing_score * 0.25)
            + (sharpness_score * 0.15)
        )

        if not raw_hints:
            raw_hints.append("quality_good")

        localized_hints = [self._hint_message(hint_key, language) for hint_key in sorted(set(raw_hints))]

        return {
            "overall_score": round(overall_score, 2),
            "pose_score": round(pose_score, 2),
            "lighting_score": round(lighting_score, 2),
            "framing_score": round(framing_score, 2),
            "sharpness_score": round(sharpness_score, 2),
            "hints": localized_hints,
        }

    def _pose_and_framing_scores(self, pose_results: Any) -> tuple[float, float, list[str]]:
        hints: list[str] = []

        if not pose_results.pose_landmarks:
            hints.extend(["step_back", "full_body", "raise_camera"])
            return 15.0, 20.0, hints

        landmarks = pose_results.pose_landmarks.landmark

        essential_indices = [
            self._mp_pose.PoseLandmark.NOSE.value,
            self._mp_pose.PoseLandmark.LEFT_SHOULDER.value,
            self._mp_pose.PoseLandmark.RIGHT_SHOULDER.value,
            self._mp_pose.PoseLandmark.LEFT_HIP.value,
            self._mp_pose.PoseLandmark.RIGHT_HIP.value,
            self._mp_pose.PoseLandmark.LEFT_ANKLE.value,
            self._mp_pose.PoseLandmark.RIGHT_ANKLE.value,
        ]

        visible_landmarks = [landmarks[index] for index in essential_indices if landmarks[index].visibility >= 0.45]
        pose_score = self._clamp((len(visible_landmarks) / len(essential_indices)) * 100.0)

        if len(visible_landmarks) < len(essential_indices):
            hints.append("full_body")

        x_values = [landmark.x for landmark in visible_landmarks] or [0.5]
        y_values = [landmark.y for landmark in visible_landmarks] or [0.5]

        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(y_values), max(y_values)

        body_width_ratio = x_max - x_min
        body_height_ratio = y_max - y_min
        body_center_x = (x_min + x_max) / 2.0

        framing_penalty = 0.0

        if body_height_ratio > 0.88:
            framing_penalty += 35.0
            hints.append("step_back")
        elif body_height_ratio < 0.55:
            framing_penalty += 22.0
            hints.append("move_closer")

        if body_width_ratio > 0.75:
            framing_penalty += 20.0
            hints.append("step_back")

        if abs(body_center_x - 0.5) > 0.18:
            framing_penalty += 18.0
            hints.append("center_body")

        nose_y = landmarks[self._mp_pose.PoseLandmark.NOSE.value].y
        if nose_y > 0.30:
            framing_penalty += 10.0
            hints.append("raise_camera")

        ankle_avg_y = (
            landmarks[self._mp_pose.PoseLandmark.LEFT_ANKLE.value].y
            + landmarks[self._mp_pose.PoseLandmark.RIGHT_ANKLE.value].y
        ) / 2.0
        if ankle_avg_y > 0.95:
            framing_penalty += 8.0
            hints.append("step_back")

        framing_score = self._clamp(100.0 - framing_penalty)
        return pose_score, framing_score, hints

    @staticmethod
    def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
        return max(lower, min(upper, value))

    @staticmethod
    def _hint_message(hint_key: str, language: str) -> str:
        english_hints = {
            "step_back": "Step back so your full body is visible.",
            "full_body": "Keep your full body in frame from head to ankles.",
            "raise_camera": "Raise camera to align your body in the center.",
            "move_closer": "Move slightly closer so body landmarks are clearer.",
            "center_body": "Center your body horizontally in the frame.",
            "better_light": "Improve lighting and avoid strong backlight.",
            "steady_camera": "Hold camera steady to reduce blur.",
            "quality_good": "Great capture quality. Ready for analysis.",
        }

        spanish_hints = {
            "step_back": "Da un paso atras para que se vea todo tu cuerpo.",
            "full_body": "Manten todo tu cuerpo en cuadro, de cabeza a tobillos.",
            "raise_camera": "Eleva la camara para centrar mejor tu cuerpo.",
            "move_closer": "Acercate un poco para mejorar la deteccion.",
            "center_body": "Centra tu cuerpo horizontalmente en la imagen.",
            "better_light": "Mejora la iluminacion y evita contraluz fuerte.",
            "steady_camera": "Manten la camara estable para reducir desenfoque.",
            "quality_good": "Muy buena calidad de captura. Lista para analizar.",
        }

        lookup = spanish_hints if language.lower() == "es" else english_hints
        return lookup.get(hint_key, english_hints.get(hint_key, "Improve image capture quality."))


@lru_cache(maxsize=1)
def get_capture_quality_service() -> CaptureQualityService:
    return CaptureQualityService()
