import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { normalizeImageSource } from '@/utils/format';
import type { RecommendationItem } from '@/types/smartfit';

interface VirtualTryOnProps {
  uploadedPreview?: string;
  tryonImage?: string;
  recommendations: RecommendationItem[];
}

interface OutfitOption {
  id: string;
  label: string;
  image: string;
}

type ComparisonMode = 'single' | 'side-by-side' | 'slider';

export const VirtualTryOn = ({
  uploadedPreview,
  tryonImage,
  recommendations,
}: VirtualTryOnProps) => {
  const options = useMemo<OutfitOption[]>(() => {
    const mapped: OutfitOption[] = [];

    const normalizedTryOn = normalizeImageSource(tryonImage);
    if (normalizedTryOn) {
      mapped.push({
        id: 'ai-preview',
        label: 'AI Try-On',
        image: normalizedTryOn,
      });
    }

    recommendations.forEach((recommendation, index) => {
      const optionImage = normalizeImageSource(recommendation.image_url);

      if (optionImage) {
        mapped.push({
          id: `recommendation-${index}`,
          label: recommendation.name,
          image: optionImage,
        });
      }
    });

    return mapped;
  }, [recommendations, tryonImage]);

  const [activeOptionId, setActiveOptionId] = useState(options[0]?.id ?? '');
  const [comparisonMode, setComparisonMode] = useState<ComparisonMode>('single');
  const [sliderPercent, setSliderPercent] = useState(52);

  useEffect(() => {
    if (!options.some((option) => option.id === activeOptionId)) {
      setActiveOptionId(options[0]?.id ?? '');
    }
  }, [activeOptionId, options]);

  const activeOption = options.find((option) => option.id === activeOptionId);
  const activeImage = activeOption?.image || uploadedPreview;

  const renderSinglePreview = () => {
    return (
      <AnimatePresence mode="wait">
        {activeImage ? (
          <motion.img
            key={activeOption?.id || 'uploaded-preview'}
            src={activeImage}
            alt={activeOption?.label || 'Uploaded user'}
            className="h-full w-full object-cover"
            initial={{ opacity: 0.2, scale: 1.02 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0.2, scale: 0.98 }}
            transition={{ duration: 0.35 }}
          />
        ) : (
          <motion.div
            key="empty-state"
            className="grid h-full place-items-center p-6 text-center text-sm text-slate-500 dark:text-slate-400"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            Preview becomes available once your backend returns try-on imagery.
          </motion.div>
        )}
      </AnimatePresence>
    );
  };

  const renderSideBySide = () => {
    if (!uploadedPreview || !activeImage) {
      return renderSinglePreview();
    }

    return (
      <div className="grid h-full grid-cols-2 gap-2">
        <div className="relative overflow-hidden rounded-xl border border-slate-300 dark:border-slate-700">
          <img src={uploadedPreview} alt="Original upload" className="h-full w-full object-cover" />
          <span className="absolute left-2 top-2 rounded-md bg-slate-950/65 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-white">
            Original
          </span>
        </div>
        <div className="relative overflow-hidden rounded-xl border border-slate-300 dark:border-slate-700">
          <img src={activeImage} alt="Try-on result" className="h-full w-full object-cover" />
          <span className="absolute left-2 top-2 rounded-md bg-brand-700/80 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-white">
            Try-On
          </span>
        </div>
      </div>
    );
  };

  const renderSlider = () => {
    if (!uploadedPreview || !activeImage) {
      return renderSinglePreview();
    }

    return (
      <div className="relative h-full w-full overflow-hidden rounded-2xl">
        <img src={uploadedPreview} alt="Original upload" className="h-full w-full object-cover" />

        <div className="absolute inset-0 overflow-hidden" style={{ width: `${sliderPercent}%` }}>
          <img src={activeImage} alt="Try-on overlay" className="h-full w-full object-cover" />
        </div>

        <div className="absolute bottom-4 left-4 right-4 rounded-xl bg-white/90 p-2 shadow-card dark:bg-slate-900/85">
          <input
            type="range"
            min={0}
            max={100}
            value={sliderPercent}
            onChange={(event) => setSliderPercent(Number(event.target.value))}
            className="focus-ring w-full"
            aria-label="Before and after slider"
          />
        </div>
      </div>
    );
  };

  const renderComparison = () => {
    if (comparisonMode === 'side-by-side') {
      return renderSideBySide();
    }

    if (comparisonMode === 'slider') {
      return renderSlider();
    }

    return renderSinglePreview();
  };

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700 dark:text-brand-300">Virtual Fitting</p>
          <h3 className="text-2xl font-bold">Virtual Try-On Preview</h3>
        </div>

        <div className="flex flex-wrap gap-2">
          {(['single', 'side-by-side', 'slider'] as ComparisonMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setComparisonMode(mode)}
              className={`focus-ring rounded-xl px-3 py-2 text-xs font-semibold transition ${
                comparisonMode === mode
                  ? 'bg-brand-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {mode === 'single'
                ? 'Single'
                : mode === 'side-by-side'
                  ? 'Side by Side'
                  : 'Before / After'}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="relative rounded-3xl border border-slate-200 bg-slate-100 p-3 dark:border-slate-700 dark:bg-slate-950">
          <div className="relative aspect-[4/5] overflow-hidden rounded-2xl bg-gradient-to-br from-slate-200 to-brand-100 dark:from-slate-900 dark:to-brand-950">
            {renderComparison()}
          </div>
          {uploadedPreview ? (
            <div className="absolute bottom-5 right-5 w-24 overflow-hidden rounded-xl border border-slate-300 shadow-card dark:border-slate-700">
              <img src={uploadedPreview} alt="Original upload" className="aspect-[3/4] w-full object-cover" />
            </div>
          ) : null}
        </div>

        <div className="space-y-5">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
            <p className="mb-2 text-sm font-semibold">Outfit Variants</p>
            <div className="flex flex-wrap gap-2">
              {options.length > 0 ? (
                options.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setActiveOptionId(option.id)}
                    className={`rounded-xl px-3 py-2 text-xs font-semibold transition ${
                      activeOptionId === option.id
                        ? 'bg-brand-600 text-white'
                        : 'bg-white text-slate-600 hover:bg-slate-100 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'
                    }`}
                  >
                    {option.label}
                  </button>
                ))
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">No outfit-specific previews returned yet.</p>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
            <p className="mb-2 text-sm font-semibold">Styling Notes</p>
            <div className="space-y-2">
              {recommendations.length > 0 ? (
                recommendations.map((item) => (
                  <div key={item.name} className="rounded-xl border border-slate-200 bg-white p-3 text-sm dark:border-slate-700 dark:bg-slate-900">
                    <p className="font-semibold">{item.name}</p>
                    <p className="text-slate-500 dark:text-slate-400">{item.description || 'Recommended based on your body profile and fit confidence.'}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">Recommendations will appear when available from API response.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
