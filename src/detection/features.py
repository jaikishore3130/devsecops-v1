from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(frozen=True)
class FeatureSet:
    name: str
    fields: list[str]


def split_feature_types(frame: pd.DataFrame, fields: list[str]) -> tuple[list[str], list[str]]:
    categorical = [field for field in fields if field in frame and not pd.api.types.is_numeric_dtype(frame[field])]
    numeric = [field for field in fields if field not in categorical]
    return numeric, categorical


def make_preprocessor(frame: pd.DataFrame, fields: list[str]) -> ColumnTransformer:
    numeric, categorical = split_feature_types(frame, fields)
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", StandardScaler(with_mean=False)),
    ])
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
    ])
    return ColumnTransformer([
        ("numeric", numeric_pipeline, numeric),
        ("categorical", categorical_pipeline, categorical),
    ], remainder="drop")


def feature_groups(contract: dict) -> dict[str, list[str]]:
    safe = set(contract["fields"]["SAFE_FEATURE"])
    return {
        "all_safe_features": sorted(safe),
        "infrastructure_cloud_workload": sorted(safe & {
            "cpu_utilization", "memory_utilization", "disk_utilization", "network_in_bytes",
            "network_out_bytes", "io_wait", "load_average", "process_count", "thread_count",
            "open_connections", "file_descriptor_usage", "task_count", "cloud_job_count",
            "instance_count", "pending_tasks", "running_tasks", "resource_requests_cpu",
            "resource_requests_memory", "resource_usage_cpu", "resource_usage_memory",
            "scheduling_delay_seconds", "queue_length", "node_pressure", "restart_count",
        }),
        "cicd_deployment": sorted(safe & {
            "environment", "region", "deployment_frequency", "deployment_age_seconds",
            "version_age_seconds", "change_size", "config_change_count", "rollback_count",
            "pipeline_duration_seconds", "queue_time_seconds", "build_duration_seconds",
            "test_duration_seconds", "deployment_duration_seconds", "retry_count", "job_count",
            "step_count", "artifact_count", "dependency_count",
        }),
        "network_security": sorted(safe & {
            "src_port", "dst_port", "protocol", "service", "connection_count", "packet_rate",
            "byte_rate", "connection_rate", "auth_attempts", "failed_auth_attempts",
            "successful_auth_attempts", "unique_source_count", "credential_failure_rate",
            "unique_destination_ports", "unique_destination_hosts", "connection_attempt_rate",
            "port_entropy", "host_entropy", "scan_burst_score", "request_rate", "source_count",
            "source_entropy", "traffic_volume_bytes",
        }),
        "safe_without_derived": sorted(safe - {
            "cpu_delta", "memory_slope", "request_rate_rolling_mean", "request_rate_rolling_std",
            "failure_rate", "retry_rate", "burst_score", "anomaly_score",
        }),
    }
