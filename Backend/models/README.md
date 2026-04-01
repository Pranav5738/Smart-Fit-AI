Place the trained size prediction model here as:

size_model.pkl

Expected model behavior:
- Input features order: [chest_cm, waist_cm, shoulder_cm]
- Output label: one of XS, S, M, L, XL, XXL (or numeric class index)
- Optional: predict_proba for confidence scores

If the model file is missing, the backend bootstraps a RandomForest model from synthetic baseline data.
If scikit-learn is unavailable, it falls back to a heuristic size predictor.
