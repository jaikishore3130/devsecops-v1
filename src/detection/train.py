from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import roc_auc_score

from .baselines import model_factories
from .data import class_distribution, detection_contract, load_split
from .evaluate import metrics, scenario_metrics, threshold_table
from .explain import feature_importance, leakage_scan
from .features import feature_groups, make_preprocessor

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "detection"
REPORT_DIR = ROOT / "reports"
CONFIG_PATH = ROOT / "metadata" / "detection_config.yaml"
SEED = 20261008
TRAIN_SAMPLE_ROWS = 250_000


def _dataset_hashes() -> dict[str, str]:
    return {
        split: hashlib.sha256((ROOT / "data" / "processed" / f"{split}.parquet").read_bytes()).hexdigest()
        for split in ("train", "validation", "test")
    }


def _load_xy(split: str, fields: list[str], sample_rows: int | None = None) -> tuple[pd.DataFrame, np.ndarray]:
    frame = load_split(split, fields + ["incident_label", "incident_type"])
    if sample_rows is not None and sample_rows < len(frame):
        frame = frame.sample(n=sample_rows, random_state=SEED).reset_index(drop=True)
    return frame[fields], frame["incident_label"].astype(int).to_numpy()


def _fit_pipeline(name: str, estimator, fields: list[str], x_train: pd.DataFrame, y_train: np.ndarray):
    preprocessor = make_preprocessor(x_train, fields)
    transformed = preprocessor.fit_transform(x_train)
    started = time.perf_counter()
    estimator.fit(transformed, y_train)
    return preprocessor, estimator, time.perf_counter() - started


def _predict(preprocessor, estimator, frame: pd.DataFrame):
    transformed = preprocessor.transform(frame)
    return estimator.predict_proba(transformed)[:, 1]


def _ablation(contract: dict, x_train: pd.DataFrame, y_train: np.ndarray, x_validation: pd.DataFrame, y_validation: np.ndarray) -> dict:
    results = {}
    for name, fields in feature_groups(contract).items():
        preprocessor = make_preprocessor(x_train, fields)
        train_transformed = preprocessor.fit_transform(x_train[fields])
        validation_transformed = preprocessor.transform(x_validation[fields])
        estimator = model_factories(SEED)["logistic_regression"]()
        estimator.fit(train_transformed, y_train)
        probabilities = estimator.predict_proba(validation_transformed)[:, 1]
        results[name] = {"feature_count": len(fields), "validation_metrics": metrics(y_validation, probabilities, 0.5)}
    return results


def _artifact_analysis(frame: pd.DataFrame, fields: list[str]) -> dict:
    target = frame["incident_label"].astype(int)
    numeric = [field for field in fields if field in frame and pd.api.types.is_numeric_dtype(frame[field])]
    univariate = []
    missingness = []
    for field in numeric:
        values = frame[field].fillna(frame[field].median())
        try:
            auc = roc_auc_score(target, values)
            univariate.append({"feature": field, "roc_auc": float(max(auc, 1 - auc))})
        except ValueError:
            continue
        missing = frame[field].isna()
        missingness.append({"feature": field, "incident_rate_missing": float(target[missing].mean()) if missing.any() else 0.0, "incident_rate_observed": float(target[~missing].mean()) if (~missing).any() else 0.0})
    categorical = []
    for field in fields:
        if field in frame and not pd.api.types.is_numeric_dtype(frame[field]):
            rates = frame.assign(_target=target).groupby(field, dropna=False)["_target"].mean()
            categorical.append({"feature": field, "max_category_incident_rate": float(rates.max()), "min_category_incident_rate": float(rates.min()), "rate_spread": float(rates.max() - rates.min())})
    return {
        "top_univariate_numeric_roc_auc": sorted(univariate, key=lambda item: item["roc_auc"], reverse=True)[:15],
        "missingness_target_effect": sorted(missingness, key=lambda item: abs(item["incident_rate_missing"] - item["incident_rate_observed"]), reverse=True)[:15],
        "categorical_target_rate_spread": categorical,
        "interpretation": "High univariate separability is treated as a synthetic-generator artifact risk, not evidence of real-world performance.",
    }


def _reproducibility_check(fields: list[str]) -> dict:
    train_x, train_y = _load_xy("train", fields, 50_000)
    validation_x, validation_y = _load_xy("validation", fields, 10_000)
    hashes = []
    metrics_runs = []
    for _ in range(2):
        preprocessor = make_preprocessor(train_x, fields)
        train_transformed = preprocessor.fit_transform(train_x)
        validation_transformed = preprocessor.transform(validation_x)
        estimator = model_factories(SEED)["xgboost"]()
        estimator.set_params(n_estimators=40)
        estimator.fit(train_transformed, train_y)
        probabilities = estimator.predict_proba(validation_transformed)[:, 1]
        hashes.append(hashlib.sha256(np.asarray(probabilities, dtype=np.float64).tobytes()).hexdigest())
        metrics_runs.append(metrics(validation_y, probabilities, 0.5))
    return {"train_rows": 50_000, "validation_rows": 10_000, "hashes": hashes, "exact_probability_hash_match": hashes[0] == hashes[1], "metrics": metrics_runs}


def run() -> dict:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    contract = detection_contract()
    fields = contract["fields"]["SAFE_FEATURE"]
    distributions = {split: class_distribution(split) for split in ("train", "validation", "test")}
    train_x, train_y = _load_xy("train", fields, TRAIN_SAMPLE_ROWS)
    validation_x, validation_y = _load_xy("validation", fields)
    validation_context = load_split("validation", fields + ["incident_type", "incident_label"])

    preprocessor = make_preprocessor(train_x, fields)
    train_transformed = preprocessor.fit_transform(train_x)
    validation_transformed = preprocessor.transform(validation_x)
    baseline_results = {}
    fitted = {}
    for name, factory in model_factories(SEED).items():
        estimator = factory()
        started = time.perf_counter()
        estimator.fit(train_transformed, train_y)
        seconds = time.perf_counter() - started
        probabilities = estimator.predict_proba(validation_transformed)[:, 1]
        baseline_results[name] = {
            "validation_metrics": metrics(validation_y, probabilities, 0.5),
            "training_rows": len(train_x),
            "feature_count": len(fields),
            "training_seconds": round(seconds, 3),
            "parameters": estimator.get_params(),
        }
        fitted[name] = (estimator, probabilities)

    serious = {name: result for name, result in baseline_results.items() if name not in {"majority", "stratified_dummy"}}
    selected_name = max(serious, key=lambda name: serious[name]["validation_metrics"]["pr_auc"])
    selected_estimator, selected_validation_probabilities = fitted[selected_name]
    thresholds = threshold_table(validation_y, selected_validation_probabilities)
    selected_threshold_row = max(thresholds, key=lambda row: (row["f1"], row["recall"], -row["false_positive_rate"]))
    selected_threshold = selected_threshold_row["threshold"]

    test_fields = fields + ["incident_type", "incident_label"]
    test_frame = load_split("test", test_fields)
    test_x = test_frame[fields]
    test_y = test_frame["incident_label"].astype(int).to_numpy()
    test_probabilities = _predict(preprocessor, selected_estimator, test_x)
    final_test = metrics(test_y, test_probabilities, selected_threshold)
    scenarios = scenario_metrics(test_frame, test_probabilities, selected_threshold)
    importance = feature_importance(selected_estimator, preprocessor)
    forbidden_tokens = set(contract["fields"]["IDENTIFIER"] + contract["fields"]["TARGET"] + contract["fields"]["FUTURE_TARGET"] + contract["fields"]["RCA_ONLY"] + contract["fields"]["REMEDIATION_ONLY"])
    leakage_scan_result = leakage_scan(importance, forbidden_tokens)
    ablation = _ablation(contract, train_x, train_y, validation_x, validation_y)
    artifact_analysis = _artifact_analysis(validation_context, fields)
    reproducibility = _reproducibility_check(fields)
    bundle = {
        "task": "D1 general binary incident detection",
        "model_name": selected_name,
        "preprocessor": preprocessor,
        "model": selected_estimator,
        "feature_fields": fields,
        "threshold": selected_threshold,
        "seed": SEED,
    }
    model_path = MODEL_DIR / "selected_detection_model.joblib"
    joblib.dump(bundle, model_path)
    (MODEL_DIR / "selected_detection_model.json").write_text(json.dumps({"model_name": selected_name, "feature_fields": fields, "threshold": selected_threshold, "seed": SEED}, indent=2, sort_keys=True))

    package_versions = {}
    for package in ["numpy", "pandas", "pyarrow", "scikit-learn", "xgboost", "joblib", "PyYAML"]:
        try:
            package_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            package_versions[package] = "unavailable"
    config = {
        "task": "D1 detection only",
        "seed": SEED,
        "dataset_commit": contract["dataset_commit"],
        "training_sample_rows": TRAIN_SAMPLE_ROWS,
        "dataset_hashes": _dataset_hashes(),
        "python": platform.python_version(),
        "packages": package_versions,
        "feature_fields": fields,
        "preprocessing": "median imputation plus missing indicators for numeric fields; most-frequent imputation and one-hot encoding for categorical fields; all fit on train only",
        "test_set_used_for_tuning": False,
        "test_set_used_for_feature_selection": False,
        "test_set_used_for_threshold_selection": False,
        "test_set_used_for_preprocessing_fit": False,
        "test_set_used_for_hyperparameter_search": False,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_artifact": str(model_path),
    }
    CONFIG_PATH.write_text(yaml.safe_dump(config, sort_keys=False))
    results = {
        "status": "COMPLETE",
        "objective": "D1 general incident detection",
        "target": {"field": "incident_label", "zero": "normal", "one": "incident/anomalous event", "positive_types": ["D1", "D2", "C1", "C2", "C3", "C4", "C5"]},
        "dataset_distributions": distributions,
        "training_rows_used": TRAIN_SAMPLE_ROWS,
        "baseline_results": baseline_results,
        "selected_model": selected_name,
        "threshold_analysis_validation": thresholds,
        "selected_threshold": selected_threshold,
        "validation_selected_metrics": selected_threshold_row,
        "final_test_metrics": final_test,
        "scenario_results_test": scenarios,
        "test_leakage_controls": {key: False for key in ["test_set_used_for_tuning", "test_set_used_for_feature_selection", "test_set_used_for_threshold_selection", "test_set_used_for_preprocessing_fit", "test_set_used_for_hyperparameter_search"]},
        "synthetic_artifact_analysis": {"note": "Strong detection performance is interpreted as controlled synthetic separability, not real-world generalization.", "missingness_target_correlation_checked": True, "identifier_features_excluded": True},
            "artifact_analysis": artifact_analysis,
            "reproducibility": reproducibility,
        "research_alignment": {
            "supported_by_project_evidence": ["controlled synthetic development with independent external-validation separation", "strict temporal and entity leakage controls", "multi-metric evaluation rather than accuracy alone"],
            "adopted_in_implementation": ["train-only preprocessing", "validation-only threshold selection", "scenario-level D1-D2/C1-C5 analysis", "baseline ladder"],
            "modified_for_this_phase": ["D1 binary detection only", "deterministic 250000-row train sample for resource-bounded baseline fitting", "XGBoost as the selected transparent tree baseline"],
            "project_specific_additions": ["110-field Phase 4A detection contract", "synthetic artifact separability analysis", "validation-selected operating threshold"],
        },
            "model_artifact": str(model_path),
        "config_artifact": str(CONFIG_PATH),
    }
    (REPORT_DIR / "PHASE_06_DETECTION_RESULTS.json").write_text(json.dumps(results, indent=2, sort_keys=True, default=str))
    (REPORT_DIR / "PHASE_06_FEATURE_IMPORTANCE.json").write_text(json.dumps({"selected_model": selected_name, "importance": importance, "leakage_scan": leakage_scan_result}, indent=2, sort_keys=True))
    (REPORT_DIR / "PHASE_06_ABLATION_RESULTS.json").write_text(json.dumps(ablation, indent=2, sort_keys=True))
    write_markdown(results, config, fields, importance, leakage_scan_result, ablation)
    return results


def write_markdown(results, config, fields, importance, leakage_scan_result, ablation) -> None:
    final = results["final_test_metrics"]
    lines = [
        "# Phase 6 — Detection Modeling", "", "## Objective", "", "Build and evaluate a binary D1 general incident detector over D1, D2, C1-C5.", "", "## Dataset", "", "Phase 5 commit `0f6bb59`; train 1,000,000, validation 50,000, test 50,000; 110 canonical fields.", "", "## Target Definition", "", "`incident_label=0` is normal and `incident_label=1` is an incident/anomalous event. Positive incidents are D1, D2, C1, C2, C3, C4, and C5. `incident_type` is retained for scenario analysis, not used as a predictor.", "", "## Feature Contract", "", f"{len(fields)} SAFE_FEATURE fields were used. The complete classification of all 110 canonical fields is in `metadata/detection_feature_contract.yaml`.", "", "## Excluded Fields", "", "Identifiers, current/future labels, raw timestamps, during-event fields, RCA outputs, and remediation outputs were excluded to prevent memorization and leakage.", "", "## Preprocessing", "", "Numeric fields use train-fitted median imputation with missing indicators and scaling. Categorical fields use train-fitted most-frequent imputation and one-hot encoding. Validation and test are transformed without fitting.", "", "## Baselines", ""]
    for name, item in results["baseline_results"].items():
        metric = item["validation_metrics"]
        lines.append(f"- {name}: F1={metric['f1']:.4f}, PR-AUC={metric['pr_auc']:.4f}, ROC-AUC={metric['roc_auc']:.4f}, recall={metric['recall']:.4f}")
    lines += ["", "## Validation Protocol", "", "Models and preprocessing were fit on train only. Model comparison and threshold selection used validation only. Test remained untouched until the selected model, preprocessing, and threshold were frozen.", "", "## Model Comparison", "", f"Selected model: `{results['selected_model']}` by validation PR-AUC.", "", "## Threshold Analysis", "", *[f"- {row['threshold']:.2f}: precision={row['precision']:.4f}, recall={row['recall']:.4f}, F1={row['f1']:.4f}, FPR={row['false_positive_rate']:.4f}, FNR={row['false_negative_rate']:.4f}" for row in results["threshold_analysis_validation"]], f"", f"Selected validation threshold: {results['selected_threshold']:.2f}", "", "## Final Test Evaluation", ""]
    lines += [f"- Accuracy: {final['accuracy']:.4f}", f"- Precision: {final['precision']:.4f}", f"- Recall: {final['recall']:.4f}", f"- F1: {final['f1']:.4f}", f"- ROC-AUC: {final['roc_auc']:.4f}", f"- PR-AUC: {final['pr_auc']:.4f}", f"- FPR: {final['false_positive_rate']:.4f}", f"- FNR: {final['false_negative_rate']:.4f}", f"- Confusion matrix: {final['confusion_matrix']}", "", "## Scenario-Level Results", ""]
    for scenario, item in results["scenario_results_test"].items():
        lines.append(f"- {scenario}: samples={item['samples']}, recall={item['recall']:.4f}, precision={item['precision']:.4f}, false_negatives={item['false_negatives']}, detection_rate={item['detection_rate']:.4f}")
    top_artifact = results["artifact_analysis"]["top_univariate_numeric_roc_auc"][:5]
    lines += ["", "## Feature Importance", "", f"Method: {importance['method']}. Leakage scan passed: {leakage_scan_result['passed']}.", *[f"- {item['feature']}: {item['importance']:.6f}" for item in importance.get("features", [])[:15]], "", "## Ablation Study", "", *[f"- {name}: validation F1={item['validation_metrics']['f1']:.4f}, PR-AUC={item['validation_metrics']['pr_auc']:.4f}, ROC-AUC={item['validation_metrics']['roc_auc']:.4f}" for name, item in ablation.items()], "", "## Synthetic Artifact Analysis", "", "The benchmark is synthetic and strong performance may reflect controlled separability. Numeric univariate ROC-AUC leaders were: " + ", ".join(f"{item['feature']}={item['roc_auc']:.4f}" for item in top_artifact) + ". Missingness, categorical target-rate spread, scenario distributions, and identifier exclusion were inspected. Results are not real-world generalization evidence.", "", "## Limitations", "", "UNSW was not used for training, calibration, feature selection, threshold tuning, or hyperparameter tuning. External validation and D2 prediction, RCA, and remediation remain future work.", "", "## Reproducibility", "", f"Seed: {config['seed']}; dataset commit: {config['dataset_commit']}; model artifact: `{config['model_artifact']}`. The reduced rerun probability hashes matched exactly: {results['reproducibility']['exact_probability_hash_match']}.", "", "## Research Interpretation", "", "Supported by project evidence: controlled synthetic development separated from independent external validation, temporal/entity leakage controls, and multi-metric evaluation. Adopted here: train-only preprocessing, validation-only threshold selection, a baseline ladder, and scenario analysis. Modified for this phase: D1 binary detection only, a deterministic 250,000-row train sample for resource-bounded fitting, and XGBoost as the selected tree baseline. Project-specific additions are the 110-field contract, synthetic artifact scan, and validation-selected threshold. This is not a claim of deployment readiness or superiority over real-world systems.", "", "## Status", "", "PHASE 6 = COMPLETE; scope is D1 detection only."]
    (REPORT_DIR / "PHASE_06_DETECTION_MODELING.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    run()
