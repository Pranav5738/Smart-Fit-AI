import { RecommendationItem, UnitSystem } from '@/types/smartfit';

export const toTitleCase = (value: string): string => {
  return value
    .replace(/[_-]+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

export const parseMeasurementInches = (
  value: number | string,
  sourceUnit: UnitSystem = 'in'
): number | null => {
  if (typeof value === 'number') {
    return sourceUnit === 'cm' ? value / 2.54 : value;
  }

  const numeric = Number.parseFloat(value.replace(/[^0-9.]/g, ''));

  if (!Number.isFinite(numeric)) {
    return null;
  }

  if (value.toLowerCase().includes('cm')) {
    return numeric / 2.54;
  }

  if (value.toLowerCase().includes('in')) {
    return numeric;
  }

  return sourceUnit === 'cm' ? numeric / 2.54 : numeric;
};

const convertInchesToUnit = (inches: number, unitSystem: UnitSystem): number => {
  if (unitSystem === 'cm') {
    return inches * 2.54;
  }

  return inches;
};

export const formatMeasurementValue = (
  value: number | string,
  unitSystem: UnitSystem = 'in',
  sourceUnit: UnitSystem = 'in'
): string => {
  const parsedInches = parseMeasurementInches(value, sourceUnit);

  if (parsedInches === null) {
    return String(value);
  }

  const converted = convertInchesToUnit(parsedInches, unitSystem);
  const suffix = unitSystem === 'cm' ? 'cm' : 'in';

  return `${converted.toFixed(1)} ${suffix}`;
};

export const confidenceToPercent = (confidence: number): number => {
  if (confidence <= 1) {
    return Math.round(confidence * 100);
  }

  return Math.min(Math.round(confidence), 100);
};

export const normalizeImageSource = (raw?: string): string | undefined => {
  if (!raw) {
    return undefined;
  }

  if (
    raw.startsWith('http://') ||
    raw.startsWith('https://') ||
    raw.startsWith('blob:') ||
    raw.startsWith('data:') ||
    raw.startsWith('/') ||
    raw.startsWith('./') ||
    raw.startsWith('../')
  ) {
    return raw;
  }

  return `data:image/png;base64,${raw}`;
};

export const normalizeRecommendations = (
  recommendations: Array<string | RecommendationItem>
): RecommendationItem[] => {
  return recommendations.map((item, index) => {
    if (typeof item === 'string') {
      return { name: item };
    }

    const inferredName = item.name || item.product_name || `Outfit ${index + 1}`;

    return {
      ...item,
      name: inferredName,
      description: item.description || item.reason,
      image_url: item.image_url,
    };
  });
};
