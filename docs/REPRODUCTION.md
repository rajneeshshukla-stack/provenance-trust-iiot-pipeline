# Reproduction instructions (V9 research package)

All commands run from the repository root. Paths are relative to it. Nothing here needs network access except the
optional SKAB clone (step 4) and package installation.

## 0. Environment

The stored results were produced on a two-vCPU Linux virtual machine (Intel Xeon 2.1 GHz, 7.8 GB RAM) with Python
3.13.18 and the package versions pinned in `requirements.txt` (cryptography 50.0.1, numpy 2.5.3, scipy 1.18.1,
pandas 3.0.5, matplotlib 3.11.2, PyYAML 6.0.3, psutil 7.2.2, paho-mqtt 2.1.0, pytest 9.1.1); every manifest
(`*.manifest.json`) records the interpreter, platform, CPU, package versions and the SHA-256 digest of `src/`.
The simulation outcomes are deterministic per specification; only fields containing `_us`, `_ns` or `wall_s` (and
the audit timings) depend on the machine.

```sh
python3 -m pip install -r requirements.txt        # or: pip install -e '.[test]'
```

## 1. Tests and frozen-file check

```sh
python3 -m pytest -q tests                         # includes tests/test_b5_corrected.py (corrected comparator)
python3 scripts/verify_prereg_hashes.py           # every file of the two freeze lists keeps its recorded SHA-256
```

The freeze lists (`research/V4/PREREGISTRATION_V4.sha256`, `..._AMENDMENT_1.sha256`) include `src/pbti/b5.py`, the
historical comparator. The corrected comparator is a separate module (`src/pbti/b5_corrected.py`), so the check
passes unchanged.

## 2. Historical (frozen) campaigns

The frozen raw results are in `results/raw/` (main evaluation and sensitivity analyses) and `results/v4/raw/`
(re-execution with the tracer, review schedules, selective holds); they were produced with the historical B5 and are
kept unchanged. Their commands are listed with the stages in Document S1 (Table "Evaluation stages ... repository
identifiers") and in `research/V3/REPRODUCTION_GUIDE.md`; for example

```sh
python3 experiments/run_v4.py experiments/v4_configs/A1_review.json --out /tmp/A1_review.jsonl   # writes a new file
```

Write to a new output file if the stored results must be kept. The second-environment re-execution kit is
`tools/reexec/reproduce_subset.sh` (records environment, commit, source and configuration hashes, commands, seeds and
exit codes; outputs in `results/v7/reexec_cloud/`).

## 3. Corrected-comparator reruns (B5 and B5s)

```sh
experiments/v9/run_all_b5c.sh [SKAB_DIR]           # about 5 h on 2 vCPUs; resumable; writes results/v9/raw/
```

The script reruns every B5 and B5s specification of the main evaluation, the mixed workload, the re-execution with
the tracer, the review-schedule evaluation, the selective-hold grid and factorial cells, the sweep, the factorial and
(with `SKAB_DIR`) the SKAB replay, on the frozen configurations and seeds. The frozen runners
(`experiments/run_campaign.py`, `experiments/run_v4.py`) are reused unchanged; only the class that `sim.World`
instantiates for B5/B5S is replaced in the running process (`experiments/v9/v9_common.py`). Every row carries
`b5_impl = b5_corrected_v9`, the SHA-256 of `src/pbti/b5_corrected.py` and `src/pbti/b5.py` and the source digest;
every output has a manifest.

The end-to-end MQTT runs of B5 (`results/raw/v3_mqtt_e2e_skab.jsonl`) contain no fork evidence (all receipts
`ACCEPT/COMMITTED`) and are unaffected by the correction; they were not rerun.

## 4. SKAB dataset (third-party input, not redistributed)

```sh
git clone https://github.com/waico/SKAB SKAB && git -C SKAB checkout b2c0d46c2971dcbfe71e26087b6d231998bb91c2
python3 -I tools/v9/check_skab.py SKAB            # per-file SHA-256 against results/raw/v3_replay_skab_dataset.json
```

SKAB (Katser and Kozitsin, 2020) is licensed GPL-3.0; the replay reads it from the local clone.

## 5. Attacker-model robustness campaign and checks

```sh
python3 experiments/v9/run_attacker_consistent.py --out results/v9/raw/attacker_consistent_impersonator.jsonl   # ~20 min
python3 experiments/v9/attacker_controls.py           # six deterministic control traces (seconds)
python3 tools/v9/a5_and_e09_e10.py               # lifecycle matrix regeneration, superseded-snapshot trace, widths
python3 tools/v9/resume_probe.py                 # fork and resume times quoted in the article (E5, seeds 21-23)
tools/v9/b5c_refmodel_campaign.sh results/v9/b5c_refmodel validation   # reference-model check (~15 min)
```

## 6. Analysis, tables, figures and manuscript

```sh
tools/v9/build_corrected_results.sh manuscript              # corrected tree, unchanged analysis scripts, figures,
                                                            # V9 analysis; generated files copied into manuscript/
sh tools/manuscript/build_all.sh manuscript                 # article and Document S1 with stable cross-references
python3 -I tools/manuscript/check_manuscript.py manuscript  # consistency checks (macros, references, wording, pages)
tools/v9/regenerate_analysis.sh TREE                        # the analysis scripts alone, on any tree
python3 -I tools/v9/build_data_s1.py ../corrected_tree . OUT_DIR   # Data S1 from the generated outputs
```

`build_corrected_results.sh` copies the repository into `TREE_DIR` (default `../corrected_tree`), replaces there
(and only there) the B5 and B5s rows of each raw file read by the frozen analysis scripts with the corrected rows of
the same specification (`tools/v9/build_corrected_tree.py`, which also checks that every historical row without fork
evidence is reproduced exactly), runs `analysis/analyze.py`, `analysis/analyze_v3.py`, `analysis/analyze_v4.py`,
`tools/v7/neutralize_tables.py`, `tools/v7/analysis_v7.py` and `tools/v7/figures_v7.py` unchanged in that tree,
draws the print-size figures (`tools/manuscript/figures_print.py`), and runs `tools/v9/analysis_v9.py`, which writes
the corrected-minus-original comparisons, the robustness tables and the `\Y...` macros. Running
`tools/v9/regenerate_analysis.sh` on an unmodified copy of the repository reproduces the stored historical summaries
in `results/summary/` and `results/v4/summary/` (the environment table marks the current source digest).

## 7. Verification record

```sh
python3 tools/v9/verify_v9.py SCRATCH_DIR     # tests, frozen files, run completeness, regeneration, spot rerun
```

writes `results/v9/summary/verification_record.json` with every command, its exit status and a summary.

## 8. What has and has not been reproduced

All runs, re-executions and checks in this package were made by the same automated research process that produced
the results; none is an external, independent reproduction, and none was run by the authors. See
`AUTHOR_COMPLETION_REQUIRED.md` in the response folder of the V9 deliverable for the verification the authors still
have to perform.
