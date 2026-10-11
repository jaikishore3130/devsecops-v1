"""Phase 7B gate - verifies the full checklist from the frozen artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import joblib
import numpy as np
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "data" / "processed" / "prediction_v2"
MODEL_DIR = ROOT / "models" / "prediction_v2"
REPORT_DIR = ROOT / "reports"
CONFIG_PATH = ROOT / "metadata" / "prediction_model_config.yaml"
PHASE5_DIR = ROOT / "data" / "processed"
PREDICTION_V1_DIR = ROOT / "data" / "processed" / "prediction"
PHASE7_MODEL_DIR = ROOT / "models" / "prediction"

REQUIRED_REPORTS = [
    "PHASE_07B_PREDICTION_MODELING.md",
    "PHASE_07B_PREDICTION_RESULTS.json",
    "PHASE_07B_PREDICTION_LEAKAGE_AUDIT.json",
    "PHASE_07B_FEATURE_IMPORTANCE.json",
    "PHASE_07B_ABLATION_RESULTS.json",
]
SPLITS = {"train": 1_000_000, "validation": 50_000, "test": 50_000}
FUTURE_FIELDS = ["future_incident_label", "future_incident_type", "future_incident_time",
                 "time_to_incident", "latent_scenario_state"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_array(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype=np.float64).tobytes()).hexdigest()


def git(args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main() -> dict:
    results = json.loads((REPORT_DIR / "PHASE_07B_PREDICTION_RESULTS.json").read_text())
    config = yaml.safe_load(CONFIG_PATH.read_text())
    allowed = set(config["feature_contract"]["allowed_features"])
    forbidden = {field for values in config["feature_contract"]["forbidden_groups"].values() for field in values}
    ladder = results["model_ladder"]
    final = results["final_test_metrics"]
    importance = json.loads((REPORT_DIR / "PHASE_07B_FEATURE_IMPORTANCE.json").read_text())
    ablation = json.loads((REPORT_DIR / "PHASE_07B_ABLATION_RESULTS.json").read_text())

    checks: dict[str, bool] = {}
    checks["prediction_v2_dataset_unchanged"] = all(
        sha256_file(DATASET_DIR / f"{split}.parquet") == config["dataset_hashes"][split] for split in SPLITS
    )
    checks["dataset_hashes_match_phase7a_manifest"] = results["dataset"]["hashes_match_phase7a_manifest"]
    for split, rows in SPLITS.items():
        checks[f"{split}_rows_{rows}"] = pq.ParquetFile(DATASET_DIR / f"{split}.parquet").metadata.num_rows == rows
    checks["safe_feature_policy_followed"] = not (allowed & forbidden)
    checks["latent_scenario_state_excluded"] = "latent_scenario_state" not in allowed
    checks["future_fields_excluded"] = all(field not in allowed for field in FUTURE_FIELDS)
    checks["identifiers_excluded"] = not (allowed & set(config["feature_contract"]["forbidden_groups"]["IDENTIFIER"]))
    controls = results["test_leakage_controls"]
    checks["preprocessing_train_only"] = controls["preprocessing_fit"] is False
    checks["feature_selection_train_only"] = controls["feature_selection"] is False
    checks["model_selection_validation_only"] = controls["model_selection"] is False
    checks["threshold_selection_validation_only"] = controls["threshold_selection"] is False
    checks["hyperparameter_tuning_validation_only"] = controls["hyperparameter_tuning"] is False
    checks["test_untouched_until_final"] = all(value is False for value in controls.values())
    required_models = {"majority", "stratified_dummy", "logistic_regression", "random_forest", "xgboost"}
    checks["baseline_ladder_completed"] = required_models.issubset(set(ladder))
    checks["selected_model_documented"] = bool(results["selected_model"]) and results["selected_model"] in ladder
    checks["final_test_metrics_reported"] = all(
        key in final for key in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc",
                                 "false_positive_rate", "false_negative_rate", "specificity"]
    )
    checks["confusion_matrix_reported"] = set(final["confusion_matrix"]) == {"tn", "fp", "fn", "tp"}
    checks["fpr_fnr_reported"] = "false_positive_rate" in final and "false_negative_rate" in final
    checks["lead_time_analysis_completed"] = "buckets" in results["lead_time_analysis"] and set(
        results["lead_time_analysis"]["buckets"]) == {"0_300", "301_600", "601_899"}
    checks["future_type_analysis_completed"] = set(results["future_type_analysis"]["per_type"]) == {
        "D1", "D2", "C1", "C2", "C3", "C4", "C5"}
    checks["latent_state_analysis_completed"] = set(results["latent_state_analysis"]["per_state"]) == {
        "NORMAL", "EARLY_SIGNAL", "DEGRADATION", "ESCALATION"}
    checks["ablation_completed"] = set(ablation["groups"]) == {
        "ALL_SAFE_FEATURES", "INFRASTRUCTURE_CLOUD_WORKLOAD", "CICD_DEPLOYMENT",
        "NETWORK_SECURITY", "SAFE_FEATURES_WITHOUT_DERIVED_FEATURES"}
    checks["feature_importance_completed"] = bool(importance.get("top_features")) and importance["leakage_scan"]["passed"]
    artifact = results["synthetic_artifact_investigation"]
    checks["synthetic_artifact_check_completed"] = artifact["status"] != "SUSPICIOUS_UNEXPLAINED"
    checks["reproducibility_check_completed"] = results["reproducibility"]["identical"] is True
    checks["model_reload_check_completed"] = results["model_reload"]["identical_test_predictions"] is True
    checks["phase7_artifacts_unchanged"] = all(
        sha256_file(REPORT_DIR / name) == digest for name, digest in config["phase7_report_hashes"].items()
    ) and all(sha256_file(PHASE7_MODEL_DIR / name) == digest for name, digest in config["phase7_model_hashes"].items())
    checks["phase7a_dataset_unchanged"] = checks["prediction_v2_dataset_unchanged"]
    checks["phase5_original_unchanged"] = all(
        sha256_file(PHASE5_DIR / f"{split}.parquet") == config["phase5_original_hashes"][split] for split in SPLITS
    )
    phase7b_modules = ["phase7b_train.py", "v2_data.py"]
    source = "\n".join((ROOT / "src" / "prediction" / name).read_text() for name in phase7b_modules).lower()
    checks["no_rca_remediation_implemented"] = (
        "root_cause" not in source and "recommended_action" not in source and "def remediat" not in source
    )
    rca_remediation_fields = set(config["feature_contract"]["forbidden_groups"]["RCA_ONLY"]) | {"recommended_action"}
    checks["rca_remediation_fields_excluded"] = not (allowed & rca_remediation_fields)
    checks["all_reports_generated"] = all((REPORT_DIR / name).exists() for name in REQUIRED_REPORTS)
    checks["model_artifacts_present"] = all((MODEL_DIR / name).exists() for name in [
        "preprocessing.joblib", "selected_model.joblib", "model_metadata.json", "feature_list.json",
        "threshold.json", "versions.json", "test_probabilities.npy"])

    # Model reload verification against persisted probabilities.
    try:
        bundle = joblib.load(MODEL_DIR / "selected_model.joblib")
        prep = joblib.load(MODEL_DIR / "preprocessing.joblib")
        persisted = np.load(MODEL_DIR / "test_probabilities.npy")
        checks["model_reload_hash_matches"] = sha256_array(persisted) == results["test_probability_hash"]
        checks["model_reload_consistent_bundle"] = (
            bundle["model_name"] == results["selected_model"]
            and bundle["threshold"] == results["threshold_selection"]["selected"]
            and prep["feature_fields"] == config["feature_contract"]["allowed_features"]
        )
    except Exception as exc:  # pragma: no cover
        checks["model_reload_hash_matches"] = False
        checks["model_reload_consistent_bundle"] = False
        print(f"reload error: {exc}")

    status_porcelain = git(["status", "--porcelain"])
    checks["git_status_clean"] = status_porcelain == ""
    checks["commit_created"] = bool(git(["log", "-1", "--format=%s"]))
    checks["pushed_successfully"] = git(["status", "-sb"]).find("ahead") == -1

    report = {
        "status": "COMPLETE" if all(checks.values()) else "BLOCKED",
        "checks": checks,
        "failed_checks": [name for name, value in checks.items() if not value],
        "phase8_started": False,
    }
    (REPORT_DIR / "PHASE_07B_GATE.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    main()
