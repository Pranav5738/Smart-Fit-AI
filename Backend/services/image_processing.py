from dataclasses import dataclass
from typing import Dict, Tuple

import cv2
import mediapipe as mp
import numpy as np

from utils.exceptions import LandmarkDetectionError


@dataclass
class PoseExtractionResult:
    pixel_measurements: Dict[str, float]
    body_height_px: float
    torso_points: Dict[str, Tuple[int, int]]


class ImageProcessingService:
    """Extract body landmarks and pixel-level body widths from an image."""

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        min_landmark_visibility: float = 0.35,
    ) -> None:
        self._mp_pose = mp.solutions.pose
        self._min_landmark_visibility = min_landmark_visibility
        self._pose = self._mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    @staticmethod
    def decode_image(image_bytes: bytes) -> np.ndarray:
        np_image = np.frombuffer(image_bytes, dtype=np.uint8)
        image_bgr = cv2.imdecode(np_image, cv2.IMREAD_COLOR)

        if image_bgr is None:
            raise LandmarkDetectionError("Invalid image input. Could not decode image bytes.")

        return image_bgr

    def extract_measurements(self, image_bgr: np.ndarray) -> PoseExtractionResult:
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self._pose.process(image_rgb)

        if not results.pose_landmarks:
            raise LandmarkDetectionError(
                "No pose landmarks detected. Use a clear full-body photo (head to ankles), face the camera, and keep shoulders, hips, and ankles visible."
            )

        image_height, image_width = image_bgr.shape[:2]
        landmarks = results.pose_landmarks.landmark

        self._ensure_visible(
            landmarks,
            [
                self._mp_pose.PoseLandmark.NOSE.value,
                self._mp_pose.PoseLandmark.LEFT_SHOULDER.value,
                self._mp_pose.PoseLandmark.RIGHT_SHOULDER.value,
                self._mp_pose.PoseLandmark.LEFT_HIP.value,
                self._mp_pose.PoseLandmark.RIGHT_HIP.value,
                self._mp_pose.PoseLandmark.LEFT_ANKLE.value,
                self._mp_pose.PoseLandmark.RIGHT_ANKLE.value,
            ],
        )

        left_shoulder = self._point(
            landmarks, self._mp_pose.PoseLandmark.LEFT_SHOULDER.value, image_width, image_height
        )
        right_shoulder = self._point(
            landmarks, self._mp_pose.PoseLandmark.RIGHT_SHOULDER.value, image_width, image_height
        )
        left_hip = self._point(
            landmarks, self._mp_pose.PoseLandmark.LEFT_HIP.value, image_width, image_height
        )
        right_hip = self._point(
            landmarks, self._mp_pose.PoseLandmark.RIGHT_HIP.value, image_width, image_height
        )

        nose = self._point(
            landmarks, self._mp_pose.PoseLandmark.NOSE.value, image_width, image_height
        )
        left_ankle = self._point(
            landmarks, self._mp_pose.PoseLandmark.LEFT_ANKLE.value, image_width, image_height
        )
        right_ankle = self._point(
            landmarks, self._mp_pose.PoseLandmark.RIGHT_ANKLE.value, image_width, image_height
        )

        chest_left = self._interpolate(left_shoulder, left_hip, 0.28)
        chest_right = self._interpolate(right_shoulder, right_hip, 0.28)

        waist_left = self._interpolate(left_shoulder, left_hip, 0.62)
        waist_right = self._interpolate(right_shoulder, right_hip, 0.62)

        shoulder_width_px = float(np.linalg.norm(left_shoulder - right_shoulder))
        chest_width_px = float(np.linalg.norm(chest_left - chest_right))
        waist_width_px = float(np.linalg.norm(waist_left - waist_right))

        ankle_center_y = float((left_ankle[1] + right_ankle[1]) / 2.0)
        body_height_px = max(ankle_center_y - nose[1], 1.0)

        if shoulder_width_px <= 1.0 or chest_width_px <= 1.0 or waist_width_px <= 1.0:
            raise LandmarkDetectionError(
                "Detected landmarks are not reliable enough to calculate measurements."
            )

        torso_points = {
            "left_shoulder": (int(left_shoulder[0]), int(left_shoulder[1])),
            "right_shoulder": (int(right_shoulder[0]), int(right_shoulder[1])),
            "left_hip": (int(left_hip[0]), int(left_hip[1])),
            "right_hip": (int(right_hip[0]), int(right_hip[1])),
        }

        return PoseExtractionResult(
            pixel_measurements={
                "shoulder": shoulder_width_px,
                "chest": chest_width_px,
                "waist": waist_width_px,
            },
            body_height_px=body_height_px,
            torso_points=torso_points,
        )

    @staticmethod
    def _point(
        landmarks: list,
        landmark_index: int,
        image_width: int,
        image_height: int,
    ) -> np.ndarray:
        landmark = landmarks[landmark_index]
        x = float(np.clip(landmark.x, 0.0, 1.0)) * image_width
        y = float(np.clip(landmark.y, 0.0, 1.0)) * image_height
        return np.array([x, y], dtype=np.float32)

    @staticmethod
    def _interpolate(start: np.ndarray, end: np.ndarray, ratio: float) -> np.ndarray:
        return start + (end - start) * ratio

    def _ensure_visible(self, landmarks: list, indices: list[int]) -> None:
        for index in indices:
            landmark = landmarks[index]
            visibility = getattr(landmark, "visibility", 1.0)
            if visibility < self._min_landmark_visibility:
                raise LandmarkDetectionError(
                    "Pose detected but key landmarks are unclear. Retake with full body visible (head to ankles), stand straight facing camera, keep arms slightly away from torso, and use bright front lighting."
                )
