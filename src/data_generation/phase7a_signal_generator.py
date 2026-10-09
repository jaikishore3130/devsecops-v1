from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .config import SCHEMA_COLUMNS, GenerationConfig

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_DIR = ROOT / "data" / "processed"
FULL_OUTPUT_DIR = ROOT / "data" / "processed" / "prediction_v2"
HORIZON_SECONDS = 900
FUTURE_TYPES = ["D1", "D2", "C1", "C2", "C3", "C4", "C5"]
TYPE_PROBABILITIES = np.array([0.15, 0.20, 0.15, 0.15, 0.12, 0.11, 0.12])


def _seed(config: GenerationConfig, split: str, start: int) -> int:
    raw = f"{config.master_seed}:{config.generator_version}:phase7a:{split}:{start}".encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def _modify_warning_signals(frame: pd.DataFrame, risk: np.ndarray, future_type: np.ndarray, rng: np.random.Generator) -> None:
    severity = np.clip(risk + rng.normal(0.0, 0.10, len(frame)), 0.0, 1.0)
    frame["cpu_utilization"] = np.clip(frame["cpu_utilization"].fillna(0.5).to_numpy() + 0.14 * severity + rng.normal(0, 0.025, len(frame)), 0, 1)
    frame["memory_utilization"] = np.clip(frame["memory_utilization"].fillna(0.5).to_numpy() + 0.12 * severity + rng.normal(0, 0.025, len(frame)), 0, 1)
    frame["queue_length"] = np.maximum(0, frame["queue_length"].fillna(0).to_numpy() + rng.poisson(18 * severity))
    frame["scheduling_delay_seconds"] = np.maximum(0, frame["scheduling_delay_seconds"].fillna(0).to_numpy() + 45 * severity + rng.normal(0, 5, len(frame)))
    frame["request_rate"] = np.maximum(0, frame["request_rate"].fillna(0).to_numpy() + 180 * severity * np.isin(future_type, ["C2", "C4"]))
    frame["source_count"] = np.maximum(0, frame["source_count"].fillna(0).to_numpy() + rng.poisson(14 * severity * np.isin(future_type, ["C1", "C2"])))
    frame["unique_destination_ports"] = np.maximum(0, frame["unique_destination_ports"].fillna(0).to_numpy() + rng.poisson(8 * severity * (future_type == "C3")))
    frame["auth_attempts"] = np.maximum(0, frame["auth_attempts"].fillna(0).to_numpy() + rng.poisson(16 * severity * (future_type == "C1")))
    frame["retry_count"] = np.maximum(0, frame["retry_count"].fillna(0).to_numpy() + rng.poisson(5 * severity * (future_type == "D1")))
    frame["restart_count"] = np.maximum(0, frame["restart_count"].fillna(0).to_numpy() + rng.poisson(3 * severity * np.isin(future_type, ["D2", "C5"])))
    frame["anomaly_score"] = frame["anomaly_score"].fillna(0).to_numpy() + 0.55 * severity + rng.normal(0, 0.45, len(frame))
    frame["cpu_delta"] = np.clip(frame["cpu_delta"].fillna(0).to_numpy() + 0.10 * severity + rng.normal(0, 0.025, len(frame)), -1, 1)
    frame["memory_slope"] = frame["memory_slope"].fillna(0).to_numpy() + 0.004 * severity + rng.normal(0, 0.001, len(frame))


def _generate_batch(frame: pd.DataFrame, split: str, start: int, config: GenerationConfig) -> pd.DataFrame:
    rng = np.random.default_rng(_seed(config, split, start))
    row_count = len(frame)
    latent_risk = rng.beta(2.0, 5.0, row_count)
    future_type = rng.choice(np.array(FUTURE_TYPES, dtype=object), row_count, p=TYPE_PROBABILITIES)
    scenario_state = np.select([latent_risk < 0.30, latent_risk < 0.55, latent_risk < 0.78], ["NORMAL", "EARLY_SIGNAL", "DEGRADATION"], default="ESCALATION")
    event_probability = np.clip(0.012 + 0.34 * latent_risk + rng.normal(0, 0.035, row_count), 0.002, 0.80)
    event_occurs = rng.random(row_count) < event_probability
    future_type = np.where(event_occurs, future_type, "NONE")
    _modify_warning_signals(frame, latent_risk, future_type, rng)
    timestamps = pd.to_datetime(frame["prediction_timestamp"], utc=True)
    lead_time = np.clip((HORIZON_SECONDS * (1.0 - latent_risk) ** 0.8 + rng.normal(0, 90, row_count)).astype(int), 1, HORIZON_SECONDS - 1)
    future_label = event_occurs.astype("int64")
    frame["future_incident_label"] = future_label
    future_time = pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns, UTC]")
    future_time.loc[event_occurs] = timestamps.loc[event_occurs] + pd.to_timedelta(lead_time[event_occurs], unit="s")
    frame["future_incident_time"] = future_time
    frame["time_to_incident"] = np.where(event_occurs, lead_time.astype(float), np.nan)
    frame["future_incident_type"] = np.where(event_occurs, future_type, "NONE")
    frame["latent_scenario_state"] = scenario_state
    return frame


def generate(output_dir: Path, split_sizes: dict[str, int], config: GenerationConfig) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for split, requested_rows in split_sizes.items():
        source = ORIGINAL_DIR / f"{split}.parquet"
        output = output_dir / f"{split}.parquet"
        temporary = output_dir / f"{split}.parquet.tmp"
        temporary.unlink(missing_ok=True)
        source_file = pq.ParquetFile(source)
        writer = None
        generated = 0
        try:
            for batch in source_file.iter_batches(batch_size=config.batch_size):
                if generated >= requested_rows:
                    break
                frame = batch.to_pandas().iloc[: requested_rows - generated].copy()
                frame = _generate_batch(frame, split, generated, config)
                table = pa.Table.from_pandas(frame, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(temporary, table.schema, compression="zstd")
                writer.write_table(table)
                generated += len(frame)
            if writer is not None:
                writer.close()
            parquet = pq.ParquetFile(temporary)
            if generated != requested_rows or parquet.metadata.num_rows != requested_rows:
                raise ValueError(f"{split}: expected {requested_rows}, got {generated}")
            temporary.replace(output)
        finally:
            if writer is not None:
                writer.close()
            temporary.unlink(missing_ok=True)
        summary[split] = {"rows": generated, "columns": len(pq.ParquetFile(output).schema_arrow.names), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "file": str(output)}
    return summary


def main() -> None:
    config = GenerationConfig()
    sizes = {"train": 1_000_000, "validation": 50_000, "test": 50_000}
    summary = generate(FULL_OUTPUT_DIR, sizes, config)
    manifest = {"status": "GENERATED_PENDING_GATE", "generator_version": "7A-latent-scenario-v1", "seed": config.master_seed, "schema_fields": len(SCHEMA_COLUMNS) + 2, "observation_window_seconds": 900, "prediction_horizon_seconds": HORIZON_SECONDS, "split_sizes": sizes, "generated_at": datetime.now(timezone.utc).isoformat(), "splits": summary}
    (ROOT / "metadata" / "prediction_v2_config.yaml").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
