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
import { useAuth } from '@/contexts/AuthContext';
import { useProfiles } from '@/contexts/ProfileContext';
import { useToast } from '@/contexts/ToastContext';
import { useUserPreferences } from '@/contexts/UserPreferencesContext';
import { analyzeImage } from '@/services/api';
import type { AgeGroup, AnalyzeResponse, FitPreference, GenderCode } from '@/types/smartfit';
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
  const { user } = useAuth();
  const { unitSystem, language } = useUserPreferences();
  const { activeProfile } = useProfiles();

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const sideFileInputRef = useRef<HTMLInputElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const countdownIntervalRef = useRef<number | null>(null);
  const previousPreviewRef = useRef('');
  const previousSidePreviewRef = useRef('');

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [sideFile, setSideFile] = useState<File | null>(null);
  const [sidePreviewUrl, setSidePreviewUrl] = useState('');
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
  const [ageGroup, setAgeGroup] = useState<AgeGroup>('adult');
  const [gender, setGender] = useState<GenderCode>('unisex');
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

  const releaseSidePreview = useCallback((next = '') => {
    const previous = previousSidePreviewRef.current;

    if (previous.startsWith('blob:')) {
      URL.revokeObjectURL(previous);
    }

    previousSidePreviewRef.current = next;
    setSidePreviewUrl(next);
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
      releaseSidePreview();
    };
  }, [releasePreview, releaseSidePreview, stopWebcam]);

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
      setErrorMessage(null);

      const quickFrontQuality = await evaluateCaptureQuality(optimized, language);
      setCaptureHints(quickFrontQuality.hints.slice(0, 2).map((hint) => `Front: ${hint}`));

      if (optimized.size < file.size) {
        notify('Image optimized for faster analysis.', 'info');
      }
    },
    [clearCaptureCountdown, language, notify, releasePreview]
  );

  const setSideImageFile = useCallback(
    async (file: File) => {
      if (!isImageFile(file)) {
        notify('Please select a valid side-view image file.', 'error');
        return;
      }

      const optimized = await compressImageForMobile(file);
      releaseSidePreview(URL.createObjectURL(optimized));
      setSideFile(optimized);
      setErrorMessage(null);

      const quickSideQuality = await evaluateCaptureQuality(optimized, language);
      setCaptureHints((current) => {
        const frontHints = current.filter((item) => item.startsWith('Front:')).slice(0, 2);
        const sideHints = quickSideQuality.hints.slice(0, 2).map((hint) => `Side: ${hint}`);
        return [...frontHints, ...sideHints];
      });

      if (optimized.size < file.size) {
        notify('Side image optimized for faster analysis.', 'info');
      }
    },
    [language, notify, releaseSidePreview]
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
      notify('Upload a front image or capture via webcam first.', 'error');
      return;
    }

    if (!sideFile) {
      notify('Upload a side-view image before analysis.', 'error');
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

      const resolvedHeightCm = ageGroup === 'adult' ? user?.heightCm : undefined;

      const response = await analyzeImage(selectedFile, sideFile, {
        fitPreference,
        userHeightCm: resolvedHeightCm,
        ageGroup,
        gender,
        preferredBrands: selectedBrands,
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
      <div className="space-y-6 pb-8 sm:space-y-8 sm:pb-10">
        <section className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white p-4 shadow-card dark:border-slate-800 dark:bg-slate-900 sm:p-8">
          <div className="pointer-events-none absolute -right-14 -top-20 h-56 w-56 rounded-full bg-brand-200/55 blur-3xl dark:bg-brand-700/30" />
          <div className="pointer-events-none absolute -bottom-24 -left-16 h-56 w-56 rounded-full bg-accent-200/55 blur-3xl dark:bg-accent-700/20" />

          <div className="relative">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700 dark:text-brand-300">
              SmartFit Dashboard
            </p>
            <h1 className="mt-2 text-[2rem] font-bold leading-tight sm:text-4xl">Analyze Your Fit Profile</h1>
            <p className="mt-3 max-w-3xl text-sm text-slate-600 dark:text-slate-300 sm:text-base">
              Upload a full-body image, run AI analysis, and review your measurements, fit confidence,
              brand mapping, and virtual try-on in one streamlined workspace.
            </p>

            <div className="mt-5 flex flex-wrap gap-2 text-xs font-semibold">
              <span className="rounded-full border border-brand-300 bg-brand-50 px-3 py-1 text-brand-700 dark:border-brand-800 dark:bg-brand-950/35 dark:text-brand-300">
                Profile: {activeProfile.name}
              </span>
              <span className="rounded-full border border-slate-300 bg-slate-100 px-3 py-1 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                Fit: {fitPreference}
              </span>
              <span className="rounded-full border border-slate-300 bg-slate-100 px-3 py-1 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">
                Brands: {selectedBrands.length}
              </span>
            </div>
          </div>
        </section>

        <form onSubmit={handleAnalyze} className="space-y-6">
          <section className="rounded-3xl border border-slate-200 bg-white p-3 shadow-card dark:border-slate-800 dark:bg-slate-900 sm:p-6">
            <div className="grid gap-4 sm:gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
              <motion.aside
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
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
                  className={`rounded-2xl border-2 border-dashed p-6 text-center transition ${
                    isDragging
                      ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/20'
                      : 'border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-950/40'
                  }`}
                >
                  <p className="text-lg font-bold">Upload or Drop Image</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">PNG, JPG, WEBP supported</p>
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

                <div className="rounded-2xl border border-slate-300 bg-slate-50 p-4 text-center dark:border-slate-700 dark:bg-slate-950/40">
                  <p className="text-sm font-bold">Upload Side Image (Required)</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Stand in side profile for torso depth capture.</p>
                  <button
                    type="button"
                    onClick={() => sideFileInputRef.current?.click()}
                    className="focus-ring mt-3 rounded-xl bg-slate-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 dark:bg-slate-200 dark:text-slate-900 dark:hover:bg-white"
                  >
                    Browse Side Image
                  </button>
                  <input
                    ref={sideFileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onInput={(event) => {
                      const file = event.currentTarget.files?.[0];
                      if (file) {
                        void setSideImageFile(file);
                      }
                    }}
                  />
                  {sideFile ? (
                    <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-300">Side image ready: {sideFile.name}</p>
                  ) : (
                    <p className="mt-2 text-xs text-rose-600 dark:text-rose-300">Side image missing.</p>
                  )}
                </div>

                <div className="grid gap-2 sm:gap-3 sm:grid-cols-3 xl:grid-cols-1">
                  <button
                    type="button"
                    onClick={startWebcam}
                    className="focus-ring rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Use Webcam
                  </button>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="focus-ring rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Replace Image
                  </button>
                  <button
                    type="submit"
                    disabled={!selectedFile || !sideFile || isAnalyzing}
                    className="focus-ring rounded-xl bg-accent-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-accent-600 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isAnalyzing ? 'Analyzing...' : 'Analyze Fit'}
                  </button>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-950/40 sm:p-4">
                  <p className="text-sm font-semibold">Demographics</p>
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    <select
                      value={ageGroup}
                      onChange={(event) => setAgeGroup(event.target.value as AgeGroup)}
                      className="focus-ring rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                    >
                      <option value="child">Child</option>
                      <option value="teen">Teen</option>
                      <option value="adult">Adult</option>
                    </select>

                    <select
                      value={gender}
                      onChange={(event) => setGender(event.target.value as GenderCode)}
                      className="focus-ring rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                    >
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="unisex">Unisex</option>
                    </select>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-950/40 sm:p-4">
                  <p className="text-sm font-semibold">Fit Preference</p>
                  <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {(['slim', 'regular', 'relaxed'] as FitPreference[]).map((option) => (
                      <button
                        key={option}
                        type="button"
                        onClick={() => setFitPreference(option)}
                        className={`focus-ring rounded-xl border px-2 py-2 text-xs font-semibold capitalize transition sm:text-sm ${
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

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-950/40 sm:p-4">
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

                {errorMessage ? (
                  <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-200">
                    {errorMessage}
                  </div>
                ) : null}
              </motion.aside>

              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="space-y-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">Live Preview</p>
                  {selectedFile ? (
                    <span className="rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-300">
                      Ready
                    </span>
                  ) : null}
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="grid h-[18rem] place-items-center overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 p-2 sm:h-[22rem] sm:p-3 lg:h-[28rem] dark:border-slate-700 dark:bg-slate-950/40">
                    {previewUrl ? (
                      <img
                        src={previewUrl}
                        alt="Front preview"
                        className="max-h-full max-w-full rounded-xl object-contain"
                      />
                    ) : (
                      <div className="text-center text-sm text-slate-500 dark:text-slate-400">
                        Upload front image.
                      </div>
                    )}
                  </div>
                  <div className="grid h-[18rem] place-items-center overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 p-2 sm:h-[22rem] sm:p-3 lg:h-[28rem] dark:border-slate-700 dark:bg-slate-950/40">
                    {sidePreviewUrl ? (
                      <img
                        src={sidePreviewUrl}
                        alt="Side preview"
                        className="max-h-full max-w-full rounded-xl object-contain"
                      />
                    ) : (
                      <div className="text-center text-sm text-slate-500 dark:text-slate-400">
                        Upload side image.
                      </div>
                    )}
                  </div>
                </div>

                {selectedFile || sideFile ? (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-300">
                    Front: <span className="font-semibold">{selectedFile?.name || 'Not selected'}</span> | Side:{' '}
                    <span className="font-semibold">{sideFile?.name || 'Not selected'}</span>
                  </div>
                ) : null}

                <div className="grid gap-3 sm:gap-4 lg:grid-cols-2">
                  <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-3 dark:border-amber-900/40 dark:bg-amber-950/20 sm:p-4">
                    <p className="text-sm font-semibold text-amber-900 dark:text-amber-100">Pose Checklist</p>
                    <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-amber-800 dark:text-amber-200">
                      {POSE_REQUIREMENTS.map((tip) => (
                        <li key={tip}>{tip}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-2xl border border-cyan-200 bg-cyan-50/70 p-3 dark:border-cyan-900/40 dark:bg-cyan-950/20 sm:p-4">
                    <p className="text-sm font-semibold text-cyan-900 dark:text-cyan-100">Capture Feedback</p>
                    <div className="mt-2 space-y-1.5 text-sm text-cyan-800 dark:text-cyan-200">
                      {captureHints.length > 0 ? (
                        captureHints.map((hint) => <p key={hint}>- {hint}</p>)
                      ) : (
                        <p>- Capture quality tips will appear after analysis starts.</p>
                      )}
                    </div>
                  </div>
                </div>

                {isWebcamOpen ? (
                  <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-950/40 sm:p-4">
                    <video ref={videoRef} autoPlay playsInline muted className="aspect-[4/3] w-full rounded-xl bg-slate-900 object-cover sm:aspect-[16/9]" />

                    <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900">
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
                        Capture Timer
                      </p>
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
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
              </motion.div>
            </div>
          </section>
        </form>

        <section className="space-y-4 rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-2xl font-bold">Results Panel</h2>
            {result ? (
              <span className="rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-300">
                Analysis Complete
              </span>
            ) : null}
          </div>

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
                    {result.size_range ? (
                      <p className="mt-1 text-xs text-brand-100">Suggested range: {result.size_range}</p>
                    ) : null}
                  </div>
                  {result.prediction_advice ? (
                    <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">{result.prediction_advice}</p>
                  ) : null}
                  {result.explainability?.size_reasoning ? (
                    <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{result.explainability.size_reasoning}</p>
                  ) : null}
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

              {result.nike_size_suggestions ? (
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold">Nike Size Pair</p>
                    <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-[11px] font-semibold text-slate-700 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200">
                      Chart-Based
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900">
                      <p className="text-xs text-slate-500 dark:text-slate-400">Tops</p>
                      <p className="text-lg font-bold">{result.nike_size_suggestions.tops_size}</p>
                    </div>
                    <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900">
                      <p className="text-xs text-slate-500 dark:text-slate-400">Bottoms</p>
                      <p className="text-lg font-bold">{result.nike_size_suggestions.bottoms_size}</p>
                    </div>
                  </div>
                </article>
              ) : null}

              {result.zara_size_suggestions ? (
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold">Zara Size Pair</p>
                    <span className="rounded-full border border-slate-300 bg-white px-2 py-0.5 text-[11px] font-semibold text-slate-700 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200">
                      Chart-Based
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900">
                      <p className="text-xs text-slate-500 dark:text-slate-400">Tops</p>
                      <p className="text-lg font-bold">{result.zara_size_suggestions.tops_size}</p>
                    </div>
                    <div className="rounded-lg bg-white px-3 py-2 dark:bg-slate-900">
                      <p className="text-xs text-slate-500 dark:text-slate-400">Bottoms</p>
                      <p className="text-lg font-bold">{result.zara_size_suggestions.bottoms_size}</p>
                    </div>
                  </div>
                </article>
              ) : null}

              <div className="grid gap-4 md:grid-cols-2">
                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
                  <p className="text-sm font-semibold">Fit Confidence</p>
                  <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-slate-50">{confidence}%</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Higher confidence means stronger measurement consistency.
                  </p>
                  {confidence < 75 ? (
                    <p className="mt-2 rounded-lg border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200">
                      Retry suggested: retake both front and side images with full body visible and a straight pose.
                    </p>
                  ) : null}
                </article>

                <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
                  <p className="text-sm font-semibold">Return Risk</p>
                  <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-slate-50">
                    {result.return_risk?.level ? toTitleCase(result.return_risk.level) : '-'}
                  </p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Score: {result.return_risk?.score ?? '-'}
                  </p>
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
