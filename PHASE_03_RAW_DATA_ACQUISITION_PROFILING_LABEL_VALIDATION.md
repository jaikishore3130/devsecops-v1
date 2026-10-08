# Phase 3 Raw Dataset Acquisition, Profiling, Label Validation and Split Design

## 1. Objective
Move the seven Phase 2 candidates from documented relevance toward record-level verification by probing official sources, checking acquisition feasibility, acquiring only bounded and responsibly downloadable records, and profiling any acquired data. No raw dataset payload was acquired in this run because no source met the bounded-size and access criteria.

## 2. Phase 2 Inputs
Phase 3 used [PHASE_02_DATASET_ACQUISITION_AUDIT.md](PHASE_02_DATASET_ACQUISITION_AUDIT.md), [metadata/external_dataset_manifest.json](metadata/external_dataset_manifest.json), [metadata/dataset_references.bib](metadata/dataset_references.bib), [metadata/cross_dataset_feature_mapping.csv](metadata/cross_dataset_feature_mapping.csv), [metadata/environment_phase2.json](metadata/environment_phase2.json), the Phase 2 file audits, and the existing `src/data_audit` tooling. D2 remains **cloud cluster/workload reliability failure**, not generic Kubernetes/containerized service failure.

## 3. Acquisition Methodology
For each candidate, the official landing page or repository was probed without downloading the dataset payload. The checks covered reachability, redirect behavior, advertised size, access host, and whether a bounded file and research-use terms were visible. A source was not downloaded when it was unbounded, very large, authentication-dependent, unresolved, or had unverified licensing. No mirror was substituted silently.

## 4. Dataset-by-Dataset Acquisition Status

| Dataset | Phase 3 status | Raw records acquired | Reason |
|---|---|---:|---|
| TravisTorrent | ACCESS_BLOCKED | 0 | Portal redirected to unrelated unresolved host |
| Alibaba ClusterData | TOO_LARGE_FOR_CURRENT_ENVIRONMENT | 0 | No bounded raw trace subset identified |
| Google Cluster Data | TOO_LARGE_FOR_CURRENT_ENVIRONMENT | 0 | No bounded raw trace shard identified |
| CIC-IDS2017 | TOO_LARGE_FOR_CURRENT_ENVIRONMENT | 0 | External download host and size/terms not bounded |
| CIC-DDoS2019 | TOO_LARGE_FOR_CURRENT_ENVIRONMENT | 0 | External download host and size/terms not bounded |
| UNSW-NB15 | TOO_LARGE_FOR_CURRENT_ENVIRONMENT | 0 | Official page states 100 GB raw packets and 2,540,044 CSV records |
| ADFA-LD | ACCESS_BLOCKED | 0 | Official Cloudstor download host did not resolve |

No dataset is marked ACQUIRED or PARTIALLY_ACQUIRED. This is a Phase 3 access result, not a rejection of the research candidates.

## 5. Actual Files Acquired
No new raw data files were acquired. Existing documentation, schemas, notebooks, bibliography, and access-status files remain supporting artifacts only. Seven new `ACCESS_STATUS.md` files record the outcomes. No compressed archive, packet capture, CSV corpus, trace shard, or system-call sequence was added.

## 6. Dataset Versions
No raw release was selected or downloaded. Alibaba remains represented locally by the Phase 2 2018 documentation snapshot; Google by trace-format v3 documentation; all other release versions remain NOT_VERIFIED. Version selection is a prerequisite for Phase 4 rather than an assumption in this phase.

## 7. Licensing/Access Information
All seven datasets remain `LICENSE_NOT_VERIFIED` for this repository. The official CIC and UNSW pages were reachable, but reachable does not establish redistribution permission. The TravisTorrent portal redirect and ADFA Cloudstor failure prevented access verification. Raw files must not be committed until license, terms, citation requirements, and redistribution restrictions are verified.

## 8. Actual Schemas
There are no acquired raw schemas in Phase 3. The existing Alibaba schema text and Google protocol buffer are documented schemas, not record-level schemas. The mapping in [metadata/cross_dataset_feature_mapping.csv](metadata/cross_dataset_feature_mapping.csv) is therefore marked `confidence=DOCUMENTED_ONLY` and `missingness=NOT_VERIFIED` for every concept. No column type, null rate, range, or field distribution is claimed as observed.

## 9. Record Counts

| Dataset | Locally profiled records | Officially documented count | Interpretation |
|---|---:|---:|---|
| TravisTorrent | 0 | NOT_VERIFIED | Tool README only |
| Alibaba ClusterData | 0 | NOT_VERIFIED | Documentation/schema only |
| Google Cluster Data | 0 | NOT_VERIFIED | Documentation/proto only |
| CIC-IDS2017 | 0 | NOT_VERIFIED | No flow files |
| CIC-DDoS2019 | 0 | NOT_VERIFIED | No flow files |
| UNSW-NB15 | 0 | 2,540,044 CSV records documented by official page | Documentation claim, not locally verified |
| ADFA-LD | 0 | NOT_VERIFIED | No sequence files |

The profiler was validated on the existing 31-row feature-mapping CSV, not presented as a dataset acquisition.

## 10. Label Distributions
No label distribution was computed from acquired data. Documented labels remain provisional: TravisTorrent build outcome; CIC attack categories; UNSW-NB15 normal/attack and attack categories; ADFA-LD normal/attack scenarios; and cluster lifecycle/resource events requiring proxy construction. No label is treated as causal root cause. No remediation label exists in the acquired artifacts because there are no acquired records.

## 11. Timestamp Analysis
No timestamp range, granularity, gaps, burst structure, or incident-window statistics were computed from raw records. Documentation indicates timestamped or ordered telemetry for TravisTorrent, both cluster datasets, CIC flow datasets, and sequence order for ADFA-LD. UNSW-NB15 timing details depend on the selected release files and remain NOT_VERIFIED. Temporal analysis must wait for a bounded raw release.

## 12. Group/Identity Analysis
No record-level identifiers were observed in Phase 3. Expected documented grouping concepts include project/repository/build for TravisTorrent; machine/job/task/instance for cluster traces; source/destination/flow for network datasets; and session/trace for ADFA-LD. These are design candidates, not verified columns. They must be measured from actual files before splitting.

## 13. Duplicate Analysis
No dataset duplicate rate was computed because no raw records were acquired. The profiler reports exact duplicates, duplicate percentage, group identifiers, and a declared sequence-overlap risk for later CSV/TSV/JSONL inputs. Near-duplicate detection and cross-file sequence overlap remain dataset-specific follow-up work. The 31-row mapping validation file had zero exact duplicates; that result is not a dataset statistic.

## 14. Leakage Analysis
The Phase 2 leakage rules remain in force. Labels, build status, attack category, failure/event category, recovery time, remediation action, restart result, and final outcome are label-derived or post-event unless proven available before the prediction timestamp. Timestamp fields are conditionally safe. Project, build, host, source, destination, service, machine, task, session, and sequence identifiers require group-aware splitting. No raw feature was reclassified from actual records in this phase.

## 15. Detection Suitability
No empirical detection suitability was tested. Documented design supports detection in principle for TravisTorrent and C1-C5 cybersecurity candidates. D2 remains PARTIAL because cluster failure targets require explicit event/resource proxy definitions. These are documented capabilities, not model results.

## 16. Prediction Suitability
No prediction suitability was tested. Prediction requires timestamped observation windows and future-horizon targets. TravisTorrent and flow/cluster sources may support temporal construction if records expose adequate ordering and pre-event features; UNSW-NB15 and ADFA-LD require release-specific verification. Random record shuffling is not permitted before temporal/group analysis.

## 17. RCA Suitability
No causal RCA evidence was acquired. Build outcomes and attack categories are Level 1 category evidence at most. Cluster component or source fields may support Level 2 localization proxies after record inspection. No source currently provides Level 3 explicit causal ground truth. Research terminology remains root-cause classification/localization, not causal inference.

## 18. Remediation Suitability
No remediation action/outcome records were acquired or identified. All seven remain Remediation = NO for direct autonomous-remediation validation. Later evaluation must use recommendation mapping, expert rules, controlled simulation, or retrospective recovery information, not claim public-dataset execution validation.

## 19. D2 Cloud Cluster/Workload Reliability Label Design
The final D2 definition remains **cloud cluster/workload reliability failure**. A future proxy label must be based only on explicitly observed lifecycle or resource-pressure evidence, for example a documented failure, eviction, lost instance, task termination, or sustained resource violation with a defined threshold and time window. Normal behavior must be defined from the same release and population. Any such target is an **engineered proxy**, not a native causal failure label. Kubernetes semantics must not be inferred unless the acquired source explicitly contains them.

## 20. Cross-Dataset Mapping
The existing mapping was retained and extended with `missingness` and `confidence`. Because no raw schemas were acquired, every row is `NOT_VERIFIED` and `DOCUMENTED_ONLY`. Canonical concepts are hypotheses from Phase 2 documentation, not confirmed common fields. Phase 4 must replace these values with actual field names, observed missingness, units, and confidence after bounded data acquisition.

## 21. Leakage-Safe Split Strategy
For detection, use chronological splits where timestamps exist and group separation by project, repository, host, source, session, or trace. For prediction, define observation window W ending at prediction time t and target occurrence in `(t, t+H]`; use only features available at t. Keep projects/hosts/sessions and overlapping windows out of multiple partitions. Keep external validation untouched during development. If a source lacks reliable time or grouping, mark prediction or external validation NOT_VERIFIED rather than random-splitting records.

Recommended later partition contract:

| Partition | Purpose | Constraint |
|---|---|---|
| Development train | Fit synthetic/development models | No external raw records |
| Development validation | Tune thresholds and preprocessing | Chronological/group separated |
| Held-out test | One-time internal evaluation | Frozen before reporting |
| External validation | Domain-shift assessment | Untouched until final evaluation |

## 22. Dataset Limitations
The main limitation is zero raw records acquired. Additional limitations are unverified license terms, large or unbounded archives, unresolved download hosts, unknown exact release versions, and absent record-level schema/label/timestamp/group statistics. The official UNSW page provides useful documented scale but not local verification.

## 23. Rejected/Unavailable Datasets
No candidate was scientifically rejected. TravisTorrent and ADFA-LD are ACCESS_BLOCKED for this environment. Alibaba, Google, CIC-IDS2017, CIC-DDoS2019, and UNSW-NB15 are unavailable for this run because raw acquisition was not bounded or feasible under the stated policy. Future work may acquire a verified small slice or use another officially recognized access route.

## 24. Reproducibility Commands

```bash
python -m py_compile src/data_audit/profile_dataset.py
python src/data_audit/profile_dataset.py \
  --dataset-dir <approved-raw-dataset-directory> \
  --output-json reports/dataset_audit/<dataset>_PHASE3_PROFILE.json
python src/data_audit/run_phase2_audits.py
python -m json.tool metadata/dataset_acquisition_manifest.json >/dev/null
```

The profiler streams CSV/TSV/JSONL rows, hashes files in chunks, computes bounded schema statistics, label distributions, timestamp candidates, group candidates, exact duplicates, and leakage classifications. It does not compute near-duplicate similarity or sequence overlap without dataset-specific keys.

## 25. Errors Encountered and Fixes
The TravisTorrent portal redirected to `bantenlogin.id`, whose host did not resolve; the redirect was rejected as untrusted. ADFA Cloudstor did not resolve; no mirror was substituted. CIC pages were reachable but pointed to external hosts without bounded download metadata. UNSW was reachable and explicitly reported 100 GB raw packets, so full acquisition was deferred. A GitHub API inspection command initially had quoting errors; it was corrected and rerun successfully. No retry loop or large transfer was performed.

## 26. Research-Paper Implications
Phase 3 improves source-access knowledge and provides reproducible profiling tooling, but it does not create external validation evidence. The paper must report zero locally acquired records, distinguish official documentation from observed records, and avoid claiming verified label distributions, temporal performance, RCA, or remediation results. The 2,540,044 UNSW figure is a documented source claim, not a local record count.

## 27. Phase 4 Prerequisites
Before Phase 4, obtain license and version confirmation, select bounded official slices, acquire them into ignored raw directories, hash and inventory every file, run the profiler, inspect actual labels/timestamps/groups, audit exact and near duplicates, define D2 proxy labels with thresholds and sensitivity checks, freeze leakage-safe splits, and retain external data untouched during development. Phase 4 must not begin model training until those evidence gaps are closed.

## Required Dataset Decision Matrix

| Dataset | Acquired | Records verified | Labels verified | Timestamp verified | Detection | Prediction | RCA | Remediation | Leakage risk | External-validation use |
|---|---|---|---|---|---|---|---|---|---|---|
| TravisTorrent | NO | NO | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | NO | NO | HIGH | NOT_VERIFIED |
| Alibaba ClusterData | NO | NO | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | PARTIAL | NO | HIGH | NOT_VERIFIED |
| Google Cluster Data | NO | NO | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | PARTIAL | NO | HIGH | NOT_VERIFIED |
| CIC-IDS2017 | NO | NO | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | PARTIAL | NO | HIGH | NOT_VERIFIED |
| CIC-DDoS2019 | NO | NO | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | PARTIAL | NO | HIGH | NOT_VERIFIED |
| UNSW-NB15 | NO | NO | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | PARTIAL | NO | HIGH | NOT_VERIFIED |
| ADFA-LD | NO | NO | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | NOT_VERIFIED | NO | HIGH | NOT_VERIFIED |

## Evidence Separation

### VERIFIED FACTS
Official endpoint probe outcomes, redirect/DNS failures, available disk capacity, the official UNSW page's stated 100 GB and 2,540,044-record figures, local file absence, profiler behavior, and zero raw records acquired.

### DOCUMENTED FACTS
Dataset purpose, expected telemetry families, published attack categories, and documented schema concepts from official pages, repositories, and retained Phase 2 evidence.

### ENGINEERED PROXIES
None were applied to records in Phase 3. The proposed D2 lifecycle/resource-pressure target is a future design proxy only.

### ASSUMPTIONS
That documented fields will be present in a selected release, that temporal windows can be constructed, and that group identifiers will support separation. These assumptions require record-level verification.

### UNKNOWN
Raw schemas, actual label distributions, timestamps and gaps, sequence counts, duplicate rates, near-duplicate rates, group cardinalities, license permissions for redistribution, and empirical external-validation performance.

## Phase 3 Conclusion
Phase 3 is **PARTIALLY COMPLETE**: acquisition was attempted systematically, all seven outcomes are documented, and reusable profiling tooling is available, but no raw dataset met the responsible bounded-acquisition criteria. No model training, synthetic generation, or platform implementation occurred.
