# Phase 7 — Future Incident Prediction

## Objective

Predict whether a genuine future incident occurs within the next 900 seconds using only information available at the prediction timestamp.

## Research Question

Which pre-cutoff telemetry groups provide useful advance warning of an incident in `(t, t+H]`?

## Formal Prediction Definition

W = 900 seconds; H = 900 seconds; target interval `(prediction_timestamp, prediction_timestamp + 900 seconds]`; target `future_incident_label`.

## Dataset

Only `data/processed/prediction/` was used. Original Phase 5 detection parquet files were not used for prediction modeling. Train=1,000,000, validation=50,000, test=50,000.

## Label Construction

Phase 5A derives targets from an independent seeded future-event calendar. Positive future timestamps are strictly after the cutoff and within H; negative rows have null future timestamps.

## Feature Availability

76 SAFE_FEATURE fields from the Phase 5A-supported contract were used. Current labels, future targets, IDs, timestamps-as-metadata, RCA, remediation, and post-event fields were excluded.

## Leakage Controls

Preprocessing was fit on train only. Model selection and threshold selection used validation only. Test was loaded once after the selected model and threshold were frozen.

## Train/Validation/Test Protocol

Full train rows available: 1,000,000. Deterministic train rows used: 250000. Validation and test were unchanged.

## Baselines

- majority: F1=0.0000, PR-AUC=0.0585, ROC-AUC=0.5000, recall=0.0000
- stratified_dummy: F1=0.0582, PR-AUC=0.0584, ROC-AUC=0.4993, recall=0.0591
- logistic_regression: F1=0.0000, PR-AUC=0.0599, ROC-AUC=0.5068, recall=0.0000
- random_forest: F1=0.0988, PR-AUC=0.0592, ROC-AUC=0.5024, recall=0.2691
- xgboost: F1=0.0000, PR-AUC=0.0591, ROC-AUC=0.5063, recall=0.0000

## Model Selection

Selected `logistic_regression` by validation PR-AUC.

## Threshold Selection

- 0.03: precision=0.0585, recall=1.0000, F1=0.1105, FPR=1.0000, FNR=0.0000
- 0.04: precision=0.0585, recall=0.9993, F1=0.1105, FPR=0.9996, FNR=0.0007
- 0.05: precision=0.0585, recall=0.9566, F1=0.1102, FPR=0.9569, FNR=0.0434
- 0.06: precision=0.0602, recall=0.4913, F1=0.1073, FPR=0.4765, FNR=0.5087
- 0.07: precision=0.0634, recall=0.0359, F1=0.0458, FPR=0.0329, FNR=0.9641
- 0.10: precision=0.0000, recall=0.0000, F1=0.0000, FPR=0.0000, FNR=1.0000
- 0.30: precision=0.0000, recall=0.0000, F1=0.0000, FPR=0.0000, FNR=1.0000
- 0.50: precision=0.0000, recall=0.0000, F1=0.0000, FPR=0.0000, FNR=1.0000
- 0.70: precision=0.0000, recall=0.0000, F1=0.0000, FPR=0.0000, FNR=1.0000
Selected threshold: 0.03

## Final Test Results — SYNTHETIC DEVELOPMENT TEST PERFORMANCE
Accuracy=0.0618; Precision=0.0618; Recall=1.0000; F1=0.1165; PR-AUC=0.0610; ROC-AUC=0.4960; FPR=1.0000; FNR=0.0000; Confusion={'tn': 0, 'fp': 46908, 'fn': 0, 'tp': 3092}

## Lead-Time Analysis
{"buckets": {"0_300": 1046, "301_600": 1029, "601_900": 1017}, "correct_future_predictions": 3092, "max_seconds": 899.0, "mean_seconds": 447.1478007761966, "median_seconds": 447.5, "min_seconds": 1.0, "percentiles_seconds": {"10": 89.10000000000002, "25": 221.0, "50": 447.5, "75": 672.25, "90": 809.9000000000001}}

## Scenario-Level Analysis
Future incident type is not present in the Phase 5A 110-field schema, so D1/D2/C1-C5 future-type performance is not scientifically available; no current incident type was relabeled as future type.

## Ablation Study

- all_safe_features: F1=0.0000, PR-AUC=0.0599, ROC-AUC=0.5068, Recall=0.0000
- infrastructure_cloud_workload: F1=0.0000, PR-AUC=0.0605, ROC-AUC=0.5094, Recall=0.0000
- cicd_deployment: F1=0.0000, PR-AUC=0.0592, ROC-AUC=0.5026, Recall=0.0000
- network_security: F1=0.0000, PR-AUC=0.0596, ROC-AUC=0.5051, Recall=0.0000
- safe_without_derived: F1=0.0000, PR-AUC=0.0602, ROC-AUC=0.5090, Recall=0.0000

## Synthetic Artifact Analysis

Univariate associations, current-state target rates, and feature importance were inspected. Results may reflect synthetic separability and are not real-world external validation.

## Feature Importance

Leakage scan passed: True. Top features are recorded in PHASE_07_PREDICTION_FEATURE_IMPORTANCE.json.

## Limitations

Future event types are not stored, so future-type scenario metrics are unavailable and are explicitly not fabricated. UNSW and all real-world datasets were excluded. No real-world generalization claim is made.

## Reproducibility

Seed=20261008; reduced probability hashes matched=True; model artifact=/workspaces/devsecops-v1/models/prediction/selected_prediction_model.joblib.

## Research Interpretation

These are synthetic development metrics only. Real-world external validation is a later activity. D2 prediction semantics remain cloud cluster/workload reliability, not Kubernetes-specific semantics.

## Phase 8 Readiness

READY; Phase 8 not started.
