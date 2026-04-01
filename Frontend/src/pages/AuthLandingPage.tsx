import { useMemo, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { WaveFooter } from '@/components/layout/WaveFooter';

type AuthMode = 'signin' | 'register';

export const AuthLandingPage = () => {
  const navigate = useNavigate();
  const { signIn, register } = useAuth();
  const { notify } = useToast();

  const [mode, setMode] = useState<AuthMode>('signin');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [signinEmail, setSigninEmail] = useState('');
  const [signinPassword, setSigninPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);

  const [registerName, setRegisterName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const featureItems = useMemo(
    () => ['AI Measurement', 'Smart Size Prediction', 'Virtual Try-On', 'Brand Mapping'],
    []
  );

  const handleSignIn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await signIn(signinEmail, signinPassword, rememberMe);
      notify('Signed in successfully.', 'success');
      navigate('/dashboard');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to sign in.';
      setErrorMessage(message);
      notify(message, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegister = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (registerPassword !== registerConfirmPassword) {
      const mismatchMessage = 'Passwords do not match.';
      setErrorMessage(mismatchMessage);
      notify(mismatchMessage, 'error');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await register({
        name: registerName,
        email: registerEmail,
        password: registerPassword,
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
    <div className="relative min-h-screen overflow-hidden bg-slate-50 px-4 pb-8 pt-6 text-slate-900 dark:bg-[#05091b] dark:text-slate-100 sm:px-6 lg:px-10">
      <div className="pointer-events-none absolute inset-0 -z-20 bg-[radial-gradient(ellipse_at_top_left,rgba(125,211,252,0.34),transparent_45%),radial-gradient(ellipse_at_bottom_right,rgba(96,165,250,0.22),transparent_50%),linear-gradient(140deg,#eff6ff_0%,#f8fafc_46%,#e2e8f0_100%)] dark:bg-[radial-gradient(ellipse_at_top_left,rgba(56,189,248,0.28),transparent_45%),radial-gradient(ellipse_at_bottom_right,rgba(37,99,235,0.22),transparent_50%),linear-gradient(140deg,#040816_0%,#070f28_46%,#0b1d45_100%)]" />
      <div className="pointer-events-none absolute inset-0 -z-10 opacity-40 [background-image:radial-gradient(rgba(71,85,105,0.24)_1px,transparent_1px)] [background-size:24px_24px] dark:opacity-70 dark:[background-image:radial-gradient(rgba(191,219,254,0.6)_1px,transparent_1px)]" />

      <header className="mx-auto w-full max-w-7xl rounded-2xl border border-slate-200/80 bg-white/85 p-2 shadow-card backdrop-blur-xl dark:border-sky-300/30 dark:bg-slate-950/55 dark:shadow-[0_0_0_1px_rgba(59,130,246,0.18),0_20px_70px_rgba(10,26,70,0.55)]">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white/70 px-4 py-2.5 dark:border-slate-700/70 dark:bg-slate-900/60">
          <div className="flex items-center gap-3">
            <img
              src="/smartfit-logo-mark.svg"
              alt="SmartFit AI"
              className="h-9 w-9 rounded-xl border border-sky-200/60 object-cover shadow-soft dark:border-sky-700/40"
            />
            <p className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">SmartFit AI</p>
          </div>

          <nav className="hidden items-center gap-8 text-base text-slate-600 lg:flex dark:text-slate-300">
            <a href="#features" className="transition hover:text-slate-900 dark:hover:text-white">
              Features
            </a>
            <Link to="/showcase" className="transition hover:text-slate-900 dark:hover:text-white">
              Showcase
            </Link>
            <a href="#how-it-works" className="transition hover:text-slate-900 dark:hover:text-white">
              How It Works
            </a>
          </nav>

          <div className="flex items-center gap-2.5">
            <Link
              to="/showcase"
              className="hidden rounded-xl px-3 py-2 text-sm font-semibold text-brand-700 transition hover:bg-slate-100 dark:text-sky-300 dark:hover:bg-white/5 sm:inline-flex"
            >
              Explore Live Demo
            </Link>
            <button
              type="button"
              onClick={() => setMode('signin')}
              className="focus-ring rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 transition hover:bg-slate-100 dark:border-sky-300/40 dark:bg-slate-900/70 dark:text-white dark:hover:bg-slate-800"
            >
              Sign In
            </button>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <div className="mx-auto mt-10 grid w-full max-w-7xl items-center gap-8 lg:grid-cols-[1.35fr_0.95fr] lg:gap-10">
        <motion.section
          initial={{ opacity: 0, x: -24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.55 }}
          className="space-y-6"
        >
          <div>
            <h1 className="text-balance text-5xl font-black leading-[1.04] text-slate-900 dark:text-white sm:text-6xl lg:text-7xl">
              Find Your Perfect Fit
              <br />
              <span className="bg-gradient-to-r from-cyan-600 via-brand-600 to-blue-700 bg-clip-text text-transparent dark:from-cyan-300 dark:via-sky-300 dark:to-blue-300">
                Powered by AI Intelligence
              </span>
            </h1>
            <p className="mt-6 max-w-3xl text-lg leading-relaxed text-slate-600 dark:text-slate-300">
              Start your fit journey securely and explore how SmartFit AI transforms a single image into personalized size recommendations with cutting-edge AI intelligence, virtual try-on capabilities, and brand-specific mappings.
            </p>
          </div>

          <ul id="features" className="grid gap-3 text-2xl font-medium sm:grid-cols-2">
            {featureItems.map((item) => (
              <li key={item} className="flex items-center gap-3 text-slate-900 dark:text-slate-100">
                <span className="grid h-8 w-8 place-items-center rounded-full bg-sky-100 text-brand-700 shadow-[0_0_0_1px_rgba(14,116,144,0.2)] dark:bg-sky-500/25 dark:text-sky-300 dark:shadow-[0_0_20px_rgba(56,189,248,0.3)]">
                  ✓
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ul>

        </motion.section>

        <motion.section
          initial={{ opacity: 0, x: 26 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.55, delay: 0.08 }}
          className="relative"
        >
          <div className="absolute -inset-0.5 -z-10 rounded-[2rem] bg-[linear-gradient(135deg,rgba(34,211,238,0.3),rgba(59,130,246,0.24),rgba(14,165,233,0.2))] blur-md dark:bg-[linear-gradient(135deg,rgba(34,211,238,0.6),rgba(59,130,246,0.45),rgba(14,165,233,0.38))]" />
          <div className="rounded-[2rem] border border-slate-200 bg-white/95 p-6 shadow-card backdrop-blur-xl dark:border-sky-300/40 dark:bg-[linear-gradient(170deg,rgba(10,18,44,0.88),rgba(17,25,58,0.82)_58%,rgba(10,28,74,0.9))] dark:shadow-[0_25px_90px_rgba(41,76,173,0.45)] sm:p-7">
            <div className="grid grid-cols-2 rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-900/70">
              <button
                type="button"
                onClick={() => {
                  setMode('signin');
                  setErrorMessage(null);
                }}
                className={`focus-ring rounded-lg px-3 py-2.5 text-base font-semibold transition ${
                  mode === 'signin'
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-[0_0_22px_rgba(56,189,248,0.35)]'
                    : 'text-slate-600 hover:bg-white dark:text-slate-300 dark:hover:bg-white/5'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode('register');
                  setErrorMessage(null);
                }}
                className={`focus-ring rounded-lg px-3 py-2.5 text-base font-semibold transition ${
                  mode === 'register'
                    ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-[0_0_22px_rgba(59,130,246,0.35)]'
                    : 'text-slate-600 hover:bg-white dark:text-slate-300 dark:hover:bg-white/5'
                }`}
              >
                Register
              </button>
            </div>

            <h2 className="mt-6 text-4xl font-extrabold text-slate-900 dark:text-white">Access SmartFit AI</h2>
            <p className="mt-2 text-base text-slate-600 dark:text-slate-300">
              {mode === 'signin'
                ? 'Sign in to access your dashboard and personalize your fit journey.'
                : 'Create an account to start your personalized fit intelligence journey.'}
            </p>

            {mode === 'signin' ? (
              <form onSubmit={handleSignIn} className="mt-5 space-y-3.5">
                <input
                  type="email"
                  autoComplete="email"
                  value={signinEmail}
                  onChange={(event) => setSigninEmail(event.target.value)}
                  placeholder="Email"
                  className="focus-ring w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base text-slate-900 placeholder:text-slate-400 dark:border-slate-600 dark:bg-slate-950/70 dark:text-white"
                  required
                />
                <input
                  type="password"
                  autoComplete="current-password"
                  value={signinPassword}
                  onChange={(event) => setSigninPassword(event.target.value)}
                  placeholder="Password"
                  className="focus-ring w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base text-slate-900 placeholder:text-slate-400 dark:border-slate-600 dark:bg-slate-950/70 dark:text-white"
                  required
                />

                <div className="flex items-center justify-between gap-3 text-base">
                  <label className="inline-flex items-center gap-2 text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(event) => setRememberMe(event.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 bg-white dark:border-slate-500 dark:bg-slate-900"
                    />
                    <span>Remember me</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => notify('Forgot password can be connected to backend reset flow.', 'info')}
                    className="text-slate-600 underline-offset-4 transition hover:text-slate-900 hover:underline dark:text-slate-300 dark:hover:text-white"
                  >
                    Forgot password?
                  </button>
                </div>

                {errorMessage ? (
                  <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-400/35 dark:bg-rose-950/40 dark:text-rose-200">
                    {errorMessage}
                  </p>
                ) : null}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="focus-ring w-full rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 px-4 py-3 text-2xl font-bold text-white shadow-[0_14px_40px_rgba(14,165,233,0.35)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {isSubmitting ? 'Signing In...' : 'Sign In'}
                </button>

                <p className="pt-1 text-base text-slate-600 dark:text-slate-300">
                  New here?{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setMode('register');
                      setErrorMessage(null);
                    }}
                    className="font-semibold text-brand-700 underline-offset-4 hover:underline dark:text-sky-300"
                  >
                    Create an account
                  </button>
                </p>
              </form>
            ) : (
              <form onSubmit={handleRegister} className="mt-5 space-y-3.5">
                <input
                  type="text"
                  autoComplete="name"
                  value={registerName}
                  onChange={(event) => setRegisterName(event.target.value)}
                  placeholder="Full Name"
                  className="focus-ring w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base text-slate-900 placeholder:text-slate-400 dark:border-slate-600 dark:bg-slate-950/70 dark:text-white"
                  required
                />
                <input
                  type="email"
                  autoComplete="email"
                  value={registerEmail}
                  onChange={(event) => setRegisterEmail(event.target.value)}
                  placeholder="Email"
                  className="focus-ring w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base text-slate-900 placeholder:text-slate-400 dark:border-slate-600 dark:bg-slate-950/70 dark:text-white"
                  required
                />
                <input
                  type="password"
                  autoComplete="new-password"
                  value={registerPassword}
                  onChange={(event) => setRegisterPassword(event.target.value)}
                  placeholder="Password"
                  className="focus-ring w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base text-slate-900 placeholder:text-slate-400 dark:border-slate-600 dark:bg-slate-950/70 dark:text-white"
                  required
                />
                <input
                  type="password"
                  autoComplete="new-password"
                  value={registerConfirmPassword}
                  onChange={(event) => setRegisterConfirmPassword(event.target.value)}
                  placeholder="Confirm Password"
                  className="focus-ring w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base text-slate-900 placeholder:text-slate-400 dark:border-slate-600 dark:bg-slate-950/70 dark:text-white"
                  required
                />

                {errorMessage ? (
                  <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-400/35 dark:bg-rose-950/40 dark:text-rose-200">
                    {errorMessage}
                  </p>
                ) : null}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="focus-ring w-full rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 px-4 py-3 text-2xl font-bold text-white shadow-[0_14px_40px_rgba(59,130,246,0.35)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {isSubmitting ? 'Creating Account...' : 'Create an Account'}
                </button>

                <p className="pt-1 text-base text-slate-600 dark:text-slate-300">
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setMode('signin');
                      setErrorMessage(null);
                    }}
                    className="font-semibold text-brand-700 underline-offset-4 hover:underline dark:text-cyan-300"
                  >
                    Sign in
                  </button>
                </p>
              </form>
            )}
          </div>
        </motion.section>
      </div>

      <section id="how-it-works" className="mx-auto mt-7 w-full max-w-7xl rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-600 dark:border-slate-700/70 dark:bg-slate-950/45 dark:text-slate-300">
        AI-first workflow: upload image -&gt; extract measurements -&gt; map fit across brands -&gt; preview virtual try-on -&gt; reduce returns with confidence.
      </section>

      <WaveFooter className="relative left-1/2 mt-10 w-screen -translate-x-1/2" />
    </div>
  );
};
