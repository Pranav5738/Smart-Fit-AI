# SmartFit AI Backend (FastAPI)

Production-ready backend for SmartFit AI with personalized fit prediction,
capture quality scoring, explainable recommendations, profile history,
privacy controls, and shareable fit artifacts.

## Feature Coverage

- Fit preference control: slim, regular, relaxed
- Capture quality checker: pose, lighting, framing, hints
- Explainable results panel payload
- Brand expansion and category-aware mapping
- Live catalog-driven recommendations with filters
- Virtual try-on comparison mode (overlay, side-by-side, before/after)
- Saved profiles, scan history, and measurement trends
- Return risk score with best/comfort/style alternatives
- Privacy layer: explicit consent, auto-delete policy, data export/delete
- Unit and language support: cm/in + English/Spanish hints
- Shareable fit card generation from saved scans

## Project Structure

- main.py
- routes/
  - analyze.py
  - quality.py
  - catalog.py
  - profiles.py
  - privacy.py
- services/
  - pipeline.py
  - quality_checker.py
  - explainability.py
  - risk_scoring.py
  - profile_store.py
  - fit_card.py
  - catalog.py
  - brand_mapping.py
  - recommendation.py
  - virtual_tryon.py
- models/
  - schemas.py
- static/
  - catalog/products.csv
  - clothing/

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Optional environment configuration:

```bash
copy .env.example .env
```

4. Run API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Key Endpoints

### Health
- GET /health

### Quality Check
- POST /quality-check
  - multipart image + optional language (en/es)
  - returns quality score and actionable hints

### Performance
- POST /optimize-image
  - mobile-friendly compression and resize fallback
  - returns optimized image data URL and compression stats

### Analyze Image
- POST /analyze-image
  - required: image, consent_accepted=true
  - optional: user_height_cm, fit_preference, unit_system, language
  - optional filters: product_categories, occasions, weather, color_preferences
  - optional persistence: profile_id, save_to_history
  - returns measurements, size, confidence, brand mapping, explainability,
    return risk, recommendations, try-on outputs, privacy summary

### Catalog
- GET /catalog/products
- GET /catalog/brands

### Profiles and History
- POST /profiles/
- GET /profiles/
- GET /profiles/{profile_id}
- GET /profiles/{profile_id}/history
- GET /profiles/{profile_id}/trends
- GET /profiles/{profile_id}/export
- DELETE /profiles/{profile_id}
- DELETE /profiles/{profile_id}/history/{scan_id}
- GET /profiles/{profile_id}/history/{scan_id}/fit-card

### Privacy Controls
- GET /privacy/policy
- GET /privacy/download-my-data/{profile_id}
- DELETE /privacy/delete-my-data/{profile_id}

## Notes

- API docs are available at /docs.
- MediaPipe is pinned to 0.10.14 for Pose compatibility.
- Uploaded image bytes are processed in-memory and discarded after inference.
- Profile and scan history are persisted in SQLite at model_artifacts/profile_store.db.


Frontend - npm run dev
backend - python -m uvicorn main:app --reload