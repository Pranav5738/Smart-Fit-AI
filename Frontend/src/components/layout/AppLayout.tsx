import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useProfiles } from '@/contexts/ProfileContext';
import { useUserPreferences } from '@/contexts/UserPreferencesContext';
import { useToast } from '@/contexts/ToastContext';
import { WaveFooter } from '@/components/layout/WaveFooter';

const links = [
  { to: '/showcase', label: 'Showcase' },
  { to: '/dashboard', label: 'Dashboard' },
];

export const AppLayout = ({ children }: { children: ReactNode }) => {
  const { user, isAuthenticated, signOut } = useAuth();
  const { profiles, activeProfileId, setActiveProfileId, createProfile, deleteProfile } = useProfiles();
  const {
    language,
    unitSystem,
    highContrast,
    setLanguage,
    setUnitSystem,
    toggleHighContrast,
    t,
  } = useUserPreferences();
  const { notify } = useToast();
  const location = useLocation();
  const visibleLinks = isAuthenticated ? links : links.filter((link) => link.to !== '/dashboard');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const settingsPanelRef = useRef<HTMLDivElement | null>(null);
  const settingsButtonRef = useRef<HTMLButtonElement | null>(null);
  const firstSettingsControlRef = useRef<HTMLSelectElement | null>(null);

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
      firstSettingsControlRef.current?.focus();
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

  const handleCreateProfile = async () => {
    const profileName = window.prompt(t('Name your new profile', 'Nombra tu nuevo perfil'));

    if (!profileName) {
      return;
    }

    try {
      await createProfile(profileName);
      notify(t('Profile created.', 'Perfil creado.'), 'success');
    } catch {
      notify(t('Unable to create profile right now.', 'No se pudo crear el perfil.'), 'error');
    }
  };

  const handleDeleteProfile = async () => {
    const selectedProfile = profiles.find((profile) => profile.id === activeProfileId);

    if (!selectedProfile) {
      return;
    }

    if (profiles.length <= 1) {
      notify(t('At least one profile is required.', 'Se requiere al menos un perfil.'), 'info');
      return;
    }

    const confirmed = window.confirm(
      t(
        `Delete profile "${selectedProfile.name}"? This action cannot be undone.`,
        `¿Eliminar el perfil "${selectedProfile.name}"? Esta accion no se puede deshacer.`
      )
    );

    if (!confirmed) {
      return;
    }

    try {
      await deleteProfile(selectedProfile.id);
      notify(t('Profile deleted.', 'Perfil eliminado.'), 'success');
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : t('Unable to delete profile right now.', 'No se pudo eliminar el perfil.');
      notify(message, 'error');
    }
  };

  const handleSignOut = () => {
    setIsSettingsOpen(false);
    signOut();
    notify(t('Signed out successfully.', 'Sesion cerrada correctamente.'), 'info');
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <a
        href="#main-content"
        className="focus-ring absolute left-3 top-3 z-[70] -translate-y-16 rounded-xl bg-brand-700 px-3 py-2 text-sm font-semibold text-white transition focus:translate-y-0"
      >
        {t('Skip to content', 'Saltar al contenido')}
      </a>

      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-[-10rem] top-[-14rem] h-[24rem] w-[24rem] rounded-full bg-brand-200/50 blur-3xl dark:bg-brand-800/30" />
        <div className="absolute bottom-[-14rem] right-[-10rem] h-[26rem] w-[26rem] rounded-full bg-accent-200/50 blur-3xl dark:bg-accent-700/20" />
      </div>

      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-xl dark:border-slate-800/80 dark:bg-slate-900/70">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
          <NavLink to={isAuthenticated ? '/dashboard' : '/'} className="flex items-center gap-3">
            <img
              src="/smartfit-logo-mark.svg"
              alt="SmartFit AI"
              className="h-9 w-9 rounded-xl border border-sky-200/60 object-cover shadow-soft dark:border-sky-700/40"
            />
            <div>
              <p className="font-heading text-lg font-bold">SmartFit AI</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">AI-Powered Size Intelligence</p>
            </div>
          </NavLink>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <nav className="hidden items-center gap-1 rounded-2xl border border-slate-200 bg-white/80 p-1 shadow-card dark:border-slate-800 dark:bg-slate-900/80 md:flex">
              {visibleLinks.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  aria-label={link.label}
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
              <div ref={settingsPanelRef} className="relative">
                <button
                  ref={settingsButtonRef}
                  type="button"
                  aria-haspopup="menu"
                  aria-expanded={isSettingsOpen}
                  onClick={() => setIsSettingsOpen((current) => !current)}
                  className="focus-ring rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  {t('Settings', 'Ajustes')}
                </button>

                {isSettingsOpen ? (
                  <div
                    role="menu"
                    aria-label={t('Settings menu', 'Menu de ajustes')}
                    onKeyDown={handleSettingsPanelKeyDown}
                    className="absolute right-0 z-50 mt-2 w-80 rounded-2xl border border-slate-200 bg-white/95 p-3 shadow-card backdrop-blur-xl dark:border-slate-800 dark:bg-slate-900/95"
                  >
                    <div className="mb-3 flex items-center justify-between rounded-xl border border-brand-200 bg-brand-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/85">
                      <div>
                        <p className="text-sm font-semibold text-brand-800 dark:text-slate-100">{user?.name}</p>
                        <p className="text-xs text-brand-700/80 dark:text-slate-300">{user?.email}</p>
                      </div>
                      <span className="rounded-full border border-brand-300 bg-white px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-brand-700 dark:border-brand-700 dark:bg-slate-900 dark:text-brand-300">
                        Active
                      </span>
                    </div>

                    <div className="space-y-3 text-xs">
                      <div>
                        <label className="mb-1 block font-semibold text-slate-600 dark:text-slate-300">
                          {t('Profile', 'Perfil')}
                        </label>
                        <select
                          ref={firstSettingsControlRef}
                          value={activeProfileId}
                          onChange={(event) => setActiveProfileId(event.target.value)}
                          className="focus-ring w-full rounded-xl border border-slate-300 bg-white px-2 py-1.5 font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                        >
                          {profiles.map((profile) => (
                            <option key={profile.id} value={profile.id}>
                              {profile.name}
                            </option>
                          ))}
                        </select>
                      </div>

                      <button
                        type="button"
                        onClick={handleCreateProfile}
                        className="focus-ring w-full rounded-xl border border-slate-300 bg-white px-2.5 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                      >
                        {t('New Profile', 'Nuevo perfil')}
                      </button>

                      <button
                        type="button"
                        onClick={handleDeleteProfile}
                        disabled={profiles.length <= 1}
                        className="focus-ring w-full rounded-xl border border-rose-300 bg-rose-50 px-2.5 py-1.5 font-semibold text-rose-700 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-rose-900/60 dark:bg-rose-950/20 dark:text-rose-200 dark:hover:bg-rose-950/35"
                      >
                        {t('Delete Profile', 'Eliminar perfil')}
                      </button>

                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="mb-1 block font-semibold text-slate-600 dark:text-slate-300">
                            {t('Language', 'Idioma')}
                          </label>
                          <select
                            value={language}
                            onChange={(event) => setLanguage(event.target.value as 'en' | 'es')}
                            className="focus-ring w-full rounded-xl border border-slate-300 bg-white px-2 py-1.5 font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                          >
                            <option value="en">EN</option>
                            <option value="es">ES</option>
                          </select>
                        </div>

                        <div>
                          <label className="mb-1 block font-semibold text-slate-600 dark:text-slate-300">
                            {t('Units', 'Unidades')}
                          </label>
                          <select
                            value={unitSystem}
                            onChange={(event) => setUnitSystem(event.target.value as 'in' | 'cm')}
                            className="focus-ring w-full rounded-xl border border-slate-300 bg-white px-2 py-1.5 font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                          >
                            <option value="in">IN</option>
                            <option value="cm">CM</option>
                          </select>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={toggleHighContrast}
                        className="focus-ring w-full rounded-xl border border-slate-300 bg-white px-2.5 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
                      >
                        {highContrast ? t('Contrast On', 'Contraste alto') : t('Contrast Off', 'Contraste normal')}
                      </button>

                      <div className="flex items-center justify-between rounded-xl border border-slate-300 bg-white px-2.5 py-1.5 dark:border-slate-700 dark:bg-slate-900">
                        <span className="font-semibold text-slate-700 dark:text-slate-200">{t('Theme', 'Tema')}</span>
                        <ThemeToggle />
                      </div>

                      <button
                        type="button"
                        onClick={handleSignOut}
                        className="focus-ring w-full rounded-xl border border-rose-300 bg-rose-50 px-2.5 py-1.5 font-semibold text-rose-700 transition hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/20 dark:text-rose-200 dark:hover:bg-rose-950/35"
                      >
                        {t('Sign Out', 'Cerrar sesion')}
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <>
                <NavLink
                  to="/signin"
                  className={({ isActive }) =>
                    `focus-ring rounded-xl border px-2.5 py-1.5 text-xs font-semibold transition ${
                      isActive
                        ? 'border-brand-600 bg-brand-600 text-white'
                        : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'
                    }`
                  }
                >
                  {t('Sign In', 'Iniciar sesion')}
                </NavLink>
                <NavLink
                  to="/register"
                  className={({ isActive }) =>
                    `focus-ring rounded-xl border px-2.5 py-1.5 text-xs font-semibold transition ${
                      isActive
                        ? 'border-brand-600 bg-brand-600 text-white'
                        : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'
                    }`
                  }
                >
                  {t('Register', 'Registrarse')}
                </NavLink>

                <ThemeToggle />
              </>
            )}
          </div>
        </div>
      </header>

      <motion.main
        id="main-content"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
      >
        {children}
      </motion.main>

      <WaveFooter />
    </div>
  );
};
