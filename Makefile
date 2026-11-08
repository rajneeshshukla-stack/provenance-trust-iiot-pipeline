# PBTI-IIoT research package (V9): tests, campaigns, analysis and manuscript.
#
# V9 targets (manuscript sources in manuscript/):
#   make install        install Python dependencies (pip)
#   make test           all tests (pytest), including tests/test_b5_corrected.py
#   make frozen         every file of the two freeze lists keeps its recorded SHA-256
#   make results-v9     corrected-comparator tree, unchanged analysis scripts, figures and V9 analysis; generated
#                       files written into manuscript/ (tools/v9/build_corrected_results.sh)
#   make paper          article and Document S1 from manuscript/ (full TeX Live)
#   make check          manuscript consistency checks (tools/manuscript/check_manuscript.py)
#   make campaign-v9    rerun every B5/B5s specification with the corrected comparator (about 5 h; results/v9/raw)
#   make e04-v9         attacker-model robustness campaign and control traces
#
# Historical campaign targets (kept as recorded in Document S1). WARNING: they write to the stored raw-result files
# named below and would overwrite the frozen results; run them on a copy of the repository, or pass the runner a new
# --out path as shown in docs/REPRODUCTION.md.
#   make campaign       security/correctness campaign: scenarios, ablations, revocation sweep, tamper audits
#   make perf           in-process throughput (E17) and device scaling (E18)
#   make e2e            MQTT v5 / mutual-TLS end-to-end latency (requires the 'mosquitto' broker binary)
#   make attribution    per-label attribution of non-legitimate authoritative observations (re-runs E5, E14, E15, mixed)
#   make analysis       statistics, figures, LaTeX tables and macros of the frozen analysis scripts (paper/generated)
#   make campaign-v3    B5/B5s/PBTI-R scenarios and mixed workload, sweep, factorial, SKAB replay (SKAB_DIR=clone)
#   make perf-v3        batching and signature-worker study
#   make e2e-v3         30-repetition MQTT/TLS latency (PBTI, B2) and SKAB replay through MQTT/TLS
#   make parity         Rego/Python policy parity (pip install regopy)
#   make regression-v3  re-run samples of every stored raw file under the current source
#   make replay-residue attack-label attribution of the SKAB replay residue
#   make campaign-v4    re-execution, review-schedule and selective-hold campaigns (about 6 h)
PY ?= python3
SEEDS ?= 10
WORKERS ?= 2

.PHONY: install test frozen results-v9 paper check campaign-v9 e04-v9 campaign perf e2e attribution analysis sample-data campaign-v3 perf-v3 e2e-v3 parity regression-v3 replay-residue

install:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q tests

frozen:
	$(PY) scripts/verify_prereg_hashes.py

results-v9:
	tools/v9/build_corrected_results.sh manuscript

paper:
	sh tools/manuscript/build_all.sh manuscript

check:
	$(PY) -I tools/manuscript/check_manuscript.py manuscript

campaign-v9:
	experiments/v9/run_all_b5c.sh $(SKAB_DIR)

e04-v9:
	$(PY) experiments/v9/run_attacker_consistent.py --out results/v9/raw/attacker_consistent_impersonator.jsonl
	$(PY) experiments/v9/attacker_controls.py

SKAB_DIR ?= ../waico/skab
campaign-v3:
	$(PY) experiments/run_campaign.py scenarios --systems B5 B5S --seeds 20 --audit-seeds 5 --workers $(WORKERS) --out results/raw/v3_scenarios_b5.jsonl
	$(PY) experiments/run_campaign.py scenarios --systems PBTI-R --scenarios S12_beyond_horizon --seeds 20 --audit-seeds 5 --workers $(WORKERS) --out results/raw/v3_scenarios_pbtir.jsonl
	$(PY) experiments/run_campaign.py ablations --systems B5 B5S PBTI-R --seeds 20 --workers $(WORKERS) --out results/raw/v3_mixed_b5.jsonl
	$(PY) experiments/run_campaign.py sweep --seeds 20 --workers $(WORKERS) --out results/raw/v3_sweep.jsonl
	$(PY) experiments/run_campaign.py factorial --seeds 20 --workers $(WORKERS) --out results/raw/v3_factorial.jsonl
	$(PY) experiments/run_campaign.py replay --skab-dir $(SKAB_DIR) --seeds 20 --audit-seeds 2 --workers $(WORKERS) --out results/raw/v3_replay_skab.jsonl

perf-v3:
	$(PY) experiments/run_batching.py --n 10000 --reps 3

e2e-v3:
	$(PY) experiments/run_mqtt_e2e.py --systems B2 PBTI --rates 1000 1250 1500 --reps 30 --warm 2 --measure 10 --drain 3 --out results/raw/v3_mqtt_e2e.jsonl
	$(PY) experiments/run_mqtt_e2e.py --payload skab --skab-dir $(SKAB_DIR) --speeds 1 5 10 --systems PBTI B4 B5 --reps 10 --warm 2 --measure 10 --drain 3 --out results/raw/v3_mqtt_e2e_skab.jsonl

parity:
	$(PY) -I tests/policy_parity/run_parity.py

regression-v3:
	$(PY) scripts/regression_check.py --v3

campaign:
	$(PY) experiments/run_campaign.py scenarios  --seeds $(SEEDS) --workers $(WORKERS)
	$(PY) experiments/run_campaign.py scenarios  --seeds $(SEEDS) --seed-start 11 --workers $(WORKERS) --out results/raw/scenarios_part2.jsonl
	$(PY) experiments/run_campaign.py ablations  --seeds $(SEEDS) --workers $(WORKERS)
	$(PY) experiments/run_campaign.py ablations  --seeds $(SEEDS) --seed-start 11 --workers $(WORKERS) --out results/raw/ablations_part2.jsonl
	$(PY) experiments/run_campaign.py revocation --seeds $(SEEDS) --workers $(WORKERS)
	$(PY) experiments/run_campaign.py revocation --seeds $(SEEDS) --seed-start 11 --workers $(WORKERS) --out results/raw/revocation_part2.jsonl
	$(PY) experiments/run_campaign.py scenarios  --systems B4 --seeds 20 --workers $(WORKERS) --out results/raw/scenarios_part3_b4.jsonl
	$(PY) experiments/run_campaign.py ablations  --systems B4 --seeds 20 --workers $(WORKERS) --out results/raw/ablations_part3_b4.jsonl
	$(PY) experiments/run_campaign.py audit      --seeds 5 --workers $(WORKERS)

perf:
	$(PY) experiments/run_throughput.py --reps 10 --n 20000
	$(PY) experiments/run_throughput.py --reps 3 --n 20000 --scaling

e2e:
	$(PY) experiments/run_mqtt_e2e.py --rates 200 500 1000 1500 --reps 5 --warm 3 --measure 12 --drain 4

attribution:
	$(PY) scripts/attribute_nonlegit.py --scenarios S05_stolen_key S15_edge_compromise S14_revocation --systems PBTI B3 --seeds 1 20
	$(PY) scripts/attribute_nonlegit.py --scenarios S99_mixed --systems PBTI --seeds 1 20 --out results/summary/nonlegit_attribution_mixed.json
	$(PY) scripts/attribute_nonlegit.py --scenarios S05_stolen_key S14_revocation --systems B4 --seeds 1 20 --out results/summary/nonlegit_attribution_b4.json

analysis:
	$(PY) analysis/analyze.py
	$(PY) analysis/analyze_v3.py
	$(PY) scripts/reference_verification.py

sample-data:
	$(PY) scripts/make_sample_data.py

replay-residue:
	$(PY) scripts/diagnose_replay_residue.py --skab-dir $(SKAB_DIR)


# ------------------------------------------------------------------ V4 stage (research/V4, results/v4)
.PHONY: checks-v4 campaign-v4 analysis-v4
checks-v4:
	$(PY) scripts/a5_lifecycle_matrix.py
	$(PY) formal/v4_locality_lifecycle_check.py
campaign-v4:            # about 6 h on two vCPUs (A0 1.5 h, A1 2.2 h, A3 1.3 h, A3 controls 0.5 h, amendment 0.5 h)
	for c in A0_core A1_review A3_selective A3_scenarios; do \
	  $(PY) experiments/run_v4.py experiments/v4_configs/$$c.json --out results/v4/raw/$$c.jsonl; done
	$(PY) experiments/run_v4.py experiments/v4_configs/amendment1/A3_factorial.json --out results/v4/raw/A3_factorial.jsonl
	$(PY) scripts/compare_a0.py results/v4/raw/A0_core.jsonl --out results/v4/summary/A0_comparison.json
analysis-v4:
	$(PY) analysis/analyze_v4.py
	$(PY) analysis/validate_v4_stats.py
