from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_generation.config import SCHEMA_COLUMNS
from src.data_generation.phase5a_prediction_target import PREDICTION_DIR
from src.detection.data import detection_contract, feature_fields


def load_split(split: str, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(PREDICTION_DIR / f"{split}.parquet", columns=columns or SCHEMA_COLUMNS)


def prediction_features() -> list[str]:
    return feature_fields()


def target_distribution(split: str) -> dict:
    frame = load_split(split, ["future_incident_label"])
    counts = frame["future_incident_label"].value_counts().to_dict()
    return {
        "split": split,
        "rows": int(len(frame)),
        "positive_count": int(counts.get(1, 0)),
        "negative_count": int(counts.get(0, 0)),
        "positive_rate": float(frame["future_incident_label"].mean()),
    }
