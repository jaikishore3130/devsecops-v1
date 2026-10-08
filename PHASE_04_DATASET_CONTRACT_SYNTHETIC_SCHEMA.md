# Phase 4 - Dataset Contract, Synthetic Telemetry Schema and Leakage-Safe Data Architecture

## 1. Objective

Phase 4 converts Phases 1-3B evidence into a version-controlled contract for
future synthetic development data and independent external validation. It
defines entities, telemetry, labels, temporal windows, availability, leakage
controls, split policy, generator design, and validation rules. No synthetic
records, models, metrics, applications, or remediation automation were made.

## 2. Evidence Inputs

Inputs were the Phase 1-3B reports, acquisition manifests, cross-dataset
feature mapping, and the bounded UNSW-NB15 profile at
`reports/dataset_audit/UNSW_NB15_PHASE3B_PROFILE.md`.

## 3. Real-Data Findings Used

The UNSW partition has 440,044 rows, 49 documented fields, 79.798838% normal
and 20.201162% attack labels, 133,325 exact duplicates (30.298107%), 38 source
IPs, 43 destination IPs, and 13 services. Numeric time fields support ordering,
not verified incident boundaries. Native categories include Reconnaissance and
Generic, but no causal RCA, component, recovery, or remediation ground truth.

## 4. Verified vs Documented vs Assumed Information

Counts, values, duplicate rate, cardinalities, and observed time positions are
verified for the bounded slice. Candidate schemas and UNSW field names are
documented mappings because the raw CSV has no header. UUID hierarchy,
synthetic progression, RCA taxonomy, recommendations, distributions, and
correlations are research-design choices. Unsupported external semantics are
rejected rather than inferred.

## 5. Entity Model

The hierarchy is organization -> project -> environment -> service ->
deployment -> host/workload, with pipeline -> job and telemetry window ->
incident -> event relationships. IDs are UUID-style and unique. Project names
are scoped to organizations and may repeat. IDs are grouping and leakage
controls, not default predictors.

## 6. Event Model

Events are timestamped telemetry, deployment, pipeline, workload, network,
security, incident, and recovery observations. `event_id` identifies an event;
`window_id` identifies an observation window. Incident records hold current and
future labels separately from telemetry evidence.

## 7. Temporal Model

Every telemetry record has `event_timestamp`. A prediction example has a
lookback `W` ending at cutoff `t` and a target horizon `H` covering `(t, t+H]`.
Features are `X(t-W:t)`; future incident fields are targets. No value after `t`
may enter prediction features.

## 8. Telemetry Architecture

Canonical groups are identity/context, deployment, CI/CD, infrastructure,
cloud cluster/workload, network, security, temporal, and derived telemetry.
Fields carry units, ranges, source type, availability stage, and missingness.
Correlated signals use shared workload and scenario factors with noise and
benign counterexamples.

## 9. Feature Taxonomy

Raw fields are direct observations; aggregated fields summarize a declared
window; derived fields include rates, deltas, slopes, rolling statistics,
entropy, burst scores, and anomaly scores. Derived lineage is cutoff-bounded.
The complete field inventory is in `metadata/synthetic_schema.csv` and task
availability is in `metadata/feature_availability_matrix.csv`.

## 10. Label Taxonomy

Detection uses binary `incident_label`. `incident_type` is `none`, D1, D2, or
C1-C5. Prediction uses future incident labels and timing. RCA uses controlled
root-cause category and component annotations, not proven causal inference.
Remediation uses recommendations, not action success.

## 11. Detection Data Contract

Detection may use telemetry available at the current event time, excluding
current labels and post-event outcomes. Exact duplicates and repeated
identity-time keys remain within a split.

## 12. Prediction Data Contract

Prediction consumes only the cutoff-safe observation window and predicts an
incident in `H`. Final build/failure status, incident labels, post-cutoff
metrics, recovery, RCA, and remediation fields are excluded.

## 13. RCA Data Contract

RCA is a downstream classification/localization task over available incident
evidence. Synthetic labels come from documented scenario rules and must not be
described as externally validated causal truth.

## 14. Remediation Recommendation Contract

Recommendations include rollback, restart, scaling, throttling, blocking,
rate-limiting, credential rotation, configuration fix, failover, quarantine,
manual investigation, and no action. No `remediation_success` field is defined.

## 15. Feature Availability

The availability matrix classifies each major field by source, before/during/
after availability, task safety, leakage risk, and derivation. During/after
fields may support retrospective RCA but are unsafe for future prediction.

## 16. Leakage Prevention

Forbidden predictors include incident, attack, build/failure, RCA,
remediation, recovery, and post-incident fields. IDs and reused network groups
are grouping controls. Derived features are cutoff-bounded; duplicate,
identity-time, temporal, group, train-only preprocessing, and external-data
isolation checks are mandatory.

## 17. Synthetic Generator Architecture

`metadata/synthetic_generator_spec.md` defines entity, baseline, telemetry,
failure, attack, incident, window, label, and leakage-validator components.
`src/data_generation/` is intentionally a design boundary only.

## 18. Correlation Model

Resource pressure can raise load, queue, latency proxies, and failure risk;
deployment changes can raise error and restart risk; flooding can raise request,
source, packet, and traffic rates; scanning can raise diversity and short-flow
frequency. These are noisy probabilistic relationships, not threshold rules.

## 19. Normal Behavior Model

Normal data includes diurnal changes, benign deployments, traffic bursts,
retries without failure, resource spikes without incidents, measurement noise,
and missing telemetry to reduce synthetic shortcuts.

## 20. Failure/Attack Progression

Scenarios may move through NORMAL, EARLY_SIGNAL, DEGRADATION, INCIDENT, and
RECOVERY, but can skip, repeat, start abruptly, or recover intermittently.
D1-D2 and C1-C5 remain the only defined types.

## 21. Missingness Model

Random, sensor-specific, outage, delayed, and environment-unavailable
missingness is allowed. Missingness cannot deterministically identify a label.

## 22. Duplicate Policy

The UNSW duplicate rate is evidence only and is not copied into synthetic data.
Repeated observations and tagged contamination scenarios stay within one split;
near-duplicates receive the same treatment.

## 23. Entity Generalization

Scenario assignment is independent of stable IDs. Protocols may hold out
organizations, projects, services, hosts, workloads, sessions, or incidents.
Repeated project names across organizations are allowed.

## 24. Split Architecture

Future targets are 1,000,000 train, 50,000 validation, and 50,000 test rows.
These are design targets only. Group, incident, duplicate, and temporal
constraints are applied before release.

## 25. External Validation Policy

UNSW-NB15 remains a partial external-validation candidate only. It is not
development data, generator calibration data, threshold-tuning data, or a
source for repeated design decisions. Its limitations must be disclosed.

## 26. Dataset Limitations

Only one bounded real slice is available. D1, D2, C1, C2, and C4 lack acquired
record-level evidence; C3 and C5 are partial through UNSW categories. Full
representativeness, timezone, near-duplicates, causal labels, and action
outcomes remain unknown.

## 27. Research Hypotheses

- H1: Multi-source telemetry can detect predefined incidents under leakage-safe evaluation.
- H2: Temporal windows improve early prediction over static point features.
- H3: Hierarchical context improves generalization to unseen entities.
- H4: Separating detection, prediction, RCA, and recommendation reduces leakage and improves interpretability.

These hypotheses are unproven.

## 28. Intended Contributions

The intended contribution is a unified, leakage-aware synthetic DevOps/security
telemetry framework with staged detection, temporal prediction, RCA annotation,
and remediation recommendation, evaluated with controlled synthetic studies
and independent real-world data where supported. It is not a claim that all
stages have real-world validation.

## 29. Reproducibility

Later generation must record contract/schema versions, evidence version,
scenario configuration, master and child seeds, generator version, and split
manifest. Phase 4 artifacts require no raw-file download to validate.

## 30. Errors and Decisions

D2 remains cloud cluster/workload reliability; Kubernetes-specific semantics
are avoided. UNSW remains external-only. Native attack categories are
non-causal. Unsupported mappings remain unverified. No unsupported result was
promoted to verified evidence.

## 31. Phase 5 Prerequisites

Review and freeze this contract, confirm UNSW header and terms, approve
scenario distributions, implement the generator and validator, and produce a
reproducible split manifest. Do not generate the 1.1M-row dataset or train
models until those gates are approved.

## D1-C5 Evidence and Design Coverage

| Type | Verified real evidence | Documented evidence | Synthetic-design support |
|---|---|---|---|
| D1 | NO | TravisTorrent concepts | YES |
| D2 | NO | Alibaba/Google cluster concepts | YES |
| C1 | NO | CIC-IDS2017 concepts | YES |
| C2 | NO | CIC-DDoS2019 concepts | YES |
| C3 | PARTIAL, UNSW Reconnaissance | CIC scanning concepts | YES |
| C4 | NO | CIC application-layer concepts | YES |
| C5 | PARTIAL, UNSW native categories | ADFA-LD/CIC concepts | YES |

## Final Status

**PARTIAL / design complete, evidence incomplete.** Phase 4 artifacts are
ready for review and later implementation. No synthetic dataset, model,
metric, dashboard, API, or autonomous remediation was created.