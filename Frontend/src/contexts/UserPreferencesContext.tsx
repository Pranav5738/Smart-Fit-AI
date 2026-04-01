import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { LanguageCode, UnitSystem } from '@/types/smartfit';

interface UserPreferencesContextValue {
  language: LanguageCode;
  unitSystem: UnitSystem;
  highContrast: boolean;
  setLanguage: (language: LanguageCode) => void;
  setUnitSystem: (unitSystem: UnitSystem) => void;
  toggleHighContrast: () => void;
  t: (english: string, spanish?: string) => string;
}

const UserPreferencesContext = createContext<UserPreferencesContextValue | undefined>(undefined);

const STORAGE_KEYS = {
  language: 'smartfit-language',
  unitSystem: 'smartfit-unit-system',
  highContrast: 'smartfit-high-contrast',
};

const getStoredLanguage = (): LanguageCode => {
  const stored = localStorage.getItem(STORAGE_KEYS.language);
  return stored === 'es' ? 'es' : 'en';
};

const getStoredUnitSystem = (): UnitSystem => {
  const stored = localStorage.getItem(STORAGE_KEYS.unitSystem);
  return stored === 'cm' ? 'cm' : 'in';
};

const getStoredHighContrast = (): boolean => {
  return localStorage.getItem(STORAGE_KEYS.highContrast) === 'true';
};

export const UserPreferencesProvider = ({ children }: { children: ReactNode }) => {
  const [language, setLanguage] = useState<LanguageCode>(getStoredLanguage);
  const [unitSystem, setUnitSystem] = useState<UnitSystem>(getStoredUnitSystem);
  const [highContrast, setHighContrast] = useState<boolean>(getStoredHighContrast);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.language, language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.unitSystem, unitSystem);
  }, [unitSystem]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.highContrast, String(highContrast));
    document.documentElement.classList.toggle('contrast', highContrast);
  }, [highContrast]);

  const toggleHighContrast = useCallback(() => {
    setHighContrast((current) => !current);
  }, []);

  const t = useCallback(
    (english: string, spanish?: string) => {
      if (language === 'es') {
        return spanish || english;
      }

      return english;
    },
    [language]
  );

  const value = useMemo(
    () => ({
      language,
      unitSystem,
      highContrast,
      setLanguage,
      setUnitSystem,
      toggleHighContrast,
      t,
    }),
    [language, unitSystem, highContrast, toggleHighContrast, t]
  );

  return <UserPreferencesContext.Provider value={value}>{children}</UserPreferencesContext.Provider>;
};

export const useUserPreferences = (): UserPreferencesContextValue => {
  const context = useContext(UserPreferencesContext);

  if (!context) {
    throw new Error('useUserPreferences must be used inside UserPreferencesProvider');
  }

  return context;
};
