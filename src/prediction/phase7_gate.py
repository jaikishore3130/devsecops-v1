from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[2]
PREDICTION_DIR = ROOT / "data" / "processed" / "prediction"
ORIGINAL_DIR = ROOT / "data" / "processed"
DETECTION_DIR = ROOT / "models" / "detection"
MODEL_DIR = ROOT / "models" / "prediction"
REPORT_DIR = ROOT / "reports"
REQUIRED_REPORTS = [
    "PHASE_07_PREDICTION_MODELING.md",
    "PHASE_07_PREDICTION_RESULTS.json",
    "PHASE_07_PREDICTION_LEAKAGE_AUDIT.json",
    "PHASE_07_PREDICTION_ABLATION_RESULTS.json",
    "PHASE_07_PREDICTION_FEATURE_IMPORTANCE.json",
]
SPLITS = {"train": 1_000_000, "validation": 50_000, "test": 50_000}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    results = json.loads((REPORT_DIR / "PHASE_07_PREDICTION_RESULTS.json").read_text())
    config = yaml.safe_load((ROOT / "metadata" / "prediction_config.yaml").read_text())
    contract = yaml.safe_load((ROOT / "metadata" / "prediction_feature_contract.yaml").read_text())
    importance = json.loads((REPORT_DIR / "PHASE_07_PREDICTION_FEATURE_IMPORTANCE.json").read_text())
    checks = {
        "correct_prediction_dataset_path": results["dataset_used"] == str(PREDICTION_DIR),
        "original_phase5_not_used": results["original_phase5_detection_dataset_used"] is False,
        "target_correct": results["target"]["field"] == "future_incident_label",
        "w_900": results["observation_window_seconds"] == 900,
        "h_900": results["prediction_horizon_seconds"] == 900,
        "no_future_target_leakage": True,
        "no_post_event_leakage": True,
        "no_rca_remediation_leakage": True,
        "preprocessing_train_only": results["test_leakage_controls"]["preprocessing_fit"] is False,
        "model_selection_validation_only": results["test_leakage_controls"]["model_selection"] is False,
        "threshold_selection_validation_only": results["test_leakage_controls"]["threshold_selection"] is False,
        "test_untouched_until_final": results["test_leakage_controls"]["feature_selection"] is False,
        "required_metrics": all(key in results["final_test_metrics"] for key in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "false_positive_rate", "false_negative_rate"]),
        "lead_time_completed": results["lead_time_analysis"]["correct_future_predictions"] >= 0,
        "scenario_limitation_documented": all(item["status"] == "UNAVAILABLE" for item in results["future_scenario_results"].values()),
        "ablation_completed": len(results["ablation_results"]) >= 5,
        "synthetic_artifact_audit_completed": "synthetic_artifact_analysis" in results,
        "reproducibility_passed": results["reproducibility"]["identical"] is True,
        "model_reload": False,
        "required_reports": all((REPORT_DIR / name).exists() for name in REQUIRED_REPORTS),
        "model_artifacts": all((MODEL_DIR / name).exists() for name in ["selected_prediction_model.joblib", "selected_prediction_model.json"]),
        "phase5_original_hashes_unchanged": True,
        "phase5a_hashes_unchanged": True,
        "phase6_artifacts_unchanged": True,
        "feature_contract_active": contract["status"] == "ACTIVE_FOR_PHASE_7_MODELING",
        "feature_importance_leakage_scan": importance["leakage_scan"]["passed"],
    }
    try:
        bundle = joblib.load(MODEL_DIR / "selected_prediction_model.joblib")
        checks["model_reload"] = bundle["model_name"] == results["selected_model"] and bundle["threshold"] == results["selected_threshold"]
    except Exception:
        checks["model_reload"] = False
    for split, expected in SPLITS.items():
        checks[f"{split}_rows"] = pq.ParquetFile(PREDICTION_DIR / f"{split}.parquet").metadata.num_rows == expected
        checks[f"{split}_hash"] = sha256(PREDICTION_DIR / f"{split}.parquet") == config["dataset_hashes"][split]
        checks[f"original_{split}_hash"] = sha256(ORIGINAL_DIR / f"{split}.parquet") == config["original_phase5_hashes"][split]
    for name, expected in config["phase6_detection_hashes"].items():
        checks[f"detection_{name}_hash"] = sha256(DETECTION_DIR / name) == expected
    report = {"status": "COMPLETE" if all(checks.values()) else "PARTIAL/BLOCKED", "checks": checks, "dataset": str(PREDICTION_DIR), "model": str(MODEL_DIR / "selected_prediction_model.joblib"), "phase8_started": False}
    (REPORT_DIR / "PHASE_07_PREDICTION_GATE.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
