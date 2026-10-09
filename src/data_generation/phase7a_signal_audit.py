from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import roc_auc_score

from .config import DEFAULT_CONFIG

ROOT = Path(__file__).resolve().parents[2]
SAFE_FIELDS = [
    "environment", "region", "deployment_frequency", "deployment_age_seconds", "version_age_seconds", "change_size", "config_change_count", "rollback_count", "pipeline_duration_seconds", "queue_time_seconds", "build_duration_seconds", "test_duration_seconds", "deployment_duration_seconds", "retry_count", "job_count", "step_count", "artifact_count", "dependency_count", "cpu_utilization", "memory_utilization", "disk_utilization", "network_in_bytes", "network_out_bytes", "io_wait", "load_average", "process_count", "thread_count", "open_connections", "file_descriptor_usage", "task_count", "cloud_job_count", "instance_count", "pending_tasks", "running_tasks", "resource_requests_cpu", "resource_requests_memory", "resource_usage_cpu", "resource_usage_memory", "scheduling_delay_seconds", "queue_length", "node_pressure", "restart_count", "src_port", "dst_port", "protocol", "service", "connection_count", "packet_rate", "byte_rate", "connection_rate", "auth_attempts", "failed_auth_attempts", "successful_auth_attempts", "unique_source_count", "credential_failure_rate", "unique_destination_ports", "unique_destination_hosts", "connection_attempt_rate", "port_entropy", "host_entropy", "scan_burst_score", "request_rate", "source_count", "source_entropy", "traffic_volume_bytes", "observation_age_seconds", "hour_of_day", "day_of_week", "cpu_delta", "memory_slope", "request_rate_rolling_mean", "request_rate_rolling_std", "failure_rate", "retry_rate", "burst_score", "anomaly_score",
]
FUTURE_TYPES = ["D1", "D2", "C1", "C2", "C3", "C4", "C5"]


def audit(path: Path) -> dict:
    frame = pd.read_parquet(path)
    target = frame["future_incident_label"].astype(int)
    numeric = []
    for field in SAFE_FIELDS:
        values = frame[field]
        if not pd.api.types.is_numeric_dtype(values):
            continue
        filled = values.fillna(values.median())
        auc = roc_auc_score(target, filled)
        numeric.append({"feature": field, "roc_auc": float(max(auc, 1 - auc))})
    future_positive = frame["future_incident_label"] == 1
    current_state_rates = frame.groupby("incident_label")["future_incident_label"].mean().to_dict()
    state_rates = frame.groupby("latent_scenario_state")["future_incident_label"].mean().to_dict()
    type_counts = frame.loc[future_positive, "future_incident_type"].value_counts().to_dict()
    time_values = frame.loc[future_positive, "time_to_incident"].dropna()
    return {
        "path": str(path),
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "positive_count": int(target.sum()),
        "positive_rate": float(target.mean()),
        "future_type_counts": {str(k): int(v) for k, v in type_counts.items()},
        "lead_time": {"min": float(time_values.min()), "median": float(time_values.median()), "max": float(time_values.max()), "unique": int(time_values.nunique())},
        "future_rate_by_current_incident_label": {str(k): float(v) for k, v in current_state_rates.items()},
        "future_rate_by_latent_state": {str(k): float(v) for k, v in state_rates.items()},
        "top_safe_univariate_auc": sorted(numeric, key=lambda item: item["roc_auc"], reverse=True)[:15],
        "target_proxy_features": [field for field in SAFE_FIELDS if frame[field].equals(target)],
        "all_positive_times_valid": bool(((pd.to_datetime(frame.loc[future_positive, "future_incident_time"], utc=True) > pd.to_datetime(frame.loc[future_positive, "prediction_timestamp"], utc=True)) & (frame.loc[future_positive, "time_to_incident"] <= 899)).all()),
        "negative_times_null": bool(frame.loc[~future_positive, "future_incident_time"].isna().all() and frame.loc[~future_positive, "time_to_incident"].isna().all()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
    report = audit(Path(args.path))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
