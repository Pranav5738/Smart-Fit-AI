import { Link } from 'react-router-dom';

const currentYear = new Date().getFullYear();

export const WaveFooter = ({ className = '' }: { className?: string }) => {
  return (
    <footer className={`relative w-full overflow-hidden border-t border-sky-300/25 bg-[#1f2436] text-slate-100 ${className}`}>
      <div className="relative h-36 overflow-hidden bg-gradient-to-b from-slate-100 via-slate-100 to-slate-200">

        <svg className="absolute inset-x-0 bottom-0 h-28 w-full" viewBox="0 0 1600 260" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 24 C420 210, 980 36, 1600 92 L1600 0 L0 0 Z" fill="#f8fafc" />
          <path d="M0 78 C380 232, 980 64, 1600 118 L1600 0 L0 0 Z" fill="rgba(203,213,225,0.82)" />
          <path d="M0 122 C470 250, 1080 84, 1600 132 L1600 260 L0 260 Z" fill="#0ea5e9" />
          <path d="M0 154 C440 262, 1040 112, 1600 150 L1600 260 L0 260 Z" fill="#0284c7" />
          <path d="M0 188 C500 276, 1180 136, 1600 168 L1600 260 L0 260 Z" fill="#2b3144" />
        </svg>
      </div>

      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[1.2fr_1fr_1fr] lg:px-8">
        <section>
          <img
            src="/smartfit-logo-full.svg"
            alt="SmartFit AI Logo"
            className="h-20 w-auto rounded-lg border border-slate-600/70 bg-slate-800/40 p-1 shadow-sm"
          />
          <p className="mt-3 max-w-sm text-sm text-slate-300">
            AI-powered fit guidance for smarter sizing, better comfort, and fewer returns.
          </p>
        </section>

        <section>
          <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-300">Quick Links</h3>
          <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
            <Link to="/" className="text-slate-300 transition hover:text-white">
              Home
            </Link>
            <Link to="/showcase" className="text-slate-300 transition hover:text-white">
              Showcase
            </Link>
            <Link to="/dashboard" className="text-slate-300 transition hover:text-white">
              Dashboard
            </Link>
            <Link to="/signin" className="text-slate-300 transition hover:text-white">
              Sign In
            </Link>
          </div>
        </section>

        <section>
          <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-300">Contact</h3>
          <div className="mt-2 space-y-1 text-sm text-slate-300">
            <p>
              <a href="mailto:support@smartfit.ai" className="text-sky-300 hover:text-sky-200">
                support@smartfit.ai
              </a>
            </p>
            <p>Mon-Fri, 9:00 AM to 6:00 PM</p>
            <p className="text-slate-400">Privacy and terms available on request.</p>
          </div>
        </section>
      </div>

      <div className="border-t border-slate-700/80 px-4 py-3 text-center text-xs text-slate-400 sm:px-6 lg:px-8">
        {`© ${currentYear} SmartFit AI. All rights reserved.`}
      </div>
    </footer>
  );
};
