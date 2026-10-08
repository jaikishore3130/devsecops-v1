# Dataset Evidence Register (Phase 2)

## Evidence Hierarchy Used
1. Original dataset repository / official landing page
2. Official institutional repository
3. Original paper / official bibliography
4. Official archives
5. Recognized academic mirrors

If a field could not be verified from accessible evidence in this environment, it is marked **NOT VERIFIED**.

## Dataset Evidence

| Dataset | Official Source | Repository / Archive | Paper | Authors | Year | License | Access Status in This Environment | Exact Validation Purpose | What It Cannot Validate |
|---|---|---|---|---|---:|---|---|---|---|
| TravisTorrent | https://travistorrent.testroots.org/ | https://github.com/TestRoots/travistorrent-tools | Beller et al. (MSR 2017) DOI:10.1109/MSR.2017.24 | Beller et al. | 2017 | NOT VERIFIED | Official portal unreachable (DNS); repository docs accessible | D1 detection, limited CI prediction proxy | Remediation outcomes, explicit RCA labels |
| Alibaba Cluster Trace (v2018 focus) | https://github.com/alibaba/clusterdata | https://github.com/alibaba/clusterdata | Repo-linked docs/bibliography (specific canonical citation NOT VERIFIED in this phase) | Alibaba authors (repo maintainers) | NOT VERIFIED | NOT VERIFIED | Accessible; schema docs and fetch script acquired | D2 detection, prediction proxy, RCA localization proxy | Direct remediation labels, explicit root-cause labels |
| Google Cluster Data | https://github.com/google/cluster-data | https://github.com/google/cluster-data | Repo bibliography (`bibliography.bib`) | Google researchers (see bibliography) | NOT VERIFIED | NOT VERIFIED | Accessible; proto schema and docs acquired | D2 detection, prediction proxy, event-type RCA proxy | Remediation labels, definitive causal RCA |
| CIC-IDS2017 | https://www.unb.ca/cic/datasets/ids-2017.html | NOT VERIFIED | Sharafaldin et al. lineage citation (exact bib field to finalize in next phase) | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | Landing page unreachable (DNS) | C1/C2/C3/C4 detection (once acquired), limited prediction proxy | Remediation outcomes, strong RCA causality |
| CIC-DDoS2019 | https://www.unb.ca/cic/datasets/ddos-2019.html | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | Landing page unreachable (DNS) | C2 detection focus (once acquired) | Remediation outcomes, high-fidelity RCA |
| UNSW-NB15 | https://research.unsw.edu.au/projects/unsw-nb15-dataset | NOT VERIFIED | Moustafa & Slay (2015) | Moustafa, Slay | 2015 | NOT VERIFIED | Landing page unreachable (DNS) | C3/C5 detection and anomaly profiling (once acquired) | Direct remediation outcomes, explicit root causes |
| ADFA-LD | https://research.unsw.edu.au/projects/adfa-ids-datasets | NOT VERIFIED | Creech & Hu (2013) ADFA-LD context | Creech, Hu | 2013 | NOT VERIFIED | Landing page unreachable (DNS) | C5 host-level anomaly detection (once acquired) | Network-scale DDOS/scan validation, remediation labels |

## Phase-2 Decision Notes
- We retained all seven Phase-1 failure classes.
- We **downgraded confidence** for datasets that could not be directly accessed in this runtime due DNS restrictions.
- For inaccessible datasets, schema and label claims remain provisional and are tagged **NOT VERIFIED** where applicable.
