export type MeasurementValue = number | string;

export type FitPreference = 'slim' | 'regular' | 'relaxed';
export type UnitSystem = 'in' | 'cm';
export type LanguageCode = 'en' | 'es';
export type ReturnRiskLevel = 'low' | 'medium' | 'high';
export type AgeGroup = 'child' | 'teen' | 'adult';
export type GenderCode = 'male' | 'female' | 'unisex';

export interface RecommendationItem {
  name: string;
  sku?: string;
  product_name?: string;
  brand?: string;
  recommended_size?: string;
  description?: string;
  reason?: string;
  image_url?: string;
  category?: string;
  occasions?: string[];
  occasion?: 'casual' | 'formal' | 'gym' | 'travel';
  weather?: string[];
  color?: string;
}

export interface TryOnComparison {
  original_image: string;
  overlay_image: string;
  side_by_side_image: string;
  before_image: string;
  after_image: string;
}

export interface PrivacySummary {
  consent_accepted: boolean;
  consent_version: string;
  image_auto_deleted: boolean;
  data_retention: string;
}

export interface ExplainabilityPanel {
  size_reasoning: string;
  key_measurements: Array<{
    metric: string;
    value: number;
    unit: UnitSystem;
    impact: string;
  }>;
  confidence_reasoning: string[];
  brand_adjustment_logic: Array<{
    brand: string;
    base_size: string;
    mapped_size: string;
    category: string;
    offset: number;
    adjustment_reason: string;
  }>;
}

export interface BackendReturnRiskScore {
  score: number;
  level: ReturnRiskLevel;
  reasons: string[];
  alternatives: {
    best_fit: string;
    comfort_fit: string;
    style_fit: string;
  };
}

export interface AnalyzeResponse {
  measurement_unit?: UnitSystem;
  age_group?: AgeGroup;
  gender?: GenderCode;
  measurements: Record<string, MeasurementValue>;
  measurement_breakdown?: {
    height_cm_used?: number;
    pixel_debug?: Record<string, number>;
  };
  fit_preference?: FitPreference;
  predicted_size: string;
  confidence: number;
  confidence_components?: Record<string, number>;
  prediction_confidence_level?: 'high' | 'medium' | 'low';
  size_range?: string;
  prediction_advice?: string;
  brand_mapping: Record<string, string>;
  recommendations: Array<string | RecommendationItem>;
  capture_quality?: {
    overall_score: number;
    pose_score: number;
    lighting_score: number;
    framing_score: number;
    sharpness_score: number;
    hints: string[];
  };
  explainability?: ExplainabilityPanel;
  return_risk?: BackendReturnRiskScore;
  tryon_image?: string;
  tryon_comparison?: TryOnComparison;
  privacy?: PrivacySummary;
  profile_id?: string;
  scan_id?: string;
}

export interface CaptureQualityReport {
  overallScore: number;
  lightingScore: number;
  framingScore: number;
  poseScore: number;
  sharpnessScore: number;
  hints: string[];
}

export interface FitAlternatives {
  bestFit: string;
  comfortFit: string;
  styleFit: string;
}

export interface ReturnRiskScore {
  score: number;
  level: ReturnRiskLevel;
  reasons: string[];
  alternatives: FitAlternatives;
}

export interface CatalogItem {
  id: string;
  name: string;
  brand: string;
  category: 'tees' | 'jeans' | 'jackets' | 'athleisure';
  sizes: string[];
  occasion: Array<'casual' | 'formal' | 'gym' | 'travel'>;
  weather: Array<'summer' | 'winter' | 'all-season'>;
  color: 'neutral' | 'dark' | 'bright';
}

export interface SavedScan {
  id: string;
  backendScanId?: string;
  analyzedAt: string;
  source: 'upload' | 'webcam';
  fitPreference: FitPreference;
  measurementUnit?: UnitSystem;
  measurements: Record<string, MeasurementValue>;
  predictedSize: string;
  confidence: number;
  brandMapping: Record<string, string>;
  returnRiskLevel: ReturnRiskLevel;
}

export interface UserProfile {
  id: string;
  name: string;
  createdAt: string;
  scans: SavedScan[];
}

export interface UploadAnalysisState {
  analysisId: string;
  result: AnalyzeResponse;
  uploadedPreview?: string;
  source: 'upload' | 'webcam';
  analyzedAt: string;
  fitPreference: FitPreference;
  qualityReport?: CaptureQualityReport;
  profileId: string;
  selectedBrands: string[];
}
