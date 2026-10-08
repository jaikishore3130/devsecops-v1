from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator


TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "latin-1")
TIMESTAMP_HINTS = ("time", "timestamp", "date", "datetime", "start", "end")
LABEL_HINTS = ("label", "class", "attack", "status", "failure", "target", "outcome")
GROUP_HINTS = {
    "project": ("project", "repo", "repository"),
    "build": ("build", "job", "run"),
    "host": ("host", "machine", "node"),
    "service": ("service", "instance", "task"),
    "source_ip": ("src_ip", "source_ip", "srcip"),
    "destination_ip": ("dst_ip", "destination_ip", "dstip"),
    "session": ("session", "flow", "trace", "sequence"),
}


def open_text(path: Path):
    for encoding in TEXT_ENCODINGS:
        try:
            return path.open("r", encoding=encoding, newline="")
        except UnicodeDecodeError:
            continue
    return path.open("r", encoding="utf-8", errors="replace", newline="")


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_timestamp(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_number(value: str) -> bool:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(parsed)


def row_hash(row: dict[str, str]) -> str:
    payload = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def iter_rows(path: Path, columns: list[str] | None = None) -> Iterator[dict[str, str]]:
    suffix = path.suffix.lower()
    with open_text(path) as handle:
        if suffix in {".jsonl", ".ndjson"}:
            for line in handle:
                if line.strip():
                    value = json.loads(line)
                    if isinstance(value, dict):
                        yield {str(key): "" if item is None else str(item) for key, item in value.items()}
            return
        delimiter = "\t" if suffix == ".tsv" else ","
        if columns:
            reader = csv.reader(handle, delimiter=delimiter)
            for values in reader:
                if values:
                    yield {column: value for column, value in zip(columns, values)}
            return
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            yield {str(key): "" if value is None else value for key, value in row.items()}


def infer_columns(rows: Iterable[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    columns: list[str] = []
    missing = Counter()
    unique_values: dict[str, set[str]] = defaultdict(set)
    numeric_values: dict[str, list[float]] = defaultdict(list)
    numeric_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "mean": 0.0, "m2": 0.0, "min": math.inf, "max": -math.inf})
    timestamp_values: dict[str, list[datetime]] = defaultdict(list)
    label_values: dict[str, Counter[str]] = defaultdict(Counter)
    group_values: dict[str, set[str]] = defaultdict(set)
    total = 0
    exact_hashes: set[str] = set()
    exact_duplicates = 0
    for row in rows:
        total += 1
        if not columns:
            columns = list(row)
        digest = row_hash(row)
        if digest in exact_hashes:
            exact_duplicates += 1
        elif len(exact_hashes) < 2_000_000:
            exact_hashes.add(digest)
        for column in columns:
            value = row.get(column, "").strip()
            if not value:
                missing[column] += 1
                continue
            if len(unique_values[column]) < 100_000:
                unique_values[column].add(value)
            if is_number(value):
                number = float(value)
                stats = numeric_stats[column]
                stats["count"] += 1
                delta = number - stats["mean"]
                stats["mean"] += delta / stats["count"]
                stats["m2"] += delta * (number - stats["mean"])
                stats["min"] = min(stats["min"], number)
                stats["max"] = max(stats["max"], number)
                if len(numeric_values[column]) < 100_000:
                    numeric_values[column].append(number)
            if any(hint in column.lower() for hint in TIMESTAMP_HINTS):
                parsed = parse_timestamp(value)
                if parsed is not None:
                    timestamp_values[column].append(parsed)
            if any(hint in column.lower() for hint in LABEL_HINTS):
                label_values[column][value] += 1
            for group_name, hints in GROUP_HINTS.items():
                if any(hint in column.lower() for hint in hints):
                    if len(group_values[group_name]) < 100_000:
                        group_values[group_name].add(value)
    schema: list[dict[str, Any]] = []
    for column in columns:
        values = numeric_values.get(column, [])
        stats = numeric_stats.get(column, {})
        timestamps = timestamp_values.get(column, [])
        schema.append({
            "column": column,
            "inferred_type": "numeric" if values else "categorical_or_text",
            "missing_count": missing[column],
            "missing_percentage": round((missing[column] / total) * 100, 6) if total else 0,
            "unique_count_observed": len(unique_values[column]),
            "unique_count_capped": len(unique_values[column]) >= 100_000,
            "numeric_count": int(stats.get("count", 0)),
            "min": stats.get("min") if stats else None,
            "max": stats.get("max") if stats else None,
            "mean": stats.get("mean") if stats else None,
            "median_sample": statistics.median(values) if values else None,
            "standard_deviation": math.sqrt(stats["m2"] / (stats["count"] - 1)) if stats.get("count", 0) > 1 else None,
            "timestamp_min": min(timestamps).isoformat() if timestamps else None,
            "timestamp_max": max(timestamps).isoformat() if timestamps else None,
            "label_distribution": dict(label_values[column].most_common(50)),
            "leakage_class": classify_leakage(column),
        })
    labels = [{"column": column, "counts": dict(counter)} for column, counter in label_values.items() if counter]
    groups = [{"group": name, "unique_count_observed": len(values), "count_capped": len(values) >= 100_000} for name, values in group_values.items() if values]
    return schema, [{"exact_duplicates": exact_duplicates, "unique_hashes_observed": len(exact_hashes), "group_identifiers": groups, "record_count": total}, *labels]


def classify_leakage(column: str) -> str:
    name = column.lower()
    if any(token in name for token in ("label", "class", "target", "attack_cat", "status", "outcome")):
        return "LABEL-DERIVED"
    if any(token in name for token in ("finish", "end", "recovery", "remediation", "result")):
        return "POST-EVENT"
    if any(token in name for token in ("failure", "incident", "event")):
        return "CONDITIONALLY SAFE"
    return "CONDITIONALLY SAFE" if any(hint in name for hint in TIMESTAMP_HINTS) else "SAFE"


def profile_file(path: Path, columns: list[str] | None = None) -> dict[str, Any]:
    schema, summaries = infer_columns(iter_rows(path, columns))
    summary = summaries[0] if summaries else {"record_count": 0, "exact_duplicates": 0}
    return {
        "file": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256sum(path),
        "record_count": summary["record_count"],
        "schema": schema,
        "duplicate_analysis": {
            "exact_duplicates": summary["exact_duplicates"],
            "duplicate_percentage": round((summary["exact_duplicates"] / summary["record_count"]) * 100, 6) if summary["record_count"] else 0,
            "near_duplicates": "NOT_COMPUTED",
            "sequence_overlap_risk": "REQUIRES_DATASET_SPECIFIC_SEQUENCE_KEYS",
            "cross_split_overlap_risk": "REQUIRES_GROUP_AWARE_SPLIT",
        },
        "group_identifiers": summary.get("group_identifiers", []),
        "label_columns": [item for item in summaries[1:] if "counts" in item],
        "timestamp_columns": [item["column"] for item in schema if item["timestamp_min"]],
    }


def profile_dataset(dataset_dir: Path, columns: list[str] | None = None) -> dict[str, Any]:
    files = [path for path in dataset_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".csv", ".tsv", ".jsonl", ".ndjson"}]
    profiles = [profile_file(path, columns) for path in files]
    return {"dataset_dir": str(dataset_dir), "file_count": len(files), "files": profiles}


def read_columns(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunked record-level dataset profiler")
    parser.add_argument("--dataset-dir", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--columns-file", type=Path, help="Documented column names for headerless CSV/TSV files")
    args = parser.parse_args()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    columns = read_columns(args.columns_file) if args.columns_file else None
    args.output_json.write_text(json.dumps(profile_dataset(args.dataset_dir, columns), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()