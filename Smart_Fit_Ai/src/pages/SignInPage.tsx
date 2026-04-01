import { useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';

interface SignInLocationState {
  from?: string;
}

export const SignInPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { notify } = useToast();
  const { signIn, isAuthenticated } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const locationState = location.state as SignInLocationState | undefined;
  const redirectPath = locationState?.from || '/dashboard';

  if (isAuthenticated) {
    return <Navigate to={redirectPath} replace />;
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      signIn(email, password, rememberMe);
      notify('Signed in successfully.', 'success');
      navigate(redirectPath, { replace: true });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to sign in.';
      setErrorMessage(message);
      notify(message, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="relative grid min-h-[70vh] place-items-center py-6">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-[6%] top-[8%] h-40 w-40 rounded-full bg-brand-200/45 blur-3xl dark:bg-brand-700/25" />
        <div className="absolute bottom-[5%] right-[8%] h-44 w-44 rounded-full bg-accent-200/40 blur-3xl dark:bg-accent-700/20" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-lg rounded-3xl border border-brand-100/80 bg-white/95 p-6 shadow-soft dark:border-brand-900/60 dark:bg-slate-900/92"
      >
        <div className="inline-flex rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-brand-700 dark:border-brand-900/60 dark:bg-brand-950/30 dark:text-brand-300">
          Welcome Back
        </div>
        <h1 className="mt-3 text-3xl font-extrabold text-slate-900 dark:text-white">Sign In</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Access your SmartFit AI profile, previous scans, and fit recommendations.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="signin-email" className="mb-1 block text-sm font-semibold text-slate-800 dark:text-slate-200">
              Email
            </label>
            <input
              id="signin-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="focus-ring w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-400"
              placeholder="you@example.com"
              required
            />
          </div>

          <div>
            <label htmlFor="signin-password" className="mb-1 block text-sm font-semibold text-slate-800 dark:text-slate-200">
              Password
            </label>
            <input
              id="signin-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="focus-ring w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-400"
              placeholder="Enter your password"
              required
            />
          </div>

          <div className="flex items-center justify-between gap-3 text-sm">
            <label className="inline-flex items-center gap-2 text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(event) => setRememberMe(event.target.checked)}
                className="focus-ring h-4 w-4"
              />
              <span>Remember me</span>
            </label>

            <button
              type="button"
              onClick={() => notify('Forgot password flow can be connected to your backend reset endpoint.', 'info')}
              className="font-semibold text-accent-700 hover:underline dark:text-accent-300"
            >
              Forgot password?
            </button>
          </div>

          {errorMessage ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-200">
              {errorMessage}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="focus-ring w-full rounded-xl bg-gradient-to-r from-brand-500 to-accent-500 px-4 py-2.5 text-sm font-semibold text-white shadow-soft transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? 'Signing In...' : 'Sign In'}
          </button>
        </form>

        <p className="mt-5 text-sm text-slate-600 dark:text-slate-300">
          New to SmartFit AI?{' '}
          <Link
            to="/register"
            className="font-semibold text-brand-700 hover:underline dark:text-brand-300"
          >
            Create an account
          </Link>
        </p>
      </motion.div>
    </section>
  );
};
