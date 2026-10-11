# Feature Groups

This taxonomy accompanies `synthetic_schema.csv` and
`dataset_contract.yaml`. It describes intended availability, not observed
coverage in every external dataset.

## Identifier and Grouping-Control Fields

`event_id`, `incident_id`, and `window_id` are canonical schema fields. They
identify events, incident groups, and observation windows respectively. They
are available for ordering, grouping, duplicate isolation, temporal grouping,
RCA/remediation grouping, and leakage-safe split validation. They are not
default predictive telemetry features and must be excluded from ordinary model
feature matrices unless a protocol explicitly uses them as grouping metadata.

## 1. Identity and Context

Organization, project, environment, region, service, host, and workload IDs
define hierarchy and grouping. IDs are UUID-style controls, not default
predictors. Environment and region may be used for explicit context protocols.

## 2. Deployment

Deployment age, frequency, change size, configuration changes, and rollback
history describe pre-outcome change pressure. Final deployment status is an
outcome, not an upstream predictor.

## 3. CI/CD

Pipeline, job, queue, build, test, deployment, retry, step, artifact, and
dependency fields describe work observed so far. Final build/failure status is
excluded when predicting that same outcome.

## 4. Infrastructure

CPU, memory, disk, network bytes, I/O wait, load, process, thread, connection,
and descriptor telemetry are correlated resource observations with explicit
units and missingness.

## 5. Workload and Cloud Cluster

Task, cloud-job, instance, queue, resource request/use, scheduling delay,
pressure, restart, eviction, and task-state fields describe cloud
cluster/workload reliability. The contract does not assume Kubernetes semantics.

## 6. Network

Anonymized source/destination groups, ports, protocol, service, flow duration,
bytes, packets, and connection rates represent network context. Reused group
tokens are split controls.

## 7. Security

Authentication, source/destination diversity, entropy, scan burst, request,
traffic, and connection fields support controlled C1-C5 scenarios. Application
fields are added only when a future source supports their semantics.

## 8. Temporal

Every record has `event_timestamp`. Prediction examples use `window_start`,
`window_end`, and `prediction_timestamp`; `W` ends at cutoff `t` and `H` is the
future horizon.

## 9. Derived

Deltas, slopes, rolling statistics, rates, entropy, burst scores, and anomaly
scores must declare source fields, aggregation, lookback, and availability.

## 10. Labels

`incident_label` supports detection. `incident_type` uses none, D1, D2, and
C1-C5. Future incident labels and timing support prediction. Labels are
targets, not features.

## 11. RCA Outputs

Root-cause category and component are controlled synthetic classification and
localization annotations, not proven causal inference or external ground truth.

## 12. Remediation Outputs

`recommended_action` is a recommendation target. It is not evidence that an
action executed or succeeded; this phase defines no `remediation_success`.