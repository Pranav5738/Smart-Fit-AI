from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def build_pipeline() -> Pipeline:
    numeric_features = ["chest_cm", "waist_cm", "shoulder_cm"]
    categorical_features = ["age_group", "gender", "fit_preference"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ]
    )

    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=16,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train SmartFit size model on real measurements")
    parser.add_argument("--data", required=True, help="Path to CSV dataset")
    parser.add_argument("--out", required=True, help="Output model path (.pkl)")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    data_path = Path(args.data)
    output_path = Path(args.out)

    df = pd.read_csv(data_path)
    required_columns = [
        "chest_cm",
        "waist_cm",
        "shoulder_cm",
        "age_group",
        "gender",
        "fit_preference",
        "size_label",
    ]

    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.dropna(subset=required_columns)

    X = df[[
        "chest_cm",
        "waist_cm",
        "shoulder_cm",
        "age_group",
        "gender",
        "fit_preference",
    ]]
    y = df["size_label"].astype(str)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=args.test_size,
        random_state=42,
        stratify=y,
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)
    print(classification_report(y_test, predictions))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_path)
    print(f"Saved model to {output_path}")


if __name__ == "__main__":
    main()
