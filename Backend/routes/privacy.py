from fastapi import APIRouter

from models.schemas import OperationStatusResponse, PrivacyPolicyResponse, ProfileExportResponse
from services.profile_store import ProfileStoreService
from utils.config import get_settings

router = APIRouter(prefix="/privacy", tags=["Privacy"])
settings = get_settings()
profile_store = ProfileStoreService(db_path=settings.data_store_path)


@router.get("/policy", response_model=PrivacyPolicyResponse)
def get_privacy_policy() -> PrivacyPolicyResponse:
    return PrivacyPolicyResponse(
        consent_version=settings.consent_version,
        image_processing_policy="Images are processed in-memory for inference and are not retained by default.",
        data_controls=[
            "POST /analyze-image requires explicit consent_accepted=true",
            "GET /privacy/download-my-data/{profile_id}",
            "DELETE /privacy/delete-my-data/{profile_id}",
        ],
    )


@router.get("/download-my-data/{profile_id}", response_model=ProfileExportResponse)
def download_my_data(profile_id: str) -> ProfileExportResponse:
    payload = profile_store.export_profile(profile_id)
    return ProfileExportResponse(**payload)


@router.delete("/delete-my-data/{profile_id}", response_model=OperationStatusResponse)
def delete_my_data(profile_id: str) -> OperationStatusResponse:
    profile_store.delete_profile(profile_id)
    return OperationStatusResponse(
        status="deleted",
        profile_id=profile_id,
        message="All user profile data has been deleted.",
    )
