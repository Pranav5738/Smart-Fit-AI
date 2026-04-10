from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

FitPreference = Literal["slim", "regular", "relaxed"]
UnitSystem = Literal["cm", "in"]
LanguageCode = Literal["en", "es"]
RiskLevel = Literal["low", "medium", "high"]
AgeGroup = Literal["child", "teen", "adult"]
GenderCode = Literal["male", "female", "unisex"]


class Measurements(BaseModel):
    chest: float = Field(..., gt=0)
    waist: float = Field(..., gt=0)
    shoulder: float = Field(..., gt=0)


class CaptureQualityReport(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=100.0)
    pose_score: float = Field(..., ge=0.0, le=100.0)
    lighting_score: float = Field(..., ge=0.0, le=100.0)
    framing_score: float = Field(..., ge=0.0, le=100.0)
    sharpness_score: float = Field(..., ge=0.0, le=100.0)
    hints: List[str]


class BrandAdjustmentDetail(BaseModel):
    brand: str
    base_size: str
    mapped_size: str
    category: str
    offset: int
    adjustment_reason: str


class ExplainabilityMeasurement(BaseModel):
    metric: str
    value: float
    unit: UnitSystem
    impact: str


class ExplainabilityPanel(BaseModel):
    size_reasoning: str
    key_measurements: List[ExplainabilityMeasurement]
    confidence_reasoning: List[str]
    brand_adjustment_logic: List[BrandAdjustmentDetail]


class FitAlternatives(BaseModel):
    best_fit: str
    comfort_fit: str
    style_fit: str


class ReturnRiskScore(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0)
    level: RiskLevel
    reasons: List[str]
    alternatives: FitAlternatives


class RecommendationItem(BaseModel):
    sku: str
    product_name: str
    brand: str
    category: str
    recommended_size: str
    occasions: List[str]
    weather: List[str]
    color: str
    reason: str
    image_url: str = ""


class TryOnComparison(BaseModel):
    original_image: str
    overlay_image: str
    side_by_side_image: str
    before_image: str
    after_image: str


class PrivacySummary(BaseModel):
    consent_accepted: bool
    consent_version: str
    image_auto_deleted: bool
    data_retention: str


class AnalyzeImageResponse(BaseModel):
    measurement_unit: UnitSystem
    age_group: AgeGroup = "adult"
    gender: GenderCode = "unisex"
    measurements: Measurements
    measurement_breakdown: Dict[str, Any] | None = None
    fit_preference: FitPreference
    predicted_size: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_components: Dict[str, float] | None = None
    prediction_confidence_level: Literal["high", "medium", "low"] | None = None
    size_range: str | None = None
    prediction_advice: str | None = None
    brand_mapping: Dict[str, str]
    recommendations: List[RecommendationItem]
    capture_quality: CaptureQualityReport
    explainability: ExplainabilityPanel
    return_risk: ReturnRiskScore
    tryon_image: str
    tryon_comparison: Optional[TryOnComparison] = None
    privacy: PrivacySummary
    profile_id: Optional[str] = None
    scan_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "measurement_unit": "cm",
                "measurements": {
                    "chest": 97.4,
                    "waist": 84.1,
                    "shoulder": 44.3,
                },
                "fit_preference": "regular",
                "predicted_size": "M",
                "confidence": 0.91,
                "brand_mapping": {
                    "Nike": "M",
                    "Zara": "L",
                    "H&M": "M",
                    "Adidas": "M",
                    "Uniqlo": "S",
                },
                "recommendations": [
                    {
                        "sku": "NK-TEE-001",
                        "product_name": "Dri-FIT Daily Tee",
                        "brand": "Nike",
                        "category": "tees",
                        "recommended_size": "M",
                        "occasions": ["casual", "gym"],
                        "weather": ["summer", "all-season"],
                        "color": "dark",
                        "reason": "Balanced fit recommendation for everyday tees.",
                        "image_url": "/static/clothing/tee.png",
                    }
                ],
                "capture_quality": {
                    "overall_score": 86.2,
                    "pose_score": 91.0,
                    "lighting_score": 83.7,
                    "framing_score": 84.0,
                    "sharpness_score": 87.5,
                    "hints": ["Great capture quality. Ready for analysis."],
                },
                "explainability": {
                    "size_reasoning": "Size M best matches chest, waist, and shoulder proportions for the selected regular preference.",
                    "key_measurements": [
                        {
                            "metric": "chest",
                            "value": 97.4,
                            "unit": "cm",
                            "impact": "Primary upper-body fit anchor.",
                        }
                    ],
                    "confidence_reasoning": [
                        "Model confidence score is 91.0% based on learned size boundaries."
                    ],
                    "brand_adjustment_logic": [
                        {
                            "brand": "Zara",
                            "base_size": "M",
                            "mapped_size": "L",
                            "category": "tees",
                            "offset": 1,
                            "adjustment_reason": "Brand tends smaller for this category or preference, mapped one step up.",
                        }
                    ],
                },
                "return_risk": {
                    "score": 24.8,
                    "level": "low",
                    "reasons": [
                        "High confidence and stable brand mapping indicate low return probability."
                    ],
                    "alternatives": {
                        "best_fit": "M",
                        "comfort_fit": "L",
                        "style_fit": "M",
                    },
                },
                "tryon_image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...",
                "tryon_comparison": {
                    "original_image": "data:image/jpeg;base64,/9j/...",
                    "overlay_image": "data:image/jpeg;base64,/9j/...",
                    "side_by_side_image": "data:image/jpeg;base64,/9j/...",
                    "before_image": "data:image/jpeg;base64,/9j/...",
                    "after_image": "data:image/jpeg;base64,/9j/...",
                },
                "privacy": {
                    "consent_accepted": True,
                    "consent_version": "v1",
                    "image_auto_deleted": True,
                    "data_retention": "Uploaded image bytes are processed in-memory and not persisted.",
                },
                "profile_id": "profile_81dc36b8f8ad",
                "scan_id": "scan_2ff9407b32989b",
            }
        }
    )


class QualityCheckResponse(BaseModel):
    capture_quality: CaptureQualityReport
    guidance: List[str]


class OptimizeImageResponse(BaseModel):
    optimized_image: str
    original_size_bytes: int
    optimized_size_bytes: int
    compression_ratio: float
    width: int
    height: int


class ProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


class ProfileSummary(BaseModel):
    id: str
    name: str
    created_at: str
    scan_count: int
    last_scan_at: Optional[str] = None


class ScanHistoryItem(BaseModel):
    scan_id: str
    profile_id: str
    analyzed_at: str
    fit_preference: FitPreference
    measurement_unit: UnitSystem
    predicted_size: str
    confidence: float
    measurements: Dict[str, Any]
    brand_mapping: Dict[str, str]
    recommendations: List[Dict[str, Any]]
    explainability: Dict[str, Any]
    return_risk: Dict[str, Any]
    capture_quality: Dict[str, Any]
    privacy: Dict[str, Any]


class MeasurementTrendPoint(BaseModel):
    analyzed_at: str
    chest: Optional[float] = None
    waist: Optional[float] = None
    shoulder: Optional[float] = None


class MeasurementTrendResponse(BaseModel):
    profile_id: str
    points: List[MeasurementTrendPoint]
    deltas: Dict[str, float]


class ProfileExportResponse(BaseModel):
    profile: ProfileSummary
    history: List[ScanHistoryItem]
    trends: MeasurementTrendResponse


class OperationStatusResponse(BaseModel):
    status: str
    profile_id: Optional[str] = None
    scan_id: Optional[str] = None
    message: Optional[str] = None


class FitCardResponse(BaseModel):
    image_data_url: str


class CatalogProductResponse(BaseModel):
    sku: str
    brand: str
    product_name: str
    category: str
    occasions: List[str]
    weather: List[str]
    color: str
    image_name: str


class PrivacyPolicyResponse(BaseModel):
    consent_version: str
    image_processing_policy: str
    data_controls: List[str]


class ErrorResponse(BaseModel):
    error_code: str
    message: str
