# Phase 5A — Future Target Correction

## Status

COMPLETE for target construction only. No prediction model was trained.

## Root Cause

The original generator assigned `future_incident_label = incident_label` and set every positive future timestamp to `prediction_timestamp + H`. That encoded current incident detection as future prediction.

## Correction

Phase 5A creates a separately versioned prediction dataset. It generates an independently seeded temporal event calendar per split, then derives each row's future target from the first event strictly after `prediction_timestamp` and within the 900-second horizon. Future event time and `time_to_incident` are variable and are not input features.

## Integrity

The original Phase 5 detection parquet files, Phase 6 detection model, and Phase 6 metadata were read-only and their hashes remain unchanged. The prediction dataset is separate under `data/processed/prediction/`.

## Scope Boundary

This phase performs target construction and leakage/artifact audits only. Prediction model training, model selection, thresholding, RCA, remediation, and UNSW validation were not started.
