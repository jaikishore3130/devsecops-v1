"""Phase 7B data access for the frozen Phase 7A prediction_v2 dataset.

This module never mutates the dataset. It only reads parquet files and derives
the approved SAFE_FEATURE contract for future-incident prediction.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "data" / "processed" / "prediction_v2"
CONTRACT_PATH = ROOT / "metadata" / "detection_feature_contract.yaml"
V2_MANIFEST_PATH = ROOT / "metadata" / "prediction_v2_config.yaml"

SPLIT_ROWS = {"train": 1_000_000, "validation": 50_000, "test": 50_000}
TARGET = "future_incident_label"

# Analysis-only fields: never predictors. Listed explicitly so the contract is
# auditable independent of the detection contract classification.
ANALYSIS_ONLY = ["future_incident_type", "latent_scenario_state"]

# Fields excluded for prediction, beyond the detection contract's own classes.
EXTRA_FORBIDDEN = [
    "future_incident_label",
    "future_incident_type",
    "future_incident_time",
    "time_to_incident",
    "latent_scenario_state",
]

# Feature groups used for the ablation study (keys match required artifact names).
DERIVED_FEATURES = [
    "cpu_delta",
    "memory_slope",
    "request_rate_rolling_mean",
    "request_rate_rolling_std",
    "failure_rate",
    "retry_rate",
    "burst_score",
    "anomaly_score",
]


def detection_contract() -> dict:
    return yaml.safe_load(CONTRACT_PATH.read_text())


def forbidden_fields() -> dict[str, list[str]]:
    contract = detection_contract()["fields"]
    groups = {
        "IDENTIFIER": contract["IDENTIFIER"],
        "TARGET": contract["TARGET"],
        "FUTURE_TARGET": contract["FUTURE_TARGET"],
        "RCA_ONLY": contract["RCA_ONLY"],
        "REMEDIATION_ONLY": contract["REMEDIATION_ONLY"],
        "UNSAFE": contract["UNSAFE"],
        "ANALYSIS_ONLY": ANALYSIS_ONLY,
    }
    return groups


def all_forbidden() -> set[str]:
    fields: set[str] = set()
    for values in forbidden_fields().values():
        fields.update(values)
    fields.update(EXTRA_FORBIDDEN)
    return fields


def allowed_features(columns: list[str] | None = None) -> list[str]:
    contract_safe = detection_contract()["fields"]["SAFE_FEATURE"]
    forbidden = all_forbidden()
    allowed = [field for field in contract_safe if field not in forbidden]
    if columns is not None:
        available = set(columns)
        missing = [field for field in allowed if field not in available]
        if missing:
            raise ValueError(f"Allowed features missing from dataset: {missing}")
    return allowed


def feature_groups(allowed: list[str]) -> dict[str, list[str]]:
    safe = set(allowed)
    infrastructure = {
        "cpu_utilization", "memory_utilization", "disk_utilization", "network_in_bytes",
        "network_out_bytes", "io_wait", "load_average", "process_count", "thread_count",
        "open_connections", "file_descriptor_usage", "task_count", "cloud_job_count",
        "instance_count", "pending_tasks", "running_tasks", "resource_requests_cpu",
        "resource_requests_memory", "resource_usage_cpu", "resource_usage_memory",
        "scheduling_delay_seconds", "queue_length", "node_pressure", "restart_count",
    }
    cicd = {
        "environment", "region", "deployment_frequency", "deployment_age_seconds",
        "version_age_seconds", "change_size", "config_change_count", "rollback_count",
        "pipeline_duration_seconds", "queue_time_seconds", "build_duration_seconds",
        "test_duration_seconds", "deployment_duration_seconds", "retry_count", "job_count",
        "step_count", "artifact_count", "dependency_count",
    }
    network = {
        "src_port", "dst_port", "protocol", "service", "connection_count", "packet_rate",
        "byte_rate", "connection_rate", "auth_attempts", "failed_auth_attempts",
        "successful_auth_attempts", "unique_source_count", "credential_failure_rate",
        "unique_destination_ports", "unique_destination_hosts", "connection_attempt_rate",
        "port_entropy", "host_entropy", "scan_burst_score", "request_rate", "source_count",
        "source_entropy", "traffic_volume_bytes",
    }
    return {
        "ALL_SAFE_FEATURES": sorted(safe),
        "INFRASTRUCTURE_CLOUD_WORKLOAD": sorted(safe & infrastructure),
        "CICD_DEPLOYMENT": sorted(safe & cicd),
        "NETWORK_SECURITY": sorted(safe & network),
        "SAFE_FEATURES_WITHOUT_DERIVED_FEATURES": sorted(safe - set(DERIVED_FEATURES)),
    }


def load_split(split: str, columns: list[str] | None = None) -> pd.DataFrame:
    path = DATASET_DIR / f"{split}.parquet"
    return pd.read_parquet(path, columns=columns)


def load_xy(split: str, allowed: list[str]) -> tuple[pd.DataFrame, "pd.Series"]:
    frame = load_split(split, allowed + [TARGET])
    return frame[allowed], frame[TARGET].astype(int)


def class_distribution(split: str) -> dict:
    frame = load_split(split, [TARGET])
    counts = frame[TARGET].value_counts().to_dict()
    positives = int(counts.get(1, 0))
    negatives = int(counts.get(0, 0))
    return {
        "split": split,
        "rows": int(len(frame)),
        "positive": positives,
        "negative": negatives,
        "positive_rate": float(positives / len(frame)),
        "negative_to_positive_ratio": float(negatives / positives) if positives else None,
    }
