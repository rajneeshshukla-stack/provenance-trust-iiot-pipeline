# Re-execution of selected seeds: comparison with the stored results

**Verdict:** ALL RE-EXECUTED OUTPUTS IDENTICAL TO STORED OUTPUTS (timing excluded)

* Label: automated re-execution in the cloud workspace (Claude Opus 5.5 session; not an author-controlled machine)
* Time (UTC): 2026-11-05T23:31:02+00:00; local: 2026-11-05T17:31:02-06:00
* CPU: Intel(R) Xeon(R) Processor @ 2.10GHz (2 logical CPUs), memory 7.83 GiB
* OS: Ubuntu 24.04.5 LTS (kernel 6.18.44-fc-v242, x86_64); Python 3.13.18
* Packages: cryptography 50.0.1, numpy 2.5.3, scipy 1.18.1, pandas 3.0.5, matplotlib 3.11.2, PyYAML 6.0.3, psutil 7.2.2, paho-mqtt 2.1.0, pytest 9.1.1
* Git commit: not a git checkout
* Source SHA-256 (src/pbti aggregate): `1e52921a372bd21215ae2b53e98ecb86499ead7332359ddeda44d71e436e630d`
* Code SHA-256 (src, experiments, analysis, formal, scripts aggregate): `4eef8d473a6917ab5c9053f4cdcad3801246631766fdcfbba79546bd9555a53e`

## Steps

| Step | Exit code | Start (UTC) | End (UTC) | Command |
|---|---|---|---|---|
| pytest | 0 | 2026-11-05T23:31:02Z | 2026-11-05T23:32:52Z | `python3 -m pytest -q tests/` |
| A0_core | 0 | 2026-11-05T23:32:52Z | 2026-11-05T23:43:26Z | `python3 experiments/run_v4.py experiments/v4_configs/A0_core.json --seeds 1 2 --workers 2 --out /home/claude/PBTI_v7/results/reexec_cloud/A0_core_subset.jsonl` |
| A1_review | 0 | 2026-11-05T23:43:26Z | 2026-11-06T00:09:52Z | `python3 experiments/run_v4.py experiments/v4_configs/A1_review.json --seeds 21 22 --workers 2 --out /home/claude/PBTI_v7/results/reexec_cloud/A1_review_subset.jsonl` |
| A3_selective | 0 | 2026-11-06T00:09:52Z | 2026-11-06T00:34:38Z | `python3 experiments/run_v4.py experiments/v4_configs/A3_selective.json --seeds 21 22 --workers 2 --out /home/claude/PBTI_v7/results/reexec_cloud/A3_selective_subset.jsonl` |
| A3_scenarios | 0 | 2026-11-06T00:34:38Z | 2026-11-06T00:41:55Z | `python3 experiments/run_v4.py experiments/v4_configs/A3_scenarios.json --seeds 1 2 --workers 2 --out /home/claude/PBTI_v7/results/reexec_cloud/A3_scenarios_subset.jsonl` |
| A3_factorial | 0 | 2026-11-06T00:41:55Z | 2026-11-06T00:50:01Z | `python3 experiments/run_v4.py experiments/v4_configs/amendment1/A3_factorial.json --seeds 21 22 --workers 2 --out /home/claude/PBTI_v7/results/reexec_cloud/A3_factorial_subset.jsonl` |
| A5_matrix | 0 | 2026-11-06T00:50:01Z | 2026-11-06T00:50:01Z | `python3 scripts/a5_lifecycle_matrix.py` |
| formal_check | 0 | 2026-11-06T00:50:01Z | 2026-11-06T00:52:09Z | `python3 formal/v4_locality_lifecycle_check.py --out /home/claude/PBTI_v7/results/reexec_cloud/v4_locality_lifecycle_check.json` |

Test suite: 187 passed, 1 skipped in 108.70s (0:01:48)

## Campaign runs

| Re-executed file | Seeds | Runs compared | Identical | Different | Errors | Field comparisons |
|---|---|---|---|---|---|---|
| A0_core_subset.jsonl | 1, 2 | 132 | 132 | 0 | 0 | 12367 |
| A1_review_subset.jsonl | 21, 22 | 176 | 176 | 0 | 0 | 19550 |
| A3_selective_subset.jsonl | 21, 22 | 294 | 294 | 0 | 0 | 29687 |
| A3_scenarios_subset.jsonl | 1, 2 | 40 | 40 | 0 | 0 | 3995 |
| A3_factorial_subset.jsonl | 21, 22 | 112 | 112 | 0 | 0 | 12282 |

Source and configuration digests as recorded by the runner (repository definition), stored campaign versus re-execution:

| Re-executed file | source_sha256 | config_sha256 | equal |
|---|---|---|---|
| A0_core_subset.jsonl | `8dfae6decd80e501…` | `230d4d21606a23b1…` | yes |
| A1_review_subset.jsonl | `8dfae6decd80e501…` | `7bb565bc8248ba66…` | yes |
| A3_selective_subset.jsonl | `8dfae6decd80e501…` | `4a9bf4bbcf758804…` | yes |
| A3_scenarios_subset.jsonl | `8dfae6decd80e501…` | `ca81520954b0b096…` | yes |
| A3_factorial_subset.jsonl | `8dfae6decd80e501…` | `0ce7c110265349dc…` | yes |

Totals: {"compared": 754, "identical": 754, "different": 0, "errors_in_new": 0, "n_field_comparisons": 77881, "missing_in_stored": 0, "not_reexecuted": 0}

Excluded (machine-dependent wall-clock timing): fields containing `_us`, and `wall_s`, `audit_static_s`, `audit_replay_s`.

Lifecycle matrix: 68 of 68 rows identical; different or missing: 0

Bounded formal check: all_pass stored=True, new=True; identical excluding timing: True

Scope: this compares the listed seeds only. It is not a full reproduction of every campaign, and a re-execution on the same code shows determinism and portability of the stored results, not the validity of the modelling assumptions.
