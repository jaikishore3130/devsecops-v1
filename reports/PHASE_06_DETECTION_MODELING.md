# Phase 6 — Detection Modeling

## Objective

Build and evaluate a binary D1 general incident detector over D1, D2, C1-C5.

## Dataset

Phase 5 commit `0f6bb59`; train 1,000,000, validation 50,000, test 50,000; 110 canonical fields.

## Target Definition

`incident_label=0` is normal and `incident_label=1` is an incident/anomalous event. Positive incidents are D1, D2, C1, C2, C3, C4, and C5. `incident_type` is retained for scenario analysis, not used as a predictor.

## Feature Contract

76 SAFE_FEATURE fields were used. The complete classification of all 110 canonical fields is in `metadata/detection_feature_contract.yaml`.

## Excluded Fields

Identifiers, current/future labels, raw timestamps, during-event fields, RCA outputs, and remediation outputs were excluded to prevent memorization and leakage.

## Preprocessing

Numeric fields use train-fitted median imputation with missing indicators and scaling. Categorical fields use train-fitted most-frequent imputation and one-hot encoding. Validation and test are transformed without fitting.

## Baselines

- majority: F1=0.0000, PR-AUC=0.2788, ROC-AUC=0.5000, recall=0.0000
- stratified_dummy: F1=0.2793, PR-AUC=0.2789, ROC-AUC=0.5004, recall=0.2791
- logistic_regression: F1=0.9962, PR-AUC=0.9999, ROC-AUC=1.0000, recall=0.9942
- random_forest: F1=0.9983, PR-AUC=0.9999, ROC-AUC=1.0000, recall=0.9973
- xgboost: F1=0.9992, PR-AUC=1.0000, ROC-AUC=1.0000, recall=0.9987

## Validation Protocol

Models and preprocessing were fit on train only. Model comparison and threshold selection used validation only. Test remained untouched until the selected model, preprocessing, and threshold were frozen.

## Model Comparison

Selected model: `xgboost` by validation PR-AUC.

## Threshold Analysis

- 0.30: precision=0.9995, recall=0.9993, F1=0.9994, FPR=0.0002, FNR=0.0007
- 0.40: precision=0.9996, recall=0.9989, F1=0.9992, FPR=0.0002, FNR=0.0011
- 0.50: precision=0.9997, recall=0.9987, F1=0.9992, FPR=0.0001, FNR=0.0013
- 0.60: precision=0.9998, recall=0.9981, F1=0.9990, FPR=0.0001, FNR=0.0019
- 0.70: precision=0.9999, recall=0.9971, F1=0.9985, FPR=0.0000, FNR=0.0029

Selected validation threshold: 0.30

## Final Test Evaluation

- Accuracy: 0.9997
- Precision: 0.9994
- Recall: 0.9996
- F1: 0.9995
- ROC-AUC: 1.0000
- PR-AUC: 1.0000
- FPR: 0.0002
- FNR: 0.0004
- Confusion matrix: {'tn': 36105, 'fp': 9, 'fn': 6, 'tp': 13880}

## Scenario-Level Results

- D1: samples=2985, recall=0.9997, precision=1.0000, false_negatives=1, detection_rate=0.9997
- D2: samples=3349, recall=0.9994, precision=1.0000, false_negatives=2, detection_rate=0.9994
- C1: samples=2022, recall=1.0000, precision=1.0000, false_negatives=0, detection_rate=1.0000
- C2: samples=1962, recall=1.0000, precision=1.0000, false_negatives=0, detection_rate=1.0000
- C3: samples=1546, recall=1.0000, precision=1.0000, false_negatives=0, detection_rate=1.0000
- C4: samples=987, recall=1.0000, precision=1.0000, false_negatives=0, detection_rate=1.0000
- C5: samples=1035, recall=0.9971, precision=1.0000, false_negatives=3, detection_rate=0.9971

## Feature Importance

Method: gain_or_split_importance_from_final_tree_model. Leakage scan passed: True.
- numeric__anomaly_score: 0.266360
- numeric__source_count: 0.132013
- numeric__queue_length: 0.086563
- numeric__unique_destination_hosts: 0.061178
- numeric__failure_rate: 0.060572
- numeric__scheduling_delay_seconds: 0.051693
- numeric__change_size: 0.037340
- numeric__failed_auth_attempts: 0.034967
- numeric__request_rate_rolling_mean: 0.031344
- numeric__request_rate: 0.030318
- numeric__network_in_bytes: 0.025559
- numeric__auth_attempts: 0.024194
- numeric__unique_destination_ports: 0.020684
- numeric__retry_count: 0.019951
- numeric__unique_source_count: 0.019478

## Ablation Study

- all_safe_features: validation F1=0.9969, PR-AUC=0.9999, ROC-AUC=1.0000
- infrastructure_cloud_workload: validation F1=0.8501, PR-AUC=0.9372, ROC-AUC=0.9654
- cicd_deployment: validation F1=0.3570, PR-AUC=0.5089, ROC-AUC=0.6106
- network_security: validation F1=0.6983, PR-AUC=0.7919, ROC-AUC=0.8388
- safe_without_derived: validation F1=0.9908, PR-AUC=0.9993, ROC-AUC=0.9997

## Synthetic Artifact Analysis

The benchmark is synthetic and strong performance may reflect controlled separability. Numeric univariate ROC-AUC leaders were: anomaly_score=0.9151, queue_length=0.8571, request_rate=0.7443, request_rate_rolling_mean=0.7417, open_connections=0.7320. Missingness, categorical target-rate spread, scenario distributions, and identifier exclusion were inspected. Results are not real-world generalization evidence.

## Limitations

UNSW was not used for training, calibration, feature selection, threshold tuning, or hyperparameter tuning. External validation and D2 prediction, RCA, and remediation remain future work.

## Reproducibility

Seed: 20261008; dataset commit: 0f6bb59; model artifact: `/workspaces/devsecops-v1/models/detection/selected_detection_model.joblib`. The reduced rerun probability hashes matched exactly: True.

## Research Interpretation

Supported by project evidence: controlled synthetic development separated from independent external validation, temporal/entity leakage controls, and multi-metric evaluation. Adopted here: train-only preprocessing, validation-only threshold selection, a baseline ladder, and scenario analysis. Modified for this phase: D1 binary detection only, a deterministic 250,000-row train sample for resource-bounded fitting, and XGBoost as the selected tree baseline. Project-specific additions are the 110-field contract, synthetic artifact scan, and validation-selected threshold. This is not a claim of deployment readiness or superiority over real-world systems.

## Status

PHASE 6 = COMPLETE; scope is D1 detection only.
