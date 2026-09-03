#!/usr/bin/env python3
"""Train credit-risk classifier (sklearn — AWS ModelCreditRisk pattern)."""

import argparse
import json
import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    parser.add_argument("--train", default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    args = parser.parse_args()

    train_path = Path(args.train)
    csv_files = list(train_path.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No training CSV in {train_path}")
    df = pd.read_csv(csv_files[0])
    target = "default"
    X = df.drop(columns=[target])
    y = df[target]
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X, y)
    preds = model.predict_proba(X)[:, 1]
    auc = float(roc_auc_score(y, preds))

    model_dir = Path(args.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "model.joblib")
    (model_dir / "metrics.json").write_text(json.dumps({"auc": auc, "model_name": "credit-risk"}))
    print(json.dumps({"auc": auc}))


if __name__ == "__main__":
    main()
