import { motion } from 'framer-motion';
import { useTheme } from '@/contexts/ThemeContext';

export const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <motion.button
      whileTap={{ scale: 0.94 }}
      onClick={toggleTheme}
      className="focus-ring rounded-xl border border-slate-200/80 bg-white/90 p-2 text-slate-700 transition hover:border-brand-300 hover:text-brand-700 dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-200 dark:hover:border-brand-700 dark:hover:text-brand-300"
      aria-label="Toggle dark mode"
      aria-pressed={theme === 'dark'}
      type="button"
    >
      {theme === 'light' ? (
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M12 3v2.5M12 18.5V21M4.93 4.93l1.76 1.76M17.31 17.31l1.76 1.76M3 12h2.5M18.5 12H21M4.93 19.07l1.76-1.76M17.31 6.69l1.76-1.76" />
          <circle cx="12" cy="12" r="4" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M21 12.4A8.4 8.4 0 1 1 11.6 3a6.8 6.8 0 1 0 9.4 9.4Z" />
        </svg>
      )}
    </motion.button>
  );
};
