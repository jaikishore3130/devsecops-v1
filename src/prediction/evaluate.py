from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def metrics(y_true, probabilities, threshold: float = 0.5) -> dict:
    predictions = (np.asarray(probabilities) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "pr_auc": float(average_precision_score(y_true, probabilities)),
        "false_positive_rate": float(fp / max(fp + tn, 1)),
        "false_negative_rate": float(fn / max(fn + tp, 1)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def threshold_table(y_true, probabilities) -> list[dict]:
    return [metrics(y_true, probabilities, threshold) for threshold in (0.03, 0.04, 0.05, 0.06, 0.07, 0.10, 0.30, 0.50, 0.70)]


def lead_time_metrics(frame, probabilities, threshold: float) -> dict:
    predicted = np.asarray(probabilities) >= threshold
    actual = frame["future_incident_label"].to_numpy() == 1
    correct = predicted & actual
    times = (pd.to_datetime(frame.loc[correct, "future_incident_time"], utc=True) - pd.to_datetime(frame.loc[correct, "prediction_timestamp"], utc=True)).dt.total_seconds()
    values = times.to_numpy(dtype=float)
    return {
        "correct_future_predictions": int(correct.sum()),
        "mean_seconds": float(values.mean()) if len(values) else None,
        "median_seconds": float(np.median(values)) if len(values) else None,
        "min_seconds": float(values.min()) if len(values) else None,
        "max_seconds": float(values.max()) if len(values) else None,
        "percentiles_seconds": {str(p): float(np.percentile(values, p)) for p in (10, 25, 50, 75, 90)} if len(values) else {},
        "buckets": {
            "0_300": int(((values >= 0) & (values <= 300)).sum()),
            "301_600": int(((values > 300) & (values <= 600)).sum()),
            "601_900": int(((values > 600) & (values <= 900)).sum()),
        },
    }
