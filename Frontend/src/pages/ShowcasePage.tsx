import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '@/contexts/AuthContext';

const workflowSteps = [
  {
    title: 'Upload Image / Use Camera',
    description: 'Capture your look via drag-and-drop image upload or live webcam snapshot.',
  },
  {
    title: 'AI Measurement Extraction',
    description: 'Computer vision estimates body dimensions and validates capture quality.',
  },
  {
    title: 'Size Prediction',
    description: 'SmartFit predicts your best fit with confidence scoring and alternatives.',
  },
  {
    title: 'Brand Mapping',
    description: 'Your profile is converted into brand-specific sizing recommendations.',
  },
  {
    title: 'Virtual Try-On',
    description: 'Compare original and AI try-on outputs before making buying decisions.',
  },
];

const highlights = [
  'Fit Preference Control',
  'Virtual Try-On Comparison',
  'Return Risk Score',
  'Smart Outfit Engine',
  'Explainable AI Panel',
];

export const ShowcasePage = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="space-y-8 pb-8">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-700 dark:text-brand-300">
          Product Showcase
        </p>
        <h1 className="mt-2 text-4xl font-extrabold">How SmartFit AI Works</h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600 dark:text-slate-300 sm:text-base">
          SmartFit AI combines camera input, AI body analysis, and brand-aware prediction logic to help users select better-fitting clothing with confidence.
        </p>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-2xl font-bold">Step-by-Step Workflow</h2>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          {workflowSteps.map((step, index) => (
            <motion.article
              key={step.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.35, delay: index * 0.06 }}
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40"
            >
              <p className="mb-2 inline-flex rounded-md bg-brand-600 px-2 py-1 text-xs font-bold text-white">
                {`Step ${index + 1}`}
              </p>
              <h3 className="text-base font-bold">{step.title}</h3>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{step.description}</p>
            </motion.article>
          ))}
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-2xl font-bold">Feature Highlights</h2>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          {highlights.map((feature, index) => (
            <motion.div
              key={feature}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ duration: 0.3, delay: index * 0.06 }}
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm font-semibold dark:border-slate-700 dark:bg-slate-950/40"
            >
              {feature}
            </motion.div>
          ))}
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-2xl font-bold">Demo Preview</h2>
        <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1fr]">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Before</p>
            <div className="aspect-[4/5] rounded-xl bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-900 dark:to-slate-800" />
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">After AI Try-On</p>
            <div className="aspect-[4/5] rounded-xl bg-gradient-to-br from-brand-200 to-accent-200 dark:from-brand-950 dark:to-accent-950" />
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-cyan-200 bg-gradient-to-br from-cyan-50 via-white to-brand-50 p-6 text-center shadow-card dark:border-brand-800/60 dark:bg-gradient-to-br dark:from-slate-900 dark:via-slate-900 dark:to-brand-950/40">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Ready to experience SmartFit AI?</h2>
        <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">
          Sign in to start your personalized fit analysis and virtual try-on journey.
        </p>
        <div className="mt-4">
          <Link
            to={isAuthenticated ? '/dashboard' : '/signin'}
            className="focus-ring inline-flex rounded-2xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            Try SmartFit Now
          </Link>
        </div>
      </section>
    </div>
  );
};
