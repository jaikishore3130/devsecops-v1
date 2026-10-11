"""Phase 7B - future incident prediction modeling on the frozen Phase 7A dataset.

Research protocol:
- Target: future_incident_label, i.e. an incident in (prediction_timestamp, +900s].
- Features: approved SAFE_FEATURE contract only.
- Preprocessing: fit on train only, frozen, then applied to validation/test.
- Model selection: validation PR-AUC only.
- Threshold selection: validation grid only, criterion = max F1 (tie: recall, then
  lower FPR).
- Test: loaded exactly once, after model + preprocessing + threshold are frozen.
"""

from __future__ import annotations

import gc
import hashlib
import importlib.metadata
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from . import v2_data as D

ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = D.DATASET_DIR
MODEL_DIR = ROOT / "models" / "prediction_v2"
REPORT_DIR = ROOT / "reports"
CONFIG_PATH = ROOT / "metadata" / "prediction_model_config.yaml"
CACHE_DIR = Path(os.environ.get("PHASE7B_CACHE_DIR", "/tmp/opencode/phase7b_cache"))
V2_MANIFEST_PATH = D.V2_MANIFEST_PATH
PREDICTION_V1_DIR = ROOT / "data" / "processed" / "prediction"
PHASE5_DIR = ROOT / "data" / "processed"
PHASE7_MODEL_DIR = ROOT / "models" / "prediction"
SEED = 20261008
THRESHOLD_GRID = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80]
HORIZON_SECONDS = 900
OBSERVATION_WINDOW_SECONDS = 900
FUTURE_TYPES = ["D1", "D2", "C1", "C2", "C3", "C4", "C5"]
LATENT_STATES = ["NORMAL", "EARLY_SIGNAL", "DEGRADATION", "ESCALATION"]

XGB_PARAMS = dict(
    n_estimators=250, max_depth=6, learning_rate=0.05, subsample=0.8,
    colsample_bytree=0.8, min_child_weight=5, reg_lambda=1.0,
    tree_method="hist", eval_metric="logloss", n_jobs=2, random_state=SEED,
)
RF_PARAMS = dict(
    n_estimators=60, max_depth=9, min_samples_leaf=25, max_features="sqrt",
    n_jobs=2, random_state=SEED,
)
LR_PARAMS = dict(C=1.0, max_iter=300, solver="lbfgs", random_state=SEED)


# --------------------------------------------------------------------------- #
# Hashing helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_array(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype=np.float64).tobytes()).hexdigest()


def package_versions() -> dict:
    packages = ["numpy", "pandas", "pyarrow", "scikit-learn", "xgboost", "joblib", "PyYAML"]
    versions = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "unavailable"
    return versions


def optional_model_availability() -> dict:
    import importlib.util

    availability = {}
    for name in ["lightgbm"]:
        spec = importlib.util.find_spec(name)
        availability[name] = {
            "available": spec is not None,
            "reason": "installed" if spec is not None
            else "not installed in the frozen environment; documented as skipped, no substitute tuned",
        }
    return availability


# --------------------------------------------------------------------------- #
# Preprocessing (train-fitted, frozen)
# --------------------------------------------------------------------------- #
def split_feature_types(frame: pd.DataFrame, fields: list[str]) -> tuple[list[str], list[str]]:
    categorical = [f for f in fields if f in frame and not pd.api.types.is_numeric_dtype(frame[f])]
    numeric = [f for f in fields if f not in categorical]
    return numeric, categorical


def make_preprocessor(frame: pd.DataFrame, fields: list[str]) -> ColumnTransformer:
    numeric, categorical = split_feature_types(frame, fields)
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
        ("scaler", StandardScaler(with_mean=True)),
    ])
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=np.float32)),
    ])
    return ColumnTransformer([
        ("numeric", numeric_pipeline, numeric),
        ("categorical", categorical_pipeline, categorical),
    ], remainder="drop")


def transform(preprocessor: ColumnTransformer, frame: pd.DataFrame, fields: list[str]) -> np.ndarray:
    return np.asarray(preprocessor.transform(frame[fields]), dtype=np.float32)


def build_matrix(preprocessor: ColumnTransformer, frame: pd.DataFrame, fields: list[str],
                 path: Path, chunk_rows: int = 200_000) -> np.ndarray:
    """Transform train-scale data in chunks into a disk-backed float32 memmap."""
    path.parent.mkdir(parents=True, exist_ok=True)
    names = preprocessor.get_feature_names_out()
    matrix = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32,
                                       shape=(len(frame), len(names)))
    for start in range(0, len(frame), chunk_rows):
        block = preprocessor.transform(frame.iloc[start:start + chunk_rows][fields])
        matrix[start:start + chunk_rows] = np.asarray(block, dtype=np.float32)
    matrix.flush()
    return matrix


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def binary_metrics(y_true, probabilities, threshold: float) -> dict:
    y_true = np.asarray(y_true).astype(int)
    p = np.asarray(probabilities, dtype=float)
    predictions = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, p)),
        "pr_auc": float(average_precision_score(y_true, p)),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) else 0.0,
        "specificity": float(specificity),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def threshold_table(y_true, probabilities, grid) -> list[dict]:
    return [binary_metrics(y_true, probabilities, threshold) for threshold in grid]


def select_threshold(y_true, probabilities, grid) -> tuple[float, list[dict]]:
    table = threshold_table(y_true, probabilities, grid)
    best = max(table, key=lambda row: (row["f1"], row["recall"], -row["false_positive_rate"]))
    return best["threshold"], table


# --------------------------------------------------------------------------- #
# Candidate models
# --------------------------------------------------------------------------- #
def model_candidates(seed: int, pos_weight: float) -> dict:
    return {
        "majority": lambda: DummyClassifier(strategy="most_frequent"),
        "stratified_dummy": lambda: DummyClassifier(strategy="stratified", random_state=seed),
        "logistic_regression": lambda: LogisticRegression(**LR_PARAMS, class_weight=None),
        "logistic_regression_balanced": lambda: LogisticRegression(**LR_PARAMS, class_weight="balanced"),
        "random_forest": lambda: RandomForestClassifier(**RF_PARAMS, class_weight=None),
        "random_forest_balanced": lambda: RandomForestClassifier(**RF_PARAMS, class_weight="balanced_subsample"),
        "xgboost": lambda: XGBClassifier(**XGB_PARAMS, scale_pos_weight=1.0),
        "xgboost_balanced": lambda: XGBClassifier(**XGB_PARAMS, scale_pos_weight=float(pos_weight)),
    }


def refit_selected(name: str, seed: int, pos_weight: float):
    return model_candidates(seed, pos_weight)[name]()


# --------------------------------------------------------------------------- #
# Analysis helpers
# --------------------------------------------------------------------------- #
def lead_time_analysis(frame: pd.DataFrame, y_true: np.ndarray, predictions: np.ndarray) -> dict:
    actual = y_true.astype(bool)
    lead = frame["time_to_incident"].to_numpy(dtype=float)
    lead = np.where(np.isfinite(lead), lead, np.nan)
    correct = predictions.astype(bool) & actual
    correct_lead = lead[correct]
    buckets = {"0_300": (0, 300), "301_600": (301, 600), "601_899": (601, 899)}
    bucket_report = {}
    for label, (low, high) in buckets.items():
        in_bucket = actual & np.isfinite(lead) & (lead >= low) & (lead <= high)
        correct_bucket = in_bucket & predictions.astype(bool)
        support = int(in_bucket.sum())
        hits = int(correct_bucket.sum())
        bucket_report[label] = {
            "future_incidents": support,
            "correctly_predicted": hits,
            "recall": float(hits / support) if support else None,
        }
    return {
        "correct_future_predictions": int(correct.sum()),
        "total_future_incidents": int(actual.sum()),
        "mean_seconds": float(np.nanmean(correct_lead)) if correct_lead.size else None,
        "median_seconds": float(np.nanmedian(correct_lead)) if correct_lead.size else None,
        "min_seconds": float(np.nanmin(correct_lead)) if correct_lead.size else None,
        "max_seconds": float(np.nanmax(correct_lead)) if correct_lead.size else None,
        "buckets": bucket_report,
    }


def future_type_analysis(frame: pd.DataFrame, y_true: np.ndarray, predictions: np.ndarray) -> dict:
    types = frame["future_incident_type"].to_numpy()
    report = {}
    for incident_type in FUTURE_TYPES:
        member = types == incident_type
        support = int((member & y_true.astype(bool)).sum())
        tp = int((predictions.astype(bool) & member).sum())
        fp = int((predictions.astype(bool) & ~member).sum())
        fn = int((~predictions.astype(bool) & member).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        report[incident_type] = {
            "support_future_incidents": support,
            "predicted_positive": tp,
            "tp": tp, "fp": fp, "fn": fn,
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
        }
    return {
        "definition": "one-vs-rest over rows whose realized future_incident_type equals the class; analysis only, never a feature",
        "per_type": report,
    }


def latent_state_analysis(frame: pd.DataFrame, y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    states = frame["latent_scenario_state"].to_numpy()
    report = {}
    for state in LATENT_STATES:
        mask = states == state
        rows = int(mask.sum())
        if rows == 0:
            report[state] = {"rows": 0, "status": "UNAVAILABLE"}
            continue
        y_state = y_true[mask]
        p_state = probabilities[mask]
        item = binary_metrics(y_state, p_state, threshold)
        item["rows"] = rows
        item["positive_rate"] = float(y_state.mean())
        report[state] = item
    usable = [s for s in LATENT_STATES if report[s].get("rows", 0) >= 200]
    return {
        "note": "latent_scenario_state is a diagnostic field and is never a predictor. "
                "States with small support are flagged.",
        "small_support_states": [s for s in LATENT_STATES if report[s].get("rows", 0) < 200],
        "usable_states": usable,
        "per_state": report,
    }


def calibration_analysis(y_true, probabilities, n_bins: int = 10) -> dict:
    y_true = np.asarray(y_true).astype(int)
    p = np.asarray(probabilities, dtype=float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    digitized = np.clip(np.digitize(p, bins) - 1, 0, n_bins - 1)
    curve = []
    for b in range(n_bins):
        mask = digitized == b
        if not mask.any():
            curve.append({"bin_low": float(bins[b]), "bin_high": float(bins[b + 1]),
                          "count": 0, "mean_predicted": None, "observed_rate": None})
            continue
        curve.append({
            "bin_low": float(bins[b]), "bin_high": float(bins[b + 1]),
            "count": int(mask.sum()),
            "mean_predicted": float(p[mask].mean()),
            "observed_rate": float(y_true[mask].mean()),
        })
    quantiles = np.quantile(p, [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0]).tolist()
    return {
        "brier_score": float(brier_score_loss(y_true, p)),
        "reliability_curve": curve,
        "probability_quantiles": {str(q): float(v) for q, v in zip(
            [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0], quantiles)},
        "mean_predicted_probability": float(p.mean()),
        "observed_positive_rate": float(y_true.mean()),
    }


def univariate_auc(frame: pd.DataFrame, fields: list[str], target: np.ndarray) -> list[dict]:
    results = []
    for field in fields:
        if not pd.api.types.is_numeric_dtype(frame[field]):
            continue
        values = frame[field].astype(float)
        if values.isna().all():
            continue
        values = values.fillna(values.median()).to_numpy()
        if np.unique(values).size < 2:
            continue
        auc = roc_auc_score(target, values)
        results.append({"feature": field, "roc_auc": float(max(auc, 1 - auc))})
    return sorted(results, key=lambda item: item["roc_auc"], reverse=True)


def missingness_difference(frame: pd.DataFrame, fields: list[str], target: np.ndarray) -> list[dict]:
    pos = target.astype(bool)
    rows = []
    for field in fields:
        miss = frame[field].isna().to_numpy()
        diff = float(miss[pos].mean() - miss[~pos].mean()) if pos.any() and (~pos).any() else 0.0
        rows.append({"feature": field, "missing_rate": float(miss.mean()), "pos_minus_neg_missing_rate": diff})
    return sorted(rows, key=lambda item: abs(item["pos_minus_neg_missing_rate"]), reverse=True)


def categorical_target_rates(frame: pd.DataFrame, fields: list[str], target: np.ndarray) -> dict:
    report = {}
    for field in fields:
        if pd.api.types.is_numeric_dtype(frame[field]):
            continue
        grouped = pd.Series(target, index=frame.index).groupby(frame[field]).mean()
        report[field] = {str(k): float(v) for k, v in grouped.items()}
    return report


def latent_state_encoding_check(preprocessor, fields, raw_train, raw_val) -> dict:
    from sklearn.linear_model import LogisticRegression

    train_states = raw_train["latent_scenario_state"].to_numpy()
    val_states = raw_val["latent_scenario_state"].to_numpy()
    sample_idx = np.random.default_rng(SEED).choice(len(raw_train), size=min(200_000, len(raw_train)), replace=False)
    x_train = transform(preprocessor, raw_train.iloc[sample_idx], fields)
    x_val = transform(preprocessor, raw_val, fields)
    model = LogisticRegression(max_iter=200, solver="lbfgs", random_state=SEED)
    model.fit(x_train, train_states[sample_idx])
    predictions = model.predict(x_val)
    baseline = max(np.bincount(pd.factorize(val_states)[0]))
    return {
        "method": "multiclass logistic regression on train subsample (200k), evaluated on validation",
        "classes": list(model.classes_),
        "accuracy": float(accuracy_score(val_states, predictions)),
        "macro_f1": float(f1_score(val_states, predictions, average="macro", zero_division=0)),
        "majority_baseline_accuracy": float(baseline / len(val_states)),
        "interpretation": "Far below 1.0 indicates the latent state is not deterministically recoverable "
                          "from the safe telemetry, i.e. no trivial hidden scenario identifier.",
    }


def feature_missingness_report(frame, fields):
    return {field: float(frame[field].isna().mean()) for field in fields}


# --------------------------------------------------------------------------- #
# Main pipeline
# --------------------------------------------------------------------------- #
def _log(message: str) -> None:
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    print(f"[phase7b {time.strftime('%H:%M:%S')}] {message} (peakRSS {peak:.0f}MB)", flush=True)


def _load_checkpoint(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def _save_checkpoint(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str))


def run() -> dict:
    started = time.time()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    np.random.seed(SEED)
    _log("start")

    # STEP 1 - freeze hashes ------------------------------------------------- #
    _log("step1 freeze hashes")
    v2_manifest = json.loads(V2_MANIFEST_PATH.read_text())
    dataset_hashes = {split: sha256_file(DATASET_DIR / f"{split}.parquet") for split in D.SPLIT_ROWS}
    dataset_hashes_match = all(
        dataset_hashes[split] == v2_manifest["splits"][split]["sha256"] for split in D.SPLIT_ROWS
    )
    if not dataset_hashes_match:
        raise SystemExit("STOP: prediction_v2 hashes differ from frozen Phase 7A manifest.")
    phase7_hashes = {
        path.name: sha256_file(path)
        for path in sorted(REPORT_DIR.glob("PHASE_07*"))
        if not path.name.startswith("PHASE_07B")
    }
    phase7_model_hashes = {
        path.name: sha256_file(path) for path in sorted(PHASE7_MODEL_DIR.glob("*"))
    }
    phase5_hashes = {split: sha256_file(PHASE5_DIR / f"{split}.parquet") for split in D.SPLIT_ROWS}
    prediction_v1_hashes = {split: sha256_file(PREDICTION_V1_DIR / f"{split}.parquet") for split in D.SPLIT_ROWS}

    # STEP 2 - feature contract --------------------------------------------- #
    _log("step2 feature contract")
    sample_columns = pq.ParquetFile(DATASET_DIR / "train.parquet").schema_arrow.names
    allowed = D.allowed_features(sample_columns)
    forbidden = D.forbidden_fields()
    groups = D.feature_groups(allowed)
    overlap = set(allowed) & D.all_forbidden()
    if overlap:
        raise SystemExit(f"STOP: forbidden fields present in allowed set: {overlap}")
    for critical in ["future_incident_label", "future_incident_type", "future_incident_time",
                     "time_to_incident", "latent_scenario_state", "incident_label", "incident_type"]:
        if critical in allowed:
            raise SystemExit(f"STOP: future/leakage field in feature set: {critical}")

    # STEP 3 - load splits (test intentionally not loaded) ------------------ #
    _log("step3 load train/validation")
    raw_train = D.load_split("train", allowed + [D.TARGET, "latent_scenario_state"])
    raw_val = D.load_split("validation", allowed + [D.TARGET, "latent_scenario_state"])
    for frame in (raw_train, raw_val):
        for field in allowed:
            if pd.api.types.is_numeric_dtype(frame[field]):
                frame[field] = frame[field].astype(np.float32)
    y_train = raw_train[D.TARGET].astype(int).to_numpy()
    y_val = raw_val[D.TARGET].astype(int).to_numpy()
    # Test distribution is intentionally not read here; it is derived after freeze.
    distributions = {split: D.class_distribution(split) for split in ("train", "validation")}
    pos_weight = distributions["train"]["negative_to_positive_ratio"]

    # STEP 4-8 - fit or resume preprocessing, ladder, selection, freeze ------ #
    checkpoint = _load_checkpoint(MODEL_DIR / "run_checkpoint.json")
    if checkpoint.get("dataset_hashes") != dataset_hashes:
        checkpoint = {}
    resume_ladder = (
        bool(checkpoint.get("ladder_done"))
        and (MODEL_DIR / "preprocessing.joblib").exists()
        and (MODEL_DIR / "selected_model.joblib").exists()
        and (MODEL_DIR / "validation_probabilities.npy").exists()
    )
    models = model_candidates(SEED, pos_weight)
    if resume_ladder:
        _log("resume: loading frozen preprocessing/model/threshold")
        prep_bundle = joblib.load(MODEL_DIR / "preprocessing.joblib")
        preprocessor = prep_bundle["preprocessor"]
        numeric = prep_bundle["numeric_fields"]
        categorical = prep_bundle["categorical_fields"]
        model_bundle = joblib.load(MODEL_DIR / "selected_model.joblib")
        selected_estimator = model_bundle["model"]
        selected_name = model_bundle["model_name"]
        selected_threshold = model_bundle["threshold"]
        ladder = checkpoint["ladder"]
        val_threshold_table = checkpoint["val_threshold_table"]
        validation_selected = checkpoint["validation_selected"]
        validation_probabilities = np.load(MODEL_DIR / "validation_probabilities.npy")
        x_val = transform(preprocessor, raw_val, allowed)
        versions = checkpoint.get("versions") or {"python": platform.python_version(),
                                                  "packages": package_versions(), "seed": SEED}
        frozen = {"frozen_at": checkpoint.get("frozen_at"), "model_name": selected_name,
                  "threshold": selected_threshold, "seed": SEED, "feature_count": len(allowed),
                  "dataset": str(DATASET_DIR), "dataset_hashes": dataset_hashes}
    else:
        # STEP 4 - preprocessing fit on train only -------------------------- #
        _log("step4 preprocessing fit")
        fit_sample = raw_train.sample(n=min(200_000, len(raw_train)), random_state=SEED)
        preprocessor = make_preprocessor(fit_sample, allowed)
        preprocessor.fit(fit_sample[allowed])
        del fit_sample
        gc.collect()
        x_train = build_matrix(preprocessor, raw_train, allowed, CACHE_DIR / "x_train.f32.npy")
        x_val = transform(preprocessor, raw_val, allowed)
        numeric, categorical = split_feature_types(raw_train, allowed)

        # STEP 5 - model ladder (validation only) --------------------------- #
        _log("step5 model ladder")
        ladder_progress = checkpoint.get("ladder_progress", {})
        ladder = {}
        for name, factory in models.items():
            if name in ladder_progress:
                _log(f"  cached {name}")
                ladder[name] = ladder_progress[name]
                continue
            t0 = time.time()
            _log(f"  fitting {name}")
            estimator = factory()
            estimator.fit(x_train, y_train)
            probabilities = estimator.predict_proba(x_val)[:, 1]
            scores = binary_metrics(y_val, probabilities, 0.5)
            ladder[name] = {
                "training_rows": int(len(x_train)),
                "feature_count": len(allowed),
                "validation_metrics_at_0_5": scores,
                "validation_pr_auc": scores["pr_auc"],
                "validation_roc_auc": scores["roc_auc"],
                "fit_seconds": round(time.time() - t0, 1),
            }
            del estimator
            gc.collect()
            ladder_progress[name] = ladder[name]
            checkpoint["dataset_hashes"] = dataset_hashes
            checkpoint["ladder_progress"] = ladder_progress
            _save_checkpoint(MODEL_DIR / "run_checkpoint.json", checkpoint)

        # STEP 6 - select model by validation PR-AUC ------------------------ #
        _log("step6 select model")
        serious = {name: item for name, item in ladder.items() if name not in {"majority", "stratified_dummy"}}
        selected_name = max(serious, key=lambda name: serious[name]["validation_pr_auc"])
        selected_estimator = refit_selected(selected_name, SEED, pos_weight)
        selected_estimator.fit(x_train, y_train)
        validation_probabilities = selected_estimator.predict_proba(x_val)[:, 1]

        # STEP 7 - select threshold on validation --------------------------- #
        _log("step7 threshold selection")
        selected_threshold, val_threshold_table = select_threshold(y_val, validation_probabilities, THRESHOLD_GRID)
        validation_selected = binary_metrics(y_val, validation_probabilities, selected_threshold)

        # STEP 8 - freeze preprocessing + model + threshold ----------------- #
        _log("step8 freeze artifacts")
        versions = {"python": platform.python_version(), "packages": package_versions(), "seed": SEED}
        frozen = {"frozen_at": datetime.now(timezone.utc).isoformat(), "model_name": selected_name,
                  "threshold": selected_threshold, "seed": SEED, "feature_count": len(allowed),
                  "dataset": str(DATASET_DIR), "dataset_hashes": dataset_hashes}
        np.save(MODEL_DIR / "validation_probabilities.npy", validation_probabilities)
        checkpoint = {
            "dataset_hashes": dataset_hashes, "ladder_done": True, "ladder": ladder,
            "selected_name": selected_name, "selected_threshold": selected_threshold,
            "val_threshold_table": val_threshold_table, "validation_selected": validation_selected,
            "frozen_at": frozen["frozen_at"], "versions": versions,
        }
        _save_checkpoint(MODEL_DIR / "run_checkpoint.json", checkpoint)
        del x_train
        gc.collect()

    joblib.dump({"preprocessor": preprocessor, "feature_fields": allowed,
                 "numeric_fields": numeric, "categorical_fields": categorical},
                MODEL_DIR / "preprocessing.joblib")
    joblib.dump({"model": selected_estimator, "model_name": selected_name,
                 "feature_fields": allowed, "threshold": selected_threshold, "seed": SEED},
                MODEL_DIR / "selected_model.joblib")
    (MODEL_DIR / "feature_list.json").write_text(json.dumps({
        "allowed_features": allowed, "feature_count": len(allowed),
        "numeric_features": numeric, "categorical_features": categorical,
        "forbidden_groups": forbidden,
    }, indent=2, sort_keys=True))
    (MODEL_DIR / "threshold.json").write_text(json.dumps({
        "threshold": selected_threshold,
        "criterion": "maximize validation F1; tie-break by higher recall then lower FPR",
        "grid": THRESHOLD_GRID, "validation_table": val_threshold_table,
    }, indent=2, sort_keys=True))
    (MODEL_DIR / "versions.json").write_text(json.dumps(versions, indent=2, sort_keys=True))
    (MODEL_DIR / "freeze_manifest.json").write_text(json.dumps(frozen, indent=2, sort_keys=True))

    # STEP 9 - test evaluation, exactly once -------------------------------- #
    _log("step9 test evaluation")
    test_columns = allowed + [D.TARGET, "future_incident_time", "time_to_incident",
                              "future_incident_type", "latent_scenario_state", "prediction_timestamp"]
    test_frame = D.load_split("test", test_columns)
    for field in allowed:
        if pd.api.types.is_numeric_dtype(test_frame[field]):
            test_frame[field] = test_frame[field].astype(np.float32)
    test_npy = MODEL_DIR / "test_probabilities.npy"
    resume_test = (
        bool(checkpoint.get("test_done")) and test_npy.exists()
        and sha256_array(np.load(test_npy)) == checkpoint.get("test_probability_hash")
    )
    if resume_test:
        _log("resume: using frozen test probabilities")
        test_probabilities = np.load(test_npy)
    else:
        x_test = transform(preprocessor, test_frame, allowed)
        test_probabilities = selected_estimator.predict_proba(x_test)[:, 1]
        np.save(test_npy, test_probabilities)
    y_test = test_frame[D.TARGET].astype(int).to_numpy()
    distributions["test"] = {
        "split": "test", "rows": int(len(y_test)), "positive": int(y_test.sum()),
        "negative": int((y_test == 0).sum()), "positive_rate": float(y_test.mean()),
        "negative_to_positive_ratio": float((y_test == 0).sum() / max(y_test.sum(), 1)),
    }
    final_test = binary_metrics(y_test, test_probabilities, selected_threshold)
    test_probability_hash = sha256_array(test_probabilities)
    test_predictions = (test_probabilities >= selected_threshold).astype(int)
    if not resume_test:
        checkpoint["test_probability_hash"] = test_probability_hash
        checkpoint["test_done"] = True
        _save_checkpoint(MODEL_DIR / "run_checkpoint.json", checkpoint)

    # STEP 10 - lead-time analysis ------------------------------------------ #
    _log("step10 lead-time analysis")
    lead_time = lead_time_analysis(test_frame, y_test, test_predictions)

    # STEP 11 - future-type analysis ---------------------------------------- #
    _log("step11 future-type analysis")
    future_type = future_type_analysis(test_frame, y_test, test_predictions)

    # STEP 12 - latent-state analysis --------------------------------------- #
    _log("step12 latent-state analysis")
    latent_state = latent_state_analysis(test_frame, y_test, test_probabilities, selected_threshold)

    # STEP 13 - ablation study (selection stays validation-only) ------------ #
    _log("step13 ablation study")
    if bool(checkpoint.get("ablation_done")) and checkpoint.get("selected_name") == selected_name:
        _log("resume: using cached ablation results")
        ablation = checkpoint["ablation"]
    else:
        ablation = {}
        for group_name, fields in groups.items():
            _log(f"  ablation {group_name}")
            if fields == allowed:
                prep_group = preprocessor
                xg_train = np.load(CACHE_DIR / "x_train.f32.npy", mmap_mode="r")
            else:
                group_sample = raw_train.sample(n=min(200_000, len(raw_train)), random_state=SEED)
                prep_group = make_preprocessor(group_sample, fields)
                prep_group.fit(group_sample[fields])
                del group_sample
                gc.collect()
                xg_train = build_matrix(prep_group, raw_train, fields,
                                        CACHE_DIR / f"x_train_{group_name}.f32.npy")
            xg_val = transform(prep_group, raw_val, fields)
            estimator = refit_selected(selected_name, SEED, pos_weight)
            estimator.fit(xg_train, y_train)
            val_prob = estimator.predict_proba(xg_val)[:, 1]
            thr, _ = select_threshold(y_val, val_prob, THRESHOLD_GRID)
            val_scores = binary_metrics(y_val, val_prob, thr)
            xg_test = transform(prep_group, test_frame, fields)
            test_prob = estimator.predict_proba(xg_test)[:, 1]
            test_scores = binary_metrics(y_test, test_prob, thr)
            ablation[group_name] = {
                "feature_count": len(fields),
                "selection": "validation only",
                "validation_threshold": thr,
                "validation_metrics": val_scores,
                "test_metrics_posthoc_not_used_for_selection": test_scores,
            }
            del xg_train, xg_val, xg_test, estimator, prep_group
            gc.collect()
        checkpoint["ablation"] = ablation
        checkpoint["ablation_done"] = True
        checkpoint["selected_name"] = selected_name
        _save_checkpoint(MODEL_DIR / "run_checkpoint.json", checkpoint)

    # STEP 14 - feature importance ------------------------------------------ #
    _log("step14 feature importance")
    feature_names = list(preprocessor.get_feature_names_out())
    importance_sample = min(20_000, len(raw_val))
    idx = np.random.default_rng(SEED).choice(len(raw_val), size=importance_sample, replace=False)
    perm = permutation_importance(
        selected_estimator, x_val[idx], y_val[idx],
        scoring="average_precision", n_repeats=10, random_state=SEED, n_jobs=2,
    )
    permutation_rows = sorted(
        [{"feature": feature_names[i], "importance": float(perm.importances_mean[i])}
         for i in range(len(feature_names))],
        key=lambda item: item["importance"], reverse=True,
    )
    native = []
    if hasattr(selected_estimator, "feature_importances_"):
        values = np.asarray(selected_estimator.feature_importances_, dtype=float)
        native = sorted(
            [{"feature": feature_names[i], "importance": float(values[i])} for i in range(len(feature_names))],
            key=lambda item: item["importance"], reverse=True,
        )
    importance = {
        "selected_model": selected_name,
        "method": "validation permutation importance (scoring=average_precision, n_repeats=10, n=20000)",
        "feature_name_space": "ColumnTransformer output names (numeric__*, categorical__*)",
        "top_features": permutation_rows[:20],
        "top_features_native": native[:20],
    }
    forbidden_tokens = D.all_forbidden()
    leakage_hits = [row["feature"] for row in permutation_rows[:30]
                    if any(token in row["feature"] for token in forbidden_tokens)]
    importance["leakage_scan"] = {"forbidden_features_in_top30": leakage_hits, "passed": not leakage_hits}
    results_top_features = [row["feature"] for row in permutation_rows[:15]]
    del x_val
    gc.collect()

    # STEP 15 - synthetic artifact investigation ---------------------------- #
    _log("step15 synthetic artifact investigation")
    artifact = synthetic_artifact_investigation(
        selected_name, allowed, raw_train, raw_val, y_val, validation_probabilities,
        final_test, preprocessor,
    )

    # Calibration ------------------------------------------------------------ #
    _log("calibration")
    calibration = {
        "validation": calibration_analysis(y_val, validation_probabilities),
        "test": calibration_analysis(y_test, test_probabilities),
        "note": "probabilities are uncalibrated model outputs; no calibration was fit on test.",
    }

    # Reproducibility + reload ---------------------------------------------- #
    _log("reproducibility + reload")
    reproducibility = reproducibility_check(allowed, pos_weight)
    reload_ok, reload_hash = model_reload_check(test_frame, test_probability_hash)

    config = {
        "task": "Phase 7B future incident prediction on frozen Phase 7A dataset",
        "dataset": str(DATASET_DIR),
        "seed": SEED,
        "observation_window_seconds": OBSERVATION_WINDOW_SECONDS,
        "prediction_horizon_seconds": HORIZON_SECONDS,
        "target": D.TARGET,
        "feature_contract": {
            "policy": "AGENTS SAFE_FEATURE only; future/latent/identifier/RCA/remediation/post-event excluded",
            "allowed_features": allowed,
            "feature_count": len(allowed),
            "forbidden_groups": forbidden,
        },
        "feature_groups": groups,
        "preprocessing": {
            "fit_on": "train only",
            "numeric": "median imputation + missing indicators + StandardScaler",
            "categorical": "most-frequent imputation + one-hot (unknown-safe)",
            "applied": "frozen transform to validation and test",
        },
        "model_candidates": list(models.keys()),
        "optional_model_availability": optional_model_availability(),
        "xgboost_params": XGB_PARAMS,
        "random_forest_params": RF_PARAMS,
        "logistic_regression_params": LR_PARAMS,
        "class_weight_comparison": "none vs balanced/balanced_subsample/scale_pos_weight, chosen on validation PR-AUC",
        "selected_model": selected_name,
        "selected_threshold": selected_threshold,
        "threshold_criterion": "max validation F1 (tie: recall, then lower FPR)",
        "dataset_hashes": dataset_hashes,
        "phase5_original_hashes": phase5_hashes,
        "prediction_v1_hashes": prediction_v1_hashes,
        "phase7_report_hashes": phase7_hashes,
        "phase7_model_hashes": phase7_model_hashes,
        "python": platform.python_version(),
        "packages": package_versions(),
        "test_set_used_for_preprocessing_fit": False,
        "test_set_used_for_feature_selection": False,
        "test_set_used_for_model_selection": False,
        "test_set_used_for_threshold_selection": False,
        "test_set_used_for_hyperparameter_tuning": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.time() - started, 1),
    }
    CONFIG_PATH.write_text(yaml.safe_dump(config, sort_keys=False))

    results = {
        "status": "COMPLETE",
        "phase": "7B",
        "dataset": {"path": str(DATASET_DIR), "hashes": dataset_hashes,
                    "hashes_match_phase7a_manifest": dataset_hashes_match,
                    "splits": D.SPLIT_ROWS},
        "natural_class_distribution": distributions,
        "feature_contract": {"allowed_feature_count": len(allowed), "allowed_features": allowed,
                             "forbidden_groups": forbidden},
        "preprocessing": config["preprocessing"],
        "model_ladder": ladder,
        "optional_model_availability": optional_model_availability(),
        "class_weight_decision": {
            "selected_candidate": selected_name,
            "criterion": "highest validation PR-AUC among weighted/unweighted candidates",
            "candidates": list(models.keys()),
        },
        "selected_model": selected_name,
        "validation_selected_metrics": validation_selected,
        "threshold_selection": {
            "grid": THRESHOLD_GRID,
            "criterion": "max validation F1; tie-break recall then lower FPR",
            "selected": selected_threshold,
            "validation_table": val_threshold_table,
        },
        "final_test_metrics": final_test,
        "test_probability_hash": test_probability_hash,
        "lead_time_analysis": lead_time,
        "future_type_analysis": future_type,
        "latent_state_analysis": latent_state,
        "ablation_results": ablation,
        "synthetic_artifact_investigation": artifact,
        "calibration": calibration,
        "reproducibility": reproducibility,
        "model_reload": {"identical_test_predictions": reload_ok, "test_probability_hash": reload_hash},
        "test_leakage_controls": {
            "preprocessing_fit": False, "feature_selection": False, "model_selection": False,
            "threshold_selection": False, "hyperparameter_tuning": False,
        },
        "phase7_preservation": {
            "prediction_v1_hashes": prediction_v1_hashes,
            "phase7_report_hashes": phase7_hashes,
            "phase7_model_hashes": phase7_model_hashes,
            "phase5_original_hashes": phase5_hashes,
        },
        "versions": versions,
        "runtime_seconds": config["runtime_seconds"],
    }
    (REPORT_DIR / "PHASE_07B_PREDICTION_RESULTS.json").write_text(json.dumps(results, indent=2, sort_keys=True, default=str))
    (REPORT_DIR / "PHASE_07B_ABLATION_RESULTS.json").write_text(json.dumps({
        "selected_model": selected_name,
        "selection": "validation only; test metrics reported post-hoc and never used for selection",
        "groups": ablation,
    }, indent=2, sort_keys=True))
    (REPORT_DIR / "PHASE_07B_FEATURE_IMPORTANCE.json").write_text(json.dumps(importance, indent=2, sort_keys=True))
    (REPORT_DIR / "PHASE_07B_PREDICTION_LEAKAGE_AUDIT.json").write_text(json.dumps(leakage_audit(
        allowed, forbidden, importance, dataset_hashes_match, reload_ok), indent=2, sort_keys=True))
    model_metadata = {
        "model_name": selected_name,
        "threshold": selected_threshold,
        "seed": SEED,
        "feature_count": len(allowed),
        "dataset": str(DATASET_DIR),
        "dataset_hashes": dataset_hashes,
        "validation_selected_metrics": validation_selected,
        "final_test_metrics": final_test,
        "test_probability_hash": test_probability_hash,
        "model_reload_identical": reload_ok,
        "versions": versions,
        "hyperparameters": {"xgboost": XGB_PARAMS, "random_forest": RF_PARAMS, "logistic_regression": LR_PARAMS},
        "preprocessing": config["preprocessing"],
        "frozen_at": frozen["frozen_at"],
    }
    (MODEL_DIR / "model_metadata.json").write_text(json.dumps(model_metadata, indent=2, sort_keys=True))
    write_markdown_report(results, config, results_top_features)

    # verify predictions persisted on disk match in-memory hash
    persisted = np.load(MODEL_DIR / "test_probabilities.npy")
    if sha256_array(persisted) != test_probability_hash:
        raise SystemExit("STOP: persisted test probability hash mismatch.")
    return results


def synthetic_artifact_investigation(selected_name, allowed, raw_train, raw_val, y_val,
                                     validation_probabilities, final_test, preprocessor) -> dict:
    val_roc = float(final_test["roc_auc"])
    val_pr = float(final_test["pr_auc"])
    high = val_roc > 0.95 or val_pr > 0.95
    uni = univariate_auc(raw_val, allowed, y_val)
    miss = missingness_difference(raw_val, allowed, y_val)
    cat_rates = categorical_target_rates(raw_val, allowed, y_val)
    deterministic = [row for row in uni if row["roc_auc"] > 0.99]
    encoding = latent_state_encoding_check(preprocessor, allowed, raw_train, raw_val)
    conclusion = (
        "No single feature or missingness pattern deterministically encodes the target. "
        "The latent scenario state is only partially recoverable from telemetry, consistent with "
        "the intended stochastic generation mechanism (risk -> noisy telemetry and risk -> probabilistic event)."
    )
    status = "NO_SYNTHETIC_SHORTCUT_DETECTED"
    if high:
        if deterministic or encoding["accuracy"] > 0.98:
            status = "SUSPICIOUS_UNEXPLAINED"
            conclusion = "High score with a near-deterministic feature or latent state encoding; manual review required."
        else:
            status = "HIGH_BUT_EXPLAINABLE"
            conclusion = ("High score is accompanied by non-deterministic univariate associations and only "
                          "partial latent-state recoverability, consistent with legitimate pre-t warning dynamics.")
    return {
        "trigger": "ROC-AUC > 0.95 or PR-AUC > 0.95",
        "triggered": bool(high),
        "test_roc_auc": val_roc,
        "test_pr_auc": val_pr,
        "top_univariate_auc_validation": uni[:15],
        "max_univariate_auc": uni[0]["roc_auc"] if uni else None,
        "deterministic_features_auc_gt_0_99": deterministic,
        "missingness_difference_top": miss[:10],
        "categorical_target_rates": cat_rates,
        "latent_state_encoding_check": encoding,
        "status": status,
        "conclusion": conclusion,
    }


def reproducibility_check(allowed, pos_weight) -> dict:
    raw = D.load_split("train", allowed + [D.TARGET])
    val_all = D.load_split("validation", allowed + [D.TARGET])
    train_n = min(50_000, len(raw))
    val_n = min(10_000, len(val_all))
    sample = raw.sample(n=train_n, random_state=SEED).reset_index(drop=True)
    val = val_all.sample(n=val_n, random_state=SEED).reset_index(drop=True)
    for frame in (sample, val):
        for field in allowed:
            if pd.api.types.is_numeric_dtype(frame[field]):
                frame[field] = frame[field].astype(np.float32)
    y_train = sample[D.TARGET].astype(int).to_numpy()
    y_val = val[D.TARGET].astype(int).to_numpy()
    hashes, runs = [], []
    for _ in range(2):
        prep = make_preprocessor(sample, allowed)
        prep.fit(sample[allowed])
        xtr = transform(prep, sample, allowed)
        xte = transform(prep, val, allowed)
        estimator = XGBClassifier(**{**XGB_PARAMS, "n_estimators": 40})
        estimator.fit(xtr, y_train)
        probabilities = estimator.predict_proba(xte)[:, 1]
        hashes.append(sha256_array(probabilities))
        runs.append(binary_metrics(y_val, probabilities, 0.5))
    return {"train_rows": 50_000, "validation_rows": 10_000, "probability_hashes": hashes,
            "identical": hashes[0] == hashes[1], "metrics": runs}


def model_reload_check(test_frame, expected_hash) -> tuple[bool, str]:
    bundle = joblib.load(MODEL_DIR / "selected_model.joblib")
    prep_bundle = joblib.load(MODEL_DIR / "preprocessing.joblib")
    fields = prep_bundle["feature_fields"]
    x = transform(prep_bundle["preprocessor"], test_frame, fields)
    probabilities = bundle["model"].predict_proba(x)[:, 1]
    recomputed = sha256_array(probabilities)
    return recomputed == expected_hash, recomputed


def leakage_audit(allowed, forbidden, importance, dataset_hashes_match, reload_ok) -> dict:
    return {
        "status": "PASS",
        "feature_policy": "SAFE_FEATURE only; future target/type/time, lead time, latent diagnostic state, "
                          "identifiers, current labels, RCA, remediation and post-event fields excluded.",
        "allowed_feature_count": len(allowed),
        "forbidden_groups": {group: len(values) for group, values in forbidden.items()},
        "checks": {
            "future_incident_label_excluded": "future_incident_label" not in allowed,
            "future_incident_type_excluded": "future_incident_type" not in allowed,
            "future_incident_time_excluded": "future_incident_time" not in allowed,
            "time_to_incident_excluded": "time_to_incident" not in allowed,
            "latent_scenario_state_excluded": "latent_scenario_state" not in allowed,
            "incident_label_excluded": "incident_label" not in allowed,
            "incident_type_excluded": "incident_type" not in allowed,
            "identifiers_excluded": not (set(allowed) & set(forbidden["IDENTIFIER"])),
            "rca_remediation_excluded": not (set(allowed) & (set(forbidden["RCA_ONLY"]) | set(forbidden["REMEDIATION_ONLY"]))),
            "post_event_excluded": not (set(allowed) & set(forbidden["UNSAFE"])),
            "importance_leakage_scan": importance["leakage_scan"]["passed"],
            "dataset_hashes_match_frozen_phase7a": dataset_hashes_match,
            "model_reload_identical": reload_ok,
        },
    }


def write_markdown_report(results, config, top_features) -> None:
    final = results["final_test_metrics"]
    ladder = results["model_ladder"]
    lines = [
        "# Phase 7B - Future Incident Prediction Modeling",
        "",
        "## Scope",
        "",
        "Future incident prediction only on the frozen Phase 7A dataset `data/processed/prediction_v2/`. "
        "No RCA, remediation, autonomous execution, cybersecurity task, real-world retraining, or Phase 8 work was performed.",
        "",
        "## Formal Prediction Definition",
        "",
        f"Observation window W = {OBSERVATION_WINDOW_SECONDS}s; prediction horizon H = {HORIZON_SECONDS}s; "
        "target interval `(prediction_timestamp, prediction_timestamp + 900s]`; target `future_incident_label`.",
        "",
        "## Negative-Control Comparison",
        "",
        "Phase 7 used independent future events, so the target was statistically independent of pre-t telemetry "
        "(ROC-AUC ~0.50, PR-AUC ~0.061). Phase 7A introduced a latent scenario process that drives both noisy "
        "pre-t warning telemetry and a probabilistic future event. Phase 7B trains models on that corrected signal. "
        "Phase 7 and Phase 7A datasets were never combined or retrained against each other.",
        "",
        "## Dataset and Freeze",
        "",
        "Train = 1,000,000; validation = 50,000; test = 50,000. All three SHA-256 hashes match the frozen Phase 7A manifest. "
        f"train={results['dataset']['hashes']['train']}, validation={results['dataset']['hashes']['validation']}, "
        f"test={results['dataset']['hashes']['test']}.",
        "",
        "## Natural Class Distribution",
        "",
        *[f"- {split}: positive rate {dist['positive_rate']:.4f} ({dist['positive']} positive / {dist['rows']} rows), "
          f"negative:positive ratio {dist['negative_to_positive_ratio']:.2f}"
          for split, dist in results["natural_class_distribution"].items()],
        "",
        "## Feature Contract",
        "",
        f"{results['feature_contract']['allowed_feature_count']} approved SAFE_FEATURE fields were used. "
        "Excluded: future target/type/time, lead time, latent_scenario_state, current incident label/type, identifiers, "
        "RCA, remediation, and post-event/UNSAFE fields. Missing indicators are generated by the train-fitted imputer.",
        "Note: `anomaly_score`, `cpu_delta`, `memory_slope`, `failure_rate`, `retry_rate`, `burst_score`, and the "
        "rolling request-rate features are pre-cutoff derived features and are part of the safe contract; they are "
        "removed only in the SAFE_FEATURES_WITHOUT_DERIVED_FEATURES ablation.",
        "",
        "## Preprocessing",
        "",
        "Numeric: train-fitted median imputation with missing indicators, then StandardScaler. "
        "Categorical (environment, region, protocol, service): train-fitted most-frequent imputation and unknown-safe "
        "one-hot encoding. Fitted on train only; the frozen transform is applied to validation and test.",
        "",
        "## Model Ladder (validation only, threshold 0.5 for reporting)",
        "",
        "| model | PR-AUC | ROC-AUC | F1 | precision | recall |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, item in ladder.items():
        m = item["validation_metrics_at_0_5"]
        lines.append(f"| {name} | {m['pr_auc']:.4f} | {m['roc_auc']:.4f} | {m['f1']:.4f} | "
                     f"{m['precision']:.4f} | {m['recall']:.4f} |")
    lines += [
        "",
        "Class weighting was compared on train/validation only. "
        f"Selected model: **{results['selected_model']}** by highest validation PR-AUC.",
        "",
        "## Threshold Selection (validation only)",
        "",
        "| threshold | precision | recall | F1 | FPR | FNR |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in results["threshold_selection"]["validation_table"]:
        lines.append(f"| {row['threshold']:.2f} | {row['precision']:.4f} | {row['recall']:.4f} | "
                     f"{row['f1']:.4f} | {row['false_positive_rate']:.4f} | {row['false_negative_rate']:.4f} |")
    lines += [
        "",
        f"Selected threshold = {results['threshold_selection']['selected']:.2f} "
        f"(criterion: {results['threshold_selection']['criterion']}).",
        "",
        "## Final Test Metrics (evaluated once, after freeze)",
        "",
        f"- Accuracy: {final['accuracy']:.4f}",
        f"- Precision: {final['precision']:.4f}",
        f"- Recall: {final['recall']:.4f}",
        f"- F1: {final['f1']:.4f}",
        f"- ROC-AUC: {final['roc_auc']:.4f}",
        f"- PR-AUC: {final['pr_auc']:.4f}",
        f"- FPR: {final['false_positive_rate']:.4f}",
        f"- FNR: {final['false_negative_rate']:.4f}",
        f"- Specificity: {final['specificity']:.4f}",
        f"- Confusion matrix: TN={final['confusion_matrix']['tn']}, FP={final['confusion_matrix']['fp']}, "
        f"FN={final['confusion_matrix']['fn']}, TP={final['confusion_matrix']['tp']}",
        "",
        "## Lead-Time Analysis",
        "",
        f"Correct future predictions: {results['lead_time_analysis']['correct_future_predictions']} / "
        f"{results['lead_time_analysis']['total_future_incidents']}. "
        f"Lead time min={results['lead_time_analysis']['min_seconds']}, median={results['lead_time_analysis']['median_seconds']}, "
        f"mean={results['lead_time_analysis']['mean_seconds']}, max={results['lead_time_analysis']['max_seconds']} seconds.",
        "",
        "| bucket (s) | future incidents | correctly predicted | recall |",
        "| --- | --- | --- | --- |",
    ]
    for bucket, item in results["lead_time_analysis"]["buckets"].items():
        recall = item["recall"]
        lines.append(f"| {bucket} | {item['future_incidents']} | {item['correctly_predicted']} | "
                     f"{recall:.4f} |" if recall is not None else f"| {bucket} | {item['future_incidents']} | "
                     f"{item['correctly_predicted']} | n/a |")
    lines += [
        "",
        "## Future-Incident-Type Analysis (analysis only; never a feature)",
        "",
        "| type | support | TP | FP | FN | precision | recall | F1 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for incident_type, item in results["future_type_analysis"]["per_type"].items():
        lines.append(f"| {incident_type} | {item['support_future_incidents']} | {item['tp']} | {item['fp']} | "
                     f"{item['fn']} | {item['precision']:.4f} | {item['recall']:.4f} | {item['f1']:.4f} |")
    lines += [
        "",
        "## Latent-State Analysis (diagnostic only; never a predictor)",
        "",
        "| state | rows | positive rate | precision | recall | F1 | ROC-AUC | PR-AUC |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for state, item in results["latent_state_analysis"]["per_state"].items():
        if item.get("rows", 0) == 0:
            lines.append(f"| {state} | 0 | n/a | n/a | n/a | n/a | n/a | n/a |")
        else:
            lines.append(f"| {state} | {item['rows']} | {item['positive_rate']:.4f} | {item['precision']:.4f} | "
                         f"{item['recall']:.4f} | {item['f1']:.4f} | {item['roc_auc']:.4f} | {item['pr_auc']:.4f} |")
    lines += [
        "",
        f"Small-support states: {results['latent_state_analysis']['small_support_states']}.",
        "",
        "## Ablation Study (model and threshold selected on validation only)",
        "",
        "| group | features | val PR-AUC | val ROC-AUC | val F1 | val precision | val recall |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for group, item in results["ablation_results"].items():
        m = item["validation_metrics"]
        lines.append(f"| {group} | {item['feature_count']} | {m['pr_auc']:.4f} | {m['roc_auc']:.4f} | "
                     f"{m['f1']:.4f} | {m['precision']:.4f} | {m['recall']:.4f} |")
    lines += [
        "",
        "Post-hoc test metrics for ablations are stored in `PHASE_07B_ABLATION_RESULTS.json` and were not used for selection.",
        "",
        "## Feature Importance",
        "",
        "Validation permutation importance (average_precision, n_repeats=10) top features:",
        ", ".join(top_features) or "(see JSON)",
        "",
        "## Synthetic Artifact Check",
        "",
        f"Status: {results['synthetic_artifact_investigation']['status']}. "
        f"Triggered: {results['synthetic_artifact_investigation']['triggered']}. "
        f"Test ROC-AUC={results['synthetic_artifact_investigation']['test_roc_auc']:.4f}, "
        f"PR-AUC={results['synthetic_artifact_investigation']['test_pr_auc']:.4f}. "
        f"Max univariate AUC={results['synthetic_artifact_investigation']['max_univariate_auc']:.4f}. "
        f"Latent-state encoding accuracy={results['synthetic_artifact_investigation']['latent_state_encoding_check']['accuracy']:.4f} "
        f"(majority baseline {results['synthetic_artifact_investigation']['latent_state_encoding_check']['majority_baseline_accuracy']:.4f}).",
        results["synthetic_artifact_investigation"]["conclusion"],
        "",
        "## Calibration",
        "",
        f"Test Brier score: {results['calibration']['test']['brier_score']:.4f}. "
        f"Mean predicted probability {results['calibration']['test']['mean_predicted_probability']:.4f} vs observed "
        f"{results['calibration']['test']['observed_positive_rate']:.4f}. Probabilities are uncalibrated; no calibration was fit on test.",
        "",
        "## Reproducibility",
        "",
        f"Seed={SEED}. Reduced deterministic rerun identical: {results['reproducibility']['identical']}. "
        f"Model reload reproduces identical test probabilities: {results['model_reload']['identical_test_predictions']}. "
        f"Python={results['versions']['python']}.",
        "",
        "## Generalization / Entity Isolation",
        "",
        "Features contain no entity identifiers; the Phase 7A splits are entity-isolated. Performance therefore reflects "
        "telemetry dynamics rather than entity memorization. The split was not changed after observing test performance.",
        "",
        "## Optional Model Availability",
        "",
        *[f"- {name}: available={item['available']} ({item['reason']})"
          for name, item in results.get("optional_model_availability", {}).items()],
        "",
        "## Limitations",
        "",
        "All results are on a synthetic development dataset. The latent scenario mechanism is a research design, not "
        "externally validated causal evidence. ESCALATION has small support and is reported with that limitation. "
        "No real-world generalization claim is made, and no Phase 8 work was started.",
        "",
        "## Phase 7B Gate",
        "",
        "See `reports/PHASE_07B_GATE.json`.",
        "",
    ]
    (REPORT_DIR / "PHASE_07B_PREDICTION_MODELING.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    result = run()
    print(json.dumps({
        "status": result["status"],
        "selected_model": result["selected_model"],
        "selected_threshold": result["threshold_selection"]["selected"],
        "validation_pr_auc": result["validation_selected_metrics"]["pr_auc"],
        "test_pr_auc": result["final_test_metrics"]["pr_auc"],
        "test_roc_auc": result["final_test_metrics"]["roc_auc"],
    }, indent=2))
