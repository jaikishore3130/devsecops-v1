from __future__ import annotations

import uuid
from typing import Dict, Tuple

from .config import ROOT_NAMESPACE


def stable_uuid(split: str, kind: str, index: int) -> str:
    return str(uuid.uuid5(ROOT_NAMESPACE, f"{split}:{kind}:{index}"))


def entity_ids(split: str, row_index: int, row_count: int) -> Dict[str, str]:
    org_index = row_index % 40
    project_index = (row_index // 10) % 250
    environment_index = row_index % 500
    service_index = row_index % 2000
    host_index = row_index % 4000
    workload_index = row_index % 3000
    deployment_index = row_index // 100
    pipeline_index = row_index // 25
    job_index = row_index
    window_index = row_index % 1800
    incident_index = row_index % 1500

    return {
        "org_id": stable_uuid(split, "org", org_index),
        "project_id": stable_uuid(split, "project", project_index),
        "environment_id": stable_uuid(split, "environment", environment_index),
        "service_id": stable_uuid(split, "service", service_index),
        "host_id": stable_uuid(split, "host", host_index),
        "workload_id": stable_uuid(split, "workload", workload_index),
        "deployment_id": stable_uuid(split, "deployment", deployment_index),
        "pipeline_id": stable_uuid(split, "pipeline", pipeline_index),
        "job_id": stable_uuid(split, "job", job_index),
        "window_id": stable_uuid(split, "window", window_index),
        "incident_id": stable_uuid(split, "incident", incident_index),
        "event_id": stable_uuid(split, "event", row_index),
    }


def load_context_features(split: str, row_index: int) -> Tuple[str, str, str, str, str]:
    env_values = ["development", "staging", "production", "test"]
    region_values = ["region-a", "region-b", "region-c", "region-d"]
    env = env_values[(row_index + len(split)) % len(env_values)]
    region = region_values[row_index % len(region_values)]
    return env, region, env_values[(row_index + 1) % len(env_values)], region_values[(row_index + 2) % len(region_values)]
