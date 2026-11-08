# PBTI-IIoT — research package (V9)

Reference implementation, baselines, deterministic evaluation testbed, raw results, analysis scripts and manuscript
build tools for the article *"Provenance-Bound Trust-Aware Ingestion for Industrial IoT Edge-to-Cloud Data Pipelines:
Per-Identity Conflict Containment and Its Security–Availability Trade-offs"* (Rajneesh Shukla and Punit Gupta;
prepared for submission to *Future Internet*, MDPI).

**Status: V9 — prepared for author completion.** The package has not been published. Its public repository URL,
release tag and commit and archive DOI do not exist yet, and the authors' own verification has not been recorded
(see the response folder of the V9 deliverable, `AUTHOR_COMPLETION_REQUIRED.md`).

## What V9 changes

* **Corrected comparator.** The feed-level comparator B5 had two defects that can disadvantage it (released observations
  held again without new fork evidence; an observation that could stay held without an open review case) and counter
  defects. They are corrected in a separate module, `src/pbti/b5_corrected.py`; the historical module
  `src/pbti/b5.py`, which produced every frozen result and is hash-frozen, is unchanged. The six points the
  specification had left open are stated in `docs/BASELINES.md` (section "B5, corrected implementation (V9)").
  Regression tests: `tests/test_b5_corrected.py`; differential check against the reference model:
  `tools/v9/b5c_refmodel_diff.py`.
* **Reruns.** Every B5/B5S specification of every stage was rerun with the corrected comparator on its original seeds
  (`experiments/v9/run_all_b5c.sh`); rows in `results/v9/raw/` (separate from the frozen rows), with manifests.
* **Attacker-model robustness.** Mixed workload with a consistent impersonator, seeds 21–40, and six control traces
  (`experiments/v9/`; results `results/v9/raw/attacker_*`); exploratory.
* **Analysis.** `tools/v9/build_corrected_results.sh` runs the unchanged analysis scripts on a tree in which only the
  B5/B5S rows are replaced, and `tools/v9/analysis_v9.py` writes the corrected-minus-original comparisons
  (`results/v9/summary/`).

## Layout

```
src/pbti/          implementation (PBTI verifier, baselines B1-B4, historical B5 b5.py, corrected B5 b5_corrected.py,
                   selective holds, reviewer, testbed sim.py, oracle, temporal tracer, ...)
tests/             unit, property, invariant, workflow and regression tests
experiments/       frozen campaign runners (run_campaign.py, run_v4.py, v4_configs/) and V9 runners (v9/)
analysis/          frozen analysis scripts (analyze.py, analyze_v3.py, analyze_v4.py, validate_v4_stats.py)
formal/            locality proof, its review checklist and automated audit, ProVerif models, bounded checks
research/          analysis plans with hashes (V3, V4 and amendment), decision logs, literature and reference-check
                   records (research/literature/reference_check_2026-11-06/)
docs/              protocol, state machine, threat model, baseline specifications, reproduction instructions,
                   historical READMEs (docs/history/)
manuscript/        V9 article and Document S1: LaTeX sources, generated tables and macros, figures with their data
results/raw/       frozen main-evaluation and sensitivity results (historical B5)
results/v4/        frozen re-execution, review-schedule and selective-hold results and summaries (historical B5)
results/v7/        earlier automated audits, reference model, re-execution and exploratory analyses
results/v9/        corrected-comparator reruns, robustness campaign, reference-model check, summaries and the
                   verification record (results/v9/summary/verification_record.json)
tools/             re-execution kit, audit tools, earlier-stage analysis and figure scripts (tools/v7/), V9 tools,
                   manuscript build tools
```

The frozen analysis scripts write their outputs to `paper/generated` and `paper/figures`, and
`tools/v9/regenerate_analysis.sh` composes the article's generated files in `paper_v7/generated`; these output
directories are created when the scripts run (normally inside a scratch copy of the repository) and are not part
of the package. Directory and file names such as `v3_`, `v4/`, `A1_review` and `tools/v7/` are the identifiers
under which the stages were run; they are kept because recorded hashes and manifests refer to them (Document S1
maps every stage to its identifiers).

## Quick start

```sh
python3 -m pip install -r requirements.txt
python3 -m pytest -q tests                          # or: make test
python3 scripts/verify_prereg_hashes.py             # or: make frozen
tools/v9/build_corrected_results.sh manuscript      # or: make results-v9 (about 5 min)
sh tools/manuscript/build_all.sh manuscript         # or: make paper (full TeX Live)
```

Full instructions, run times and the third-party dataset (SKAB, not redistributed): `docs/REPRODUCTION.md`.

> Scope: PBTI provides verifiable evidence about identity, integrity, authorization, provenance and processing history
> within its threat model. It does **not** establish that a measurement is physically correct.

License: Apache-2.0 (`LICENSE`). The SKAB dataset used by the replay is GPL-3.0 and is not included.
