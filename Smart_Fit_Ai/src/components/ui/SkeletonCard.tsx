interface SkeletonCardProps {
  lines?: number;
}

export const SkeletonCard = ({ lines = 3 }: SkeletonCardProps) => {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-4 h-4 w-32 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
      <div className="space-y-3">
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={`skeleton-line-${index}`}
            className="h-3 animate-pulse rounded bg-slate-200 dark:bg-slate-700"
            style={{ width: `${100 - index * 12}%` }}
          />
        ))}
      </div>
    </div>
  );
};
