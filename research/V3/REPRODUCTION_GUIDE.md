# Reproduction guide (V3)

Everything below runs from the repository root. Virtual-time results are fully determined by the seed and the
source digest (`results/raw/*.manifest.json` records both); wall-clock results depend on the host and will differ.

## 1. Environment

* Python 3.11+ (the study used 3.13.18), `pip install -r requirements.txt` (exact versions with hashes:
  `deploy/requirements.lock.txt`; `pip install --require-hashes --no-deps -r deploy/requirements.lock.txt`).
* Mosquitto 2.0.x for the MQTT/TLS experiments; TeX Live (full, incl. `texlive-fonts-extra` for `bbm.sty`) and
  latexmk for the paper; pandoc and LibreOffice for the Word copy.
* Optional: `pip install regopy` (Rego parity), ProVerif 2.05 (`formal/run_proverif.sh`), Docker with BuildKit.
* SKAB replay: `git clone https://github.com/waico/SKAB ../waico/skab && git -C ../waico/skab checkout b2c0d46c2971dcbfe71e26087b6d231998bb91c2`
  (GPL-3.0; not redistributed here). Per-file SHA-256 hashes of the files used: `results/raw/v3_replay_skab_dataset.json`.

Container alternative: `docker build -f deploy/Dockerfile.v3 --build-context pbti_deploy=deploy -t pbti:v3 .`
then `docker run --rm pbti:v3 make test` (see `deploy/run_container_checks.sh`).

## 2. One-command paths

| Goal | Command | Time on the study host (2 vCPUs) |
|---|---|---|
| Tests | `make test` | about 3 min |
| Revision-2 campaigns | `make campaign` | several hours |
| V3 virtual-time campaigns | `make campaign-v3 SKAB_DIR=../waico/skab` | about 4 h |
| V3 batching / workers | `make perf-v3` | about 12 min (quiet host) |
| V3 MQTT/TLS (30 reps) and SKAB through MQTT | `make e2e-v3 SKAB_DIR=../waico/skab` | about 1.5 h (quiet host) |
| Rego parity | `make parity` | about 7 min |
| Rule L bounded check | `python3 formal/rule_l_bounded_check.py --workers 2 --log results/formal/rule_l_bounded_check_final.log` | about 1 h (2 workers) |
| Tamper audits with the final auditor | `python3 experiments/run_campaign.py audit --seeds 5 --workers 2 --out results/raw/v3_audit_rerun.jsonl` | about 12 min |
| Regression check of stored results | `make regression-v3` | about 10 min (2 workers) |
| Analysis, tables, figures, macros | `make analysis` | about 1 min |
| Paper (full TeX Live, no stubs) | `cd paper && latexmk -pdf main.tex && latexmk -pdf supplementary.tex` | 1 min |
| Consistency gate | `make check` (every macro used is generated) | seconds |
| Submission gate, validation report, issue matrix | `make final` | seconds |
| Attribution of the SKAB replay residue | `make replay-residue SKAB_DIR=../waico/skab` | about 6 min |
| Word copy | `make export` | 1 min |

## 3. What each V3 claim rests on

| Claim in the manuscript | Raw data | Analysis output |
|---|---|---|
| B5/B5s vs PBTI, predictions P1-P4, decision rules | `results/raw/v3_scenarios_b5.jsonl`, revision-2 `scenarios*.jsonl` | `results/summary/v3_x1_preregistered_tests.csv`, `v3_analysis_report.json` (`predictions`) |
| Release workflow in E11b and mixed workload | `v3_scenarios_pbtir.jsonl`, `v3_mixed_b5.jsonl` | `v3_x2_mixed.csv`, Table S14 |
| Sweep and factorial | `v3_sweep.jsonl`, `v3_factorial.jsonl` | `v3_sweep_summary.csv`, `v3_sweep_tests.csv`, `v3_factorial_effects.csv` |
| SKAB replay | `v3_replay_skab.jsonl`, `v3_replay_skab_dataset.json` | `v3_replay_summary.csv`, `v3_replay_tests.csv` |
| SKAB replay residue attribution | re-run of seeds 1-3 (`make replay-residue`) | `results/summary/v3_replay_residue.json` |
| Batching and workers | `v3_batching.jsonl` | `v3_batching_summary.csv` |
| 30-rep MQTT/TLS latency, SKAB through MQTT | `v3_mqtt_e2e.jsonl`, `v3_mqtt_e2e_skab.jsonl` | `v3_e2e_summary.csv`, `v3_e2e_tests.csv`, `v3_e2e_skab_summary.csv` |
| Rego parity | — | `results/policy_parity/parity_results.json` |
| ProVerif and Rule L bounded checks | — | `results/formal/proverif_output.txt`, `rule_l_bounded_check_final.log` (final source; the earlier run on a pre-final verifier is in `results/formal/superseded/`) |
| Container build and checks | — | `results/containers/` |
| Stored V2/V3 results reproduce under the final source | all of the above | `results/summary/regression_check_v3.json` |

Host state at the start of each wall-clock run: `logs/v3_*_host_state.txt`.

## 4. Not reproducible here

Multi-host and constrained-device experiments were not performed (no hardware); scripts and protocols:
`docs/V3_HARDWARE_PROTOCOLS.md`, `experiments/run_multihost.py`, `experiments/run_device_bench.py`.
