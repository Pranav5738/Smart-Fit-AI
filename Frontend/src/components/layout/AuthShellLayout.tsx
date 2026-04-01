import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import type { ReactNode } from 'react';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';
import { WaveFooter } from '@/components/layout/WaveFooter';

const publicLinks = [
  { to: '/showcase', label: 'Showcase' },
];

export const AuthShellLayout = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated, signOut } = useAuth();
  const { notify } = useToast();
  const location = useLocation();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const settingsPanelRef = useRef<HTMLDivElement | null>(null);
  const settingsButtonRef = useRef<HTMLButtonElement | null>(null);
  const menuPanelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setIsSettingsOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!isSettingsOpen) {
      return;
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (!settingsPanelRef.current?.contains(event.target as Node)) {
        setIsSettingsOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsSettingsOpen(false);
        requestAnimationFrame(() => {
          settingsButtonRef.current?.focus();
        });
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isSettingsOpen]);

  useEffect(() => {
    if (!isSettingsOpen) {
      return;
    }

    requestAnimationFrame(() => {
      const firstFocusable = menuPanelRef.current?.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      firstFocusable?.focus();
    });
  }, [isSettingsOpen]);

  const handleSettingsPanelKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Tab') {
      return;
    }

    const focusableElements = event.currentTarget.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) {
      return;
    }

    const first = focusableElements[0];
    const last = focusableElements[focusableElements.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
      return;
    }

    if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const handleSignOut = () => {
    setIsSettingsOpen(false);
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
          <NavLink to={isAuthenticated ? '/dashboard' : '/signin'} className="flex items-center gap-2.5">
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

                <div ref={settingsPanelRef} className="relative">
                  <button
                    ref={settingsButtonRef}
                    type="button"
                    aria-haspopup="menu"
                    aria-expanded={isSettingsOpen}
                    onClick={() => setIsSettingsOpen((current) => !current)}
                    className="focus-ring rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Settings
                  </button>

                  {isSettingsOpen ? (
                    <div
                      ref={menuPanelRef}
                      role="menu"
                      aria-label="Settings menu"
                      onKeyDown={handleSettingsPanelKeyDown}
                      className="absolute right-0 z-50 mt-2 w-64 rounded-2xl border border-slate-200 bg-white/95 p-3 shadow-card backdrop-blur-xl dark:border-slate-800 dark:bg-slate-900/95"
                    >
                      <div className="mb-3 flex items-center justify-between rounded-xl border border-slate-300 bg-white px-2.5 py-1.5 dark:border-slate-700 dark:bg-slate-900">
                        <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">Theme</span>
                        <ThemeToggle />
                      </div>

                      <button
                        type="button"
                        onClick={handleSignOut}
                        className="focus-ring w-full rounded-xl border border-rose-300 bg-rose-50 px-2.5 py-1.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/20 dark:text-rose-200 dark:hover:bg-rose-950/35"
                      >
                        Sign Out
                      </button>
                    </div>
                  ) : null}
                </div>
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

            {!isAuthenticated ? <ThemeToggle /> : null}
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
