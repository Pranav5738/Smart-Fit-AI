from fastapi import APIRouter, status

from models.schemas import (
    FitCardResponse,
    MeasurementTrendResponse,
    OperationStatusResponse,
    ProfileCreateRequest,
    ProfileExportResponse,
    ProfileSummary,
    ProfileUpdateRequest,
    ScanHistoryItem,
)
from services.fit_card import FitCardService
from services.profile_store import ProfileStoreService
from utils.config import get_settings

router = APIRouter(prefix="/profiles", tags=["Profiles"])
settings = get_settings()
profile_store = ProfileStoreService(db_path=settings.data_store_path)
fit_card_service = FitCardService()


@router.post("/", response_model=ProfileSummary, status_code=status.HTTP_201_CREATED)
def create_profile(payload: ProfileCreateRequest) -> ProfileSummary:
    profile = profile_store.create_profile(name=payload.name)
    return ProfileSummary(**profile)


@router.get("/", response_model=list[ProfileSummary])
def list_profiles() -> list[ProfileSummary]:
    profiles = profile_store.list_profiles()
    return [ProfileSummary(**profile) for profile in profiles]


@router.get("/{profile_id}", response_model=ProfileSummary)
def get_profile(profile_id: str) -> ProfileSummary:
    return ProfileSummary(**profile_store.get_profile(profile_id))


@router.put("/{profile_id}", response_model=ProfileSummary)
def update_profile(profile_id: str, payload: ProfileUpdateRequest) -> ProfileSummary:
    updated = profile_store.update_profile(profile_id=profile_id, name=payload.name)
    return ProfileSummary(**updated)


@router.get("/{profile_id}/history", response_model=list[ScanHistoryItem])
def get_profile_history(profile_id: str, limit: int = 100) -> list[ScanHistoryItem]:
    history = profile_store.list_history(profile_id=profile_id, limit=limit)
    return [ScanHistoryItem(**record) for record in history]


@router.get("/{profile_id}/trends", response_model=MeasurementTrendResponse)
def get_profile_trends(profile_id: str) -> MeasurementTrendResponse:
    trend_payload = profile_store.trends(profile_id)
    return MeasurementTrendResponse(**trend_payload)


@router.get("/{profile_id}/export", response_model=ProfileExportResponse)
def export_profile_data(profile_id: str) -> ProfileExportResponse:
    payload = profile_store.export_profile(profile_id)
    return ProfileExportResponse(**payload)


@router.delete("/{profile_id}", response_model=OperationStatusResponse)
def delete_profile(profile_id: str) -> OperationStatusResponse:
    profile_store.delete_profile(profile_id)
    return OperationStatusResponse(
        status="deleted",
        profile_id=profile_id,
        message="Profile and all scans were removed.",
    )


@router.delete("/{profile_id}/history/{scan_id}", response_model=OperationStatusResponse)
def delete_profile_scan(profile_id: str, scan_id: str) -> OperationStatusResponse:
    profile_store.delete_scan(profile_id=profile_id, scan_id=scan_id)
    return OperationStatusResponse(
        status="deleted",
        profile_id=profile_id,
        scan_id=scan_id,
        message="Scan removed from history.",
    )


@router.get("/{profile_id}/history/{scan_id}/fit-card", response_model=FitCardResponse)
def get_fit_card(profile_id: str, scan_id: str) -> FitCardResponse:
    profile = profile_store.get_profile(profile_id)
    scan = profile_store.get_scan(profile_id=profile_id, scan_id=scan_id)

    data_url = fit_card_service.render_from_scan(profile_name=profile["name"], scan=scan)
    return FitCardResponse(image_data_url=data_url)
