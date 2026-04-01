import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { registerAuthUser, signInAuthUser } from '@/services/api';

interface AuthUser {
  id: string;
  name: string;
  email: string;
  heightCm?: number;
  weightKg?: number;
  createdAt?: string;
  lastLoginAt?: string;
}

interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  heightCm?: number;
  weightKg?: number;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  signIn: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEYS = {
  persistentSession: 'smartfit-auth-session',
  session: 'smartfit-auth-session-storage',
};

const normalizeEmail = (email: string): string => email.trim().toLowerCase();

const restoreSession = (): AuthUser | null => {
  const raw =
    localStorage.getItem(STORAGE_KEYS.persistentSession) ||
    sessionStorage.getItem(STORAGE_KEYS.session);

  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as AuthUser;

    if (!parsed?.id || !parsed?.email) {
      return null;
    }

    return {
      id: parsed.id,
      name: parsed.name,
      email: parsed.email,
      heightCm: parsed.heightCm,
      weightKg: parsed.weightKg,
      createdAt: parsed.createdAt,
      lastLoginAt: parsed.lastLoginAt,
    };
  } catch {
    return null;
  }
};

const persistSession = (user: AuthUser, rememberMe: boolean) => {
  if (rememberMe) {
    localStorage.setItem(STORAGE_KEYS.persistentSession, JSON.stringify(user));
    sessionStorage.removeItem(STORAGE_KEYS.session);
    return;
  }

  sessionStorage.setItem(STORAGE_KEYS.session, JSON.stringify(user));
  localStorage.removeItem(STORAGE_KEYS.persistentSession);
};

const clearSession = () => {
  localStorage.removeItem(STORAGE_KEYS.persistentSession);
  sessionStorage.removeItem(STORAGE_KEYS.session);
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(restoreSession);

  const register = useCallback(async (payload: RegisterPayload) => {
    const trimmedName = payload.name.trim();
    const normalizedEmail = normalizeEmail(payload.email);
    const trimmedPassword = payload.password.trim();

    if (!trimmedName) {
      throw new Error('Name is required.');
    }

    if (!normalizedEmail) {
      throw new Error('Email is required.');
    }

    if (trimmedPassword.length < 6) {
      throw new Error('Password must be at least 6 characters.');
    }

    if (payload.heightCm !== undefined && payload.heightCm <= 0) {
      throw new Error('Height must be greater than 0.');
    }

    if (payload.weightKg !== undefined && payload.weightKg <= 0) {
      throw new Error('Weight must be greater than 0.');
    }

    const createdUser = await registerAuthUser({
      name: trimmedName,
      email: normalizedEmail,
      password: trimmedPassword,
      heightCm: payload.heightCm,
      weightKg: payload.weightKg,
    });

    const nextUser: AuthUser = {
      id: createdUser.id,
      name: createdUser.name,
      email: createdUser.email,
      heightCm: createdUser.heightCm,
      weightKg: createdUser.weightKg,
      createdAt: createdUser.createdAt,
      lastLoginAt: createdUser.lastLoginAt,
    };

    setUser(nextUser);
    persistSession(nextUser, true);
  }, []);

  const signIn = useCallback(async (email: string, password: string, rememberMe = false) => {
    const normalizedEmail = normalizeEmail(email);
    const trimmedPassword = password.trim();

    if (!normalizedEmail || !trimmedPassword) {
      throw new Error('Email and password are required.');
    }

    const authenticatedUser = await signInAuthUser(normalizedEmail, trimmedPassword);

    const nextUser: AuthUser = {
      id: authenticatedUser.id,
      name: authenticatedUser.name,
      email: authenticatedUser.email,
      heightCm: authenticatedUser.heightCm,
      weightKg: authenticatedUser.weightKg,
      createdAt: authenticatedUser.createdAt,
      lastLoginAt: authenticatedUser.lastLoginAt,
    };

    setUser(nextUser);
    persistSession(nextUser, rememberMe);
  }, []);

  const signOut = useCallback(() => {
    setUser(null);
    clearSession();
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      signIn,
      register,
      signOut,
    }),
    [user, signIn, register, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }

  return context;
};
