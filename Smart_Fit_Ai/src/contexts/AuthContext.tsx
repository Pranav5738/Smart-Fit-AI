import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

interface AuthUser {
  id: string;
  name: string;
  email: string;
  heightCm?: number;
  weightKg?: number;
}

interface StoredUser extends AuthUser {
  password: string;
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
  signIn: (email: string, password: string, rememberMe?: boolean) => void;
  register: (payload: RegisterPayload) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEYS = {
  users: 'smartfit-auth-users',
  persistentSession: 'smartfit-auth-session',
  session: 'smartfit-auth-session-storage',
};

const normalizeEmail = (email: string): string => email.trim().toLowerCase();

const readUsers = (): StoredUser[] => {
  const raw = localStorage.getItem(STORAGE_KEYS.users);

  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw) as StoredUser[];

    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed;
  } catch {
    return [];
  }
};

const writeUsers = (users: StoredUser[]) => {
  localStorage.setItem(STORAGE_KEYS.users, JSON.stringify(users));
};

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
    };
  } catch {
    return null;
  }
};

const generateUserId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `user-${Date.now()}-${Math.round(Math.random() * 1000)}`;
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

  const register = useCallback((payload: RegisterPayload) => {
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

    const users = readUsers();

    if (users.some((existingUser) => normalizeEmail(existingUser.email) === normalizedEmail)) {
      throw new Error('An account already exists with this email.');
    }

    const newUser: StoredUser = {
      id: generateUserId(),
      name: trimmedName,
      email: normalizedEmail,
      password: trimmedPassword,
      heightCm: payload.heightCm,
      weightKg: payload.weightKg,
    };

    writeUsers([newUser, ...users]);

    const nextUser: AuthUser = {
      id: newUser.id,
      name: newUser.name,
      email: newUser.email,
      heightCm: newUser.heightCm,
      weightKg: newUser.weightKg,
    };

    setUser(nextUser);
    persistSession(nextUser, true);
  }, []);

  const signIn = useCallback((email: string, password: string, rememberMe = false) => {
    const normalizedEmail = normalizeEmail(email);
    const trimmedPassword = password.trim();

    if (!normalizedEmail || !trimmedPassword) {
      throw new Error('Email and password are required.');
    }

    const users = readUsers();
    const matchedUser = users.find(
      (existingUser) =>
        normalizeEmail(existingUser.email) === normalizedEmail &&
        existingUser.password === trimmedPassword
    );

    if (!matchedUser) {
      throw new Error('Invalid email or password.');
    }

    const nextUser: AuthUser = {
      id: matchedUser.id,
      name: matchedUser.name,
      email: matchedUser.email,
      heightCm: matchedUser.heightCm,
      weightKg: matchedUser.weightKg,
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
