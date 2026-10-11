from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .config import DEFAULT_CONFIG, GenerationConfig
from .generator import SyntheticGenerator
from .validation import validate_generated_dataset


def run_generation(output_dir: str | None = None) -> dict:
    config = GenerationConfig(output_dir=Path(output_dir) if output_dir else DEFAULT_CONFIG.output_dir)
    generator = SyntheticGenerator(config)
    summary = generator.generate_all()
    validation = {}
    for split in config.split_order:
        validation[split] = validate_generated_dataset(summary[split]["file"])
    return {"summary": summary, "validation": validation}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic DevSecOps telemetry dataset.")
    parser.add_argument("--output-dir", type=str, default="data/processed")
    args = parser.parse_args()
    result = run_generation(args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
