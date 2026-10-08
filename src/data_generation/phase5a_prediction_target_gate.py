from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import yaml

from .config import SCHEMA_COLUMNS

ROOT = Path(__file__).resolve().parents[2]
PREDICTION_DIR = ROOT / "data" / "processed" / "prediction"
HORIZON_SECONDS = 900
SPLITS = {"train": 1_000_000, "validation": 50_000, "test": 50_000}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_split(split: str) -> dict:
    path = PREDICTION_DIR / f"{split}.parquet"
    parquet = pq.ParquetFile(path)
    result = {"rows": parquet.metadata.num_rows, "schema_columns": len(parquet.schema_arrow.names), "equality_count": 0, "positive_count": 0, "current_normal_future_incident": 0, "current_incident_future_none": 0, "positive_time_deltas": [], "positive_at_horizon": 0, "future_time_not_after": 0, "future_time_beyond_horizon": 0, "negative_future_time_count": 0, "time_to_incident_mismatch": 0}
    for batch in parquet.iter_batches(columns=["incident_label", "future_incident_label", "future_incident_time", "time_to_incident", "prediction_timestamp"], batch_size=100_000):
        frame = batch.to_pandas()
        result["equality_count"] += int((frame["incident_label"] == frame["future_incident_label"]).sum())
        positive = frame["future_incident_label"] == 1
        result["positive_count"] += int(positive.sum())
        result["current_normal_future_incident"] += int(((frame["incident_label"] == 0) & positive).sum())
        result["current_incident_future_none"] += int(((frame["incident_label"] == 1) & ~positive).sum())
        future_time = pd.to_datetime(frame["future_incident_time"], utc=True)
        cutoff = pd.to_datetime(frame["prediction_timestamp"], utc=True)
        delta = (future_time - cutoff).dt.total_seconds()
        result["positive_time_deltas"].extend(delta[positive].tolist())
        result["future_time_not_after"] += int((future_time[positive] <= cutoff[positive]).sum())
        result["future_time_beyond_horizon"] += int((future_time[positive] > cutoff[positive] + pd.Timedelta(seconds=HORIZON_SECONDS)).sum())
        result["negative_future_time_count"] += int(future_time[~positive].notna().sum())
        result["positive_at_horizon"] += int((delta[positive] == HORIZON_SECONDS).sum())
        expected = delta[positive].to_numpy()
        actual = frame.loc[positive, "time_to_incident"].to_numpy()
        result["time_to_incident_mismatch"] += int((abs(expected - actual) > 1e-9).sum())
    result["equality_rate"] = result["equality_count"] / result["rows"]
    result["time_to_incident_min"] = min(result["positive_time_deltas"]) if result["positive_time_deltas"] else None
    result["time_to_incident_median"] = float(pd.Series(result["positive_time_deltas"]).median()) if result["positive_time_deltas"] else None
    result["time_to_incident_mean"] = float(pd.Series(result["positive_time_deltas"]).mean()) if result["positive_time_deltas"] else None
    result["time_to_incident_max"] = max(result["positive_time_deltas"]) if result["positive_time_deltas"] else None
    result["time_to_incident_unique"] = len(set(result["positive_time_deltas"]))
    del result["positive_time_deltas"]
    return result


def main() -> None:
    before = {split: _hash(ROOT / "data" / "processed" / f"{split}.parquet") for split in SPLITS}
    detection_before = {path.name: _hash(path) for path in (ROOT / "models" / "detection").glob("*")}
    splits = {split: audit_split(split) for split in SPLITS}
    feature_contract = yaml.safe_load((ROOT / "metadata" / "detection_feature_contract.yaml").read_text())
    checks = {
        "row_counts": all(item["rows"] == SPLITS[split] for split, item in splits.items()),
        "schema": all(item["schema_columns"] == len(SCHEMA_COLUMNS) for item in splits.values()),
        "future_label_not_current_label": all(item["equality_rate"] < 1.0 for item in splits.values()),
        "current_normal_future_incident_examples": all(item["current_normal_future_incident"] > 0 for item in splits.values()),
        "current_incident_future_none_examples": all(item["current_incident_future_none"] > 0 for item in splits.values()),
        "future_time_strictly_after_cutoff": all(item["future_time_not_after"] == 0 for item in splits.values()),
        "future_time_within_horizon": all(item["future_time_beyond_horizon"] == 0 for item in splits.values()),
        "negative_rows_have_no_future_time": all(item["negative_future_time_count"] == 0 for item in splits.values()),
        "time_to_incident_matches": all(item["time_to_incident_mismatch"] == 0 for item in splits.values()),
        "time_to_incident_varies": all(item["time_to_incident_unique"] > 1 for item in splits.values()),
        "not_all_positive_at_horizon": all(item["positive_at_horizon"] < item["positive_count"] for item in splits.values()),
        "future_fields_excluded_from_safe_features": not set(feature_contract["fields"]["FUTURE_TARGET"]).intersection(feature_contract["fields"]["SAFE_FEATURE"]),
        "phase5_hashes_unchanged": before == {split: _hash(ROOT / "data" / "processed" / f"{split}.parquet") for split in SPLITS},
        "phase6_artifacts_unchanged": detection_before == {path.name: _hash(path) for path in (ROOT / "models" / "detection").glob("*")},
    }
    report = {"status": "COMPLETE" if all(checks.values()) else "BLOCKED", "checks": checks, "splits": splits, "phase5_hashes": before, "phase6_artifact_hashes": detection_before, "model_training_started": False}
    (ROOT / "reports" / "PHASE_05A_PREDICTION_TARGET_AUDIT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
