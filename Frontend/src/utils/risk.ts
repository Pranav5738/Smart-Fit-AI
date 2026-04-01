import type {
  AnalyzeResponse,
  CaptureQualityReport,
  FitAlternatives,
  FitPreference,
  ReturnRiskScore,
} from '@/types/smartfit';
import { confidenceToPercent } from '@/utils/format';

const SIZE_SCALE = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL'];

const normalizeSize = (size: string): string => {
  return size.toUpperCase().replace(/\s+/g, '');
};

const shiftSize = (size: string, step: number): string => {
  const normalized = normalizeSize(size);
  const index = SIZE_SCALE.indexOf(normalized);

  if (index === -1) {
    return size;
  }

  const targetIndex = Math.max(0, Math.min(SIZE_SCALE.length - 1, index + step));
  return SIZE_SCALE[targetIndex];
};

export const deriveFitAlternatives = (
  baseSize: string,
  fitPreference: FitPreference
): FitAlternatives => {
  const styleShift = fitPreference === 'slim' ? -1 : fitPreference === 'relaxed' ? 1 : 0;

  return {
    bestFit: baseSize,
    comfortFit: shiftSize(baseSize, 1),
    styleFit: shiftSize(baseSize, styleShift),
  };
};

const calculateBrandVariancePenalty = (brandMapping: Record<string, string>): number => {
  const normalized = Object.values(brandMapping)
    .map((size) => normalizeSize(size))
    .filter((size) => size.length > 0 && size !== '-');

  const uniqueCount = new Set(normalized).size;

  if (uniqueCount <= 1) {
    return 2;
  }

  if (uniqueCount === 2) {
    return 10;
  }

  return 18;
};

export const calculateReturnRisk = (
  response: AnalyzeResponse,
  fitPreference: FitPreference,
  qualityReport?: CaptureQualityReport
): ReturnRiskScore => {
  const confidence = confidenceToPercent(response.confidence);
  const qualityScore = qualityReport?.overallScore ?? 78;

  const lowConfidencePenalty = Math.max(0, 100 - confidence) * 0.55;
  const qualityPenalty = Math.max(0, 80 - qualityScore) * 0.6;
  const brandPenalty = calculateBrandVariancePenalty(response.brand_mapping || {});
  const fitPenalty = fitPreference === 'slim' ? 9 : fitPreference === 'relaxed' ? 6 : 4;

  const score = Math.round(Math.min(100, lowConfidencePenalty + qualityPenalty + brandPenalty + fitPenalty));

  let level: ReturnRiskScore['level'] = 'low';
  if (score >= 60) {
    level = 'high';
  } else if (score >= 34) {
    level = 'medium';
  }

  const reasons: string[] = [];

  if (confidence < 78) {
    reasons.push('Confidence is moderate, so fit variance may increase across garments.');
  }

  if (qualityScore < 70) {
    reasons.push('Capture quality can be improved with better framing and lighting.');
  }

  if (brandPenalty >= 10) {
    reasons.push('Brand sizing is spread across multiple size labels.');
  }

  if (fitPreference === 'slim') {
    reasons.push('Slim fit preference tightens tolerance, increasing return risk slightly.');
  }

  if (reasons.length === 0) {
    reasons.push('High confidence and consistent brand mapping indicate stable fit prediction.');
  }

  return {
    score,
    level,
    reasons,
    alternatives: deriveFitAlternatives(response.predicted_size || '-', fitPreference),
  };
};
