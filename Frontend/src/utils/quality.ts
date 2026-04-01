import { qualityCheck } from '@/services/api';
import type { CaptureQualityReport, LanguageCode } from '@/types/smartfit';

const clamp = (value: number, min = 0, max = 100): number => {
  return Math.max(min, Math.min(max, value));
};

const fileToImage = async (file: File): Promise<HTMLImageElement> => {
  return new Promise((resolve, reject) => {
    const image = new Image();
    const objectUrl = URL.createObjectURL(file);

    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(image);
    };

    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error('Unable to load image for quality analysis.'));
    };

    image.src = objectUrl;
  });
};

export const fileToDataUrl = async (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('Unable to convert image preview.'));
    reader.readAsDataURL(file);
  });
};

export const compressImageForMobile = async (file: File): Promise<File> => {
  const MAX_SIDE = 1600;
  const TARGET_QUALITY = 0.82;

  if (file.size < 1_300_000) {
    return file;
  }

  const image = await fileToImage(file);

  const ratio = Math.min(1, MAX_SIDE / Math.max(image.width, image.height));
  const targetWidth = Math.round(image.width * ratio);
  const targetHeight = Math.round(image.height * ratio);

  const canvas = document.createElement('canvas');
  canvas.width = targetWidth;
  canvas.height = targetHeight;

  const context = canvas.getContext('2d');
  if (!context) {
    return file;
  }

  context.drawImage(image, 0, 0, targetWidth, targetHeight);

  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, 'image/jpeg', TARGET_QUALITY);
  });

  if (!blob) {
    return file;
  }

  return new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), {
    type: 'image/jpeg',
    lastModified: Date.now(),
  });
};

export const evaluateCaptureQuality = async (
  file: File,
  language: LanguageCode = 'en'
): Promise<CaptureQualityReport> => {
  try {
    return await qualityCheck(file, language);
  } catch {
    // Fall back to local estimation when backend quality endpoint is unavailable.
  }

  const image = await fileToImage(file);

  const sampleWidth = Math.max(120, Math.round(image.width * 0.22));
  const sampleHeight = Math.max(180, Math.round(image.height * 0.22));

  const canvas = document.createElement('canvas');
  canvas.width = sampleWidth;
  canvas.height = sampleHeight;

  const context = canvas.getContext('2d', { willReadFrequently: true });
  if (!context) {
    return {
      overallScore: 75,
      lightingScore: 75,
      framingScore: 75,
      poseScore: 75,
      sharpnessScore: 75,
      hints: ['Could not fully evaluate image quality. Proceed if the body is clearly visible.'],
    };
  }

  context.drawImage(image, 0, 0, sampleWidth, sampleHeight);
  const pixelData = context.getImageData(0, 0, sampleWidth, sampleHeight).data;

  let luminanceSum = 0;
  let luminanceSquaredSum = 0;
  let edgeSum = 0;
  let edgeCount = 0;

  const luminanceValues = new Float32Array(sampleWidth * sampleHeight);

  for (let i = 0; i < pixelData.length; i += 4) {
    const r = pixelData[i];
    const g = pixelData[i + 1];
    const b = pixelData[i + 2];
    const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;

    const index = i / 4;
    luminanceValues[index] = luminance;

    luminanceSum += luminance;
    luminanceSquaredSum += luminance * luminance;
  }

  for (let y = 0; y < sampleHeight - 1; y += 1) {
    for (let x = 0; x < sampleWidth - 1; x += 1) {
      const index = y * sampleWidth + x;
      const right = index + 1;
      const down = index + sampleWidth;

      const horizontalDiff = Math.abs(luminanceValues[index] - luminanceValues[right]);
      const verticalDiff = Math.abs(luminanceValues[index] - luminanceValues[down]);

      edgeSum += (horizontalDiff + verticalDiff) * 0.5;
      edgeCount += 1;
    }
  }

  const totalPixels = sampleWidth * sampleHeight;
  const meanLuminance = luminanceSum / totalPixels;
  const variance = luminanceSquaredSum / totalPixels - meanLuminance * meanLuminance;
  const stdDev = Math.sqrt(Math.max(variance, 0));

  const aspectRatio = image.width / image.height;
  const minDimension = Math.min(image.width, image.height);
  const edgeAverage = edgeCount > 0 ? edgeSum / edgeCount : 0;

  const brightnessScore = clamp(100 - (Math.abs(meanLuminance - 135) / 135) * 120);
  const contrastScore = clamp((stdDev / 62) * 100);
  const lightingScore = Math.round(brightnessScore * 0.64 + contrastScore * 0.36);

  const portraitBiasPenalty = image.width > image.height ? 25 : 0;
  const aspectPenalty = Math.abs(aspectRatio - 0.72) * 155;
  const resolutionPenalty = minDimension < 700 ? 18 : minDimension < 900 ? 10 : 0;

  const framingScore = Math.round(clamp(100 - aspectPenalty - resolutionPenalty));
  const poseScore = Math.round(clamp(100 - aspectPenalty * 0.8 - portraitBiasPenalty));
  const sharpnessScore = Math.round(clamp((edgeAverage / 24) * 100));

  const overallScore = Math.round(
    lightingScore * 0.32 + framingScore * 0.23 + poseScore * 0.2 + sharpnessScore * 0.25
  );

  const hints: string[] = [];

  if (lightingScore < 65) {
    hints.push('Lighting is low. Move near a bright source or avoid backlight.');
  }

  if (framingScore < 70) {
    hints.push('Step back and frame your full body vertically for better fit detection.');
  }

  if (poseScore < 70) {
    hints.push('Stand straight with arms slightly away from your torso.');
  }

  if (sharpnessScore < 65) {
    hints.push('Image looks soft. Hold still and avoid camera shake.');
  }

  if (hints.length === 0) {
    hints.push('Capture quality looks strong for high-confidence measurements.');
  }

  return {
    overallScore,
    lightingScore,
    framingScore,
    poseScore,
    sharpnessScore,
    hints,
  };
};
