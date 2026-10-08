from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from .config import DEFAULT_CONFIG, SCHEMA_COLUMNS, GenerationConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREDICTION_DIR = PROJECT_ROOT / "data" / "processed" / "prediction"
HORIZON_SECONDS = 900
EVENT_RATE_PER_MINUTE = 0.004
FUTURE_SCENARIOS = ["D1", "D2", "C1", "C2", "C3", "C4", "C5"]
FUTURE_SCENARIO_PROBABILITIES = np.array([0.15, 0.20, 0.15, 0.15, 0.12, 0.11, 0.12])


def _seed(config: GenerationConfig, split: str) -> int:
    raw = f"{config.master_seed}:{config.generator_version}:{config.contract_version}:future_timeline:{split}".encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def _epoch(split: str) -> int:
    return {"train": 1577836800, "validation": 1640995200, "test": 1704067200}[split]


def build_future_timeline(split: str, rows: int, config: GenerationConfig) -> dict:
    rng = np.random.default_rng(_seed(config, split))
    row_seconds = _epoch(split) + np.arange(rows, dtype=np.int64) * 60
    event_mask = rng.random(rows) < EVENT_RATE_PER_MINUTE
    event_offsets = rng.integers(1, 60, size=rows, dtype=np.int64)
    event_seconds = row_seconds[event_mask] + event_offsets[event_mask]
    event_types = rng.choice(FUTURE_SCENARIOS, size=len(event_seconds), p=FUTURE_SCENARIO_PROBABILITIES)
    order = np.argsort(event_seconds)
    return {
        "event_seconds": event_seconds[order],
        "event_types": event_types[order],
        "seed": _seed(config, split),
    }


def transform_split(split: str, config: GenerationConfig) -> dict:
    source = PROJECT_ROOT / "data" / "processed" / f"{split}.parquet"
    output = PREDICTION_DIR / f"{split}.parquet"
    temporary = PREDICTION_DIR / f"{split}.parquet.tmp"
    PREDICTION_DIR.mkdir(parents=True, exist_ok=True)
    temporary.unlink(missing_ok=True)
    output.unlink(missing_ok=True)
    source_file = pq.ParquetFile(source)
    rows = source_file.metadata.num_rows
    timeline = build_future_timeline(split, rows, config)
    event_seconds = timeline["event_seconds"]
    writer = None
    positives = 0
    current_normal_future_incident = 0
    current_incident_future_none = 0
    time_values: list[float] = []
    try:
        start = 0
        for batch in source_file.iter_batches(batch_size=config.batch_size):
            frame = batch.to_pandas()
            timestamps = pd.to_datetime(frame["prediction_timestamp"], utc=True)
            timestamp_seconds = (timestamps - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds().to_numpy(dtype=np.int64)
            positions = np.searchsorted(event_seconds, timestamp_seconds + 1, side="left")
            valid = positions < len(event_seconds)
            next_seconds = np.full(len(frame), np.nan, dtype=float)
            next_seconds[valid] = event_seconds[positions[valid]]
            in_horizon = valid & (next_seconds <= timestamp_seconds + HORIZON_SECONDS)
            frame["future_incident_label"] = in_horizon.astype("int64")
            future_time = pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns, UTC]")
            future_time.loc[in_horizon] = pd.to_datetime(next_seconds[in_horizon], unit="s", utc=True)
            frame["future_incident_time"] = future_time
            time_to_incident = np.full(len(frame), np.nan, dtype=float)
            time_to_incident[in_horizon] = next_seconds[in_horizon] - timestamp_seconds[in_horizon]
            frame["time_to_incident"] = time_to_incident
            frame = frame[SCHEMA_COLUMNS]
            table = pa.Table.from_pandas(frame, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(temporary, table.schema, compression="zstd")
            writer.write_table(table)
            positives += int(in_horizon.sum())
            current_normal_future_incident += int(((frame["incident_label"] == 0) & (frame["future_incident_label"] == 1)).sum())
            current_incident_future_none += int(((frame["incident_label"] == 1) & (frame["future_incident_label"] == 0)).sum())
            time_values.extend(time_to_incident[in_horizon].tolist())
            start += len(frame)
        if writer is not None:
            writer.close()
        parquet = pq.ParquetFile(temporary)
        if parquet.metadata.num_rows != rows or parquet.schema_arrow.names != SCHEMA_COLUMNS:
            raise ValueError(f"{split} prediction output failed row/schema validation")
        pq.read_schema(temporary)
        temporary.replace(output)
    finally:
        if writer is not None:
            writer.close()
        temporary.unlink(missing_ok=True)
    return {
        "rows": rows,
        "positive_future_labels": positives,
        "current_normal_future_incident": current_normal_future_incident,
        "current_incident_future_none": current_incident_future_none,
        "timeline_event_count": int(len(event_seconds)),
        "timeline_scenario_counts": {scenario: int((timeline["event_types"] == scenario).sum()) for scenario in FUTURE_SCENARIOS},
        "seed": timeline["seed"],
        "time_to_incident_min": min(time_values) if time_values else None,
        "time_to_incident_max": max(time_values) if time_values else None,
        "time_to_incident_unique": len(set(time_values)),
        "output": str(output),
    }


def main() -> None:
    config = DEFAULT_CONFIG
    summaries = {split: transform_split(split, config) for split in config.split_order}
    manifest = {
        "status": "GENERATED_PENDING_GATE",
        "generator": "phase5a_independent_future_event_timeline",
        "generator_version": config.generator_version,
        "contract_version": config.contract_version,
        "seed": config.master_seed,
        "observation_window_seconds": config.observation_window_seconds,
        "prediction_horizon_seconds": HORIZON_SECONDS,
        "event_rate_per_minute": EVENT_RATE_PER_MINUTE,
        "schema_columns": len(SCHEMA_COLUMNS),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "splits": summaries,
    }
    for split in config.split_order:
        manifest["splits"][split]["sha256"] = hashlib.sha256((PREDICTION_DIR / f"{split}.parquet").read_bytes()).hexdigest()
    (PROJECT_ROOT / "metadata" / "prediction_dataset_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
