from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from models.schemas import LanguageCode, QualityCheckResponse
from services.image_processing import get_image_processing_service
from services.quality_checker import get_capture_quality_service

router = APIRouter(tags=["Quality"])


@router.post(
    "/quality-check",
    response_model=QualityCheckResponse,
    summary="Evaluate capture quality before final analysis",
)
async def quality_check(
    image: UploadFile = File(..., description="Input body image"),
    language: LanguageCode = Form(default="en", description="Localized hint language: en or es"),
) -> QualityCheckResponse:
    if image.content_type is None or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Please upload a valid image.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    image_processing = get_image_processing_service()
    quality_checker = get_capture_quality_service()
    image_bgr = image_processing.decode_image(image_bytes)
    report = quality_checker.assess(image_bgr=image_bgr, language=language)

    return QualityCheckResponse(
        capture_quality=report,
        guidance=report["hints"],
    )
