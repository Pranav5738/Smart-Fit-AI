import { motion } from 'framer-motion';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export const ProcessingState = () => {
  return (
    <motion.div
      className="fixed inset-0 z-50 grid place-items-center bg-slate-950/45 px-4 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <motion.div
        initial={{ y: 16, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 16, opacity: 0 }}
        className="flex w-full max-w-sm flex-col items-center gap-4 rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-card dark:border-slate-700 dark:bg-slate-900"
      >
        <LoadingSpinner />
        <h3 className="font-heading text-xl font-bold">Analyzing your body measurements...</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          SmartFit AI is extracting dimensions, predicting your size, and preparing brand mapping.
        </p>
      </motion.div>
    </motion.div>
  );
};
