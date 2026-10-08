from __future__ import annotations

import pandas as pd


def build_temporal_fields(event_timestamp: pd.Series, observation_window_seconds: int, prediction_horizon_seconds: int) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    window_start = event_timestamp - pd.to_timedelta(observation_window_seconds, unit="s")
    window_end = event_timestamp
    prediction_timestamp = event_timestamp
    observation_age_seconds = (prediction_timestamp - window_start).dt.total_seconds()
    return window_start, window_end, prediction_timestamp, observation_age_seconds


def split_time_ranges(split: str, rows: int, start_epoch: int) -> tuple[pd.Series, pd.Series]:
    timestamps = pd.to_datetime(start_epoch + pd.Series(range(rows)) * 60, unit="s", utc=True)
    return timestamps, timestamps + pd.to_timedelta(900, unit="s")
