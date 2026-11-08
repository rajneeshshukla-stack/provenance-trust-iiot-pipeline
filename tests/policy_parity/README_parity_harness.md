# Rego / Python PDP parity harness (PBTI-IIoT, released version)

Files in this directory for Task 1:

| file | content |
|---|---|
| `parity_test.py` | the harness (Python PDP vs `policies/admission.rego`) |
| `parity_results.json` | results of the validation run: counts per category, headline numbers, every mismatch, all non-grid cases with both outputs |
| `logs/parity_run_regopy.log` | console output of that run |
| `logs/pip_install_regopy.log` | installation of the Rego interpreter |
| `logs/parity_opa_backend_check.log` | what happens with `--backend opa` here (no OPA binary; dry run) |

The repository under test (`/home/claude/PBTI_v3/01_repo_base/pbti-iiot`) was only read. The harness sets
`sys.dont_write_bytecode` before importing `pbti`, so no `__pycache__` is written into it.

## How to run

```
pip install --break-system-packages regopy          # rego-cpp Python bindings (1.5.2 was used)
python3 -I parity_test.py                           # regopy back end, writes parity_results.json
python3 -I parity_test.py --backend opa             # only if an `opa` binary is ALREADY installed
python3 -I parity_test.py --backend opa --opa-dry-run DIR   # writes data files + exact `opa eval` commands, runs nothing
```

`--repo PATH` selects another checkout; `--opa-bin PATH` gives an explicit OPA binary; `--opa-per-case` runs one
`opa eval` process per case instead of one batch per policy version.

## What is compared

* **Python:** `PDP(PolicyStore).evaluate(did, aid, wid, sch, origin_kind, t_ms)` with the default
  `check_origin=True`, which is the call the PBTI verifier makes (`verifier.py`, line 209). Result: `(permit, reason, version)`.
  The uncached core `PDP._decide` is also recorded for each case, which separates memo-cache artefacts from the
  policy logic.
* **Rego:** `data.pbti.admission.allow` and `data.pbti.admission.reason`, with `data.pbti` set to the document of the
  policy version and `input = {"did", "aid", "wid", "sch", "origin_kind"}` (the input contract in the header of
  `admission.rego`). Each case gets its own input document (`set_input_term(json.dumps(case))`). As a check, the
  304 hand-written boundary cases were also run through `set_input(python value)`, and all 304 results were the same.
* **Input convention:** each case is one JSON object. A field that is absent is passed to Python as `None`, because the
  Python signature has no way to say "absent"; Rego sees it as undefined.
* **Policy versions:** Python picks the version from `t_ms` (`PDP.active_version`). Rego has no time input, so the
  harness loads the version in force at `t_ms`, computed separately from the documented rule ("latest version
  with `t_ms <= t`, else the first"). It also checks that Python reports that same version.
* **Outcome classes per case:** exact match (same allow and same reason), `REASON_MISMATCH` (same allow, different
  reason), `ALLOW_MISMATCH`, `PY_ERROR` (Python raised an exception; Rego decided), `REGO_ERROR`, and
  `VERSION_SELECTION`. `permit_by_one_side_only` counts errors as deny (fail-closed).

### Cases

* **Grid.** Every (did, aid, wid, sch, origin) combination that can be built from the policy document of
  `build("S01_normal","PBTI",1).policy_doc`. That is 24 devices × 24 assets × 4 workloads × 1 schema ×
  3 origin kinds = **6,912 per version**. The origin kinds are {`device`, `workload`} from the verifier plus
  `gateway`, which is the other origin value the document contains. The S01 document has the same devices and
  workloads as `policies/admission_policy.example.json`.
* **Five policy versions,** all made with the repository's own `World.policy_update`, a deep copy plus mutate plus
  `PolicyStore.update`. Only the scheduled policy-update events are fired; the simulation is not run.
  * v1 (t=0): S01.
  * v2 (t=150 s): `pa-c3-d06` moves from cell 3 to cell 2, using `scenarios.move_device`, the same move as in `S99_mixed`.
  * v3 (t=200 s): device `pa-c2-d03` set `active=false`.
  * v4 (t=250 s): workload cell 4 set `active=false`.
  * v5 (t=280 s): both re-activated. Its digest is identical to v2's.
  
  The grid runs on every version, giving 34,560 cases.
* **Boundary cases (304).** Unknown device, unknown workload, asset not assigned, schema not allowed, origin-kind
  mismatch (device vs gateway/legacy origin), inactive device, inactive workload, device moved (v1 vs v2),
  clock boundary of version selection (t = −1, 0, 1, and t_k−1, t_k, t_k+1 for every change, plus 10^12), missing
  fields, wrong types (int, float, bool, null, list, object), and empty strings.
* **Malformed policy document (47 cases).** This goes beyond the request. Neither implementation validates the policy
  document, so the harness checks what each one does with non-boolean `active` values, scalar strings where lists
  are expected, missing keys, an unknown `origin` requirement value, and non-object entries.

## Results (validation run, regopy 1.5.2 / rego-cpp 1.5.2, Python 3.13.18)

34,911 cases were evaluated in 192 s (niced, on a shared host). The harness SHA-256 is `61710d41…70fe`.
Every mismatch is listed in `parity_results.json` → `mismatches` (458 entries).

| case set | n | allow parity | exact (allow+reason) | reason mismatch | allow mismatch | Python exception | Rego error |
|---|---|---|---|---|---|---|---|
| grid, 5 versions | 34,560 | **34,560** | 34,286 | 274 | 0 | 0 | 0 |
| well-formed boundary categories | 189 | 189 | 127 | 62 | 0 | 0 | 0 |
| missing fields / wrong types / empty strings | 115 | 75 (+40 Python exceptions; Rego denied all) | 33 | 42 | 0 | 40 | 0 |
| malformed policy document | 47 | 12 | 7 | 5 | **27** | 8 | 0 |
| **all** | 34,911 | 34,836 | 34,453 | 383 | 27 | 48 | 0 |

Per-category counts are in `summary`, and the aggregate numbers are in `headline`.

### Findings

1. **Permit/deny parity holds on every well-formed request against a well-formed policy document.** That is
   34,749/34,749 (grid plus well-formed boundary categories), with 0 version-selection errors. The cross-version
   counts also agree: the v1→v2 move changes 6 grid decisions in both implementations, and v5 decides exactly like v2
   in both.
2. **Reason codes are not equivalent.** `admission.rego` defines reason rules only for `PERMIT`, `ASSET_NOT_ASSIGNED`
   and `PATH_NOT_AUTHORIZED`. Every other denial falls through to `default reason := "DEVICE_NOT_REGISTERED"`.
   All 383 reason mismatches have this form. The Python reasons and their counts:

   | Python reason | Rego reason | count |
   |---|---|---|
   | `ORIGIN_SIGNER_TOO_WEAK` | `DEVICE_NOT_REGISTERED` | 205 |
   | `WORKLOAD_NOT_REGISTERED` | `DEVICE_NOT_REGISTERED` | 104 |
   | `SCHEMA_NOT_ALLOWED` | `DEVICE_NOT_REGISTERED` | 45 |
   | `ORIGIN_SIGNER_INVALID` | `DEVICE_NOT_REGISTERED` | 29 |

   The verifier writes `UNAUTHORIZED:<reason>` into every evidence record. If the Rego policy replaced the Python PDP,
   those evidence reasons would change, even though no permit/deny decision changes.
3. **Malformed requests (PDP level).**
   * Rego never permitted and never raised an error.
   * Python raised `TypeError: unhashable type` in 40 cases where a field was a list or an object.
   * In 24 of those 40, the exception comes only from the memo-cache key in `PDP.evaluate`; the uncached
     `_decide` would have denied. In the other 16, the field is `did` or `wid`, and the dict lookup raises as well.
   * In the PBTI pipeline these inputs cannot reach the PDP: `envelope.pbti_parse` rejects missing, empty and
     non-string `did`/`aid`/`sch`/`wid` as `MALFORMED`, and the verifier computes `origin_kind` itself.
4. **Malformed policy document: 27 cases where only one implementation permits.** In 8 of them Rego permits and
   Python denies; in 19 Python permits and Rego denies.
   * **Non-boolean `active`** (`null`, `0`, `""`, `[]`, `{}`): Python treats these as inactive and denies. Rego
     treats them as active (only `false` fails) and **permits**. This covers 8 cases (5 device, 3 workload).
   * **`assets`, `schemas` or `relay` given as a string instead of a list:** Python's `in` becomes a substring test.
     For example, `aid="a02"` with `assets="pa-c1-a02"` is **permitted** by Python (fail-open); Rego denies.
   * **`origin` requirement not in {device, gateway}** (for example `"legacy"`, `"Gateway"`, `""`): Python falls
     through the origin checks and **permits any `origin_kind`**, including `"garbage"`. Rego denies, because
     `origin_ok` is undefined.
   * **Missing `assets`/`relay` keys, or non-object entries:** Python raises `KeyError` (2 cases) or
     `AttributeError` (6 cases), and an exception inside `ingest` is not caught. Rego denies.

   Validating the policy document against a schema, in `PolicyStore.update` or before loading it into OPA, would remove
   all of these.
5. **Interpreter caveat.** In regopy 1.5.2 a query using `with input as …` returns `undefined` for a trivial
   policy and segfaults for `admission.rego`. The harness therefore never uses `with` with regopy. The OPA batch mode
   does use `with input as`, which is standard OPA, but it was not executed here.

## Requested parity categories that are not policy-layer decisions here

The PDP decides only `(permit, reason)` as a function of `(policy version, did, aid, wid, sch, origin kind)`
(docs/PROTOCOL_SPECIFICATION.md §7; `policy.py`). The following are **verifier checks outside the PDP**
(`src/pbti/verifier.py`, `identity.py`). They were **not tested** here, and the harness does not simulate them:

* **Valid/invalid credentials.** Handled by `UNKNOWN_KEY`, `KEY_SUBJECT_MISMATCH`, `KEY_KIND_INVALID`,
  `INTEGRITY_RELAY`, `BINDING_MISMATCH` and `INTEGRITY_OBS`. Only the derived `origin_kind` reaches the PDP, and
  that is tested.
* **Expired credentials.** Handled by `KEY_NOT_YET_VALID`, `KEY_EXPIRED` (quarantine) and `KEY_IN_GRACE`.
  `rotation_grace_ms` is read from the policy document but applied by the verifier.
* **Revocation.** Handled by `REVOKED`, `REVOKED_BUFFERED` (quarantine) and taint propagation. Policy deactivation
  (`active=false`) is tested, but it is not revocation.
* **Quarantine and recovery.** The PDP returns only permit or deny. All quarantine dispositions are verifier
  dispositions: `FUTURE_TS`, `STALE_TS`, `KEY_EXPIRED`, `REVOKED_BUFFERED`, `STALE_SLOT`, `STALE_EPOCH`, `SEQ_JUMP`.
  The only recovery tested is policy-level recovery (v5).
* **Freshness and clock checks.** `skew_max_ms`, `h_max_ms`, the retry window and epoch drain are verifier checks.
  The PDP's only time dependence is version selection, and that is tested on the Python side.
* **Legacy data, unknown identity, missing fields and malformed input** are only partly PDP decisions:
  * The legacy-*device* origin rule, and unknown *did/wid*, are tested.
  * Aged legacy *data* (`STALE_TS`/`STALE_EPOCH`) and unknown *keys* (`UNKNOWN_KEY`) are verifier checks.
  * Missing or malformed fields are stopped by `pbti_parse` before the PDP. They were tested at the PDP level only.

The same list, with file and rule references, is stored in `parity_results.json` → `scope`.

## Not verified

* **No OPA.** OPA was not run, as the environment policy requires; `which opa` finds nothing. The Rego semantics come
  from rego-cpp, Microsoft's independent implementation. Where its behaviour on the constructs used here (truthiness of
  `null`/`0`, `in` on non-collections, `object.get` on non-objects, default rules) differs from OPA's, the results
  could differ under OPA.
* **The `--backend opa` code path** was exercised only up to the "no binary" stop and in dry-run mode, which writes the
  data files and the exact `opa eval` command lines.
* **The B2 baseline call** `evaluate(..., check_origin=False)` has no Rego counterpart and was not compared.
