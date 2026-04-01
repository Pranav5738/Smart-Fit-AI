# SmartFit AI Frontend

Production-ready React + Vite frontend for AI-powered fit intelligence.

## Stack

- React + TypeScript (Vite)
- Tailwind CSS
- Framer Motion
- Axios

## Features

- Landing page with hero and feature cards
- Upload page with drag-and-drop and webcam capture
- Fit preference control (Slim, Regular, Relaxed)
- Capture quality checker (lighting, framing, pose, sharpness + hints)
- Mobile-first pre-upload image compression
- API integration for `POST /analyze-image` with multipart form-data
- Processing overlay animation (`Analyzing your body measurements...`)
- Results dashboard with explainability panel and return risk scoring
- Brand expansion and catalog mapping by category (tees, jeans, jackets)
- Smart outfit engine filters (occasion, weather, color, category)
- Virtual try-on comparison modes (single, side-by-side, before/after slider)
- Saved profiles, scan history, and measurement trend deltas
- Privacy controls (consent, auto-delete local image memory, download/delete data)
- Shareable fit card image export
- Dark/Light mode toggle with persistence
- High-contrast mode, keyboard skip link, and screen-reader toast live region
- Language toggle (EN/ES) and unit toggle (in/cm)
- Toast notifications and skeleton loading states
- Lazy-loaded routes for better first render performance
- Responsive layout for desktop and mobile

## API Contract

The frontend expects:

```json
{
  "measurements": { "chest": "38 in", "waist": "32 in", "shoulder": "17 in" },
  "predicted_size": "M",
  "confidence": 0.92,
  "brand_mapping": { "Nike": "M", "Zara": "M", "H&M": "L" },
  "recommendations": [
    { "name": "Relaxed Tee + Straight Jeans", "description": "Balanced silhouette" }
  ],
  "tryon_image": "<base64-or-url>"
}
```

## Local Run

1. Install dependencies:

   npm install

2. Optional: set backend base URL:

   Create `.env` and add:

   VITE_API_BASE_URL=http://localhost:8000

3. Start dev server:

   npm run dev

4. Production build:

   npm run build
