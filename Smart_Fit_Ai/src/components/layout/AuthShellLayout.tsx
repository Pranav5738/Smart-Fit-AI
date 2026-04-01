import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import type { ReactNode } from 'react';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';
import { WaveFooter } from '@/components/layout/WaveFooter';

const publicLinks = [
  { to: '/', label: 'Start' },
  { to: '/showcase', label: 'Showcase' },
];

export const AuthShellLayout = ({ children }: { children: ReactNode }) => {
  const { user, isAuthenticated, signOut } = useAuth();
  const { notify } = useToast();

  const handleSignOut = () => {
    signOut();
    notify('Signed out successfully.', 'info');
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-[-11rem] top-[-13rem] h-[22rem] w-[22rem] rounded-full bg-brand-200/50 blur-3xl dark:bg-brand-800/20" />
        <div className="absolute bottom-[-11rem] right-[-9rem] h-[24rem] w-[24rem] rounded-full bg-accent-200/40 blur-3xl dark:bg-accent-700/20" />
      </div>

      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/85 backdrop-blur-xl dark:border-slate-800/70 dark:bg-slate-900/75">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <NavLink to={isAuthenticated ? '/dashboard' : '/'} className="flex items-center gap-2.5">
            <img
              src="/smartfit-logo-mark.svg"
              alt="SmartFit AI"
              className="h-9 w-9 rounded-xl border border-sky-200/60 object-cover shadow-soft dark:border-sky-700/40"
            />
            <div>
              <p className="font-heading text-base font-bold">SmartFit AI</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Auth & Product Hub</p>
            </div>
          </NavLink>

          <div className="flex items-center gap-2">
            <nav className="hidden items-center gap-1 rounded-2xl border border-slate-200 bg-white/80 p-1 shadow-card dark:border-slate-800 dark:bg-slate-900/80 md:flex">
              {publicLinks.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) =>
                    `focus-ring rounded-xl px-3 py-1.5 text-sm font-semibold transition ${
                      isActive
                        ? 'bg-brand-600 text-white'
                        : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                    }`
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>

            {isAuthenticated ? (
              <>
                <NavLink
                  to="/dashboard"
                  className={({ isActive }) =>
                    `focus-ring rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
                      isActive
                        ? 'border-brand-600 bg-brand-600 text-white'
                        : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'
                    }`
                  }
                >
                  Dashboard
                </NavLink>
                <span className="hidden rounded-xl bg-brand-50 px-2.5 py-1.5 text-xs font-semibold text-brand-700 dark:bg-brand-950/30 dark:text-brand-200 sm:inline-flex">
                  {user?.name}
                </span>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="focus-ring rounded-xl border border-rose-300 bg-rose-50 px-2.5 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/20 dark:text-rose-200 dark:hover:bg-rose-950/35"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <NavLink
                  to="/signin"
                  className={({ isActive }) =>
                    `focus-ring rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
                      isActive
                        ? 'border-brand-600 bg-brand-600 text-white'
                        : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'
                    }`
                  }
                >
                  Sign In
                </NavLink>
                <NavLink
                  to="/register"
                  className={({ isActive }) =>
                    `focus-ring rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
                      isActive
                        ? 'border-brand-600 bg-brand-600 text-white'
                        : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'
                    }`
                  }
                >
                  Register
                </NavLink>
              </>
            )}

            <ThemeToggle />
          </div>
        </div>
      </header>

      <motion.main
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6"
      >
        {children}
      </motion.main>

      <WaveFooter />
    </div>
  );
};
