from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from models.schemas import OptimizeImageResponse
from services.image_optimizer import ImageOptimizerService

router = APIRouter(tags=["Performance"])
optimizer = ImageOptimizerService()


@router.post(
    "/optimize-image",
    response_model=OptimizeImageResponse,
    summary="Optimize image payload for mobile-first performance",
)
async def optimize_image(
    image: UploadFile = File(..., description="Input image to optimize"),
    max_side: int = Form(default=1400, ge=640, le=2200),
    jpeg_quality: int = Form(default=82, ge=45, le=95),
) -> OptimizeImageResponse:
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

    return OptimizeImageResponse(
        **optimizer.optimize(
            image_bytes=image_bytes,
            max_side=max_side,
            jpeg_quality=jpeg_quality,
        )
    )
