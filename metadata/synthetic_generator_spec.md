# Synthetic Generator Specification

## Scope

This is a design specification only. Phase 4 creates no synthetic rows and
does not train or evaluate models. A later generator must be deterministic
under a recorded master seed and emit provenance for every scenario.

## Components

The planned package under `src/data_generation/` contains:

- `entity_generator`: creates the organization, project, environment, service,
  deployment, host, workload, pipeline, job, window, incident, and event
  hierarchy with unique UUID-style identifiers.
- `baseline_generator`: samples correlated normal behavior, workload cycles,
  diurnal effects, benign bursts, deployments, retries, and sensor noise.
- `telemetry_generator`: emits timestamped raw telemetry with explicit missing
  values; resource, workload, network, and security signals share latent
  workload and service factors.
- `failure_generator`: creates D1 CI/CD and D2 cloud cluster/workload failure
  scenarios with gradual, sudden, intermittent, and noisy paths.
- `attack_generator`: creates C1 authentication, C2 flooding, C3 scanning,
  C4 application-layer, and C5 malicious/anomalous network scenarios.
- `incident_generator`: creates variable incident boundaries and progression;
  it does not force every scenario through one fixed sequence.
- `temporal_window_generator`: constructs a lookback `W` ending at cutoff `t`
  and a target horizon `H`, excluding observations after `t` from X.
- `label_generator`: emits detection, prediction, RCA, and recommendation
  targets separately; RCA is annotation, not causal proof.
- `leakage_validator`: checks availability, label exclusion, feature lineage,
  duplicate containment, and split/group isolation.

## Correlation and Progression

Latent scenario intensity changes telemetry probabilistically. Resource pressure
can raise load, queue, latency proxies, and failure risk; deployment changes can
raise error and restart risk; flooding can raise request, source, packet, and
traffic rates; scanning can raise destination/port diversity and short-flow
frequency. No threshold maps directly to a label.

Scenarios may use `NORMAL`, `EARLY_SIGNAL`, `DEGRADATION`, `INCIDENT`, and
`RECOVERY`, but can skip or repeat states, start abruptly, or recover slowly.

## Normal Behavior and Missingness

Normal data includes diurnal workload changes, deployment without failure,
benign traffic bursts, retries without failure, resource spikes without
incidents, measurement noise, and missing telemetry. Missingness includes
random, sensor-specific, outage, delayed, and unavailable-environment cases.
Missingness must not deterministically identify a label.

## Distribution and Evidence Boundaries

UNSW's 79.798838/20.201162 normal/attack balance and 30.298107 percent exact
duplicate rate are observed properties of one slice, not universal synthetic
targets. D1-D2 and C1-C5 mixtures are research-design choices until bounded
external evidence exists. Seed, mixture, and scenario configuration must be
recorded rather than presented as measured facts.

## Duplicate, Entity, and Reproducibility Policy

Repeated observations may be generated only under an explicit window policy;
duplicate-contamination scenarios are separately tagged. Exact and near
duplicates, incident windows, and identity/session groups cannot cross splits.
Scenario assignment is independent of stable entity IDs. Use a master seed and
named child streams for entities, baselines, telemetry, scenarios, missingness,
and splits. Persist generator and contract versions.

## Planned Output and Stop Conditions

Later phases may target 1,000,000 train rows, 50,000 validation rows, and
50,000 test rows only after approval. Stop on invalid ranges, time-order
violations, cross-split duplicates, future-value use, or unsupported mappings.