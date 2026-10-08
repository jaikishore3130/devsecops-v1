# Synthetic Data Requirements From Real Evidence

This document records only requirements supported by the acquired UNSW-NB15 evidence slice. It does not generate data or assert that the slice represents all UNSW-NB15 releases.

| Requirement | Evidence | Constraint |
|---|---|---|
| Include binary normal/attack targets | UNSW-NB15_4.csv: 351,150 label 0 and 88,894 label 1 | Preserve imbalance scenarios; do not use label as an input |
| Include multi-class attack categories | Nine observed non-empty `attack_cat` categories | Keep category labels separate from causal RCA labels |
| Include missing category labels for normal traffic | 351,150 `attack_cat` values missing | Model missingness explicitly; do not impute normal rows as a root cause |
| Include network identity context | 38 source IPs and 43 destination IPs observed | Generate group reuse and enforce group-aware split tests |
| Include service/protocol/state categorical context | 13 services and observed `proto`/`state` fields | Preserve categorical skew and leakage controls |
| Include temporal ordering and gaps | `Stime`/`Ltime`, one-second median gap, maximum 296-second gap | Generate burst and gap behavior; use observation cutoff time |
| Include duplicate/repeated-observation scenarios for audit testing | 133,325 exact duplicates and 43,782 repeated identity-time keys | Do not silently deduplicate; test duplicate-window prevention |
| Include flow/resource values with long-tail handling | Numeric flow/resource fields in the 49-field layout | Use documented units and transformations only after validation |

Unknowns that must not be invented from this slice include cloud-service semantics, Kubernetes events, causal root causes, remediation actions, and cross-dataset correlations.
