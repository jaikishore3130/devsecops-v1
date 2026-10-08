# Dataset Evidence Register (Phase 2)

The register is conservative: a local README, schema, protocol buffer, fetch script, or access marker is an artifact, not a dataset acquisition. Because no raw records are present, every dataset is status **C - officially identified and evidence-supported, but not acquired**. No status A or B claim is made.

| Dataset | ID | Official source | Local evidence | Status | Raw data | Telemetry | Labels/timestamps/sequences | Intended class | Main limitation |
|---|---|---|---|---|---|---|---|---|---|
| TravisTorrent | DSET_DEVOPS_TRAVISTORRENT | [official portal](https://travistorrent.testroots.org/) | Tool README | C | No | CI/build metadata | Outcome labels documented; timestamps and project histories expected | D1 | Failed build is not RCA or remediation ground truth |
| Alibaba Cluster Trace | DSET_DEVOPS_ALIBABA_CLUSTERDATA | [official repository](https://github.com/alibaba/clusterdata) | README, schema, trace docs, fetch script | C | No | Cluster/workload/resource telemetry | Timestamped trace design; no unified failure label | Revised D2 | Not Kubernetes-specific; proxy labels required |
| Google Cluster Data | DSET_DEVOPS_GOOGLE_CLUSTER_DATA | [official repository](https://github.com/google/cluster-data) | README, 2019 docs, proto, bibliography | C | No | Scheduler/task/machine/event telemetry | Timestamped event schema; no unified failure label | Revised D2 | Proxy labels required; no remediation outcomes |
| CIC-IDS2017 | DSET_CYBER_CIC_IDS2017 | [official landing page](https://www.unb.ca/cic/datasets/ids-2017.html) | Access status marker | C | No | Network flows | Attack categories and timestamps documented; local distribution unavailable | C1, C2, C3, C4 | Lab traffic and category-only labels |
| CIC-DDoS2019 | DSET_CYBER_CIC_DDOS2019 | [official landing page](https://www.unb.ca/cic/datasets/ddos-2019.html) | Access status marker | C | No | DDoS network flows | Attack families and timestamps documented | C2 | Category-only labels and lab realism |
| UNSW-NB15 | DSET_CYBER_UNSW_NB15 | [official landing page](https://research.unsw.edu.au/projects/unsw-nb15-dataset) | Access status marker | C | No | Network flows/features | Attack categories documented; sequence context limited | C3, C5 | Testbed and older-traffic domain shift |
| ADFA-LD | DSET_CYBER_ADFA_LD | [official landing page](https://research.unsw.edu.au/projects/adfa-ids-datasets) | Access status marker | C | No | Linux system-call sequences | Normal/attack scenarios; sequence order | C5 | Host-centric, not network-scale or remediation evidence |

Detailed file hashes and local profiles are in `metadata/external_dataset_manifest.json` and `reports/dataset_audit/*_AUDIT.json`.

## Evidence Interpretation

Official source identity and published dataset descriptions support relevance. They do not establish local availability, row counts, class balance, exact schema, or empirical model performance. DNS failures affected several official landing pages during this run; those fields remain explicitly unverified rather than inferred from filenames.
