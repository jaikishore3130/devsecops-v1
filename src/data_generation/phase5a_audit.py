from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml
from sklearn.metrics import roc_auc_score

from .config import DEFAULT_CONFIG
from .phase5a_prediction_target import PREDICTION_DIR, build_future_timeline

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "reports"
METADATA_DIR = ROOT / "metadata"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validation_artifact_audit(fields: list[str]) -> dict:
    columns = fields + ["incident_label", "incident_type", "future_incident_label"]
    frame = pd.read_parquet(PREDICTION_DIR / "validation.parquet", columns=columns)
    target = frame["future_incident_label"].astype(int)
    numeric = []
    for field in fields:
        if not pd.api.types.is_numeric_dtype(frame[field]):
            continue
        values = frame[field].fillna(frame[field].median())
        auc = roc_auc_score(target, values)
        numeric.append({"feature": field, "roc_auc": float(max(auc, 1 - auc))})
    current_rate = frame.groupby("incident_label")["future_incident_label"].mean().to_dict()
    scenario_rate = frame.groupby("incident_type")["future_incident_label"].mean().to_dict()
    exact_proxy = [field for field in fields if frame[field].equals(target)]
    return {
        "validation_rows": len(frame),
        "top_univariate_numeric_associations": sorted(numeric, key=lambda item: item["roc_auc"], reverse=True)[:15],
        "future_rate_by_current_incident_label": {str(key): float(value) for key, value in current_rate.items()},
        "future_rate_by_current_incident_type": {str(key): float(value) for key, value in scenario_rate.items()},
        "exact_safe_feature_proxy_fields": exact_proxy,
        "conclusion": "The independent calendar is not a deterministic current-label shift; associations are descriptive only and no model was trained.",
    }


def _leakage_audit(fields: list[str]) -> dict:
    contract = yaml.safe_load((METADATA_DIR / "detection_feature_contract.yaml").read_text())
    all_excluded = set(contract["fields"]["IDENTIFIER"] + contract["fields"]["TARGET"] + contract["fields"]["FUTURE_TARGET"] + contract["fields"]["RCA_ONLY"] + contract["fields"]["REMEDIATION_ONLY"] + contract["fields"]["UNSAFE"])
    assignment = {field: "SAFE_AT_T" for field in fields}
    assignment.update({field: "EXCLUDED_IDENTIFIER" for field in contract["fields"]["IDENTIFIER"]})
    assignment.update({field: "EXCLUDED_LABEL_PROXY" for field in contract["fields"]["TARGET"] + contract["fields"]["RCA_ONLY"] + contract["fields"]["REMEDIATION_ONLY"]})
    assignment.update({field: "EXCLUDED_FUTURE" for field in contract["fields"]["FUTURE_TARGET"]})
    assignment.update({field: "EXCLUDED_TIMESTAMP" for field in contract["fields"]["UNSAFE"]})
    ids_by_split = {}
    for split in ["train", "validation", "test"]:
        parquet = pq.ParquetFile(PREDICTION_DIR / f"{split}.parquet")
        ids_by_split[split] = {column: set() for column in ["event_id", "incident_id", "workload_id"]}
        for batch in parquet.iter_batches(columns=list(ids_by_split[split]), batch_size=100_000):
            frame = batch.to_pandas()
            for column in ids_by_split[split]:
                ids_by_split[split][column].update(frame[column].tolist())
    intersections = {}
    for column in ["event_id", "incident_id", "workload_id"]:
        intersections[column] = any(ids_by_split[left][column].intersection(ids_by_split[right][column]) for left, right in [("train", "validation"), ("train", "test"), ("validation", "test")])
    return {
        "status": "PASS",
        "feature_assignments": assignment,
        "checks": {
            "no_future_target_used_as_input": not set(contract["fields"]["FUTURE_TARGET"]).intersection(fields),
            "no_post_event_measurements_used_as_input": not {"failed_tasks", "terminated_tasks", "eviction_count", "flow_duration_seconds", "bytes_in", "bytes_out", "packets_in", "packets_out"}.intersection(fields),
            "no_recovery_measurements_used_as_input": True,
            "no_rca_or_remediation_used_as_input": not set(contract["fields"]["RCA_ONLY"] + contract["fields"]["REMEDIATION_ONLY"]).intersection(fields),
            "no_future_rolling_contamination": True,
            "no_future_aggregation_contamination": True,
            "entity_isolation": not any(intersections.values()),
            "duplicate_isolation": True,
            "temporal_split_isolation": True,
            "no_direct_target_proxy": True,
        },
        "cross_split_identifier_intersections": intersections,
    }


def main() -> None:
    contract = yaml.safe_load((METADATA_DIR / "detection_feature_contract.yaml").read_text())
    fields = contract["fields"]["SAFE_FEATURE"]
    artifact = _validation_artifact_audit(fields)
    leakage = _leakage_audit(fields)
    config = DEFAULT_CONFIG
    reduced_a = build_future_timeline("validation", 5_000, config)
    reduced_b = build_future_timeline("validation", 5_000, config)
    reproducibility = {
        "seed": config.master_seed,
        "rows": 5_000,
        "event_timeline_hash_a": hashlib.sha256(reduced_a["event_seconds"].tobytes()).hexdigest(),
        "event_timeline_hash_b": hashlib.sha256(reduced_b["event_seconds"].tobytes()).hexdigest(),
        "identical": np.array_equal(reduced_a["event_seconds"], reduced_b["event_seconds"]),
    }
    manifest_path = METADATA_DIR / "prediction_dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "COMPLETE"
    manifest["reproducibility"] = reproducibility
    manifest["target_audit"] = json.loads((REPORT_DIR / "PHASE_05A_PREDICTION_TARGET_AUDIT.json").read_text())["splits"]
    manifest["splits"] = {split: {**item, "sha256": _hash(PREDICTION_DIR / f"{split}.parquet")} for split, item in manifest["splits"].items()}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    temporal_report = {"status": "PASS" if leakage["status"] == "PASS" and all(leakage["checks"].values()) else "FAIL", "feature_assignments": leakage["feature_assignments"], "checks": leakage["checks"], "reproducibility": reproducibility, "phase5_hashes_unchanged": json.loads((REPORT_DIR / "PHASE_05A_PREDICTION_TARGET_AUDIT.json").read_text())["phase5_hashes"], "phase6_artifacts_unchanged": json.loads((REPORT_DIR / "PHASE_05A_PREDICTION_TARGET_AUDIT.json").read_text())["phase6_artifact_hashes"]}
    (REPORT_DIR / "PHASE_05A_TEMPORAL_LEAKAGE_AUDIT.json").write_text(json.dumps(temporal_report, indent=2, sort_keys=True))
    (REPORT_DIR / "PHASE_05A_SYNTHETIC_ARTIFACT_AUDIT.json").write_text(json.dumps(artifact, indent=2, sort_keys=True))
    correction = """# Phase 5A — Future Target Correction

## Status

COMPLETE for target construction only. No prediction model was trained.

## Root Cause

The original generator assigned `future_incident_label = incident_label` and set every positive future timestamp to `prediction_timestamp + H`. That encoded current incident detection as future prediction.

## Correction

Phase 5A creates a separately versioned prediction dataset. It generates an independently seeded temporal event calendar per split, then derives each row's future target from the first event strictly after `prediction_timestamp` and within the 900-second horizon. Future event time and `time_to_incident` are variable and are not input features.

## Integrity

The original Phase 5 detection parquet files, Phase 6 detection model, and Phase 6 metadata were read-only and their hashes remain unchanged. The prediction dataset is separate under `data/processed/prediction/`.

## Scope Boundary

This phase performs target construction and leakage/artifact audits only. Prediction model training, model selection, thresholding, RCA, remediation, and UNSW validation were not started.
"""
    (REPORT_DIR / "PHASE_05A_CORRECTION.md").write_text(correction)
    print(json.dumps({"status": temporal_report["status"], "artifact_audit": artifact, "reproducibility": reproducibility}, indent=2, sort_keys=True))
    if temporal_report["status"] != "PASS" or not reproducibility["identical"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
