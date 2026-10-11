from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


TEXT_EXT = {".md", ".txt", ".log", ".proto", ".bib", ".yaml", ".yml", ".json", ".csv", ".tsv"}


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sniff_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8", errors="ignore")[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        return dialect.delimiter
    except csv.Error:
        return ","


def csv_stats(path: Path) -> dict[str, Any]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else sniff_delimiter(path)
    rows = 0
    headers: list[str] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for i, row in enumerate(reader):
            if i == 0:
                headers = row
            rows += 1
    return {
        "delimiter": repr(delimiter),
        "rows_including_header": rows,
        "record_count_estimate": max(rows - 1, 0),
        "column_count": len(headers),
        "columns": headers,
    }


def text_stats(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    return {
        "line_count": len(lines),
        "char_count": len(text),
        "first_nonempty_line": next((ln.strip() for ln in lines if ln.strip()), ""),
    }


def file_stats(path: Path, base_dir: Path) -> dict[str, Any]:
    absolute_path = (base_dir / path).resolve()
    entry: dict[str, Any] = {
        "name": path.name,
        "relative_path": str(path),
        "extension": path.suffix.lower(),
        "size_bytes": absolute_path.stat().st_size,
        "sha256": sha256sum(absolute_path),
    }
    ext = path.suffix.lower()
    try:
        if ext in {".csv", ".tsv"}:
            entry["tabular_profile"] = csv_stats(absolute_path)
        elif ext in TEXT_EXT:
            entry["text_profile"] = text_stats(absolute_path)
    except Exception as exc:  # noqa: BLE001
        entry["profile_error"] = str(exc)
    return entry


def dataset_profile(dataset_dir: Path, dataset_name: str) -> dict[str, Any]:
    files = [p for p in dataset_dir.rglob("*") if p.is_file()]
    profiles = [file_stats(p.relative_to(dataset_dir), dataset_dir) for p in files]
    return {
        "dataset_name": dataset_name,
        "dataset_dir": str(dataset_dir),
        "file_count": len(files),
        "total_size_bytes": sum(p.stat().st_size for p in files),
        "profiles": profiles,
    }


def markdown_report(profile: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {profile['dataset_name']} AUDIT")
    lines.append("")
    lines.append("## Local Artifact Summary")
    lines.append(f"- Local path: `{profile['dataset_dir']}`")
    lines.append(f"- File count: {profile['file_count']}")
    lines.append(f"- Total size (bytes): {profile['total_size_bytes']}")
    lines.append("")
    lines.append("## File-Level Evidence")
    lines.append("| File | Extension | Size (bytes) | SHA256 | Notes |")
    lines.append("|---|---|---:|---|---|")
    for item in profile["profiles"]:
        notes = []
        if "tabular_profile" in item:
            t = item["tabular_profile"]
            notes.append(f"rows~{t['record_count_estimate']}; cols={t['column_count']}")
        if "text_profile" in item:
            t = item["text_profile"]
            first = t["first_nonempty_line"].replace("|", "\\|")[:80]
            notes.append(f"lines={t['line_count']}; first='{first}'")
        if "profile_error" in item:
            notes.append(f"PROFILE_ERROR={item['profile_error']}")
        lines.append(
            f"| `{item['relative_path']}` | `{item['extension'] or 'NONE'}` | {item['size_bytes']} | `{item['sha256']}` | {'; '.join(notes) if notes else 'NOT PROFILED'} |"
        )
    lines.append("")
    lines.append("## Audit Gaps")
    lines.append("- This report audits only locally acquired artifacts.")
    lines.append("- If raw dataset files are unavailable locally, record-level statistics remain NOT VERIFIED.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only dataset artifact auditor")
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir).resolve()
    profile = dataset_profile(dataset_dir, args.dataset_name)

    Path(args.output_json).write_text(json.dumps(profile, indent=2), encoding="utf-8")
    Path(args.output_md).write_text(markdown_report(profile), encoding="utf-8")


if __name__ == "__main__":
    main()
