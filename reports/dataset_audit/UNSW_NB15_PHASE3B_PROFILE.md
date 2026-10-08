# UNSW-NB15 Phase 3B Evidence-Slice Profile

## Acquisition

- Source: Zenodo record `10.5281/zenodo.10140548`
- File: `UNSW-NB15_4.csv`
- License declared by source: CC-BY-4.0
- Raw file size: 97,588,754 bytes
- MD5: `f55875cab7f037fdad40b5b737e7db5e`
- SHA-256: `cdf563692d51d405541dd659ddcdad9fa01f001f05fe9fc4b67f00ca12fbc96a`
- Format: CSV without an embedded header
- Column names: documented 49-field layout in `data/external/cybersecurity/unsw_nb15/metadata/UNSW_NB15_4_COLUMNS.txt`

## Records and Schema

- Records: 440,044
- Fields: 49
- Missing `attack_cat`: 351,150 rows (79.798838%)
- Native binary `label`: 0 = 351,150 (79.798838%); 1 = 88,894 (20.201162%)
- Source IP cardinality observed: 38
- Destination IP cardinality observed: 43
- Service cardinality observed: 13
- No session or flow identifier was verified in the acquired partition.

The raw partition has no header. The documented column manifest is used only to interpret field positions; names are not claimed to have been embedded in the raw file.

## Labels

`label` is a directly present binary target in the partition. `attack_cat` is a directly present category field for attack rows, with categories:

| Category | Rows |
|---|---:|
| Generic | 61,878 |
| Exploits | 11,439 |
| Fuzzers | 5,390 |
| DoS | 4,907 |
| Reconnaissance | 3,530 |
| Analysis | 670 |
| Backdoor | 666 |
| Shellcode | 371 |
| Worms | 43 |

These are native dataset categories, not causal root causes. `Reconnaissance` is evidence relevant to C3 scanning only as a category proxy; it does not prove every record is a port/service scan. The broad attack categories support C5 malicious/anomalous network behavior classification only partially. No RCA or remediation ground truth is present.

## Time

The documented `Stime` and `Ltime` fields are numeric epoch-like values:

- `Stime`: 1,424,249,984 to 1,424,262,068
- `Ltime`: 1,424,250,009 to 1,424,262,069
- Observed `Stime` span: 12,084 seconds
- Unique `Stime` seconds: 11,773
- Sorted unique-time gap: minimum 1 second, median 1 second, maximum 296 seconds
- Timezone: NOT VERIFIED from the acquired file

These fields establish temporal ordering and burst/gap analysis, but not a verified incident boundary. Window construction must avoid using post-event fields such as final category and binary label.

## Duplicate Analysis

- Exact duplicate rows: 133,325
- Exact duplicate percentage: 30.298107%
- Repeated `(srcip, dstip, Stime, Ltime)` keys: 43,782
- Rows in repeated identity keys: 247,762
- Near duplicates: NOT COMPUTED
- Sequence overlap: NOT_VERIFIED; no explicit sequence/session key was observed

Duplicates were not removed. They may represent repeated observations or source duplication and require dataset-specific investigation before any split. Random splitting is unsafe because source/destination identities and repeated time keys recur across the partition.

## Leakage Findings

- `label` and `attack_cat`: LABEL-DERIVED; targets only.
- `Stime` and `Ltime`: conditionally safe for temporal ordering, but prediction features require a cutoff at time `t`.
- `srcip`, `dstip`, and service: group/reuse risk; do not allow identity leakage across evaluation groups without an explicit protocol.
- Exact duplicate rows and repeated time/identity keys: high cross-split overlap risk.
- No remediation or recovery fields were observed.

## Suitability

| Task | Evidence-slice decision | Reason |
|---|---|---|
| Detection | PARTIAL | Native binary labels and attack categories are present, but this is one partition with substantial duplicates |
| Prediction | PARTIAL | Numeric time fields and one-second ordering exist; future-horizon and entity grouping require design |
| C3 scanning | PARTIAL | `Reconnaissance` category is present, but is broader than verified port/service scanning |
| C5 anomalous/malicious network behavior | PARTIAL | Native attack categories exist; category labels are not causal explanations |
| C1, C2, C4 | NOT_VERIFIED_IN_SELECTED_SLICE | No verified evidence in this selected partition was used for those mappings |
| RCA | NO | No explicit causal or component root-cause field |
| Remediation | NO | No action/outcome ground truth |

This is an evidence slice, not development data and not yet a reserved final external-validation dataset. Its `PARTIAL` external-validation status reflects the single partition, duplicate burden, header provenance, and unverified licensing terms for redistribution.
