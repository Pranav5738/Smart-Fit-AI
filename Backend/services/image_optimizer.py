from __future__ import annotations

import base64
from typing import Any

import cv2
import numpy as np

from utils.exceptions import SmartFitError


class ImageOptimizerService:
    """Optimize images for faster mobile upload and processing."""

    def optimize(
        self,
        image_bytes: bytes,
        max_side: int = 1400,
        jpeg_quality: int = 82,
    ) -> dict[str, Any]:
        np_image = np.frombuffer(image_bytes, dtype=np.uint8)
        image_bgr = cv2.imdecode(np_image, cv2.IMREAD_COLOR)

        if image_bgr is None:
            raise SmartFitError(
                message="Invalid image input for optimization.",
                error_code="IMAGE_OPTIMIZATION_FAILED",
            )

        height, width = image_bgr.shape[:2]
        longest_side = max(height, width)
        scale = min(1.0, max_side / max(longest_side, 1))

        if scale < 1.0:
            resized = cv2.resize(
                image_bgr,
                (max(1, int(width * scale)), max(1, int(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        else:
            resized = image_bgr

        encode_quality = min(max(jpeg_quality, 45), 95)
        is_encoded, encoded = cv2.imencode(
            ".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), encode_quality]
        )
        if not is_encoded:
            raise SmartFitError(
                message="Failed to encode optimized image.",
                error_code="IMAGE_OPTIMIZATION_FAILED",
            )

        optimized_bytes = encoded.tobytes()
        encoded_base64 = base64.b64encode(optimized_bytes).decode("utf-8")

        compression_ratio = len(optimized_bytes) / max(len(image_bytes), 1)
        optimized_height, optimized_width = resized.shape[:2]

        return {
            "optimized_image": f"data:image/jpeg;base64,{encoded_base64}",
            "original_size_bytes": len(image_bytes),
            "optimized_size_bytes": len(optimized_bytes),
            "compression_ratio": round(compression_ratio, 4),
            "width": optimized_width,
            "height": optimized_height,
        }
