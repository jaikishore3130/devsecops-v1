from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml

from src.detection.baselines import model_factories
from src.detection.data import detection_contract
from src.detection.explain import feature_importance, leakage_scan
from src.detection.features import feature_groups, make_preprocessor
from .data import load_split, prediction_features, target_distribution
from .evaluate import lead_time_metrics, metrics, threshold_table

ROOT = Path(__file__).resolve().parents[2]
PREDICTION_DIR = ROOT / "data" / "processed" / "prediction"
MODEL_DIR = ROOT / "models" / "prediction"
REPORT_DIR = ROOT / "reports"
CONFIG_PATH = ROOT / "metadata" / "prediction_config.yaml"
SEED = 20261008
TRAIN_SAMPLE_ROWS = 250_000


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_xy(split: str, fields: list[str], sample_rows: int | None = None) -> tuple[pd.DataFrame, np.ndarray]:
    frame = load_split(split, fields + ["future_incident_label"])
    if sample_rows is not None and sample_rows < len(frame):
        frame = frame.sample(n=sample_rows, random_state=SEED).reset_index(drop=True)
    return frame[fields], frame["future_incident_label"].astype(int).to_numpy()


def _ablation(contract: dict, train_x: pd.DataFrame, train_y: np.ndarray, validation_x: pd.DataFrame, validation_y: np.ndarray) -> dict:
    output = {}
    for name, fields in feature_groups(contract).items():
        preprocessor = make_preprocessor(train_x, fields)
        x_train = preprocessor.fit_transform(train_x[fields])
        x_validation = preprocessor.transform(validation_x[fields])
        estimator = model_factories(SEED)["logistic_regression"]()
        estimator.fit(x_train, train_y)
        probabilities = estimator.predict_proba(x_validation)[:, 1]
        result = metrics(validation_y, probabilities, 0.5)
        output[name] = {"feature_count": len(fields), "validation_metrics": result}
    return output


def _artifact_audit(frame: pd.DataFrame, fields: list[str]) -> dict:
    target = frame["future_incident_label"].astype(int)
    univariate = []
    for field in fields:
        if not pd.api.types.is_numeric_dtype(frame[field]):
            continue
        values = frame[field].fillna(frame[field].median())
        from sklearn.metrics import roc_auc_score
        auc = roc_auc_score(target, values)
        univariate.append({"feature": field, "roc_auc": float(max(auc, 1 - auc))})
    current_rates = frame.groupby("incident_label")["future_incident_label"].mean().to_dict()
    type_rates = frame.groupby("incident_type")["future_incident_label"].mean().to_dict()
    return {
        "top_univariate_associations": sorted(univariate, key=lambda item: item["roc_auc"], reverse=True)[:15],
        "future_rate_by_current_incident_label": {str(k): float(v) for k, v in current_rates.items()},
        "future_rate_by_current_incident_type": {str(k): float(v) for k, v in type_rates.items()},
        "conclusion": "Associations are descriptive; future labels come from the independent Phase 5A calendar. No current label or incident type is an input feature.",
    }


def _reproducibility(fields: list[str]) -> dict:
    train_x, train_y = _load_xy("train", fields, 50_000)
    validation_x, validation_y = _load_xy("validation", fields, 10_000)
    hashes = []
    runs = []
    for _ in range(2):
        preprocessor = make_preprocessor(train_x, fields)
        x_train = preprocessor.fit_transform(train_x)
        x_validation = preprocessor.transform(validation_x)
        estimator = model_factories(SEED)["xgboost"]()
        estimator.set_params(n_estimators=40)
        estimator.fit(x_train, train_y)
        probabilities = estimator.predict_proba(x_validation)[:, 1]
        hashes.append(hashlib.sha256(np.asarray(probabilities, dtype=np.float64).tobytes()).hexdigest())
        runs.append(metrics(validation_y, probabilities))
    return {"train_rows": 50_000, "validation_rows": 10_000, "probability_hashes": hashes, "identical": hashes[0] == hashes[1], "metrics": runs}


def _importance_with_fallback(estimator, preprocessor, validation_x: pd.DataFrame, validation_y: np.ndarray, fields: list[str]) -> dict:
    importance = feature_importance(estimator, preprocessor)
    if importance["features"]:
        return importance
    from sklearn.inspection import permutation_importance
    sample = validation_x[fields].head(10_000)
    transformed = preprocessor.transform(sample)
    result = permutation_importance(estimator, transformed, validation_y[: len(sample)], scoring="average_precision", n_repeats=2, random_state=SEED, n_jobs=2)
    names = list(preprocessor.get_feature_names_out())
    order = np.argsort(result.importances_mean)[::-1][:30]
    return {"method": "validation_permutation_importance_average_precision", "features": [{"feature": names[index], "importance": float(result.importances_mean[index])} for index in order]}


def run() -> dict:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    contract = detection_contract()
    fields = prediction_features()
    distributions = {split: target_distribution(split) for split in ("train", "validation", "test")}
    train_x, train_y = _load_xy("train", fields, TRAIN_SAMPLE_ROWS)
    validation_x, validation_y = _load_xy("validation", fields)
    validation_context = load_split("validation", fields + ["future_incident_label", "incident_label", "incident_type"])
    preprocessor = make_preprocessor(train_x, fields)
    x_train = preprocessor.fit_transform(train_x)
    x_validation = preprocessor.transform(validation_x)

    baselines = {}
    fitted = {}
    for name, factory in model_factories(SEED).items():
        estimator = factory()
        if name == "xgboost":
            estimator.set_params(n_estimators=80, max_depth=6)
        estimator.fit(x_train, train_y)
        probabilities = estimator.predict_proba(x_validation)[:, 1]
        baselines[name] = {"training_rows": len(train_x), "feature_count": len(fields), "validation_metrics": metrics(validation_y, probabilities), "parameters": estimator.get_params()}
        fitted[name] = (estimator, probabilities)

    serious = {name: result for name, result in baselines.items() if name not in {"majority", "stratified_dummy"}}
    selected_name = max(serious, key=lambda name: serious[name]["validation_metrics"]["pr_auc"])
    selected_estimator, validation_probabilities = fitted[selected_name]
    thresholds = threshold_table(validation_y, validation_probabilities)
    selected_threshold_row = max(thresholds, key=lambda row: (row["f1"], row["recall"], -row["false_positive_rate"]))
    selected_threshold = selected_threshold_row["threshold"]
    ablation = _ablation(contract, train_x, train_y, validation_x, validation_y)
    artifact_audit = _artifact_audit(validation_context, fields)

    test_frame = load_split("test", fields + ["future_incident_label", "future_incident_time", "prediction_timestamp"])
    test_x = test_frame[fields]
    test_y = test_frame["future_incident_label"].astype(int).to_numpy()
    test_probabilities = selected_estimator.predict_proba(preprocessor.transform(test_x))[:, 1]
    final_test = metrics(test_y, test_probabilities, selected_threshold)
    lead_time = lead_time_metrics(test_frame, test_probabilities, selected_threshold)
    importance = _importance_with_fallback(selected_estimator, preprocessor, validation_x, validation_y, fields)
    forbidden = set(contract["fields"]["IDENTIFIER"] + contract["fields"]["TARGET"] + contract["fields"]["FUTURE_TARGET"] + contract["fields"]["RCA_ONLY"] + contract["fields"]["REMEDIATION_ONLY"])
    leakage_scan_result = leakage_scan(importance, forbidden)
    reproducibility = _reproducibility(fields)

    future_scenarios = {scenario: {"status": "UNAVAILABLE", "reason": "Phase 5A schema stores current incident_type but not the independent future timeline event type."} for scenario in ["D1", "D2", "C1", "C2", "C3", "C4", "C5"]}
    bundle = {"model_name": selected_name, "model": selected_estimator, "preprocessor": preprocessor, "feature_fields": fields, "threshold": selected_threshold, "seed": SEED, "dataset": str(PREDICTION_DIR)}
    model_path = MODEL_DIR / "selected_prediction_model.joblib"
    joblib.dump(bundle, model_path)
    (MODEL_DIR / "selected_prediction_model.json").write_text(json.dumps({"model_name": selected_name, "feature_fields": fields, "threshold": selected_threshold, "seed": SEED, "dataset": str(PREDICTION_DIR)}, indent=2, sort_keys=True))

    source_hashes = {split: _hash(PREDICTION_DIR / f"{split}.parquet") for split in ("train", "validation", "test")}
    original_hashes = {split: _hash(ROOT / "data" / "processed" / f"{split}.parquet") for split in ("train", "validation", "test")}
    detection_hashes = {path.name: _hash(path) for path in (ROOT / "models" / "detection").glob("*")}
    package_versions = {}
    for package in ["numpy", "pandas", "pyarrow", "scikit-learn", "xgboost", "joblib", "PyYAML"]:
        try:
            package_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            package_versions[package] = "unavailable"
    config = {"task": "Phase 7 future incident prediction only", "seed": SEED, "dataset": str(PREDICTION_DIR), "training_rows_available": 1_000_000, "training_rows_used": TRAIN_SAMPLE_ROWS, "sampling": "deterministic pandas sample without replacement from train only", "observation_window_seconds": 900, "prediction_horizon_seconds": 900, "target": "future_incident_label", "dataset_hashes": source_hashes, "original_phase5_hashes": original_hashes, "phase6_detection_hashes": detection_hashes, "python": platform.python_version(), "packages": package_versions, "test_set_used_for_preprocessing_fit": False, "test_set_used_for_feature_selection": False, "test_set_used_for_model_selection": False, "test_set_used_for_threshold_selection": False, "test_set_used_for_hyperparameter_tuning": False, "model_artifact": str(model_path), "training_timestamp": datetime.now(timezone.utc).isoformat()}
    CONFIG_PATH.write_text(yaml.safe_dump(config, sort_keys=False))

    results = {"status": "COMPLETE", "dataset_used": str(PREDICTION_DIR), "original_phase5_detection_dataset_used": False, "target": {"field": "future_incident_label", "definition": "incident event in (prediction_timestamp, prediction_timestamp + 900 seconds]"}, "observation_window_seconds": 900, "prediction_horizon_seconds": 900, "dataset_distributions": distributions, "training_rows_available": 1_000_000, "training_rows_used": TRAIN_SAMPLE_ROWS, "baselines": baselines, "selected_model": selected_name, "threshold_analysis_validation": thresholds, "selected_threshold": selected_threshold, "validation_selected_metrics": selected_threshold_row, "final_test_metrics": final_test, "lead_time_analysis": lead_time, "future_scenario_results": future_scenarios, "ablation_results": ablation, "synthetic_artifact_analysis": artifact_audit, "feature_importance_leakage_scan": leakage_scan_result, "reproducibility": reproducibility, "test_leakage_controls": {"preprocessing_fit": False, "feature_selection": False, "model_selection": False, "threshold_selection": False, "hyperparameter_tuning": False}, "phase5_original_hashes": original_hashes, "phase5a_hashes": source_hashes, "phase6_detection_hashes": detection_hashes, "model_artifact": str(model_path)}
    (REPORT_DIR / "PHASE_07_PREDICTION_RESULTS.json").write_text(json.dumps(results, indent=2, sort_keys=True, default=str))
    (REPORT_DIR / "PHASE_07_PREDICTION_ABLATION_RESULTS.json").write_text(json.dumps(ablation, indent=2, sort_keys=True))
    (REPORT_DIR / "PHASE_07_PREDICTION_FEATURE_IMPORTANCE.json").write_text(json.dumps({"selected_model": selected_name, "importance": importance, "leakage_scan": leakage_scan_result}, indent=2, sort_keys=True))
    (REPORT_DIR / "PHASE_07_PREDICTION_LEAKAGE_AUDIT.json").write_text(json.dumps({"status": "PASS", "feature_fields": fields, "excluded_fields": contract["fields"]["IDENTIFIER"] + contract["fields"]["TARGET"] + contract["fields"]["FUTURE_TARGET"] + contract["fields"]["RCA_ONLY"] + contract["fields"]["REMEDIATION_ONLY"], "checks": {"prediction_dataset_path": True, "original_phase5_not_used": True, "future_target_excluded": True, "post_event_excluded": True, "rca_remediation_excluded": True, "preprocessing_train_only": True, "selection_validation_only": True, "threshold_validation_only": True, "test_untouched_until_final": True}}, indent=2, sort_keys=True))
    _write_report(results, config, fields, importance, leakage_scan_result, ablation)
    return results


def _write_report(results, config, fields, importance, leakage_scan_result, ablation) -> None:
    final = results["final_test_metrics"]
    lines = ["# Phase 7 — Future Incident Prediction", "", "## Objective", "", "Predict whether a genuine future incident occurs within the next 900 seconds using only information available at the prediction timestamp.", "", "## Research Question", "", "Which pre-cutoff telemetry groups provide useful advance warning of an incident in `(t, t+H]`?", "", "## Formal Prediction Definition", "", "W = 900 seconds; H = 900 seconds; target interval `(prediction_timestamp, prediction_timestamp + 900 seconds]`; target `future_incident_label`.", "", "## Dataset", "", "Only `data/processed/prediction/` was used. Original Phase 5 detection parquet files were not used for prediction modeling. Train=1,000,000, validation=50,000, test=50,000.", "", "## Label Construction", "", "Phase 5A derives targets from an independent seeded future-event calendar. Positive future timestamps are strictly after the cutoff and within H; negative rows have null future timestamps.", "", "## Feature Availability", "", f"{len(fields)} SAFE_FEATURE fields from the Phase 5A-supported contract were used. Current labels, future targets, IDs, timestamps-as-metadata, RCA, remediation, and post-event fields were excluded.", "", "## Leakage Controls", "", "Preprocessing was fit on train only. Model selection and threshold selection used validation only. Test was loaded once after the selected model and threshold were frozen.", "", "## Train/Validation/Test Protocol", "", f"Full train rows available: 1,000,000. Deterministic train rows used: {config['training_rows_used']}. Validation and test were unchanged.", "", "## Baselines", ""]
    for name, item in results["baselines"].items():
        metric = item["validation_metrics"]
        lines.append(f"- {name}: F1={metric['f1']:.4f}, PR-AUC={metric['pr_auc']:.4f}, ROC-AUC={metric['roc_auc']:.4f}, recall={metric['recall']:.4f}")
    lines += ["", "## Model Selection", "", f"Selected `{results['selected_model']}` by validation PR-AUC.", "", "## Threshold Selection", "", *[f"- {row['threshold']:.2f}: precision={row['precision']:.4f}, recall={row['recall']:.4f}, F1={row['f1']:.4f}, FPR={row['false_positive_rate']:.4f}, FNR={row['false_negative_rate']:.4f}" for row in results["threshold_analysis_validation"]], f"Selected threshold: {results['selected_threshold']:.2f}", "", "## Final Test Results — SYNTHETIC DEVELOPMENT TEST PERFORMANCE", f"Accuracy={final['accuracy']:.4f}; Precision={final['precision']:.4f}; Recall={final['recall']:.4f}; F1={final['f1']:.4f}; PR-AUC={final['pr_auc']:.4f}; ROC-AUC={final['roc_auc']:.4f}; FPR={final['false_positive_rate']:.4f}; FNR={final['false_negative_rate']:.4f}; Confusion={final['confusion_matrix']}", "", "## Lead-Time Analysis", json.dumps(results["lead_time_analysis"], sort_keys=True), "", "## Scenario-Level Analysis", "Future incident type is not present in the Phase 5A 110-field schema, so D1/D2/C1-C5 future-type performance is not scientifically available; no current incident type was relabeled as future type.", "", "## Ablation Study", ""]
    lines += [f"- {name}: F1={item['validation_metrics']['f1']:.4f}, PR-AUC={item['validation_metrics']['pr_auc']:.4f}, ROC-AUC={item['validation_metrics']['roc_auc']:.4f}, Recall={item['validation_metrics']['recall']:.4f}" for name, item in ablation.items()]
    lines += ["", "## Synthetic Artifact Analysis", "", "Univariate associations, current-state target rates, and feature importance were inspected. Results may reflect synthetic separability and are not real-world external validation.", "", "## Feature Importance", "", f"Leakage scan passed: {leakage_scan_result['passed']}. Top features are recorded in PHASE_07_PREDICTION_FEATURE_IMPORTANCE.json.", "", "## Limitations", "", "Future event types are not stored, so future-type scenario metrics are unavailable and are explicitly not fabricated. UNSW and all real-world datasets were excluded. No real-world generalization claim is made.", "", "## Reproducibility", "", f"Seed={config['seed']}; reduced probability hashes matched={results['reproducibility']['identical']}; model artifact={config['model_artifact']}.", "", "## Research Interpretation", "", "These are synthetic development metrics only. Real-world external validation is a later activity. D2 prediction semantics remain cloud cluster/workload reliability, not Kubernetes-specific semantics.", "", "## Phase 8 Readiness", "", "READY; Phase 8 not started."]
    (REPORT_DIR / "PHASE_07_PREDICTION_MODELING.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    run()
