from __future__ import annotations

import csv
import uuid
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "metadata" / "synthetic_schema.csv"

INCIDENT_TYPES = ["none", "D1", "D2", "C1", "C2", "C3", "C4", "C5"]
SCENARIO_LABELS = ["none", "D1", "D2", "C1", "C2", "C3", "C4", "C5"]


def _schema_fields() -> list[str]:
    with SCHEMA_PATH.open(newline="") as handle:
        return [row["field_name"] for row in csv.DictReader(handle)]


SCHEMA_COLUMNS = _schema_fields()
ROOT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "devsecops-synthetic-generator")


@dataclass
class GenerationConfig:
    master_seed: int = 20261008
    generator_version: str = "1.0.0"
    contract_version: str = "1.0.0"
    schema_version: str = "1.0.0"
    split_sizes: dict[str, int] = field(
        default_factory=lambda: {"train": 1_000_000, "validation": 50_000, "test": 50_000}
    )
    scenario_probabilities: dict[str, float] = field(
        default_factory=lambda: {
            "none": 0.72,
            "D1": 0.06,
            "D2": 0.07,
            "C1": 0.04,
            "C2": 0.04,
            "C3": 0.03,
            "C4": 0.02,
            "C5": 0.02,
        }
    )
    observation_window_seconds: int = 900
    prediction_horizon_seconds: int = 900
    batch_size: int = 100_000
    output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data" / "processed")
    metadata_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "metadata")
    reports_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "reports")

    @property
    def split_order(self) -> list[str]:
        return ["train", "validation", "test"]


DEFAULT_CONFIG = GenerationConfig()
