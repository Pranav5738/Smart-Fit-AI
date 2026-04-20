import axios, { AxiosError } from 'axios';
import {
  AgeGroup,
  AnalyzeResponse,
  CaptureQualityReport,
  FitPreference,
  GenderCode,
  LanguageCode,
  RecommendationItem,
  UnitSystem,
  UserProfile,
} from '@/types/smartfit';

const resolveApiBaseUrl = (): string => {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configured) {
    return configured;
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname.toLowerCase();
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8000';
    }
  }

  return 'https://smart-fit-ai.onrender.com';
};

const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 30000,
});

const POSE_GUIDANCE_ERROR =
  'Pose was detected, but sizing landmarks are unclear. Retake with full body visible (head to ankles), face the camera, keep arms slightly away from torso, and use bright front lighting.';

let activeAccessToken: string | null = null;

export const configureAccessToken = (accessToken: string | null) => {
  activeAccessToken = accessToken?.trim() || null;

  if (activeAccessToken) {
    api.defaults.headers.common.Authorization = `Bearer ${activeAccessToken}`;
    return;
  }

  delete api.defaults.headers.common.Authorization;
};

export const getConfiguredAccessToken = (): string | null => activeAccessToken;

interface AnalyzeImageOptions {
  fitPreference?: FitPreference;
  userHeightCm?: number;
  ageGroup?: AgeGroup;
  gender?: GenderCode;
  preferredBrands?: string[];
  profileId?: string;
  saveToHistory?: boolean;
  consentAccepted?: boolean;
  unitSystem?: UnitSystem;
  language?: LanguageCode;
  includeTryonComparison?: boolean;
  productCategories?: string[];
  occasions?: string[];
  weather?: string[];
  colorPreferences?: string[];
}

interface BackendQualityCheckResponse {
  capture_quality: {
    overall_score: number;
    pose_score: number;
    lighting_score: number;
    framing_score: number;
    sharpness_score: number;
    hints: string[];
  };
  guidance: string[];
}

interface BackendProfileSummary {
  id: string;
  name: string;
  created_at: string;
  scan_count: number;
  last_scan_at?: string;
}

interface BackendAuthUser {
  id: string;
  name: string;
  email: string;
  height_cm?: number;
  weight_kg?: number;
  created_at: string;
  last_login_at?: string;
}

interface BackendAuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  access_expires_at: string;
  refresh_expires_at: string;
}

interface BackendAuthSession {
  user: BackendAuthUser;
  tokens: BackendAuthTokens;
}

interface RegisterAuthPayload {
  name: string;
  email: string;
  password: string;
  heightCm?: number;
  weightKg?: number;
}

export interface AuthUserRecord {
  id: string;
  name: string;
  email: string;
  heightCm?: number;
  weightKg?: number;
  createdAt: string;
  lastLoginAt?: string;
}

export interface AuthTokenRecord {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  accessExpiresAt: string;
  refreshExpiresAt: string;
}

export interface AuthSessionRecord {
  user: AuthUserRecord;
  tokens: AuthTokenRecord;
}

const normalizeApiError = (error: unknown): string => {
  if (error instanceof AxiosError) {
    const responsePayload = error.response?.data as
      | {
          message?: string;
          detail?: string | Array<{ msg?: string }>;
          error_code?: string;
        }
      | undefined;

    const errorCode = String(responsePayload?.error_code || '').toUpperCase();

    if (errorCode === 'LANDMARK_DETECTION_ERROR') {
      return POSE_GUIDANCE_ERROR;
    }

    const detailMessage =
      typeof responsePayload?.detail === 'string'
        ? responsePayload.detail
        : Array.isArray(responsePayload?.detail)
          ? responsePayload.detail.map((item) => item?.msg).filter(Boolean).join(', ')
          : '';

    const responseMessage = responsePayload?.message || detailMessage || error.message;

    if (/landmark|pose detected|full-body|full body/i.test(responseMessage)) {
      return POSE_GUIDANCE_ERROR;
    }

    return responseMessage || 'Unable to analyze the image right now. Please try again.';
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'Unexpected error while processing your request.';
};

const toCsv = (values?: string[]): string | undefined => {
  const cleaned = (values || []).map((value) => value.trim()).filter(Boolean);
  return cleaned.length > 0 ? cleaned.join(',') : undefined;
};

const normalizeRecommendation = (item: string | RecommendationItem, index: number): RecommendationItem => {
  if (typeof item === 'string') {
    return { name: item };
  }

  const name = item.name || item.product_name || `Outfit ${index + 1}`;
  return {
    ...item,
    name,
    description: item.description || item.reason,
  };
};

const normalizeAnalyzeResponse = (payload: AnalyzeResponse): AnalyzeResponse => {
  return {
    ...payload,
    recommendations: (payload.recommendations || []).map((item, index) =>
      normalizeRecommendation(item, index)
    ),
  };
};

const mapBackendProfileToUserProfile = (profile: BackendProfileSummary): UserProfile => {
  return {
    id: profile.id,
    name: profile.name,
    createdAt: profile.created_at,
    scans: [],
  };
};

const mapBackendAuthUser = (user: BackendAuthUser): AuthUserRecord => {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    heightCm: user.height_cm,
    weightKg: user.weight_kg,
    createdAt: user.created_at,
    lastLoginAt: user.last_login_at,
  };
};

const mapBackendAuthTokens = (tokens: BackendAuthTokens): AuthTokenRecord => {
  return {
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    tokenType: tokens.token_type || 'bearer',
    accessExpiresAt: tokens.access_expires_at,
    refreshExpiresAt: tokens.refresh_expires_at,
  };
};

const mapBackendAuthSession = (payload: BackendAuthSession): AuthSessionRecord => {
  return {
    user: mapBackendAuthUser(payload.user),
    tokens: mapBackendAuthTokens(payload.tokens),
  };
};

const mapQualityResponse = (payload: BackendQualityCheckResponse): CaptureQualityReport => {
  return {
    overallScore: payload.capture_quality.overall_score,
    poseScore: payload.capture_quality.pose_score,
    lightingScore: payload.capture_quality.lighting_score,
    framingScore: payload.capture_quality.framing_score,
    sharpnessScore: payload.capture_quality.sharpness_score,
    hints: payload.capture_quality.hints || payload.guidance || [],
  };
};

export const analyzeImage = async (
  frontImageFile: File,
  sideImageFile: File,
  options?: AnalyzeImageOptions
): Promise<AnalyzeResponse> => {
  const formData = new FormData();
  formData.append('front_image', frontImageFile);
  formData.append('side_image', sideImageFile);

  formData.append('fit_preference', options?.fitPreference || 'regular');
  formData.append('age_group', options?.ageGroup || 'adult');
  formData.append('gender', options?.gender || 'unisex');
  formData.append('unit_system', options?.unitSystem || 'in');
  formData.append('language', options?.language || 'en');
  formData.append(
    'include_tryon_comparison',
    String(options?.includeTryonComparison ?? true)
  );
  formData.append('consent_accepted', String(options?.consentAccepted ?? true));

  if (typeof options?.userHeightCm === 'number') {
    formData.append('user_height_cm', String(options.userHeightCm));
  }

  const categories = toCsv(options?.productCategories);
  if (categories) {
    formData.append('product_categories', categories);
  }

  const preferredBrands = toCsv(options?.preferredBrands);
  if (preferredBrands) {
    formData.append('preferred_brands', preferredBrands);
  }

  const occasions = toCsv(options?.occasions);
  if (occasions) {
    formData.append('occasions', occasions);
  }

  const weather = toCsv(options?.weather);
  if (weather) {
    formData.append('weather', weather);
  }

  const colors = toCsv(options?.colorPreferences);
  if (colors) {
    formData.append('color_preferences', colors);
  }

  if (options?.profileId) {
    formData.append('profile_id', options.profileId);
    formData.append('save_to_history', String(options.saveToHistory ?? true));
  }

  try {
    const { data } = await api.post<AnalyzeResponse>('/analyze-image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return normalizeAnalyzeResponse(data);
  } catch (error) {
    throw new Error(normalizeApiError(error));
  }
};

export const qualityCheck = async (
  imageFile: File,
  language: LanguageCode = 'en'
): Promise<CaptureQualityReport> => {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('language', language);

  try {
    const { data } = await api.post<BackendQualityCheckResponse>('/quality-check', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return mapQualityResponse(data);
  } catch (error) {
    throw new Error(normalizeApiError(error));
  }
};

export const listProfiles = async (): Promise<UserProfile[]> => {
  try {
    const { data } = await api.get<BackendProfileSummary[]>('/profiles/');
    return data.map(mapBackendProfileToUserProfile);
  } catch (error) {
    throw new Error(normalizeApiError(error));
  }
};

export const createProfile = async (name: string): Promise<UserProfile> => {
  try {
    const { data } = await api.post<BackendProfileSummary>('/profiles/', { name });
    return mapBackendProfileToUserProfile(data);
  } catch (error) {
    throw new Error(normalizeApiError(error));
  }
};

export const updateProfile = async (profileId: string, name: string): Promise<UserProfile> => {
  try {
    const { data } = await api.put<BackendProfileSummary>(`/profiles/${profileId}`, { name });
    return mapBackendProfileToUserProfile(data);
  } catch (error) {
    throw new Error(normalizeApiError(error));
  }
};

export const deleteProfile = async (profileId: string): Promise<void> => {
  try {
    await api.delete(`/profiles/${profileId}`);
  } catch (error) {
    throw new Error(normalizeApiError(error));
  }
};

export const registerAuthUser = async (payload: RegisterAuthPayload): Promise<AuthSessionRecord> => {
  try {
    const { data } = await api.post<BackendAuthSession>('/auth/register', {
      name: payload.name,
      email: payload.email,
      password: payload.password,
      height_cm: payload.heightCm,
      weight_kg: payload.weightKg,
    });

    return mapBackendAuthSession(data);
  } catch (error) {
    throw new Error(normalizeApiError(error));
  }
};

export const signInAuthUser = async (email: string, password: string): Promise<AuthSessionRecord> => {
  try {
    const { data } = await api.post<BackendAuthSession>('/auth/signin', {
      email,
      password,
    });

    return mapBackendAuthSession(data);
  } catch (error) {
    throw new Error(normalizeApiError(error));
  }
};

export const refreshAuthSession = async (refreshToken: string): Promise<AuthSessionRecord> => {
  try {
    const { data } = await api.post<BackendAuthSession>('/auth/refresh', {
      refresh_token: refreshToken,
    });

    return mapBackendAuthSession(data);
  } catch (error) {
    throw new Error(normalizeApiError(error));
  }
};

export const fetchAuthMe = async (accessToken: string): Promise<AuthUserRecord> => {
  try {
    const { data } = await api.get<BackendAuthUser>('/auth/me', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    return mapBackendAuthUser(data);
  } catch (error) {
    throw new Error(normalizeApiError(error));
  }
};

export const signOutAuthSession = async (refreshToken: string): Promise<void> => {
  try {
    await api.post('/auth/signout', {
      refresh_token: refreshToken,
    });
  } catch (error) {
    throw new Error(normalizeApiError(error));
  }
};
