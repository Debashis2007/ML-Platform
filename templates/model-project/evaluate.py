#!/usr/bin/env python3
"""Evaluate trained model; write metrics.json for conditional register gate."""

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import roc_auc_score, accuracy_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default="/opt/ml/processing/model")
    parser.add_argument("--input-dir", default="/opt/ml/processing/input")
    parser.add_argument("--output-dir", default="/opt/ml/processing/output")
    args = parser.parse_args()

    model_path = Path(args.model_dir) / "model.joblib"
    model = joblib.load(model_path)

    input_dir = Path(args.input_dir)
    csv_files = list(input_dir.glob("*.csv"))
    df = pd.read_csv(csv_files[0])
    target = "default"
    X = df.drop(columns=[target])
    y = df[target]
    proba = model.predict_proba(X)[:, 1]
    metrics = {
        "auc": float(roc_auc_score(y, proba)),
        "accuracy": float(accuracy_score(y, (proba >= 0.5).astype(int))),
        "model_name": "credit-risk",
    }

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
