# PHASE 1 — RESEARCH SCOPE, DATASET STRATEGY AND VALIDATION PLAN

## 1. Executive Summary
This phase defines a **scientifically defensible** methodology for an AI-powered autonomous DevOps platform that performs detection, prediction, root-cause classification, and remediation recommendation for a limited set of DevOps and cybersecurity failures.

The recommended strategy is:
- **Train/validate/test on controlled synthetic telemetry** (for reproducibility and experiment control)
- **Validate externally on independent public real-world datasets** (for generalization evidence)

This avoids the invalid claim that synthetic performance alone implies real-world performance.

---

## 2. Problem Definition
Cloud and cloud-native operations produce heterogeneous telemetry (build logs, infra metrics, network flows, app/service signals). Failures and attacks are often detected late, diagnosed manually, and remediated inconsistently.

The research problem is to design a unified, leakage-resistant multi-stage intelligence pipeline that can:
1. detect incidents,
2. predict near-term incidents,
3. classify likely root-cause category,
4. recommend safe remediation actions,
while preserving scientific rigor and external validity.

---

## 3. Research Objective
Develop and evaluate a reproducible methodology for multi-stage incident intelligence in DevOps/cloud environments using:
- controlled synthetic telemetry for development,
- independent real-world datasets for external validation,
- explicit domain-shift analysis,
- strict leakage controls.

---

## 4. Research Questions
1. Can controlled synthetic telemetry support strong in-distribution performance for detection/prediction/RCA/remediation recommendation?
2. How much performance degrades on independent real-world datasets?
3. Which feature groups transfer best from synthetic to real domains?
4. Which failure classes are externally validatable with currently available public datasets?
5. Can a unified telemetry representation support multiple tasks without leakage?

---

## 5. Comparison of the Three Dataset Strategies

### Option A — Fully synthetic only
**Pros**: high control, cheap scaling, reproducible.
**Cons**: weak external validity; high risk of overfitting to generator artifacts; low paper defensibility for real-world claims.

### Option B — Merge multiple real datasets into one “unified” dataset
**Pros**: stronger realism potential.
**Cons**: severe schema mismatch, inconsistent labels, incompatible telemetry granularity, hidden leakage across merged corpora, heavy integration cost.

### Option C — Synthetic development + independent real-world external validation
**Pros**: controlled experimentation + explicit generalization test; strongest practical defensibility under time constraints.
**Cons**: still requires careful feature/label mapping; domain gap may remain large.

### Comparative assessment
- **Research validity**: C > B > A
- **Reproducibility**: A ≈ C > B
- **Data availability practicality**: C > A > B
- **Domain-shift transparency**: C > B > A
- **Implementation complexity**: A < C < B
- **Paper defensibility**: C > B > A

---

## 6. Recommended Strategy
**RECOMMENDED APPROACH: OPTION C**

Rationale:
1. Preserves controlled experimental development.
2. Enables independent external validation.
3. Makes limitations explicit (synthetic-real gap).
4. Avoids weak claim that synthetic results prove deployment readiness.

---

## 7. Selected DevOps Failure Types
1. **D1: CI/CD pipeline/build failure** (failed build/test/deploy run)
2. **D2: Containerized service reliability failure** (crash/restart/resource-exhaustion/service degradation in orchestrated environments)

---

## 8. Selected Cybersecurity Failure Types
1. **C1: Brute-force/authentication attack**
2. **C2: DDoS / flooding attack**
3. **C3: Port/service scanning (reconnaissance)**
4. **C4: Web/application-layer attack** (e.g., SQLi/XSS/brute-force web login)
5. **C5: Malicious or anomalous host/network behavior**

---

## 9. Scientific Justification for Each Failure Type
- They are operationally important and observably distinct in telemetry.
- They support staged tasks:
  - Detection: presence/type of incident
  - Prediction: near-term risk score
  - RCA: likely cause category (not strict causal proof)
  - Remediation recommendation: candidate action ranking
- Public datasets exist for detection validation; fewer exist for remediation outcome validation (explicit limitation).

---

## 10. Real-World Dataset Candidates
### D1 — CI/CD pipeline/build failure
**Dataset:** TravisTorrent  
**Official source URL:** https://travistorrent.testroots.org/  
**Owner/repository:** TravisTorrent project (research dataset; Travis CI + GitHub mined data)  
**Publication:** Beller et al., MSR 2017 (DOI in References)  
**Dataset size:** multi-project CI history (millions of records across language subsets; exact row count depends on selected release/slice)  
**Telemetry type:** CI/build metadata + commit/PR/project attributes  
**Features:** build state, durations, commit metadata, file churn, language/project identifiers  
**Labels:** passed/failed build outcomes  
**Failure classes:** build success vs failure (can be remapped to D1)  
**Timestamps:** yes  
**Sequences:** yes (build histories per project/repo)  
**Train/test split provided:** typically no canonical split; must define chronological split  
**Licensing/access restrictions:** academic/public dataset access; verify terms on portal before redistribution  
**Academic legal use:** generally suitable for academic research  
**Validates failure type:** D1  
**Can validate stages:** detection, limited prediction, limited RCA-category proxies  
**Cannot validate:** remediation execution outcomes, full causal RCA  
**Expected preprocessing:** project-level filtering, temporal ordering, feature harmonization to synthetic schema  
**Known limitations:** CI ecosystem drift; label = build status not full root cause  
**Domain mismatch vs synthetic:** synthetic may include richer infra/security telemetry than CI-only records  

### D2 — Containerized service reliability failure
**Dataset A:** Alibaba Cluster Trace (clusterdata-2018)  
**Official source URL:** https://github.com/alibaba/clusterdata  
**Owner/repository:** Alibaba  
**Publication:** Alibaba production cluster trace release documentation (repo papers/docs)  
**Dataset size:** very large production trace corpus (machine/container/job-level tables over time; exact size depends on selected subset)  
**Telemetry type:** cluster scheduling/resource/instance telemetry  
**Features:** CPU/memory usage, scheduling events, machine and instance states  
**Labels:** no single unified “failure” label; labels must be engineered (e.g., anomalies/resource exhaustion proxies)  
**Failure classes:** supports D2 reliability degradation/anomaly proxies  
**Timestamps:** yes  
**Sequences:** yes  
**Train/test split provided:** no canonical split  
**Licensing/access restrictions:** use per repository license/terms  
**Academic legal use:** generally suitable for research (subject to terms)  
**Validates failure type:** D2  
**Can validate stages:** detection, prediction, partial RCA-category localization  
**Cannot validate:** explicit remediation ground truth; Kubernetes-specific semantics in full  
**Expected preprocessing:** table joins, timestamp alignment, label engineering, normalization  
**Known limitations:** no direct Kubernetes labels; inference required  
**Domain mismatch vs synthetic:** synthetic may encode Kubernetes-native signals not directly present  

**Dataset B:** Google Cluster Data  
**Official source URL:** https://github.com/google/cluster-data  
**Owner/repository:** Google  
**Publication:** Google cluster trace papers/docs linked from repository  
**Dataset size:** large-scale cluster traces (size depends on release version)  
**Telemetry type:** scheduler/task/machine events  
**Features:** resource allocation/usage, event logs, job/task state transitions  
**Labels:** weak/no direct failure labels; requires proxy label design  
**Failure classes:** D2 reliability/performance degradation proxies  
**Timestamps:** yes  
**Sequences:** yes  
**Train/test split provided:** no  
**Licensing/access restrictions:** see repository terms  
**Academic legal use:** generally usable for research under terms  
**Validates failure type:** D2 (external robustness check)  
**Can validate stages:** detection/prediction (with engineered labels)  
**Cannot validate:** definitive RCA or remediation outcomes  
**Expected preprocessing:** schema normalization and proxy target construction  
**Known limitations:** indirect failure labeling  
**Domain mismatch vs synthetic:** workload/scheduler semantics may differ from modern Kubernetes deployments  

### C1/C2/C3/C4 — Network and application attacks
**Dataset:** CIC-IDS2017  
**Official source URL:** https://www.unb.ca/cic/datasets/ids-2017.html  
**Owner/repository:** Canadian Institute for Cybersecurity (UNB)  
**Publication:** CICFlowMeter/CICIDS publications (linked by CIC/UNB)  
**Dataset size:** multiple days of traffic, flow-based records (commonly used extracted set ~2.8M flows; size varies by preprocessing)  
**Telemetry type:** network flow telemetry and attack scenario traces  
**Features:** CICFlowMeter statistical flow features (duration, bytes, packets, flags, rates, etc.)  
**Labels:** benign + multiple attack classes  
**Failure classes:** brute force, DDoS, PortScan, web attacks (SQLi/XSS/BruteForce web)  
**Timestamps:** yes  
**Sequences:** yes (time-ordered flows)  
**Train/test split provided:** not strict canonical split; user-defined temporal split required  
**Licensing/access restrictions:** public academic dataset; verify latest terms before redistribution  
**Academic legal use:** yes, commonly used in research  
**Validates failure types:** C1, C2, C3, C4  
**Can validate stages:** detection strongly; limited prediction via temporal windows; limited RCA-category mapping  
**Cannot validate:** remediation execution and organization-specific policy actions  
**Expected preprocessing:** cleaning, class harmonization, severe imbalance handling, feature scaling  
**Known limitations:** synthetic lab traffic; potential outdated traffic patterns  
**Domain mismatch vs synthetic:** enterprise/cloud telemetry mix may differ from CIC scenario generation  

**Dataset:** CIC-DDoS2019  
**Official source URL:** https://www.unb.ca/cic/datasets/ddos-2019.html  
**Owner/repository:** Canadian Institute for Cybersecurity (UNB)  
**Publication:** CIC DDoS 2019 dataset documentation/papers  
**Dataset size:** large multi-attack DDoS flow dataset (size depends on selected files)  
**Telemetry type:** network flow telemetry focused on DDoS scenarios  
**Features:** flow-level statistical features  
**Labels:** benign + DDoS attack-type labels  
**Failure classes:** C2 primarily  
**Timestamps:** yes  
**Sequences:** yes  
**Train/test split provided:** usually no fixed universal split  
**Licensing/access restrictions:** public academic use subject to dataset terms  
**Academic legal use:** yes (with terms compliance)  
**Validates failure type:** C2  
**Can validate stages:** detection, limited prediction  
**Cannot validate:** RCA depth beyond class labels; remediation outcomes  
**Expected preprocessing:** attack-family mapping, balancing, normalization  
**Known limitations:** attack-lab realism gap  
**Domain mismatch vs synthetic:** production cloud baseline traffic diversity may be higher  

### C3/C5 — Reconnaissance and broad anomalous behavior
**Dataset:** UNSW-NB15  
**Official source URL:** https://research.unsw.edu.au/projects/unsw-nb15-dataset  
**Owner/repository:** UNSW Canberra Cyber  
**Publication:** UNSW-NB15 papers listed by UNSW  
**Dataset size:** ~2.5M records total; standard train/test subsets released  
**Telemetry type:** network flow + engineered network features  
**Features:** 40+ flow/content/time features  
**Labels:** normal/attack + attack categories (including reconnaissance)  
**Failure classes:** C3 (recon/scan proxies), C5 (generic malicious behavior classes)  
**Timestamps:** limited/derived timing context depending on release files  
**Sequences:** weak compared to continuous traces; mostly record-wise classification format  
**Train/test split provided:** yes (official train/test files)  
**Licensing/access restrictions:** public research dataset with usage terms  
**Academic legal use:** yes  
**Validates failure types:** C3, C5  
**Can validate stages:** detection; limited prediction with constructed windows  
**Cannot validate:** strong RCA causality and remediation outcomes  
**Expected preprocessing:** category remapping, imbalance handling, potential sequence reconstruction  
**Known limitations:** synthetic testbed origin; older traffic characteristics  
**Domain mismatch vs synthetic:** may lack modern cloud-native service context  

**Dataset:** ADFA-LD (within ADFA IDS datasets)  
**Official source URL:** https://research.unsw.edu.au/projects/adfa-ids-datasets  
**Owner/repository:** UNSW Canberra  
**Publication:** ADFA-LD papers from UNSW  
**Dataset size:** host-based sequence corpus (smaller than large network-flow IDS sets)  
**Telemetry type:** Linux host/system-call behavior traces  
**Features:** syscall/event sequences (sequence modeling required)  
**Labels:** normal vs attack scenarios  
**Failure classes:** C5 (host-level anomalous/malicious behavior)  
**Timestamps:** sequence order yes; explicit wall-clock timestamps may be limited depending on release  
**Sequences:** yes (primary strength)  
**Train/test split provided:** dataset provides normal/attack partitions; custom experiment split still needed  
**Licensing/access restrictions:** research access terms apply  
**Academic legal use:** generally yes for academic work  
**Validates failure type:** C5  
**Can validate stages:** detection, sequence-based anomaly classification, partial RCA-category hints  
**Cannot validate:** DDoS/scan-specific network behavior at scale, remediation outcomes  
**Expected preprocessing:** sequence encoding, windowing, vocabulary handling  
**Known limitations:** host-centric and comparatively narrow environment diversity  
**Domain mismatch vs synthetic:** system-call domain differs from cloud network/CI telemetry

---

## 11. Official Dataset Sources
- TravisTorrent: https://travistorrent.testroots.org/
- TravisTorrent paper (MSR): https://dl.acm.org/doi/10.1145/2901739.2903508
- Alibaba cluster data repo: https://github.com/alibaba/clusterdata
- Google cluster data portal: https://github.com/google/cluster-data
- CIC-IDS2017: https://www.unb.ca/cic/datasets/ids-2017.html
- CIC-DDoS2019: https://www.unb.ca/cic/datasets/ddos-2019.html
- UNSW-NB15: https://research.unsw.edu.au/projects/unsw-nb15-dataset
- ADFA-LD / ADFA IDS datasets: https://research.unsw.edu.au/projects/adfa-ids-datasets

---

## 12. Dataset-to-Failure Mapping
| Failure Type | Real-world dataset(s) |
|---|---|
| D1 CI/CD build failure | TravisTorrent |
| D2 Containerized service reliability failure | Alibaba clusterdata-2018, Google cluster data |
| C1 Brute-force/auth attack | CIC-IDS2017 |
| C2 DDoS/flooding | CIC-DDoS2019, CIC-IDS2017 |
| C3 Port/service scanning | CIC-IDS2017, UNSW-NB15 |
| C4 Web/app attack | CIC-IDS2017 (WebAttack classes) |
| C5 Malicious/anomalous behavior | UNSW-NB15, ADFA-LD |

---

## 13. Dataset-to-Model Mapping
| Failure | Synthetic Training | Synthetic Test | Synthetic Validation | Real-world Validation | Detection | Prediction | RCA | Remediation |
|---|---|---|---|---|---|---|---|---|
| D1 | Yes | Yes | Yes | TravisTorrent | Yes | Limited (time-based build risk) | Limited (coarse cause categories) | Recommendation only |
| D2 | Yes | Yes | Yes | Alibaba + Google cluster traces | Yes | Yes | Limited (resource/scheduling/dependency classes) | Recommendation only |
| C1 | Yes | Yes | Yes | CIC-IDS2017 | Yes | Limited (window-based early warning) | Limited | Recommendation only |
| C2 | Yes | Yes | Yes | CIC-DDoS2019 + CIC-IDS2017 | Yes | Limited | Limited | Recommendation only |
| C3 | Yes | Yes | Yes | CIC-IDS2017 + UNSW-NB15 | Yes | Limited | Limited | Recommendation only |
| C4 | Yes | Yes | Yes | CIC-IDS2017 | Yes | Limited | Limited | Recommendation only |
| C5 | Yes | Yes | Yes | UNSW-NB15 + ADFA-LD | Yes | Limited | Better than others (behavior categories) | Recommendation only |

**Critical limitation:** public datasets mostly validate **detection**; robust external validation for remediation outcomes is generally unavailable.

---

## 14. Synthetic Dataset Design
Planned size:
- Train: **1,000,000**
- Validation: **50,000**
- Test: **50,000**

Design principles:
- Time-indexed telemetry events/windows.
- Multi-tenant context (org/project/service/environment).
- Mixed normal and incident trajectories.
- Failure progression states (pre-incident, onset, active, post-action).
- Cross-feature correlations (not independent random columns).

Initial class balance target (to be versioned and justified):
- Normal: 70%
- DevOps failures (D1+D2): 15%
- Cyber incidents (C1–C5): 15%

Include controlled imbalance scenarios for realistic evaluation.

---

## 15. Feature Architecture
Feature groups:
1. **Identity/context**: org_id (UUID), project_id (UUID), service_id (UUID), environment, region
2. **Deployment context**: version, release_age, rollout_type, config_change_flag
3. **Workload/infra**: cpu, memory, disk I/O, pod restarts, queue depth, latency, error rate
4. **Network/security**: flow counts, unique src IPs, failed auth rate, SYN rate, port entropy, HTTP error mix
5. **Pipeline**: stage durations, retry counts, test failure counts, dependency resolution failures
6. **Temporal/derived**: rolling means/stds, gradients, EWMA, lag features (strictly historical)
7. **Labels**:
   - stage-1: normal/devops/cyber + subclass
   - stage-2: future incident in horizon H
   - stage-3: root-cause class
   - stage-4: remediation recommendation label

---

## 16. Leakage Prevention Strategy
Strict controls:
1. **Temporal split first**, feature engineering second.
2. No features computed with future timestamps.
3. Prediction labels based on future horizon; prediction features restricted to pre-horizon window.
4. Remove post-incident and post-remediation fields from detection/prediction features.
5. No direct label proxies (e.g., “incident_status”, “remediation_success”) in upstream tasks.
6. Group-wise splits by org/project/service to prevent entity leakage.
7. De-duplicate windows and prevent overlap leakage between train/val/test.
8. Generator parameters must not deterministically encode class labels.
9. Separate feature sets per stage (detection vs prediction vs RCA vs remediation).
10. Maintain feature availability matrix: **available-before**, **available-during**, **available-after** incident.

---

## 17. Detection Methodology
- Task: classify current window into normal/devops/cyber and subclass.
- Inputs: current and historical telemetry up to event time t.
- Outputs: class probabilities + uncertainty/confidence.
- Evaluation: macro/micro F1, PR-AUC, ROC-AUC (where valid), per-class confusion matrix.

---

## 18. Prediction Methodology
- Task: predict whether incident occurs in horizon **H** (e.g., next 5–30 minutes).
- Observation window: W minutes before t.
- Target: incident occurrence in (t, t+H].
- Allowed features: only those available at time t.
- Evaluation: PR-AUC, recall at fixed precision, lead-time distribution.

---

## 19. RCA Methodology
- Frame as **root-cause classification/localization**, not proven causality.
- Candidate classes: deployment/configuration issue, resource exhaustion, dependency failure, auth attack, network anomaly, app-layer attack.
- Inputs: telemetry up to/around incident onset (time-bounded).
- Outputs: ranked cause probabilities + explanation artifacts.

---

## 20. Remediation Methodology
- First scope: **recommendation only**, not automatic execution.
- Action space: rollback, restart, scale, block source, throttle traffic, rotate credentials, config fix, quarantine.
- Evaluate recommendation quality against expert rulebook and retrospective outcomes where available.
- Autonomous execution is future work behind safety gates and approvals.

---

## 21. External Real-World Validation Methodology
1. Independent real datasets remain unseen during synthetic training.
2. Build feature mapping dictionary (synthetic -> real fields).
3. Handle missing features (imputation/ablation/adapter model).
4. Apply normalization fit on synthetic-train only; transform real without refit.
5. Map categorical vocabularies with “unknown” handling.
6. Harmonize labels to shared taxonomy.
7. Preserve timestamps and sequence order.
8. Evaluate dataset-by-dataset, then aggregate.
9. Measure domain shift (feature distribution distance + performance drop).
10. Report generalization gap per metric, not accuracy only.

---

## 22. Retraining/Iteration Methodology
Tracked per experiment:
- experiment_id
- synthetic_generator_version
- synthetic_dataset_version
- feature_schema_version
- model_version + hyperparameters
- split policy version
- metrics (synthetic val/test + real validation)
- failure analysis notes
- reason for modification

Loop:
1. Train on synthetic
2. Validate/test on synthetic
3. External real validation
4. Error analysis (class-wise + domain shift)
5. Document justified change
6. Retrain and re-evaluate

No undocumented “metric chasing.”

---

## 23. Evaluation Metrics
Mandatory:
- Precision, Recall, F1 (macro + weighted)
- PR-AUC (especially imbalanced classes)
- ROC-AUC (binary/OVR where applicable)
- confusion matrix
- false-positive rate / false-negative rate
- calibration (optional but recommended)
- lead time metrics for prediction

Generalization:
- Synthetic test score = X
- Real-world validation score = Y
- Generalization gap = X − Y

---

## 24. Research Hypotheses
- **H1**: Controlled synthetic telemetry can produce high in-distribution performance (target benchmark on held-out synthetic test).
- **H2**: Models retain non-trivial performance on independent real-world datasets despite measurable domain shift.
- **H3**: Temporal + infrastructure-aware features outperform non-temporal baselines for prediction and detection.
- **H4**: Stage-specific leakage controls improve external generalization versus naïve unified feature use.
- **H5**: Unified telemetry schema supports multiple downstream tasks without requiring label-derived proxy features.

---

## 25. Expected Research Contributions
1. Leakage-resistant synthetic telemetry generation protocol for cloud/DevOps/security incidents.
2. Multi-stage intelligence framework (detection, prediction, RCA classification, remediation recommendation).
3. External validation protocol across heterogeneous real-world datasets.
4. Quantified domain-shift and generalization-gap analysis.
5. Safety-first remediation architecture separating recommendation from autonomous actuation.

---

## 26. Platform Architecture
Planned (not implemented in this phase):
- Frontend: Streamlit
- Backend API: FastAPI
- Data/Auth: Supabase (PostgreSQL + Supabase Auth)
- Auth provider: Google OAuth via Supabase
- Development environment: GitHub Codespaces

High-level pipeline:
1. telemetry ingestion adapters (future)
2. feature/sequence builder
3. multi-stage model services
4. incident + recommendation store
5. analyst UI and approval workflow

---

## 27. Multi-Tenant Organization/Project Architecture
Entity hierarchy:
- user
- organization (UUID)
- organization_membership(role)
- project (UUID, scoped within organization)
- telemetry_source
- telemetry_event
- model_prediction
- incident
- remediation_recommendation
- remediation_execution_log

Project names are unique only within organization scope; IDs are UUID-based.

---

## 28. Security Architecture Requirements
- Tenant isolation via org_id/project_id boundaries
- Row-level security policies (Supabase/PostgreSQL)
- OAuth-based identity + short-lived API tokens
- Role-based authorization (owner/admin/member/viewer)
- Secrets in managed secret store (not code)
- Audit logs for prediction/remediation actions
- Approval gates for high-risk remediations
- Immutable incident timeline records

---

## 29. Research Limitations
1. Most public datasets are IDS/network-centric; limited direct remediation ground truth.
2. DevOps datasets (especially Kubernetes-specific failures) are less standardized.
3. External datasets differ in schema and environment; strong domain shift expected.
4. RCA labels are often coarse; causal claims must be avoided.
5. Autonomous remediation cannot be fully validated from offline public datasets alone.

---

## 30. Reproducibility Strategy
- Version all datasets and generators.
- Fix random seeds and log software/hardware environment.
- Store preprocessing configs and label mappings.
- Preserve train/val/test and external validation manifests.
- Use experiment tracking with immutable IDs.
- Document exact commands and runtime location (Codespaces terminal, venv, dashboard, browser).

---

## 31. Documentation Strategy
Every phase must produce a Markdown record with:
- objective, questions, methodology
- alternatives + decisions
- dataset evidence and source URLs
- environment + commands (with where-to-run)
- results + metrics
- failures/errors + fixes
- limitations + reproducibility notes
- paper relevance + next-phase prerequisites
- preserved AI assistant outputs where relevant

---

## 32. Complete Phase-1 Decision Table
| Decision Area | Decision | Justification | Limitation |
|---|---|---|---|
| Dataset strategy | Option C | Best validity/practicality balance | Domain gap remains |
| Failure scope | 7 selected classes | Distinct and telemetry-observable | Some class overlap in real traffic |
| Real-world validation | Per-dataset independent validation | Avoids synthetic-only claims | Mapping overhead |
| Prediction design | Window W + horizon H | Temporal rigor | Requires timestamp fidelity |
| RCA framing | Classification/localization | Avoids false causality claim | Coarse labels |
| Remediation scope | Recommendation-first | Safety + evaluability | Limited execution proof |
| Metrics | Multi-metric (not accuracy-only) | Better for imbalance | More complex interpretation |
| Iteration loop | Versioned, justified retraining | Scientific traceability | Slower iteration |

---

## 33. Phase-2 Prerequisites
Before Phase 2 begins, the following must be approved/completed:
1. Final approval of Option C strategy.
2. Final approval of 7 failure taxonomy and label definitions.
3. Real-world dataset acquisition/access verification and licensing check.
4. Feature availability matrix (before/during/after incident) finalized.
5. Leakage-control protocol finalized (split rules + overlap policy).
6. Synthetic telemetry schema v1 approved.
7. Experiment tracking template approved (IDs, versions, metrics, rationale fields).
8. External validation mapping templates approved per dataset.
9. Evaluation metric protocol approved (per-class + imbalance metrics).
10. Documentation template for Phase 2 approved.

---

## 34. References
1. TravisTorrent dataset portal: https://travistorrent.testroots.org/
2. Beller et al., “TravisTorrent: Synthesizing Travis CI and GitHub for Full-Stack Research on Continuous Integration”, MSR 2017, DOI: https://doi.org/10.1109/MSR.2017.24
3. Alibaba Cluster Data repository: https://github.com/alibaba/clusterdata
4. Google Cluster Data repository: https://github.com/google/cluster-data
5. CIC-IDS2017 dataset: https://www.unb.ca/cic/datasets/ids-2017.html
6. CIC-DDoS2019 dataset: https://www.unb.ca/cic/datasets/ddos-2019.html
7. UNSW-NB15 dataset: https://research.unsw.edu.au/projects/unsw-nb15-dataset
8. ADFA IDS datasets (including ADFA-LD): https://research.unsw.edu.au/projects/adfa-ids-datasets

---

## Final Required Decision
**RECOMMENDED APPROACH: OPTION C**

### Exact 7 selected failure types
1. D1 CI/CD pipeline/build failure
2. D2 Containerized service reliability failure
3. C1 Brute-force/authentication attack
4. C2 DDoS/flooding attack
5. C3 Port/service scanning
6. C4 Web/application-layer attack
7. C5 Malicious/anomalous host/network behavior

### Real-world dataset(s) used to validate each failure type
- **D1** → TravisTorrent (https://travistorrent.testroots.org/)
- **D2** → Alibaba clusterdata-2018 (https://github.com/alibaba/clusterdata), Google cluster data (https://github.com/google/cluster-data)
- **C1** → CIC-IDS2017 (https://www.unb.ca/cic/datasets/ids-2017.html)
- **C2** → CIC-DDoS2019 (https://www.unb.ca/cic/datasets/ddos-2019.html), CIC-IDS2017
- **C3** → CIC-IDS2017, UNSW-NB15 (https://research.unsw.edu.au/projects/unsw-nb15-dataset)
- **C4** → CIC-IDS2017 (WebAttack classes)
- **C5** → UNSW-NB15, ADFA-LD (https://research.unsw.edu.au/projects/adfa-ids-datasets)

### PHASE 2 INPUT REQUIREMENTS
Exactly these inputs are required:
1. Signed-off failure taxonomy (7 classes + RCA categories)
2. Signed-off synthetic schema (features, labels, temporal windows)
3. Signed-off leakage checklist and split protocol
4. Dataset access + legal-use confirmation for all external datasets
5. Feature/label mapping sheets from synthetic schema to each external dataset
6. Experiment registry format (experiment_id, versions, metrics, rationale)
7. Metric protocol (class-wise and imbalance-aware)
8. Phase-2 execution plan with explicit “where to run” for each command

**Do not proceed to Phase 2 implementation until all eight inputs are approved.**
