from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from utils.exceptions import LandmarkDetectionError


@dataclass
class PoseExtractionResult:
    pixel_measurements: Dict[str, float]
    body_height_px: float
    torso_points: Dict[str, Tuple[int, int]]
    pose_quality: Dict[str, float]
    measurement_debug: Dict[str, float]
    view: str


class ImageProcessingService:
    """Extract body landmarks and pixel-level body widths from an image."""

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        min_landmark_visibility: float = 0.35,
    ) -> None:
        import mediapipe as mp

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

    def extract_measurements(self, image_bgr: np.ndarray, view: str = "front") -> PoseExtractionResult:
        normalized_view = (view or "front").strip().lower()
        if normalized_view not in {"front", "side"}:
            normalized_view = "front"

        image_height, image_width = image_bgr.shape[:2]
        if min(image_height, image_width) < 420:
            raise LandmarkDetectionError(
                "Image resolution is too low for accurate measurements. Use a higher resolution full-body image."
            )

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self._pose.process(image_rgb)

        if not results.pose_landmarks:
            raise LandmarkDetectionError(
                "No pose landmarks detected. Use a clear full-body photo (head to ankles), face the camera, and keep shoulders, hips, and ankles visible."
            )

        landmarks = results.pose_landmarks.landmark

        if normalized_view == "front":
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

        left_shoulder = self._optional_point(
            landmarks, self._mp_pose.PoseLandmark.LEFT_SHOULDER.value, image_width, image_height
        )
        right_shoulder = self._optional_point(
            landmarks, self._mp_pose.PoseLandmark.RIGHT_SHOULDER.value, image_width, image_height
        )
        left_elbow = self._optional_point(
            landmarks, self._mp_pose.PoseLandmark.LEFT_ELBOW.value, image_width, image_height
        )
        right_elbow = self._optional_point(
            landmarks, self._mp_pose.PoseLandmark.RIGHT_ELBOW.value, image_width, image_height
        )
        left_hip = self._optional_point(
            landmarks, self._mp_pose.PoseLandmark.LEFT_HIP.value, image_width, image_height
        )
        right_hip = self._optional_point(
            landmarks, self._mp_pose.PoseLandmark.RIGHT_HIP.value, image_width, image_height
        )

        if not any([left_shoulder is not None, right_shoulder is not None]):
            raise LandmarkDetectionError("Shoulders are not visible clearly. Retake with body centered.")
        if not any([left_hip is not None, right_hip is not None]):
            raise LandmarkDetectionError("Hips are not visible clearly. Retake with full body visible.")

        left_shoulder = left_shoulder or right_shoulder
        right_shoulder = right_shoulder or left_shoulder
        left_hip = left_hip or right_hip
        right_hip = right_hip or left_hip
        left_elbow = left_elbow or left_shoulder
        right_elbow = right_elbow or right_shoulder

        assert left_shoulder is not None and right_shoulder is not None
        assert left_hip is not None and right_hip is not None
        assert left_elbow is not None and right_elbow is not None

        nose = self._point(
            landmarks, self._mp_pose.PoseLandmark.NOSE.value, image_width, image_height
        )
        left_ankle = self._optional_point(
            landmarks, self._mp_pose.PoseLandmark.LEFT_ANKLE.value, image_width, image_height
        )
        right_ankle = self._optional_point(
            landmarks, self._mp_pose.PoseLandmark.RIGHT_ANKLE.value, image_width, image_height
        )

        if left_ankle is None and right_ankle is None:
            raise LandmarkDetectionError("Full body is not visible. Keep ankles in frame.")

        left_ankle = left_ankle or right_ankle
        right_ankle = right_ankle or left_ankle
        assert left_ankle is not None and right_ankle is not None

        chest_left = self._interpolate(left_shoulder, left_hip, 0.28)
        chest_right = self._interpolate(right_shoulder, right_hip, 0.28)

        waist_left = self._interpolate(left_shoulder, left_hip, 0.62)
        waist_right = self._interpolate(right_shoulder, right_hip, 0.62)

        shoulder_raw_px = float(np.linalg.norm(left_shoulder - right_shoulder))
        chest_torso_px = float(np.linalg.norm(chest_left - chest_right))
        elbow_proxy_px = float(np.linalg.norm(left_elbow - right_elbow))
        hip_width_px = float(np.linalg.norm(left_hip - right_hip))
        waist_torso_px = float(np.linalg.norm(waist_left - waist_right))

        shoulder_slope = abs(float(left_shoulder[1] - right_shoulder[1])) / max(shoulder_raw_px, 1.0)
        shoulder_slope_correction = float(np.clip(1.0 + (shoulder_slope * 0.22), 1.0, 1.15))

        shoulder_center = (left_shoulder + right_shoulder) / 2.0
        hip_center = (left_hip + right_hip) / 2.0
        torso_height_px = max(float(np.linalg.norm(hip_center - shoulder_center)), 1.0)
        ratio_shoulder_to_torso = shoulder_raw_px / torso_height_px

        body_bbox_width_px = max(
            float(max(point[0] for point in [left_shoulder, right_shoulder, left_hip, right_hip])
            - min(point[0] for point in [left_shoulder, right_shoulder, left_hip, right_hip])),
            1.0,
        )
        body_bbox_height_px = max(
            float(max(point[1] for point in [left_shoulder, right_shoulder, left_hip, right_hip, left_ankle, right_ankle])
            - min(point[1] for point in [nose, left_shoulder, right_shoulder, left_hip, right_hip])),
            1.0,
        )
        bbox_aspect_ratio = body_bbox_width_px / body_bbox_height_px

        perspective_depth_factor = float(
            np.clip(
                1.0 + max(0.0, 0.72 - ratio_shoulder_to_torso) * 0.35 + max(0.0, 0.40 - bbox_aspect_ratio) * 0.28,
                1.0,
                1.22,
            )
        )

        chest_width_px = ((chest_torso_px * 0.72) + (elbow_proxy_px * 0.28)) * perspective_depth_factor
        waist_width_px = ((waist_torso_px * 0.56) + (hip_width_px * 0.44)) * perspective_depth_factor
        shoulder_width_px = (shoulder_raw_px * shoulder_slope_correction) * perspective_depth_factor

        ankle_center_y = float((left_ankle[1] + right_ankle[1]) / 2.0)
        body_height_px = max(ankle_center_y - nose[1], 1.0)

        if shoulder_width_px <= 1.0 or chest_width_px <= 1.0 or waist_width_px <= 1.0:
            raise LandmarkDetectionError(
                "Detected landmarks are not reliable enough to calculate measurements."
            )

        visibility_values = [
            float(getattr(landmarks[index], "visibility", 1.0))
            for index in [
                self._mp_pose.PoseLandmark.NOSE.value,
                self._mp_pose.PoseLandmark.LEFT_SHOULDER.value,
                self._mp_pose.PoseLandmark.RIGHT_SHOULDER.value,
                self._mp_pose.PoseLandmark.LEFT_HIP.value,
                self._mp_pose.PoseLandmark.RIGHT_HIP.value,
                self._mp_pose.PoseLandmark.LEFT_ANKLE.value,
                self._mp_pose.PoseLandmark.RIGHT_ANKLE.value,
            ]
        ]
        visibility_score = float(np.clip(np.mean(visibility_values) * 100.0, 0.0, 100.0))

        shoulder_level_penalty = min(abs(float(left_shoulder[1] - right_shoulder[1])) / body_height_px * 210.0, 35.0)
        hip_level_penalty = min(abs(float(left_hip[1] - right_hip[1])) / body_height_px * 190.0, 30.0)
        symmetry_score = float(np.clip(100.0 - shoulder_level_penalty - hip_level_penalty, 0.0, 100.0))

        torso_tilt = abs(float(shoulder_center[0] - hip_center[0])) / max(torso_height_px, 1.0)
        posture_score = float(np.clip(100.0 - (torso_tilt * 220.0), 0.0, 100.0))

        measurement_consistency = float(
            np.clip(
                100.0 - abs((chest_width_px - shoulder_width_px) / max(chest_width_px, 1.0)) * 100.0,
                0.0,
                100.0,
            )
        )

        full_body_score = float(np.clip(((ankle_center_y - nose[1]) / max(float(image_height), 1.0)) * 100.0, 0.0, 100.0))
        tilt_degrees = float(
            np.degrees(
                np.arctan2(
                    abs(float(shoulder_center[0] - hip_center[0])),
                    max(abs(float(shoulder_center[1] - hip_center[1])), 1.0),
                )
            )
        )
        resolution_score = float(np.clip((min(image_height, image_width) / 1080.0) * 100.0, 0.0, 100.0))
        pose_quality_score = float(
            np.clip(
                (visibility_score * 0.32)
                + (symmetry_score * 0.23)
                + (posture_score * 0.20)
                + (full_body_score * 0.15)
                + (resolution_score * 0.10),
                0.0,
                100.0,
            )
        )

        if full_body_score < 58.0:
            raise LandmarkDetectionError(
                "Full body not visible. Keep head-to-ankles in frame for accurate sizing."
            )

        if tilt_degrees > 20.0:
            raise LandmarkDetectionError(
                "Body tilt is too high. Stand straight and face camera for accurate sizing."
            )

        if visibility_score < 38.0 or symmetry_score < 32.0:
            raise LandmarkDetectionError(
                "Pose quality is too low for reliable sizing. Stand straight facing the camera with full body visible."
            )

        if normalized_view == "side" and body_bbox_width_px < 16.0:
            raise LandmarkDetectionError(
                "Side profile could not be measured. Turn 90 degrees and keep full body in frame."
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
            pose_quality={
                "overall_score": round(pose_quality_score, 2),
                "visibility_score": round(visibility_score, 2),
                "symmetry_score": round(symmetry_score, 2),
                "posture_score": round(posture_score, 2),
                "measurement_consistency": round(measurement_consistency, 2),
                "full_body_score": round(full_body_score, 2),
                "tilt_degrees": round(tilt_degrees, 2),
                "resolution_score": round(resolution_score, 2),
            },
            measurement_debug={
                "shoulder_raw_px": round(shoulder_raw_px, 2),
                "shoulder_slope_correction": round(shoulder_slope_correction, 4),
                "chest_torso_px": round(chest_torso_px, 2),
                "elbow_proxy_px": round(elbow_proxy_px, 2),
                "waist_torso_px": round(waist_torso_px, 2),
                "hip_width_px": round(hip_width_px, 2),
                "depth_factor": round(perspective_depth_factor, 4),
                "bbox_aspect_ratio": round(bbox_aspect_ratio, 4),
                "shoulder_to_torso_ratio": round(ratio_shoulder_to_torso, 4),
                "hip_to_shoulder_ratio": round(hip_width_px / max(shoulder_raw_px, 1.0), 4),
                "perspective_factor": round(perspective_depth_factor, 4),
            },
            view=normalized_view,
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
    def _optional_point(
        landmarks: list,
        landmark_index: int,
        image_width: int,
        image_height: int,
        min_visibility: float = 0.2,
    ) -> Optional[np.ndarray]:
        landmark = landmarks[landmark_index]
        visibility = getattr(landmark, "visibility", 1.0)
        if visibility < min_visibility:
            return None
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


@lru_cache(maxsize=1)
def get_image_processing_service() -> ImageProcessingService:
    return ImageProcessingService()
