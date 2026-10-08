from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT = REPO_ROOT / "src" / "data_audit" / "audit_dataset.py"
REPORT_DIR = REPO_ROOT / "reports" / "dataset_audit"

DATASETS = [
    ("TRAVISTORRENT", REPO_ROOT / "data" / "external" / "devops" / "travistorrent"),
    ("ALIBABA_CLUSTERDATA", REPO_ROOT / "data" / "external" / "devops" / "alibaba_clusterdata"),
    ("GOOGLE_CLUSTER_DATA", REPO_ROOT / "data" / "external" / "devops" / "google_cluster_data"),
    ("CIC_IDS2017", REPO_ROOT / "data" / "external" / "cybersecurity" / "cic_ids2017"),
    ("CIC_DDOS2019", REPO_ROOT / "data" / "external" / "cybersecurity" / "cic_ddos2019"),
    ("UNSW_NB15", REPO_ROOT / "data" / "external" / "cybersecurity" / "unsw_nb15"),
    ("ADFA_LD", REPO_ROOT / "data" / "external" / "cybersecurity" / "adfa_ld"),
]


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    for dataset_name, dataset_dir in DATASETS:
        md_path = REPORT_DIR / f"{dataset_name}_AUDIT.md"
        json_path = REPORT_DIR / f"{dataset_name}_AUDIT.json"
        cmd = [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--dataset-name",
            dataset_name,
            "--dataset-dir",
            str(dataset_dir),
            "--output-md",
            str(md_path),
            "--output-json",
            str(json_path),
        ]
        subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
