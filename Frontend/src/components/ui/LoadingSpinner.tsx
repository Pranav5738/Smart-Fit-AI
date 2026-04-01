import { motion } from 'framer-motion';

export const LoadingSpinner = () => {
  return (
    <div className="relative grid h-16 w-16 place-items-center">
      <motion.span
        className="absolute h-16 w-16 rounded-full border-4 border-brand-200 dark:border-brand-900"
        animate={{ scale: [1, 1.15, 1], opacity: [0.7, 0.25, 0.7] }}
        transition={{ repeat: Infinity, duration: 1.8 }}
      />
      <motion.span
        className="absolute h-11 w-11 rounded-full border-4 border-brand-600 border-t-transparent"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, ease: 'linear', duration: 0.9 }}
      />
    </div>
  );
};
