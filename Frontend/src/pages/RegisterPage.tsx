import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';

export const RegisterPage = () => {
  const navigate = useNavigate();
  const { notify } = useToast();
  const { register, isAuthenticated } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [heightCm, setHeightCm] = useState('');
  const [weightKg, setWeightKg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (password !== confirmPassword) {
      const mismatchMessage = 'Passwords do not match.';
      setErrorMessage(mismatchMessage);
      notify(mismatchMessage, 'error');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await register({
        name,
        email,
        password,
        heightCm: heightCm ? Number(heightCm) : undefined,
        weightKg: weightKg ? Number(weightKg) : undefined,
      });
      notify('Account created successfully.', 'success');
      navigate('/dashboard');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to create account.';
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
        className="w-full max-w-xl rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900/[0.92]"
      >
        <div className="inline-flex rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-brand-700 dark:border-brand-900/60 dark:bg-brand-950/30 dark:text-brand-300">
          Create Account
        </div>
        <h1 className="mt-3 text-3xl font-extrabold text-slate-900 dark:text-white">Register</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Set up your SmartFit AI account to track measurement history and recommendations.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="register-name" className="mb-1 block text-sm font-semibold text-slate-800 dark:text-slate-200">
              Full Name
            </label>
            <input
              id="register-name"
              type="text"
              autoComplete="name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="focus-ring w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-400"
              placeholder="Alex Johnson"
              required
            />
          </div>

          <div>
            <label htmlFor="register-email" className="mb-1 block text-sm font-semibold text-slate-800 dark:text-slate-200">
              Email
            </label>
            <input
              id="register-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="focus-ring w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-400"
              placeholder="you@example.com"
              required
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="register-password" className="mb-1 block text-sm font-semibold text-slate-800 dark:text-slate-200">
                Password
              </label>
              <input
                id="register-password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="focus-ring w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-400"
                placeholder="8+ chars with upper, lower, number, symbol"
                required
              />
            </div>

            <div>
              <label htmlFor="register-confirm-password" className="mb-1 block text-sm font-semibold text-slate-800 dark:text-slate-200">
                Confirm Password
              </label>
              <input
                id="register-confirm-password"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="focus-ring w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-400"
                placeholder="Re-enter password"
                required
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="register-height" className="mb-1 block text-sm font-semibold text-slate-800 dark:text-slate-200">
                Height (cm) - optional
              </label>
              <input
                id="register-height"
                type="number"
                min={0}
                step="0.1"
                value={heightCm}
                onChange={(event) => setHeightCm(event.target.value)}
                className="focus-ring w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-400"
                placeholder="172"
              />
            </div>

            <div>
              <label htmlFor="register-weight" className="mb-1 block text-sm font-semibold text-slate-800 dark:text-slate-200">
                Weight (kg) - optional
              </label>
              <input
                id="register-weight"
                type="number"
                min={0}
                step="0.1"
                value={weightKg}
                onChange={(event) => setWeightKg(event.target.value)}
                className="focus-ring w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-400"
                placeholder="68"
              />
            </div>
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
            {isSubmitting ? 'Creating Account...' : 'Register'}
          </button>
        </form>

        <p className="mt-5 text-sm text-slate-600 dark:text-slate-300">
          Already have an account?{' '}
          <Link
            to="/signin"
            className="font-semibold text-brand-700 hover:underline dark:text-brand-300"
          >
            Sign in here
          </Link>
        </p>
      </motion.div>
    </section>
  );
};
