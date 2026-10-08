# Phase 3B Real Data Evidence Closure

## 1. Objective
Attempt bounded, research-permitted real-data acquisition to close Phase 3 record-level evidence gaps without downloading full corpora, fabricating records, training models, generating synthetic data, or implementing the platform.

## 2. Phase 3 Starting State
Phase 3 ended PARTIALLY COMPLETE with zero raw records. Its profiler and access manifests existed, but actual schemas, labels, timestamps, groups, duplicate rates, and temporal structure remained unknown. Phase 3B began at commit `ce119ba` with a clean working tree. D2 remains **cloud cluster/workload reliability failure**.

## 3. Acquisition Strategy
Priority was given to CIC-IDS2017, CIC-DDoS2019, and UNSW-NB15, followed by cluster traces, ADFA-LD, and TravisTorrent. Official sources were probed for reachability, redirects, file sizes, license metadata, and download mechanisms. A recognized Zenodo record was used only after its dataset identity, DOI, file size, checksum, and CC-BY-4.0 declaration were visible. The smallest useful bounded file was selected: one UNSW-NB15 CSV partition, not the full corpus or packet capture.

## 4. Dataset Acquisition Results

| Dataset | Status | Raw slice | Records profiled | Evidence result |
|---|---|---|---:|---|
| TravisTorrent | ACCESS_BLOCKED | None | 0 | Official portal redirected to unrelated unresolved host |
| Alibaba ClusterData | TOO_LARGE_FOR_CURRENT_ENVIRONMENT | None | 0 | No bounded official raw shard identified |
| Google Cluster Data | TOO_LARGE_FOR_CURRENT_ENVIRONMENT | None | 0 | No bounded official raw shard identified |
| CIC-IDS2017 | TOO_LARGE_FOR_CURRENT_ENVIRONMENT | None | 0 | External host and bounded size/terms unavailable |
| CIC-DDoS2019 | TOO_LARGE_FOR_CURRENT_ENVIRONMENT | None | 0 | External host and bounded size/terms unavailable |
| UNSW-NB15 | PARTIALLY_ACQUIRED | `UNSW-NB15_4.csv` | 440,044 | Native labels, documented 49-field layout, times, identities, and duplicates profiled |
| ADFA-LD | ACCESS_BLOCKED | None | 0 | Official Cloudstor host unresolved |

## 5. License and Version Verification
The acquired slice is from Zenodo record `10.5281/zenodo.10140548`, DOI `10.5281/zenodo.10140548`, titled UNSW-NB15, with source-declared CC-BY-4.0 metadata. This is recorded as `DECLARED_CC-BY-4.0`; publication and redistribution terms still require verification before release. The file is partition 4, `UNSW-NB15_4.csv`. Other datasets remain `LICENSE_NOT_VERIFIED` and version-unverified.

## 6. Raw Files Acquired

| File | Size | MD5 | SHA-256 | Git policy |
|---|---:|---|---|---|
| `data/external/cybersecurity/unsw_nb15/raw/UNSW-NB15_4.csv` | 97,588,754 bytes | `f55875cab7f037fdad40b5b737e7db5e` | `cdf563692d51d405541dd659ddcdad9fa01f001f05fe9fc4b67f00ca12fbc96a` | Ignored, not committed |

The raw file is outside Git tracking. The small documented column manifest and profiling outputs are committed.

## 7. Record-Level Statistics

- Records: 440,044
- Fields: 49
- Usable/invalid row split: not separately identified; all CSV rows parsed into 49 fields
- Binary `label`: 351,150 normal (79.798838%), 88,894 attack (20.201162%)
- `attack_cat` missing: 351,150 rows (79.798838%), corresponding to normal rows in this partition
- Exact duplicates: 133,325 (30.298107%)
- Near duplicates: NOT_COMPUTED

## 8. Actual Schemas
The acquired CSV has no embedded header and each row has 49 fields. The field order is recorded in `UNSW_NB15_4_COLUMNS.txt` as a documented schema mapping: source/destination IP and ports, protocol/state, duration and byte/packet features, timing/flow features, connection-count features, `attack_cat`, and `label`. The profiler observed 49 positions, numeric/categorical values, and missingness. Column names are documented interpretations, not header bytes observed in the raw file.

## 9. Label Verification
`label` and `attack_cat` are directly present at the end of each 49-field row under the documented layout. Observed `label` values are `0` and `1`. Observed non-empty attack categories are Exploits 11,439; Fuzzers 5,390; Backdoor 666; DoS 4,907; Generic 61,878; Reconnaissance 3,530; Shellcode 371; Analysis 670; Worms 43. These are **NATIVE_LABEL** and **NATIVE_CATEGORY** values, not causal labels. No engineered or proxy label was applied to the acquired rows.

Detection: PARTIAL. Prediction: PARTIAL. RCA classification: PARTIAL at category level, not causal. Component localization: NO. Remediation evaluation: NO.

## 10. Timestamp Verification
The documented `Stime` and `Ltime` positions were numeric in every profiled row. `Stime` ranged from epoch-like 1,424,249,984 to 1,424,262,068; `Ltime` ranged from 1,424,250,009 to 1,424,262,069. The observed `Stime` span is 12,084 seconds, with 11,773 unique seconds, a 1-second median gap, and a 296-second maximum gap. Timezone is NOT_VERIFIED. The fields verify ordering potential, not incident boundaries or causal timing.

## 11. Group/Identity Verification
Observed cardinalities were 38 source IPs, 43 destination IPs, and 13 services. Repeated `(srcip, dstip, Stime, Ltime)` keys occurred 43,782 times and covered 247,762 rows. No explicit session or flow identifier was verified. IPs and time keys must therefore be treated as group/leakage controls, not ordinary independent-row features.

## 12. Duplicate Analysis
The profiler found 133,325 exact duplicate rows, 30.298107% of the partition. Duplicates were not removed. They may represent repeated observations or source duplication; the evidence slice does not establish which. Near-duplicate similarity and sequence overlap were not computed. Repeated identities and exact rows make random row splits scientifically unsafe.

## 13. Leakage Analysis
`label` and `attack_cat` are LABEL-DERIVED and targets only. `Stime`/`Ltime` are conditionally safe and require a cutoff at prediction time. Source/destination IPs and service values have group-reuse risk. Exact duplicates and repeated identity-time keys create cross-split overlap risk. No remediation, recovery, or post-incident action fields were observed. Final splits must be group-aware and temporal.

## 14. D1 CI/CD Evidence
No TravisTorrent records were acquired. Detection and prediction remain documented possibilities only. Build failure is not a causal root-cause label; RCA and remediation remain NO. The official portal redirect was not trusted.

## 15. D2 Cloud Cluster/Workload Evidence
No Alibaba or Google raw records were acquired. D2 remains cloud cluster/workload reliability failure. No engineered D2 proxy was created. A future proxy requires observed lifecycle/resource events and must be tested for class balance, temporal concentration, false-positive risk, and interpretability.

## 16. C1 Authentication/Brute-Force Evidence
No CIC-IDS2017 records were acquired. C1 is NOT_VERIFIED in Phase 3B and remains documentation-supported only.

## 17. C2 DDoS Evidence
No CIC-DDoS2019 or CIC-IDS2017 records were acquired. C2 is NOT_VERIFIED in Phase 3B. No DDoS class balance or temporal continuity claim is made.

## 18. C3 Scanning Evidence
The UNSW slice contains 3,530 `Reconnaissance` category rows. This is PARTIAL evidence for C3: reconnaissance is broader than verified port/service scanning, and the category is not a causal explanation. CIC-IDS2017 scanning evidence remains NOT_VERIFIED in the selected slice because no CIC records were acquired.

## 19. C4 Web/Application Attack Evidence
No CIC-IDS2017 records were acquired. C4 is NOT_VERIFIED in Phase 3B. The UNSW slice is not used to infer application-layer attack semantics.

## 20. C5 Malicious/Anomalous Behavior Evidence
The UNSW slice contains native attack labels and multiple attack categories, including Generic, Exploits, Fuzzers, and Reconnaissance. This is PARTIAL evidence for malicious/anomalous network behavior detection. It is not causal RCA, host-process evidence, or remediation evidence. ADFA-LD remains blocked.

## 21. D2 Proxy Label Analysis
No actual Alibaba/Google records were available, so no D2 proxy experiment was possible. Proposed future candidates remain: explicit lifecycle failure events; resource-pressure thresholds; and failure plus temporal persistence. None is a current label or result. No Kubernetes-specific interpretation is permitted.

## 22. Cross-Dataset Feature Mapping
`metadata/cross_dataset_feature_mapping.csv` now includes missingness and confidence fields. UNSW concepts supported by the acquired slice are marked as documented-only until the header mapping and semantics are independently confirmed. No unsupported CIC, cluster, ADFA, or TravisTorrent equivalence was forced. The acquired evidence supports source/destination, protocol, service/state, time, category, and binary-label concepts only.

## 23. Leakage-Safe Split Design
The UNSW evidence slice must not be used as development training data. For future detection evaluation, use chronological and group-aware partitions, hold exact duplicates together, and prevent repeated source/destination/time identities across partitions where the protocol requires entity generalization. For prediction, use observation window W ending at t and target event in `(t, t+H]`, excluding `label`, `attack_cat`, and post-t features. Keep any final external-validation reservation untouched during development.

## 24. External Validation Reservation
UNSW-NB15 is a **PARTIAL external-validation candidate** only. The acquired file is one partition, has 30.298107% exact duplicates, uses a documented external header mapping, and has declared but not fully independently verified license terms. It must remain reserved and untouched by model-development decisions. The other six datasets are NOT_VERIFIED for record-level external validation.

## 25. Synthetic Data Requirements From Real Evidence
The evidence-backed requirements are recorded in [metadata/synthetic_data_requirements_from_real_evidence.md](metadata/synthetic_data_requirements_from_real_evidence.md). They include normal/attack imbalance, nine attack categories, missing attack categories for normal rows, repeated identities, one-second temporal ordering with gaps, categorical network context, and duplicate-audit scenarios. No synthetic data was generated.

## 26. Dataset Limitations
Only one bounded slice from one dataset was acquired. Its raw file has no header, requiring a documented column manifest. The slice has high exact duplication, no verified session identifier, no timezone metadata, and category labels that are not causes. It does not establish C1, C2, C4, D1, D2, ADFA-LD, or TravisTorrent evidence.

## 27. Blocked Sources
TravisTorrent was blocked by an unrelated unresolved redirect. ADFA-LD was blocked by unresolved Cloudstor. Alibaba and Google had no bounded raw shard identified. CIC downloads had no bounded file/terms route suitable for this run. UNSW official SharePoint returned 403, but a recognized Zenodo derived partition provided the bounded evidence slice.

## 28. Reproducibility

```bash
python -m py_compile src/data_audit/*.py
python src/data_audit/profile_dataset.py \
  --dataset-dir data/external/cybersecurity/unsw_nb15/raw \
  --columns-file data/external/cybersecurity/unsw_nb15/metadata/UNSW_NB15_4_COLUMNS.txt \
  --output-json reports/dataset_audit/UNSW_NB15_PHASE3B_PROFILE.json
python -m json.tool metadata/dataset_acquisition_manifest.json >/dev/null
python -m json.tool metadata/raw_acquisition_manifest.json >/dev/null
```

Raw acquisition is reproducible from the Zenodo API endpoint recorded in `metadata/raw_acquisition_manifest.json`; the raw file is intentionally not committed.

## 29. Errors and Fixes
The first profile treated the no-header first row as column names. This was corrected by verifying the 49-field row width and adding an explicit documented-column mode to the profiler. A separate 43-field Zenodo header artifact was rejected as mismatched. The profiler’s initial numeric statistics were sample-capped; streaming min/max/mean/standard deviation were corrected and rerun. No raw record was fabricated or changed.

## 30. Research-Paper Implications
Phase 3B achieved Outcome B: one bounded real slice provides meaningful schema, label, timestamp, identity, and duplicate evidence. It supports only partial C3/C5 external evidence and does not validate the full seven-failure platform, RCA, prediction performance, or remediation. The paper must disclose the slice provenance, no-header interpretation, duplicate burden, and reserved-data policy.

## 31. Phase 4 Readiness
**PARTIALLY READY.** The UNSW evidence slice is ready for documented future external-evaluation planning, not model development. Phase 4 must first verify the header mapping and redistribution terms, decide how duplicates and entity reuse are handled, acquire or approve additional bounded datasets for the remaining failure classes, freeze group/temporal splits, and only then begin any permitted modeling work.

## Final Dataset Decision Matrix

| Dataset | Raw slice acquired | Records verified | Labels verified | Time verified | Groups verified | Duplicate audit | Leakage audit | D1 | D2 | C1 | C2 | C3 | C4 | C5 | External validation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TravisTorrent | NO | NO | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |
| Alibaba ClusterData | NO | NO | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |
| Google Cluster Data | NO | NO | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |
| CIC-IDS2017 | NO | NO | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |
| CIC-DDoS2019 | NO | NO | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |
| UNSW-NB15 | PARTIAL | YES | YES | YES | YES | YES | PARTIAL | NO | NO | NO | NO | PARTIAL | NO | PARTIAL | PARTIAL |
| ADFA-LD | NO | NO | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | PARTIAL | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |

## Evidence Separation

### VERIFIED FACTS
One 97,588,754-byte UNSW-NB15 CSV partition was downloaded from the recorded Zenodo endpoint. Its checksum, 49-field row width, 440,044 rows, native label values, attack categories, numeric time positions, source/destination/service cardinalities, exact duplicates, and temporal ranges were profiled.

### DOCUMENTED FACTS
The Zenodo record declares CC-BY-4.0 and identifies itself as UNSW-NB15. The 49 field names come from the documented original UNSW-NB15 layout; the raw CSV itself has no header. Official pages document the remaining candidate datasets and their intended categories.

### ENGINEERED PROXIES
None were applied to the acquired UNSW rows. `Reconnaissance` is retained as a native category proxy relevant to C3, not relabeled as port scanning. No D2 proxy was created.

### ASSUMPTIONS
The documented 49-field order aligns with this Zenodo partition, subject to final source-version confirmation. Source/destination/time groups are useful leakage controls. Both require explicit protocol confirmation before publication.

### UNKNOWN
Full-dataset representativeness, timezone, near-duplicates, sequence overlap, causal labels, remediation actions, and verified redistribution permission remain unknown.
