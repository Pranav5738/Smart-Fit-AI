import { lazy, Suspense, type ReactNode } from 'react';
import { AnimatePresence } from 'framer-motion';
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { AuthShellLayout } from '@/components/layout/AuthShellLayout';
import { PageTransition } from '@/components/ui/PageTransition';
import { useAuth } from '@/contexts/AuthContext';
import { AuthProvider } from '@/contexts/AuthContext';
import { ProfileProvider } from '@/contexts/ProfileContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { ToastProvider } from '@/contexts/ToastContext';
import { UserPreferencesProvider } from '@/contexts/UserPreferencesContext';

const ShowcasePage = lazy(() => import('@/pages/ShowcasePage').then((module) => ({ default: module.ShowcasePage })));
const DashboardPage = lazy(() => import('@/pages/DashboardPage').then((module) => ({ default: module.DashboardPage })));
const SignInPage = lazy(() => import('@/pages/SignInPage').then((module) => ({ default: module.SignInPage })));
const RegisterPage = lazy(() => import('@/pages/RegisterPage').then((module) => ({ default: module.RegisterPage })));

const RouteSkeleton = () => {
  return (
    <div className="grid min-h-[60vh] gap-4 md:grid-cols-2 xl:grid-cols-3" aria-hidden="true">
      {Array.from({ length: 6 }).map((_, index) => (
        <div
          key={`route-skeleton-${index}`}
          className="h-32 animate-pulse rounded-3xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
        />
      ))}
    </div>
  );
};

const DashboardLayoutRoute = ({ children }: { children: ReactNode }) => {
  return (
    <AppLayout>
      <PageTransition>{children}</PageTransition>
    </AppLayout>
  );
};

const PublicLayoutRoute = ({ children }: { children: ReactNode }) => {
  return (
    <AuthShellLayout>
      <PageTransition>{children}</PageTransition>
    </AuthShellLayout>
  );
};

const AuthHomeRoute = () => {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Navigate to="/signin" replace />;
};

const ProtectedRoute = () => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/signin" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
};

const AnimatedRoutes = () => {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route
          path="/"
          element={
            <PageTransition>
              <AuthHomeRoute />
            </PageTransition>
          }
        />
        <Route
          path="/showcase"
          element={
            <PublicLayoutRoute>
              <ShowcasePage />
            </PublicLayoutRoute>
          }
        />
        <Route
          path="/signin"
          element={
            <PublicLayoutRoute>
              <SignInPage />
            </PublicLayoutRoute>
          }
        />
        <Route
          path="/sign"
          element={
            <PublicLayoutRoute>
              <SignInPage />
            </PublicLayoutRoute>
          }
        />
        <Route
          path="/login"
          element={
            <PublicLayoutRoute>
              <SignInPage />
            </PublicLayoutRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicLayoutRoute>
              <RegisterPage />
            </PublicLayoutRoute>
          }
        />

        <Route element={<ProtectedRoute />}>
          <Route
            path="/dashboard"
            element={
              <DashboardLayoutRoute>
                <DashboardPage />
              </DashboardLayoutRoute>
            }
          />
          <Route path="/upload" element={<Navigate to="/dashboard" replace />} />
          <Route path="/results" element={<Navigate to="/dashboard" replace />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  );
};

function App() {
  return (
    <ThemeProvider>
      <UserPreferencesProvider>
        <AuthProvider>
          <ProfileProvider>
            <ToastProvider>
              <Suspense fallback={<RouteSkeleton />}>
                <AnimatedRoutes />
              </Suspense>
            </ToastProvider>
          </ProfileProvider>
        </AuthProvider>
      </UserPreferencesProvider>
    </ThemeProvider>
  );
}

export default App;
