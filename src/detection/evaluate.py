from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


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


def threshold_table(y_true, probabilities, thresholds=(0.30, 0.40, 0.50, 0.60, 0.70)) -> list[dict]:
    return [metrics(y_true, probabilities, threshold) for threshold in thresholds]


def scenario_metrics(frame, probabilities, threshold: float) -> dict:
    predictions = (np.asarray(probabilities) >= threshold).astype(int)
    output = {}
    for scenario in ["D1", "D2", "C1", "C2", "C3", "C4", "C5"]:
        mask = frame["incident_type"].to_numpy() == scenario
        actual = frame.loc[mask, "incident_label"].to_numpy()
        predicted = predictions[mask]
        false_negatives = int(((actual == 1) & (predicted == 0)).sum())
        output[scenario] = {
            "samples": int(mask.sum()),
            "recall": float(recall_score(actual, predicted, zero_division=0)),
            "precision": float(precision_score(actual, predicted, zero_division=0)),
            "false_negatives": false_negatives,
            "detection_rate": float(((actual == 1) & (predicted == 1)).sum() / max(mask.sum(), 1)),
        }
    return output
