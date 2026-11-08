# PBTI repository — V7 state (read this before README.md)

`README.md` describes an earlier state of this repository and is kept unchanged as part of the historical record.
Where it differs, this file is current (6 November 2026):

* **Tests:** the suite has 188 tests (`python3 -m pytest -q tests/`: 187 passed, 1 skipped by design), not 70.
* **Policy parity:** the Rego formulation of the admission policy *was* executed, with the rego-cpp interpreter
  (regopy 1.5.2); Open Policy Agent itself was not run (`results/policy_parity/parity_results.json`).
* **Formal material:** `formal/LOCALITY_PROOF.md` contains a pen-and-paper proof of the locality property of Rule L
  (stated as a proof sketch in the article; checked by bounded enumeration and an AI-performed audit, **not yet reviewed
  by a human**), `formal/*.pv` a ProVerif model, and `formal/*_check.py` the bounded checks.
* **Quarantine release** is implemented (signed review; `src/pbti/review.py`); see the corrected `docs/BASELINES.md`,
  `docs/THREAT_MODEL.md` and `docs/EXPERIMENT_PLAN.md`.
* **V7 materials:** `paper_v7/` (article and supplement), `tools/` (re-execution kit, V7 analysis and figures, audit
  tools), `results/v7/` (re-execution, analyses, audit outputs). Reproduction: `04_Reports/08_REPRODUCIBILITY_INSTRUCTIONS.md`
  in the V7 package.
* **Known limitations of the prototype** (article Sections 8 and 9, Table S34): no verifier restart recovery (the
  SQLite store is recreated at start-up), MQTT acknowledgements before commit, broker without persistence, unbounded
  verifier state, in-process witness, software keys only; single-host measurements only.
* **Known B5 defects** (kept in the frozen code; effects reported in the article's Section S3): re-hold of released
  observations without new fork evidence; a latent permanent hold when a stale case is released into a held feed; a
  hold counter that double counts.
* **Known attacker and threat-model limits** (article Sections 7 and 8): the mixed workload's impersonation attacker
  is not fully consistent (exploratory re-run with a consistent attacker: `tools/v7/consistent_impersonator_check.py`);
  forgeries under fresh identities (null `prev` at seq > 0, sequence jumps, epoch advances) were not evaluated.
