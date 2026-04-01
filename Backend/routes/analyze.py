from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from models.schemas import AnalyzeImageResponse, FitPreference, LanguageCode, UnitSystem
from services.pipeline import SmartFitPipeline
from services.profile_store import ProfileStoreService
from utils.config import get_settings
from utils.exceptions import SmartFitError
from utils.logger import get_logger

router = APIRouter(tags=["SmartFit"])
logger = get_logger(__name__)
settings = get_settings()
pipeline = SmartFitPipeline()
profile_store = ProfileStoreService(db_path=settings.data_store_path)


def _parse_csv_field(raw_value: Optional[str]) -> list[str]:
    if not raw_value:
        return []
    return [value.strip().lower() for value in raw_value.split(",") if value.strip()]


@router.post(
    "/analyze-image",
    response_model=AnalyzeImageResponse,
    summary="Analyze image and predict clothing size",
)
async def analyze_image(
    image: UploadFile = File(..., description="Input body image"),
    user_height_cm: Optional[float] = Form(
        default=None,
        gt=80,
        lt=280,
        description="Optional user height in centimeters for scaling calibration",
    ),
    fit_preference: FitPreference = Form(
        default="regular",
        description="Fit preference: slim, regular, relaxed",
    ),
    unit_system: UnitSystem = Form(
        default="cm",
        description="Measurement unit for output: cm or in",
    ),
    language: LanguageCode = Form(
        default="en",
        description="Localized hints language: en or es",
    ),
    product_categories: Optional[str] = Form(
        default=None,
        description="Comma-separated catalog categories: tees,jeans,jackets",
    ),
    occasions: Optional[str] = Form(
        default=None,
        description="Comma-separated occasion filters: formal,casual,gym,travel",
    ),
    weather: Optional[str] = Form(
        default=None,
        description="Comma-separated weather filters: summer,winter,all-season",
    ),
    color_preferences: Optional[str] = Form(
        default=None,
        description="Comma-separated color filters: dark,neutral,bright",
    ),
    profile_id: Optional[str] = Form(
        default=None,
        description="Optional profile ID to persist scan history",
    ),
    save_to_history: bool = Form(
        default=True,
        description="Persist scan to profile history if profile_id is provided",
    ),
    include_tryon_comparison: bool = Form(
        default=True,
        description="Include side-by-side and before/after try-on outputs",
    ),
    consent_accepted: bool = Form(
        ...,
        description="Explicit consent acknowledgement before processing image",
    ),
) -> AnalyzeImageResponse:
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

    if not consent_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before image analysis.",
        )

    try:
        result = pipeline.analyze_image(
            image_bytes=image_bytes,
            user_height_cm=user_height_cm,
            fit_preference=fit_preference,
            unit_system=unit_system,
            language=language,
            categories=_parse_csv_field(product_categories),
            occasions=_parse_csv_field(occasions),
            weather=_parse_csv_field(weather),
            colors=_parse_csv_field(color_preferences),
            include_tryon_comparison=include_tryon_comparison,
        )

        if profile_id:
            result["profile_id"] = profile_id

        if profile_id and save_to_history:
            scan_id = profile_store.save_scan(profile_id=profile_id, analysis_payload=result)
            result["scan_id"] = scan_id

        result["privacy"] = {
            "consent_accepted": True,
            "consent_version": settings.consent_version,
            "image_auto_deleted": settings.auto_delete_uploaded_images,
            "data_retention": "Uploaded image bytes are processed in-memory and automatically discarded after inference.",
        }

        return AnalyzeImageResponse(**result)
    except SmartFitError:
        raise
    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected image analysis failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected server error while analyzing image.",
        )
