import base64
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from utils.exceptions import TryOnGenerationError
from utils.logger import get_logger

logger = get_logger(__name__)


class VirtualTryOnService:
    """Create a lightweight virtual try-on output aligned to shoulder and hip points."""

    def __init__(self, assets_dir: Path) -> None:
        self.assets_dir = assets_dir
        self.template = self._load_template()

    def _load_template(self) -> Optional[np.ndarray]:
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        candidate_files = [
            self.assets_dir / "shirt.png",
            self.assets_dir / "default_shirt.png",
            self.assets_dir / "tee.png",
        ]

        for file_path in candidate_files:
            if not file_path.exists():
                continue

            template = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)
            if template is not None:
                logger.info("Loaded virtual try-on template: %s", file_path)
                return template

        logger.info("No clothing template found. Using procedural overlay.")
        return None

    def generate_tryon(self, image_bgr: np.ndarray, torso_points: Dict[str, Tuple[int, int]]) -> str:
        outputs = self.generate_tryon_outputs(
            image_bgr=image_bgr,
            torso_points=torso_points,
            include_comparison=False,
        )
        return str(outputs["tryon_image"])

    def generate_tryon_outputs(
        self,
        image_bgr: np.ndarray,
        torso_points: Dict[str, Tuple[int, int]],
        include_comparison: bool = True,
    ) -> Dict[str, Any]:
        self._validate_torso_points(torso_points)

        try:
            if self.template is not None:
                rendered_image = self._overlay_template(image_bgr, torso_points)
            else:
                rendered_image = self._draw_procedural_shirt(image_bgr, torso_points)

            overlay_data_url = self._encode_data_url(rendered_image)
            response: Dict[str, Any] = {
                "tryon_image": overlay_data_url,
                "tryon_comparison": None,
            }

            if include_comparison:
                original_data_url = self._encode_data_url(image_bgr)
                side_by_side = self._build_side_by_side(image_bgr, rendered_image)
                side_by_side_data_url = self._encode_data_url(side_by_side)

                response["tryon_comparison"] = {
                    "original_image": original_data_url,
                    "overlay_image": overlay_data_url,
                    "side_by_side_image": side_by_side_data_url,
                    "before_image": original_data_url,
                    "after_image": overlay_data_url,
                }

            return response
        except TryOnGenerationError:
            raise
        except Exception as exc:
            logger.exception("Virtual try-on generation failed: %s", exc)
            raise TryOnGenerationError()

    def _encode_data_url(self, image_bgr: np.ndarray) -> str:
        is_encoded, encoded_image = cv2.imencode(
            ".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        )
        if not is_encoded:
            raise TryOnGenerationError("Could not encode generated try-on image.")

        encoded_base64 = base64.b64encode(encoded_image.tobytes()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded_base64}"

    @staticmethod
    def _build_side_by_side(original_bgr: np.ndarray, overlay_bgr: np.ndarray) -> np.ndarray:
        target_height = min(original_bgr.shape[0], overlay_bgr.shape[0])

        resized_original = VirtualTryOnService._resize_to_height(original_bgr, target_height)
        resized_overlay = VirtualTryOnService._resize_to_height(overlay_bgr, target_height)

        divider = np.full((target_height, 8, 3), 235, dtype=np.uint8)
        return np.concatenate([resized_original, divider, resized_overlay], axis=1)

    @staticmethod
    def _resize_to_height(image_bgr: np.ndarray, target_height: int) -> np.ndarray:
        if image_bgr.shape[0] == target_height:
            return image_bgr

        scale = target_height / max(image_bgr.shape[0], 1)
        target_width = max(1, int(image_bgr.shape[1] * scale))
        return cv2.resize(image_bgr, (target_width, target_height), interpolation=cv2.INTER_LINEAR)

    def _overlay_template(
        self, image_bgr: np.ndarray, torso_points: Dict[str, Tuple[int, int]]
    ) -> np.ndarray:
        rendered = image_bgr.copy().astype(np.float32)
        image_height, image_width = rendered.shape[:2]

        destination_quad = self._expanded_torso_quad(torso_points)
        template = self.template
        if template is None:
            return image_bgr

        if template.ndim == 2:
            template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGRA)
        elif template.shape[2] == 3:
            alpha = np.full((template.shape[0], template.shape[1], 1), 255, dtype=np.uint8)
            template = np.concatenate([template, alpha], axis=2)

        template_height, template_width = template.shape[:2]
        source_quad = np.array(
            [
                [0, 0],
                [template_width - 1, 0],
                [template_width - 1, template_height - 1],
                [0, template_height - 1],
            ],
            dtype=np.float32,
        )

        transform_matrix = cv2.getPerspectiveTransform(source_quad, destination_quad)
        warped = cv2.warpPerspective(
            template,
            transform_matrix,
            (image_width, image_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0),
        )

        overlay_rgb = warped[:, :, :3].astype(np.float32)
        alpha_mask = (warped[:, :, 3:4].astype(np.float32) / 255.0) * 0.9

        composed = (overlay_rgb * alpha_mask) + (rendered * (1.0 - alpha_mask))
        return composed.astype(np.uint8)

    def _draw_procedural_shirt(
        self, image_bgr: np.ndarray, torso_points: Dict[str, Tuple[int, int]]
    ) -> np.ndarray:
        rendered = image_bgr.copy()
        overlay = rendered.copy()

        torso_quad = self._expanded_torso_quad(torso_points).astype(np.int32)

        cv2.fillConvexPoly(overlay, torso_quad, color=(190, 90, 40))
        cv2.addWeighted(overlay, 0.45, rendered, 0.55, 0, rendered)

        left_shoulder = np.array(torso_points["left_shoulder"], dtype=np.float32)
        right_shoulder = np.array(torso_points["right_shoulder"], dtype=np.float32)
        neck_center = ((left_shoulder + right_shoulder) / 2.0).astype(np.int32)
        neck_radius = max(int(np.linalg.norm(right_shoulder - left_shoulder) * 0.12), 8)

        cv2.circle(rendered, tuple(neck_center), neck_radius, color=(225, 225, 225), thickness=-1)
        cv2.circle(rendered, tuple(neck_center), neck_radius, color=(120, 120, 120), thickness=1)

        return rendered

    @staticmethod
    def _expanded_torso_quad(torso_points: Dict[str, Tuple[int, int]]) -> np.ndarray:
        left_shoulder = np.array(torso_points["left_shoulder"], dtype=np.float32)
        right_shoulder = np.array(torso_points["right_shoulder"], dtype=np.float32)
        left_hip = np.array(torso_points["left_hip"], dtype=np.float32)
        right_hip = np.array(torso_points["right_hip"], dtype=np.float32)

        shoulder_width = max(np.linalg.norm(right_shoulder - left_shoulder), 1.0)
        torso_height = max(
            np.linalg.norm(((left_hip + right_hip) / 2.0) - ((left_shoulder + right_shoulder) / 2.0)),
            1.0,
        )

        expand_x = shoulder_width * 0.18
        expand_top = torso_height * 0.08
        expand_bottom = torso_height * 0.10

        quad = np.array(
            [
                [left_shoulder[0] - expand_x, left_shoulder[1] - expand_top],
                [right_shoulder[0] + expand_x, right_shoulder[1] - expand_top],
                [right_hip[0] + expand_x * 0.7, right_hip[1] + expand_bottom],
                [left_hip[0] - expand_x * 0.7, left_hip[1] + expand_bottom],
            ],
            dtype=np.float32,
        )

        return quad

    @staticmethod
    def _validate_torso_points(torso_points: Dict[str, Tuple[int, int]]) -> None:
        required = {"left_shoulder", "right_shoulder", "left_hip", "right_hip"}
        missing = required.difference(torso_points.keys())
        if missing:
            missing_points = ", ".join(sorted(missing))
            raise TryOnGenerationError(
                f"Missing torso landmarks for virtual try-on: {missing_points}."
            )
