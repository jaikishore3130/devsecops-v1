# Phase 5 — Synthetic Dataset Generation

## Status

**COMPLETE**

## Dataset

Train: 1000000
Validation: 50000
Test: 50000
Total: 1100000
Columns: 110

## Generation Configuration

Master seed: 20261008
Generator version: 1.0.0
Schema version: 1.0.0
Chunk size: 100000
Generation timestamp: 2026-10-08T19:27:11.709514+00:00

## Incident Distribution

NONE: 71.954182%
D1: 5.991%
D2: 6.991455%
C1: 4.026455%
C2: 4.005273%
C3: 3.006%
C4: 2.005455%
C5: 2.020182%

## Parquet Integrity

train: readable=True; rows=1000000; columns=110; schema_match=True
validation: readable=True; rows=50000; columns=110; schema_match=True
test: readable=True; rows=50000; columns=110; schema_match=True

## Leakage Validation

### Entity Isolation
PASS
### Exact Duplicate Isolation
PASS
### Future Target Leakage
PASS
### Identifier Contract
PASS
### Incident Distribution
PASS
### Incident Isolation
PASS
### Missingness
PASS
### Near Duplicate Isolation
PASS
### Parquet Integrity
PASS
### Reproducibility
PASS
### Research Integrity
PASS
### Row Counts
PASS
### Scenario Sanity
PASS
### Schema
PASS
### Temporal Leakage
PASS
### Test Integrity
PASS
### Test Temporal
PASS
### Train Integrity
PASS
### Train Temporal
PASS
### Validation Integrity
PASS
### Validation Temporal
PASS

## Missingness

Overall: 0.031274
deployment: 0.018751
ci_cd: 0.020532
infrastructure: 0.025013
cloud_workload: 0.024941
network_security: 0.02061
derived_temporal: 0.016064

## Scenario Sanity

All scenarios none/D1/D2/C1-C5 are represented: PASS.

## Reproducibility

The 20k/5k/5k recovery test passed twice with identical canonical hashes.

## Research Integrity

- UNSW was not used for synthetic calibration.
- UNSW remains external-only.
- RCA labels are not causal ground truth.
- Remediation labels are recommendations.
- No model was trained.
- No performance claim was made.

## Limitations

Synthetic scenario distributions and labels are design choices, not causal real-world evidence. Near-duplicate isolation uses a documented rounded telemetry signature.

## Phase 6 Readiness

READY
