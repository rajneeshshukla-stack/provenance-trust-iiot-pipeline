# PBTI V9 — author-run verification: summary

* Executor: Rajneesh Shukla
* Started (UTC): 2026-11-07T10:30:10Z; finished (UTC): 2026-11-07T14:09:23+00:00
* Machine: Ubuntu 26.04.1 LTS (x86_64), Intel(R) Core(TM) i5-10310U CPU @ 1.70GHz, 8 logical CPUs, 7.7 GiB RAM, WSL: True
* Python 3.14.4; pinned packages installed: True
* ProVerif: None
* WORKERS: 4

| Check | Status | Detail |
|---|---|---|
| Repository integrity (before and after) | **PASS** | tree SHA-256 6d21d50b83799a64… vs manifest 6d21d50b83799a64…; 744 files; unchanged after the run: True |
| Frozen-file check (scripts/verify_prereg_hashes.py) | **PASS** | exit 0 |
| Corrected-comparator regression tests (tests/test_b5_corrected.py) | **PASS** | exit 0; 12 passed in 3.28s |
| Re-execution kit (tools/reexec/reproduce_subset.sh) | **CHECK** | 754 of 754 re-executed runs identical to the stored runs (timing fields excluded; 77881 field comparisons; different 0, errors 0); sub-steps {'pytest': 0, 'A0_core': 0, 'A1_review': 0, 'A3_selective': 0, 'A3_scenarios': 0, 'A3_factorial': 0, 'A5_matrix': 0, 'formal_check': 0}; lifecycle matrix 68 of 68 rows identical; bounded locality check: all invariants pass True, identical False (differing fields ['/python', '/source_sha256/b5_corrected.py']; explained: False, the check records the SHA-256 of every source file and the V9 repository adds one); configuration digests equal: True; source digest equal: False (explained: True; the V9 repository adds src/pbti/b5_corrected.py, which these runners do not load; the digest of src/ without it equals the digest stored with the original runs). Re-execution kit's own verdict line: "DIFFERENCES OR FAILURES FOUND - see details" |
| ProVerif models (3) against the stored RESULT lines | **NOT RUN** | ProVerif not found |

Not every automated check passed or ran; the details above and the logs in this folder say which.

The manual reviews (ProVerif model assumptions, Proposition 1 proof, comparator code, manuscript) are recorded in the log sheet, not here.

## Steps

| Step | Exit | Start (UTC) | End (UTC) |
|---|---|---|---|
| 00_environment | 0 | 2026-11-07T10:30:10Z | 2026-11-07T10:30:10Z |
| 01_integrity_before | 0 | 2026-11-07T10:30:10Z | 2026-11-07T10:30:15Z |
| 02_file_hashes | 0 | 2026-11-07T10:30:15Z | 2026-11-07T10:30:16Z |
| 03_frozen_files | 0 | 2026-11-07T10:30:16Z | 2026-11-07T10:30:16Z |
| 04_regression_tests | 0 | 2026-11-07T10:30:16Z | 2026-11-07T10:30:19Z |
| 05_reexecution | 0 | 2026-11-07T10:30:19Z | 2026-11-07T14:09:16Z |
| 06_proverif | SKIPPED | 2026-11-07T14:09:16Z | 2026-11-07T14:09:16Z |
| 08_integrity_after | 0 | 2026-11-07T14:09:16Z | 2026-11-07T14:09:23Z |

## SHA-256 of the files under review

* `src/pbti/b5_corrected.py`: `53cf2167a1dc2a323799384f61580cf8558d5cc64a633b85f2029669a82c20d1`
* `src/pbti/b5.py`: `19dc116609e87f561ebd28ff2cb7e94a1307395d829bbba9d304804a0566816a`
* `src/pbti/verifier.py`: `9c2deed4ed42f392033401be01c809a167331dce33e5eff0e465befeb36724c4`
* `src/pbti/review.py`: `6de3ea62d7802777050b038c62f65e912e795f93f596ccba5026836be70ae18c`
* `src/pbti/registry.py`: `0160acfc11e51fdee9781f798bc887f5ad519f8cfa2db0fe7abbe5af287a5a0c`
* `src/pbti/envelope.py`: `6a1027d89786be2b0071b956caf83b546cd63445a8889f934e36a28e593dc8ef`
* `tests/test_b5_corrected.py`: `f4656be8c474f4611841d81fc6f70203497e01ae38eae2370a11d5d658901c7b`
* `docs/BASELINES.md`: `dfbf8dbfe793013d8c7374fc929173760af447385b0bb34d7e029aab6911290a`
* `formal/LOCALITY_PROOF.md`: `56a80c16b09d6492ed978bcfa1810635b6b943b7ed39f24fced7873cb02c2aa7`
* `formal/PROOF_REVIEW_CHECKLIST.md`: `7d0384cf3fa8ee29c54822693a7fde16bbe9c32ccae1f41e80b06aa33414a1dd`
* `formal/pbti.pv`: `c899431fd546dd7d514cfd89cb1876617fa4318e98aecf587e7de611cea1e60a`
* `formal/pbti_variant_nocompromise.pv`: `f216dadb74bb392278af01b020dabc2c3dd3ebb4234169d90b8502992a9c5016`
* `formal/pbti_variant_otlink_attacker.pv`: `768dcc4556dc7b84d90d2f6b7004a00baefe9077a6af258800c6ba315ece1b22`
* `results/formal/proverif_output.txt`: `67fa4c7f4abccfb0d8c6ad8560c02c377dd33feff09c9596620130a75e408df8`
* `RELEASE_TREE_MANIFEST.json`: `f1c5c10c8afd054e12976442cc5e8501fd17854dc9ab738054b92fc24f3fff13`
