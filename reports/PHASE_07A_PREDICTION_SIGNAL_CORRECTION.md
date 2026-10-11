# Phase 7A — Prediction Signal Correction

## Executive Summary

Phase 7's independent future-event calendar was a valid negative-control experiment but produced near-chance prediction because the future event was independent of pre-t telemetry. Phase 7A creates a separate `data/processed/prediction_v2/` dataset with a latent scenario process that influences both noisy pre-t warning telemetry and the future event.

No prediction model was trained in Phase 7A.

## Previous Phase 7 Negative Control

Phase 7 used independent future-event generation and produced ROC-AUC approximately 0.496, PR-AUC approximately 0.061, F1 approximately 0.116, and FPR 1.0 at its selected threshold. That result remains preserved as a scientifically useful negative control.

## Corrected Generator Design

For each row, Phase 7A samples a latent risk and scenario state: `NORMAL`, `EARLY_SIGNAL`, `DEGRADATION`, or `ESCALATION`. The latent process influences multiple pre-cutoff telemetry trajectories with noise, missingness inherited from the source generator, and scenario-specific effects. A stochastic event probability then determines whether a future incident occurs, and the same latent scenario selects its future incident type.

The relationship is probabilistic, not a threshold rule and not a copy of the current incident label.

## Temporal Definition

- Observation window W: 900 seconds
- Prediction timestamp: `prediction_timestamp`
- Prediction horizon H: 900 seconds
- Future interval: `(t, t+900 seconds]`
- Positive target: `future_incident_label=1`
- Future type: `future_incident_type`, analysis-only and excluded from features

Positive lead times vary from 1 to 899 seconds. Negative rows have null future time and lead time.

## Dataset

Train: 1,000,000 rows  
Validation: 50,000 rows  
Test: 50,000 rows  
Schema: 112 fields, consisting of the frozen 110 fields plus `future_incident_type` and diagnostic `latent_scenario_state`.

The original Phase 5, Phase 5A, Phase 6, and Phase 7 artifacts were not overwritten.

## Future Incident Distribution

Train future-positive rate: 10.956%  
Validation future-positive rate: 10.982%  
Test future-positive rate: 11.046%

All D1, D2, C1, C2, C3, C4, and C5 future types are represented in every split.

## Lead-Time Distribution

Train median: 631 seconds; minimum 1; maximum 899.  
Validation median: 630 seconds; minimum 1; maximum 899.  
Test median: 633 seconds; minimum 60; maximum 899.

## Predictive Signal Audit

Latent-state future rates in validation increase from 7.28% for NORMAL to 14.74% for EARLY_SIGNAL, 22.66% for DEGRADATION, and 27.82% for ESCALATION.

Top safe-feature validation univariate AUC values:

- `source_count`: 0.5985
- `restart_count`: 0.5783
- `scheduling_delay_seconds`: 0.5652
- `request_rate`: 0.5584
- `memory_slope`: 0.5498
- `unique_destination_ports`: 0.5465
- `retry_count`: 0.5447

These are moderate associations, not deterministic shortcuts. No safe feature exactly equals the future target.

## Leakage Audit

PASS. Future labels, future type, future times, lead times, post-event measurements, recovery state, RCA, remediation, identifiers, and diagnostic latent state are excluded from the safe feature policy. Entity intersections across splits are absent, and future times satisfy the strict horizon bounds.

## Synthetic Artifact Audit

PASS. The corrected process introduces above-independence signal through a documented latent scenario mechanism. It does not use a direct target threshold, current incident label copy, or fixed future time. The resulting signal remains synthetic and requires later independent external validation.

## Reproducibility

PASS. A 10,000-row diagnostic rerun under seed `20261008` produced identical parquet hashes.

## Limitations

The latent scenario is a research-design mechanism, not externally validated causal evidence. Future-type labels are synthetic annotations. The diagnostic state is retained for auditability but is not an allowed prediction feature.

## Phase 7A Gate Decision

**COMPLETE.** The corrected dataset is ready for separate review before any Phase 7B modeling. No model training, RCA, remediation, or Phase 8 work occurred.
