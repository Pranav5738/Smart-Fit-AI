import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  configureAccessToken,
  refreshAuthSession,
  registerAuthUser,
  signInAuthUser,
  signOutAuthSession,
  type AuthSessionRecord,
  type AuthTokenRecord,
} from '@/services/api';

interface AuthUser {
  id: string;
  name: string;
  email: string;
  heightCm?: number;
  weightKg?: number;
  createdAt?: string;
  lastLoginAt?: string;
}

interface AuthSessionState {
  user: AuthUser;
  tokens: AuthTokenRecord;
}

interface RestoredAuthSession {
  session: AuthSessionState | null;
  rememberMe: boolean;
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

const isIsoTimestampExpired = (timestamp: string): boolean => {
  const parsed = Date.parse(timestamp);

  if (Number.isNaN(parsed)) {
    return true;
  }

  return parsed <= Date.now();
};

const toAuthSessionState = (record: AuthSessionRecord): AuthSessionState => {
  return {
    user: {
      id: record.user.id,
      name: record.user.name,
      email: record.user.email,
      heightCm: record.user.heightCm,
      weightKg: record.user.weightKg,
      createdAt: record.user.createdAt,
      lastLoginAt: record.user.lastLoginAt,
    },
    tokens: record.tokens,
  };
};

const parseStoredSession = (raw: string): AuthSessionState | null => {
  try {
    const parsed = JSON.parse(raw) as AuthSessionState;

    if (!parsed?.user?.id || !parsed?.user?.email) {
      return null;
    }

    if (!parsed?.tokens?.accessToken || !parsed?.tokens?.refreshToken) {
      return null;
    }

    if (!parsed.tokens.accessExpiresAt || !parsed.tokens.refreshExpiresAt) {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
};

const restoreSession = (): RestoredAuthSession => {
  const persistentRaw = localStorage.getItem(STORAGE_KEYS.persistentSession);
  if (persistentRaw) {
    return {
      session: parseStoredSession(persistentRaw),
      rememberMe: true,
    };
  }

  const sessionRaw = sessionStorage.getItem(STORAGE_KEYS.session);
  if (sessionRaw) {
    return {
      session: parseStoredSession(sessionRaw),
      rememberMe: false,
    };
  }

  return {
    session: null,
    rememberMe: false,
  };
};

const persistSession = (session: AuthSessionState, rememberMe: boolean) => {
  if (rememberMe) {
    localStorage.setItem(STORAGE_KEYS.persistentSession, JSON.stringify(session));
    sessionStorage.removeItem(STORAGE_KEYS.session);
    return;
  }

  sessionStorage.setItem(STORAGE_KEYS.session, JSON.stringify(session));
  localStorage.removeItem(STORAGE_KEYS.persistentSession);
};

const clearSession = () => {
  localStorage.removeItem(STORAGE_KEYS.persistentSession);
  sessionStorage.removeItem(STORAGE_KEYS.session);
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const restoredSession = restoreSession();
  const restoredSessionRef = useRef<RestoredAuthSession>(restoredSession);
  const [session, setSession] = useState<AuthSessionState | null>(restoredSession.session);

  useEffect(() => {
    configureAccessToken(session?.tokens.accessToken || null);
  }, [session?.tokens.accessToken]);

  useEffect(() => {
    let cancelled = false;

    const currentSession = restoredSessionRef.current.session;
    const currentRememberMe = restoredSessionRef.current.rememberMe;

    if (!currentSession) {
      return;
    }

    const clearAllSessionState = () => {
      setSession(null);
      clearSession();
      configureAccessToken(null);
    };

    const tryRefresh = async () => {
      const refreshed = await refreshAuthSession(currentSession.tokens.refreshToken);
      const nextSession = toAuthSessionState(refreshed);
      if (cancelled) {
        return;
      }
      setSession(nextSession);
      persistSession(nextSession, currentRememberMe);
    };

    const hydrate = async () => {
      if (isIsoTimestampExpired(currentSession.tokens.refreshExpiresAt)) {
        clearAllSessionState();
        return;
      }

      if (isIsoTimestampExpired(currentSession.tokens.accessExpiresAt)) {
        try {
          await tryRefresh();
        } catch {
          if (!cancelled) {
            clearAllSessionState();
          }
        }
      }
    };

    void hydrate();

    return () => {
      cancelled = true;
    };
  }, []);

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

    const hasStrongPassword =
      trimmedPassword.length >= 8 &&
      /[a-z]/.test(trimmedPassword) &&
      /[A-Z]/.test(trimmedPassword) &&
      /\d/.test(trimmedPassword) &&
      /[^A-Za-z0-9]/.test(trimmedPassword);

    if (!hasStrongPassword) {
      throw new Error(
        'Password must be at least 8 characters and include upper, lower, number, and symbol.'
      );
    }

    if (payload.heightCm !== undefined && payload.heightCm <= 0) {
      throw new Error('Height must be greater than 0.');
    }

    if (payload.weightKg !== undefined && payload.weightKg <= 0) {
      throw new Error('Weight must be greater than 0.');
    }

    const createdSession = toAuthSessionState(
      await registerAuthUser({
      name: trimmedName,
      email: normalizedEmail,
      password: trimmedPassword,
      heightCm: payload.heightCm,
      weightKg: payload.weightKg,
      })
    );

    setSession(createdSession);
    persistSession(createdSession, true);
  }, []);

  const signIn = useCallback(async (email: string, password: string, rememberMe = false) => {
    const normalizedEmail = normalizeEmail(email);
    const trimmedPassword = password.trim();

    if (!normalizedEmail || !trimmedPassword) {
      throw new Error('Email and password are required.');
    }

    const authenticatedSession = toAuthSessionState(
      await signInAuthUser(normalizedEmail, trimmedPassword)
    );

    setSession(authenticatedSession);
    persistSession(authenticatedSession, rememberMe);
  }, []);

  const signOut = useCallback(() => {
    const refreshToken = session?.tokens.refreshToken;

    setSession(null);
    clearSession();

    if (refreshToken) {
      void signOutAuthSession(refreshToken).catch(() => {
        // Ignore signout API failures during local logout.
      });
    }
  }, [session?.tokens.refreshToken]);

  const value = useMemo(
    () => ({
      user: session?.user || null,
      isAuthenticated: Boolean(session?.user),
      signIn,
      register,
      signOut,
    }),
    [session?.user, signIn, register, signOut]
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
