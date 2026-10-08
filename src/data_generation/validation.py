from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import SCHEMA_COLUMNS


REQUIRED_COLUMNS = SCHEMA_COLUMNS


def validate_generated_dataset(path: str | Path) -> dict:
    frame = pd.read_parquet(path)
    results = {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "schema_match": list(frame.columns) == REQUIRED_COLUMNS,
        "required_ids_present": {"event_id": "event_id" in frame.columns, "incident_id": "incident_id" in frame.columns, "window_id": "window_id" in frame.columns},
        "duplicate_event_ids": int(frame["event_id"].duplicated().sum()),
        "duplicate_window_ids": int(frame["window_id"].duplicated().sum()),
    }
    return results


def reproducibility_check(base_dir: str | Path) -> dict:
    runs = []
    for file in sorted(Path(base_dir).glob("*.parquet")):
        hash_value = __import__("hashlib").sha256(file.read_bytes()).hexdigest()
        runs.append((file.name, hash_value))
    return {"runs": runs}
