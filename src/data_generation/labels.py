from __future__ import annotations

import numpy as np
import pandas as pd

ROOT_CAUSE_MAP = {
    "D1": ("deployment_change", "pipeline"),
    "D2": ("resource_exhaustion", "workload"),
    "C1": ("authentication_attack", "auth_gateway"),
    "C2": ("traffic_flooding", "edge_gateway"),
    "C3": ("scanning_activity", "network_boundary"),
    "C4": ("application_layer_attack", "application"),
    "C5": ("network_anomaly", "host"),
}

RECOMMENDED_ACTION = {
    "D1": "rollback",
    "D2": "scale_up",
    "C1": "rotate_credentials",
    "C2": "rate_limit",
    "C3": "block_source",
    "C4": "quarantine",
    "C5": "manual_investigation",
}


def attach_label_fields(frame: pd.DataFrame, horizon_seconds: int) -> pd.DataFrame:
    frame["incident_label"] = (frame["incident_type"] != "none").astype(int)
    frame["future_incident_label"] = frame["incident_label"].copy()
    frame["future_incident_time"] = pd.NaT
    frame["time_to_incident"] = np.nan
    mask = frame["incident_label"] == 1
    frame.loc[mask, "future_incident_time"] = frame.loc[mask, "event_timestamp"] + pd.to_timedelta(horizon_seconds, unit="s")
    frame.loc[mask, "time_to_incident"] = float(horizon_seconds)
    frame["root_cause_category"] = frame["incident_type"].map(lambda x: ROOT_CAUSE_MAP.get(x, ("none", "none"))[0])
    frame["root_component"] = frame["incident_type"].map(lambda x: ROOT_CAUSE_MAP.get(x, ("none", "none"))[1])
    frame["recommended_action"] = frame["incident_type"].map(lambda x: RECOMMENDED_ACTION.get(x, "no_action"))
    frame.loc[frame["incident_type"] == "none", ["root_cause_category", "root_component", "recommended_action"]] = ["none", "none", "no_action"]
    return frame
