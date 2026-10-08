# Phase 2 Dataset Acquisition and Evidence Audit

## 1. Phase Objective
Finalize the Phase 1 external-validation evidence audit without bulk acquisition, model training, synthetic-data generation, or platform construction. This document separates documented relevance from locally acquired records and states what each source can and cannot validate.

## 2. Phase 1 Traceability
Phase 1 selected D1 CI/CD pipeline/build failure; D2 containerized service reliability failure; C1 brute-force/authentication; C2 DDoS/flooding; C3 port/service scanning; C4 web/application-layer attack; and C5 malicious/anomalous host/network behavior. Candidates were TravisTorrent, Alibaba ClusterData, Google Cluster Data, CIC-IDS2017, CIC-DDoS2019, UNSW-NB15, and ADFA-LD.

**D2 decision**

- **Phase 1 definition:** Containerized service reliability failure.
- **Phase 2 evidence:** Alibaba ClusterData and Google Cluster Data document cluster, workload, scheduler, machine, resource, task, and instance-event telemetry. The retained evidence does not establish Kubernetes-specific service semantics or a unified service-failure label.
- **Final definition:** **Cloud cluster/workload reliability failure.**
- **Reason:** This wording is supported by the documented telemetry and does not claim generic cluster traces are Kubernetes-specific failure datasets. Kubernetes/containerized service reliability remains a future specialization requiring suitable labels and telemetry.

## 3. Dataset Evidence Methodology
Evidence was ranked as official repository or landing page, institutional source, original paper/bibliography, official archive, then recognized academic mirror. Local files were hashed and profiled by `src/data_audit/audit_dataset.py`. A README, schema, protocol buffer, fetch script, or `ACCESS_STATUS.txt` is supporting evidence only, not raw data acquisition. DNS-unreachable sources were recorded as access limitations rather than repeatedly retried.

Status meanings: **A** fully acquired and audited; **B** partially acquired; **C** officially identified and relevance-supported but not acquired; **D** rejected. All seven datasets are C. No raw records, complete label distributions, or empirical external validation results are claimed.

## 4. Dataset Inventory

| Dataset | ID | Organization/authors | Telemetry | Intended class | Status |
|---|---|---|---|---|---|
| TravisTorrent | DSET_DEVOPS_TRAVISTORRENT | TravisTorrent project; Beller et al. | CI/build metadata | D1 | C |
| Alibaba Cluster Trace | DSET_DEVOPS_ALIBABA_CLUSTERDATA | Alibaba | Cluster/workload/resource traces | Revised D2 | C |
| Google Cluster Data | DSET_DEVOPS_GOOGLE_CLUSTER_DATA | Google researchers | Scheduler/task/machine/event traces | Revised D2 | C |
| CIC-IDS2017 | DSET_CYBER_CIC_IDS2017 | Canadian Institute for Cybersecurity | Network flows | C1, C2, C3, C4 | C |
| CIC-DDoS2019 | DSET_CYBER_CIC_DDOS2019 | Canadian Institute for Cybersecurity | DDoS network flows | C2 | C |
| UNSW-NB15 | DSET_CYBER_UNSW_NB15 | UNSW Canberra Cyber | Network flows/features | C3, C5 | C |
| ADFA-LD | DSET_CYBER_ADFA_LD | UNSW Canberra | Linux system-call sequences | C5 | C |

## 5. Dataset Acquisition Status
The local directories contain only documentation artifacts or access markers. Alibaba and Google are not acquired datasets merely because schemas/protocol definitions exist. TravisTorrent has a tools README, not generated data. The four cybersecurity directories contain access markers and no records. No large download was attempted.

## 6. Dataset Provenance
Official URLs, references, local artifact lists, hashes, and access limitations are recorded in [metadata/external_dataset_manifest.json](metadata/external_dataset_manifest.json) and [metadata/dataset_evidence.md](metadata/dataset_evidence.md). Per-dataset Markdown and JSON profiles under [reports/dataset_audit](reports/dataset_audit) provide file-level evidence. Citation or licensing fields that could not be verified remain explicitly unverified.

## 7. Dataset Schema Audit
TravisTorrent documentation supports build/project/commit-oriented records. Alibaba and Google documentation supports resource, scheduling, instance, task, event, and timestamp fields. CIC-IDS2017 and CIC-DDoS2019 are flow-feature datasets; UNSW-NB15 is a network-feature dataset; ADFA-LD is a system-call sequence dataset. Because no raw tables or sequences are local, column counts, null rates, actual units, record counts, and value ranges are **NOT VERIFIED**.

## 8. Dataset Label Audit
TravisTorrent supports build outcome labels, but outcome is not a root-cause label. Cybersecurity sources document benign/attack or attack-family labels, supporting detection and category classification but not causal inference. Cluster datasets have no unified failure label in the retained documentation; D2 labels must be engineered from events or resource-pressure proxies and remain PARTIAL. No source provides remediation action/outcome pairs.

## 9. Seven Failure Validation Matrix
YES means the published dataset design supports a stage in principle; PARTIAL means proxy labels, temporal construction, or domain-shift qualification is required; NO means the required ground truth is absent.

| Failure | Dataset evidence | Detection | Prediction | RCA | Remediation | Limitation |
|---|---|---|---|---|---|---|
| D1 CI/CD build failure | TravisTorrent | YES | PARTIAL | NO | NO | Build status is not cause or recovery action |
| D2 cloud cluster/workload reliability failure | Alibaba ClusterData; Google Cluster Data | PARTIAL | PARTIAL | PARTIAL | NO | Proxy labels; not Kubernetes-specific |
| C1 brute-force/authentication attack | CIC-IDS2017 | YES | PARTIAL | PARTIAL | NO | Attack category is not causal RCA |
| C2 DDoS/flooding | CIC-DDoS2019; CIC-IDS2017 | YES | PARTIAL | PARTIAL | NO | Lab traffic and category labels |
| C3 port/service scanning | CIC-IDS2017; UNSW-NB15 | YES | PARTIAL | PARTIAL | NO | Cross-source label harmonization required |
| C4 web/application-layer attack | CIC-IDS2017 | YES | PARTIAL | PARTIAL | NO | Web categories do not provide remediation outcomes |
| C5 malicious/anomalous host/network behavior | UNSW-NB15; ADFA-LD | YES | PARTIAL | PARTIAL | NO | Network-flow and host-call domains differ |

These are validation capabilities, not completed experiments. Status C means this phase did not execute those validations locally.

## 10. Feature Availability Audit
The existing mapping retains canonical feature, source feature, type, stage, task support, transformation, leakage risk, and notes. Stages are interpreted as **pre-event**, **during-event**, **post-event**, **label-derived**, or **leakage-prone**. Timestamps and baseline/resource/flow features can support pre-event windows only when cut off before the target event. Outcome labels, attack labels, and failure categories are target fields, not predictors. D2 mapping uses `d2_cloud_cluster_workload_reliability`, not a Kubernetes-specific name.

## 11. Cross-Dataset Feature Mapping
The authoritative mapping is [metadata/cross_dataset_feature_mapping.csv](metadata/cross_dataset_feature_mapping.csv). It preserves the existing architecture for build, resource, scheduler, flow, and system-call fields. Transformations include unit normalization, categorical harmonization, log scaling, timestamp ordering, sequence tokenization, and anonymization where needed. `supports_remediation` is NO for every listed external feature because no public remediation outcome is available.

## 12. Leakage Audit
The Phase 1 strategy remains mandatory: temporal train/validation/test splits; no future or post-event features for prediction; no label-derived fields as inputs; no remediation outcome as an input; project/build, host, source, service, and dataset-group separation where applicable; duplicate-window prevention; and sequence-overlap prevention. Build status, attack labels, event-derived failure labels, and recovery outcomes are labels or evaluation data only.

## 13. RCA Suitability
RCA terminology is limited to root-cause **classification/localization**, not proven causal inference. Level 0 means no RCA information; Level 1 means failure/attack category only; Level 2 means component/source localization; Level 3 means explicit root-cause information. TravisTorrent and cybersecurity datasets are generally Level 1. Cluster event/domain fields may offer Level 2 proxies. No dataset provides Level 3 causal ground truth.

## 14. Remediation Suitability
**External public datasets do not provide sufficient remediation ground truth for direct validation of autonomous remediation.** All seven datasets are Remediation = NO. The project should evaluate **remediation recommendation** using expert/rule-based action mapping, controlled simulation, and retrospective recovery information where available. It must not claim these public datasets validate autonomous remediation execution.

## 15. Dataset Quality Scores
Each dimension is scored 0–5: provenance, accessibility, label quality, feature richness, temporal information, failure relevance, external-validation suitability, RCA suitability, remediation suitability, and reproducibility. Scores are transparent heuristics, not empirical benchmarks. Documentation-only acquisition caps accessibility, reproducibility, and external validation; absent action outcomes make remediation 0.

| Dataset | Provenance | Access | Labels | Features | Time | Relevance | External | RCA | Remediation | Reproducibility | Total/50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TravisTorrent | 4 | 1 | 3 | 3 | 4 | 4 | 3 | 1 | 0 | 2 | 25 |
| Alibaba Cluster Trace | 4 | 2 | 1 | 4 | 4 | 3 | 2 | 2 | 0 | 3 | 25 |
| Google Cluster Data | 4 | 2 | 1 | 4 | 4 | 3 | 2 | 2 | 0 | 3 | 25 |
| CIC-IDS2017 | 4 | 1 | 4 | 4 | 4 | 4 | 3 | 1 | 0 | 2 | 27 |
| CIC-DDoS2019 | 4 | 1 | 4 | 4 | 4 | 4 | 3 | 1 | 0 | 2 | 27 |
| UNSW-NB15 | 4 | 1 | 4 | 4 | 2 | 4 | 3 | 1 | 0 | 3 | 26 |
| ADFA-LD | 4 | 1 | 3 | 3 | 2 | 3 | 3 | 1 | 0 | 3 | 23 |

## 16. Final External Validation Dataset Selection
Retain all seven as **candidate external validation sources**, with domain-specific claims. TravisTorrent is the D1 candidate. Alibaba and Google support only the revised cloud cluster/workload D2 proxy. CIC-IDS2017 is the broadest cybersecurity candidate; CIC-DDoS2019 specializes C2; UNSW-NB15 supports C3/C5; ADFA-LD supports host-level C5. Selection does not imply local acquisition or successful model validation.

## 17. Preliminary Synthetic Dataset Requirements
No synthetic data was generated. The eventual target remains Training 1,000,000, Validation 50,000, Testing 50,000. The generator must include realistic temporal dependencies, correlated telemetry, failure progression, normal baselines, class imbalance, project/service and infrastructure context, security and CI/CD telemetry, strict label isolation, and stage-specific feature availability.

## 18. Dataset Limitations
No raw records were acquired; record-level audit is unavailable. Several official hosts were DNS-unreachable. Cluster sources are not Kubernetes-specific. Public attack sources are often lab-generated and category-labeled. Cross-domain schemas and time granularity differ. RCA labels are shallow, and remediation actions/outcomes are absent.

## 19. Research Paper Implications
The paper must separate synthetic model evaluation from real-world external validation. It may claim the sources support detection-oriented external validation and limited temporal/category analyses. It must not claim all stages, RCA, or autonomous remediation are validated by real-world datasets.

## 20. Reproducibility
Reproduce the file audit with `python src/data_audit/run_phase2_audits.py`. Hashes and local artifact lists are in the manifest. The run intentionally excludes bulk downloads, model training, GPU work, and synthetic generation. Environment notes are in [metadata/environment_phase2.json](metadata/environment_phase2.json).

## 21. Existing Files and Artifacts
Relevant artifacts are [PHASE_01_RESEARCH_SCOPE_DATASET_STRATEGY.md](PHASE_01_RESEARCH_SCOPE_DATASET_STRATEGY.md), the metadata files, [src/data_audit/audit_dataset.py](src/data_audit/audit_dataset.py), [src/data_audit/run_phase2_audits.py](src/data_audit/run_phase2_audits.py), local `data/external` documentation/access markers, and the seven Markdown/JSON reports under [reports/dataset_audit](reports/dataset_audit).

## 22. Commands Executed
The existing run recorded `python src/data_audit/run_phase2_audits.py`, `python src/data_audit/audit_dataset.py --dataset-name ...`, and raw GitHub retrieval commands for small documentation artifacts. Finalization ran repository inspection, JSON/CSV validation, report checks, `git diff --stat`, and the requested file/status checks. No large download, training, synthetic generation, or Phase 3 operation was run.

## 23. Problems and Resolutions
DNS restrictions prevented access to several institutional landing pages and the TravisTorrent portal. Resolution: preserve official URLs and existing evidence, classify sources as C, and mark unverified fields explicitly. Existing D2 wording overstated Kubernetes/container semantics. Resolution: rename the final taxonomy to cloud cluster/workload reliability failure. Documentation-only artifacts were not treated as acquired data.

## 24. Phase 2 Conclusions

### What is proven
The seven candidate datasets and official source identities are documented, relevant telemetry families are identified, local artifacts are hashed, and the external-validation strategy is reproducible at the evidence level. Detection-oriented mappings are defensible in principle for D1 and C1-C5; D2 is defensible only as a cloud cluster/workload proxy.

### What is partially supported
Temporal prediction is possible in principle where timestamps and sequences exist, but requires leakage-controlled window construction. Cluster reliability and RCA localization require engineered proxy labels. Cybersecurity category labels support classification/localization proxies, not causality.

### What is not externally validated
No model was trained or evaluated in this phase. No dataset supplies sufficient evidence for direct validation of autonomous remediation, and no dataset supplies Level 3 causal RCA ground truth.

### What remains a research limitation
All raw datasets remain unavailable locally, several sources have access restrictions, domain shift is substantial, and synthetic-to-real transfer remains unmeasured. Claims must distinguish synthetic model evaluation from real-world external validation.

## 25. Phase 3 Prerequisites
Phase 3 may begin only after selecting permitted small slices or access procedures, verifying licenses and versions, acquiring raw data intentionally, profiling records, implementing leakage-safe temporal/group splits, and defining proxy labels with documented validity. It must not assume remediation ground truth or Kubernetes-specific D2 labels from these sources.

## 26. References
See [metadata/dataset_references.bib](metadata/dataset_references.bib), the official URLs in [metadata/external_dataset_manifest.json](metadata/external_dataset_manifest.json), and repository bibliographies retained under `data/external`. Exact release citations and licensing terms must be verified before redistribution or publication.
