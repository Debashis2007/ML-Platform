#!/usr/bin/env python3
"""Preprocess credit-risk dataset (AWS ModelCreditRisk sample pattern)."""

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline as SkPipeline
import joblib


def preprocess(df: pd.DataFrame):
    target = "default"
    if target not in df.columns:
        raise ValueError(f"Expected column '{target}' in input data")
    y = df[target]
    X = df.drop(columns=[target])
    cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
    num_cols = [c for c in X.columns if c not in cat_cols]
    transformer = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
            ("num", "passthrough", num_cols),
        ]
    )
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    pipe = SkPipeline([("prep", transformer)])
    X_train_t = pipe.fit_transform(X_train)
    X_val_t = pipe.transform(X_val)
    return pipe, X_train_t, X_val_t, y_train, y_val


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="/opt/ml/processing/input")
    parser.add_argument("--output-dir", default="/opt/ml/processing/output")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = list(input_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV in {input_dir}")
    df = pd.read_csv(csv_files[0])
    pipe, X_train, X_val, y_train, y_val = preprocess(df)

    joblib.dump(pipe, output_dir / "preprocessor.joblib")
    pd.DataFrame(X_train).to_csv(output_dir / "train_features.csv", index=False)
    pd.DataFrame(X_val).to_csv(output_dir / "val_features.csv", index=False)
    y_train.to_csv(output_dir / "train_labels.csv", index=False, header=["default"])
    y_val.to_csv(output_dir / "val_labels.csv", index=False, header=["default"])
    print(json.dumps({"rows": len(df), "train": len(y_train), "val": len(y_val)}))


if __name__ == "__main__":
    main()
