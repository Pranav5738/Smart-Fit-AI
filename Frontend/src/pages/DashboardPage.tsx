import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
  type FormEvent,
} from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ProcessingState } from '@/components/processing/ProcessingState';
import { VirtualTryOn } from '@/components/results/VirtualTryOn';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { BRAND_OPTIONS, DEFAULT_BRANDS } from '@/data/brands';
import { useProfiles } from '@/contexts/ProfileContext';
import { useToast } from '@/contexts/ToastContext';
import { useUserPreferences } from '@/contexts/UserPreferencesContext';
import { analyzeImage } from '@/services/api';
import type { AnalyzeResponse, FitPreference } from '@/types/smartfit';
import {
  confidenceToPercent,
  formatMeasurementValue,
  normalizeRecommendations,
  toTitleCase,
} from '@/utils/format';
import { compressImageForMobile, evaluateCaptureQuality } from '@/utils/quality';

const isImageFile = (file: File): boolean => file.type.startsWith('image/');

const POSE_REQUIREMENTS = [
  'Frame full body from head to ankles.',
  'Face the camera and stand straight.',
  'Keep both arms slightly away from torso.',
  'Use bright front lighting and a plain background.',
  'Keep camera vertical at chest height, about 2-3 meters away.',
];

type CaptureTimerOption = 0 | 3 | 5 | 10;

const CAPTURE_TIMER_OPTIONS: CaptureTimerOption[] = [0, 3, 5, 10];

export const DashboardPage = () => {
  const { notify } = useToast();
  const { unitSystem, language } = useUserPreferences();
  const { activeProfile } = useProfiles();

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const countdownIntervalRef = useRef<number | null>(null);
  const previousPreviewRef = useRef('');

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isWebcamOpen, setIsWebcamOpen] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [captureHints, setCaptureHints] = useState<string[]>([]);
  const [captureTimerSec, setCaptureTimerSec] = useState<CaptureTimerOption>(0);
  const [countdownSec, setCountdownSec] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [fitPreference, setFitPreference] = useState<FitPreference>('regular');
  const [selectedBrands, setSelectedBrands] = useState<string[]>(DEFAULT_BRANDS);

  const clearCaptureCountdown = useCallback(() => {
    if (countdownIntervalRef.current !== null) {
      window.clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }

    setCountdownSec(null);
  }, []);

  const releasePreview = useCallback((next = '') => {
    const previous = previousPreviewRef.current;

    if (previous.startsWith('blob:')) {
      URL.revokeObjectURL(previous);
    }

    previousPreviewRef.current = next;
    setPreviewUrl(next);
  }, []);

  const stopWebcam = useCallback(() => {
    clearCaptureCountdown();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setStream(null);
    setIsWebcamOpen(false);
  }, [clearCaptureCountdown]);

  useEffect(() => {
    if (!videoRef.current || !stream) {
      return;
    }

    videoRef.current.srcObject = stream;
    void videoRef.current.play().catch(() => {
      setErrorMessage('Unable to autoplay webcam preview. Click capture again.');
    });
  }, [stream]);

  useEffect(() => {
    return () => {
      stopWebcam();
      releasePreview();
    };
  }, [releasePreview, stopWebcam]);

  const setImageFile = useCallback(
    async (file: File) => {
      if (!isImageFile(file)) {
        notify('Please select a valid image file.', 'error');
        return;
      }

      clearCaptureCountdown();
      const optimized = await compressImageForMobile(file);
      releasePreview(URL.createObjectURL(optimized));
      setSelectedFile(optimized);
      setCaptureHints([]);
      setErrorMessage(null);

      if (optimized.size < file.size) {
        notify('Image optimized for faster analysis.', 'info');
      }
    },
    [clearCaptureCountdown, notify, releasePreview]
  );

  const toggleBrand = (brand: string) => {
    setSelectedBrands((currentBrands) => {
      if (currentBrands.includes(brand)) {
        if (currentBrands.length === 1) {
          return currentBrands;
        }

        return currentBrands.filter((item) => item !== brand);
      }

      return [...currentBrands, brand];
    });
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);

    const file = event.dataTransfer.files?.[0];
    if (file) {
      void setImageFile(file);
    }
  };

  const startWebcam = async () => {
    clearCaptureCountdown();

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
      streamRef.current = mediaStream;
      setStream(mediaStream);
      setIsWebcamOpen(true);
      notify('Webcam opened. Capture when ready.', 'info');
    } catch {
      const message = 'Unable to access webcam in this browser.';
      setErrorMessage(message);
      notify(message, 'error');
    }
  };

  const captureFrameFromWebcam = useCallback(() => {
    if (!videoRef.current) {
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth || 720;
    canvas.height = videoRef.current.videoHeight || 960;

    const context = canvas.getContext('2d');
    if (!context) {
      notify('Unable to capture webcam image.', 'error');
      return;
    }

    context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (!blob) {
        notify('Capture failed. Try again.', 'error');
        return;
      }

      const webcamFile = new File([blob], `smartfit-webcam-${Date.now()}.jpg`, {
        type: 'image/jpeg',
      });

      void setImageFile(webcamFile);
      stopWebcam();
    }, 'image/jpeg', 0.95);
  }, [notify, setImageFile, stopWebcam]);

  const captureFromWebcam = () => {
    if (!videoRef.current) {
      return;
    }

    if (countdownSec !== null) {
      return;
    }

    if (captureTimerSec === 0) {
      captureFrameFromWebcam();
      return;
    }

    let remainingSeconds = captureTimerSec;
    setCountdownSec(remainingSeconds);
    notify(`Photo will be taken in ${captureTimerSec} seconds.`, 'info');

    countdownIntervalRef.current = window.setInterval(() => {
      remainingSeconds -= 1;

      if (remainingSeconds <= 0) {
        clearCaptureCountdown();
        captureFrameFromWebcam();
        return;
      }

      setCountdownSec(remainingSeconds);
    }, 1000);
  };

  const cancelCaptureTimer = () => {
    if (countdownSec === null) {
      return;
    }

    clearCaptureCountdown();
    notify('Capture timer cancelled.', 'info');
  };


  const handleAnalyze = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!selectedFile) {
      notify('Upload an image or capture via webcam first.', 'error');
      return;
    }

    if (selectedBrands.length === 0) {
      notify('Choose at least one brand.', 'error');
      return;
    }

    setIsAnalyzing(true);
    setErrorMessage(null);

    try {
      const qualityReport = await evaluateCaptureQuality(selectedFile, language);
      setCaptureHints(qualityReport.hints.slice(0, 3));

      const response = await analyzeImage(selectedFile, {
        fitPreference,
        profileId: activeProfile.id,
        saveToHistory: true,
        consentAccepted: true,
        unitSystem,
        language,
        includeTryonComparison: true,
      });

      setResult(response);
      notify('Analysis complete. Dashboard updated.', 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to analyze image.';
      setErrorMessage(message);
      notify(message, 'error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const recommendations = useMemo(
    () => normalizeRecommendations(result?.recommendations || []),
    [result?.recommendations]
  );

  const confidence = result ? confidenceToPercent(result.confidence) : 0;

  const measurementRows = useMemo(() => {
    if (!result?.measurements) {
      return [] as Array<{ label: string; value: string }>;
    }

    const sourceUnit = result.measurement_unit || 'in';

    return Object.entries(result.measurements).map(([key, value]) => ({
      label: toTitleCase(key),
      value: formatMeasurementValue(value, unitSystem, sourceUnit),
    }));
  }, [result?.measurement_unit, result?.measurements, unitSystem]);

  const brandRows = useMemo(() => {
    return selectedBrands.map((brand) => ({
      brand,
      size: result?.brand_mapping?.[brand] || result?.brand_mapping?.[brand.toLowerCase()] || '-',
    }));
  }, [result?.brand_mapping, selectedBrands]);

  return (
    <>
      <div className="space-y-6 pb-8">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700 dark:text-brand-300">
            SmartFit Dashboard
          </p>
          <h1 className="mt-2 text-3xl font-bold">Analyze Your Fit Profile</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Upload or capture an image, run AI analysis, and review measurements, predicted size, brand mapping, confidence score, try-on preview, and recommendations.
          </p>
        </section>

        <form onSubmit={handleAnalyze} className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900"
          >
            <div
              onDragOver={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={(event) => {
                event.preventDefault();
                setIsDragging(false);
              }}
              onDrop={handleDrop}
              className={`rounded-2xl border-2 border-dashed p-8 text-center transition ${
                isDragging
                  ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/20'
                  : 'border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-950/40'
              }`}
            >
              <p className="text-lg font-bold">Upload Image</p>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Drag and drop or browse from your device</p>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="focus-ring mt-4 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
              >
                Browse Image
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onInput={(event) => {
                  const file = event.currentTarget.files?.[0];
                  if (file) {
                    void setImageFile(file);
                  }
                }}
              />
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={startWebcam}
                className="focus-ring rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Use Webcam
              </button>
              <button
                type="submit"
                disabled={!selectedFile || isAnalyzing}
                className="focus-ring rounded-xl bg-accent-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-accent-600 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isAnalyzing ? 'Analyzing...' : 'Analyze Fit'}
              </button>
            </div>

            <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4 dark:border-amber-900/40 dark:bg-amber-950/20">
              <p className="text-sm font-semibold text-amber-900 dark:text-amber-100">Pose Checklist</p>
              <div className="mt-2 space-y-1.5 text-sm text-amber-800 dark:text-amber-200">
                {POSE_REQUIREMENTS.map((tip) => (
                  <p key={tip}>- {tip}</p>
                ))}
              </div>
            </div>

            {captureHints.length > 0 ? (
              <div className="rounded-2xl border border-cyan-200 bg-cyan-50/70 p-4 dark:border-cyan-900/40 dark:bg-cyan-950/20">
                <p className="text-sm font-semibold text-cyan-900 dark:text-cyan-100">Capture Feedback</p>
                <div className="mt-2 space-y-1.5 text-sm text-cyan-800 dark:text-cyan-200">
                  {captureHints.map((hint) => (
                    <p key={hint}>- {hint}</p>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
              <p className="text-sm font-semibold">Fit Preference</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                {(['slim', 'regular', 'relaxed'] as FitPreference[]).map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setFitPreference(option)}
                    className={`focus-ring rounded-xl border px-3 py-2 text-sm font-semibold capitalize transition ${
                      fitPreference === option
                        ? 'border-brand-600 bg-brand-600 text-white'
                        : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
              <p className="text-sm font-semibold">Brands</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {BRAND_OPTIONS.map((brand) => {
                  const isSelected = selectedBrands.includes(brand);

                  return (
                    <button
                      key={brand}
                      type="button"
                      onClick={() => toggleBrand(brand)}
                      className={`focus-ring rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                        isSelected
                          ? 'border-brand-600 bg-brand-600 text-white'
                          : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'
                      }`}
                    >
                      {brand}
                    </button>
                  );
                })}
              </div>
            </div>

            {isWebcamOpen ? (
              <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
                <video ref={videoRef} autoPlay playsInline muted className="aspect-[4/5] w-full rounded-xl bg-slate-900 object-cover" />

                <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
                    Capture Timer
                  </p>
                  <div className="grid grid-cols-4 gap-2">
                    {CAPTURE_TIMER_OPTIONS.map((seconds) => {
                      const selected = captureTimerSec === seconds;

                      return (
                        <button
                          key={seconds}
                          type="button"
                          onClick={() => setCaptureTimerSec(seconds)}
                          disabled={countdownSec !== null}
                          className={`focus-ring rounded-lg border px-2 py-1.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${
                            selected
                              ? 'border-brand-600 bg-brand-600 text-white'
                              : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'
                          }`}
                        >
                          {seconds === 0 ? 'None' : `${seconds}s`}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={captureFromWebcam}
                    disabled={countdownSec !== null}
                    className="focus-ring rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
                  >
                    {countdownSec !== null
                      ? `Capturing in ${countdownSec}s`
                      : captureTimerSec === 0
                        ? 'Capture'
                        : `Capture in ${captureTimerSec}s`}
                  </button>

                  {countdownSec !== null ? (
                    <button
                      type="button"
                      onClick={cancelCaptureTimer}
                      className="focus-ring rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-800 transition hover:bg-amber-100 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200 dark:hover:bg-amber-900/30"
                    >
                      Stop Timer
                    </button>
                  ) : null}

                  <button
                    type="button"
                    onClick={stopWebcam}
                    className="focus-ring rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : null}

            {errorMessage ? (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-200">
                {errorMessage}
              </div>
            ) : null}
          </motion.section>

          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="space-y-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900"
          >
            <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">Preview</p>
            <div className="grid min-h-[26rem] place-items-center overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 p-4 dark:border-slate-700 dark:bg-slate-950/40">
              {previewUrl ? (
                <img src={previewUrl} alt="Selected preview" className="h-full w-full rounded-xl object-cover" />
              ) : (
                <div className="text-center text-sm text-slate-500 dark:text-slate-400">
                  Upload or capture an image to preview it here.
                </div>
              )}
            </div>
            {selectedFile ? (
              <p className="text-sm text-slate-600 dark:text-slate-300">
                Selected file: <span className="font-semibold">{selectedFile.name}</span>
              </p>
            ) : null}
          </motion.section>
        </form>

        <section className="space-y-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900">
          <h2 className="text-2xl font-bold">Results Panel</h2>

          {isAnalyzing ? (
            <div className="grid gap-4 md:grid-cols-3">
              <SkeletonCard lines={4} />
              <SkeletonCard lines={4} />
              <SkeletonCard lines={4} />
            </div>
          ) : result ? (
            <div className="space-y-5">
              <div className="grid gap-4 md:grid-cols-3">
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
                  <p className="text-sm font-semibold">Measurements</p>
                  <div className="mt-3 space-y-2 text-sm">
                    {measurementRows.map((row) => (
                      <div key={row.label} className="flex items-center justify-between rounded-lg bg-white px-2 py-1.5 dark:bg-slate-900">
                        <span>{row.label}</span>
                        <span className="font-semibold">{row.value}</span>
                      </div>
                    ))}
                  </div>
                </article>

                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
                  <p className="text-sm font-semibold">Size Prediction</p>
                  <div className="mt-3 rounded-xl bg-gradient-to-br from-brand-600 to-brand-800 p-4 text-white">
                    <p className="text-xs uppercase tracking-[0.12em] text-brand-100">Recommended</p>
                    <p className="mt-1 text-4xl font-extrabold">{result.predicted_size || '-'}</p>
                    <p className="text-sm text-brand-100">Confidence: {confidence}%</p>
                  </div>
                </article>

                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
                  <p className="text-sm font-semibold">Brand Mapping</p>
                  <div className="mt-3 space-y-2 text-sm">
                    {brandRows.map((row) => (
                      <div key={row.brand} className="flex items-center justify-between rounded-lg bg-white px-2 py-1.5 dark:bg-slate-900">
                        <span>{row.brand}</span>
                        <span className="font-semibold">{row.size}</span>
                      </div>
                    ))}
                  </div>
                </article>
              </div>

              <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
                <p className="text-sm font-semibold">Recommendations</p>
                <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                  {recommendations.length > 0 ? (
                    recommendations.map((item, index) => (
                      <div key={`${item.name}-${index}`} className="rounded-xl bg-white p-3 text-sm dark:bg-slate-900">
                        <p className="font-semibold">{item.name}</p>
                        <p className="text-slate-500 dark:text-slate-400">
                          {item.description || 'Suggested based on your fit profile and selected brands.'}
                        </p>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-xl border border-dashed border-slate-300 p-3 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                      No recommendations returned by API.
                    </div>
                  )}
                </div>
              </section>

              <VirtualTryOn
                uploadedPreview={previewUrl || undefined}
                tryonImage={result.tryon_image}
                recommendations={recommendations}
              />
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
              Run analysis to view measurements, size prediction, brand mapping, confidence score, and virtual try-on preview.
            </div>
          )}
        </section>
      </div>

      <AnimatePresence>{isAnalyzing ? <ProcessingState /> : null}</AnimatePresence>
    </>
  );
};
