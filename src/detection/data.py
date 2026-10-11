from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "metadata" / "synthetic_schema.csv"
CONTRACT_PATH = PROJECT_ROOT / "metadata" / "detection_feature_contract.yaml"
DATA_DIR = PROJECT_ROOT / "data" / "processed"


def canonical_fields() -> list[str]:
    with SCHEMA_PATH.open(newline="") as handle:
        return [row["field_name"] for row in csv.DictReader(handle)]


def detection_contract() -> dict:
    return yaml.safe_load(CONTRACT_PATH.read_text())


def feature_fields() -> list[str]:
    return detection_contract()["fields"]["SAFE_FEATURE"]


def load_split(split: str, columns: list[str] | None = None) -> pd.DataFrame:
    requested = columns or canonical_fields()
    return pd.read_parquet(DATA_DIR / f"{split}.parquet", columns=requested)


def class_distribution(split: str) -> dict:
    frame = load_split(split, ["incident_label", "incident_type"])
    counts = frame["incident_type"].value_counts().to_dict()
    return {
        "split": split,
        "rows": int(len(frame)),
        "normal_count": int((frame["incident_label"] == 0).sum()),
        "incident_count": int((frame["incident_label"] == 1).sum()),
        "incident_type_counts": {str(key): int(value) for key, value in counts.items()},
        "positive_rate": float(frame["incident_label"].mean()),
    }
