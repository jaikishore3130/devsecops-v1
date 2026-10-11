from __future__ import annotations

import numpy as np
import pandas as pd


def apply_missingness(frame: pd.DataFrame, rng: np.random.Generator, missing_rate: float = 0.025) -> pd.DataFrame:
    telemetry_columns = [
        c for c in frame.columns if c not in {
            "org_id", "project_id", "environment_id", "service_id", "host_id", "workload_id",
            "deployment_id", "pipeline_id", "job_id", "window_id", "incident_id", "event_id",
            "event_timestamp", "window_start", "window_end", "prediction_timestamp", "future_incident_time",
            "incident_label", "incident_type", "future_incident_label", "time_to_incident",
            "root_cause_category", "root_component", "recommended_action"
        }
    ]
    for column in telemetry_columns:
        if pd.api.types.is_numeric_dtype(frame[column]):
            mask = rng.random(len(frame)) < missing_rate
            frame.loc[mask, column] = np.nan
    return frame
