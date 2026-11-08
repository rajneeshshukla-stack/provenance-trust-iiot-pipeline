# Validation report: admission policy parity and Docker deployment (PBTI-IIoT, released version)

* **Date:** 2026-11-04 (UTC).
* **Repository under test:** `/home/claude/PBTI_v3/01_repo_base/pbti-iiot`. It was only read, never modified.
  * Before copying, all 166 files matched `01_repo_base_SHA256.txt` (`logs/build_copy_sha256_check.log`).
  * At the end the same check passed again: 166/166 OK, no extra files, no `__pycache__` (`logs/repo_base_integrity_end.log`).
  * Nothing was written to `01_repo_v3`. Another experiment (`run_campaign.py`, 2 workers) ran there concurrently; it was not mine and was not touched.
* **Host:** 2 vCPU (shared with that experiment), 7.8 GiB RAM, glibc 2.39, Python 3.13.18. Tooling: Docker Engine 29.9.2,
  buildx 0.38.1, Docker Compose v5.6.1.
  * Every container run was capped at `--cpus=1`, and host-side Python was run under `nice`.
  * Because the host was shared, **all timings and latencies below are indicative only**.
* **Container time:** about 14 minutes of timed container work (builds plus checks), plus about 2 minutes of short probes.

## 1. What ran

| # | step | outcome | log |
|---|---|---|---|
| 1 | `pip install --break-system-packages regopy` | regopy 1.5.2 installed (rego-cpp 1.5.2) | `logs/pip_install_regopy.log` |
| 2 | `parity_test.py` (regopy back end), 34,911 cases | ran, exit 0, 192 s | `logs/parity_run_regopy.log`, `parity_results.json` |
| 3 | `parity_test.py --backend opa` | stops with BLOCKED: no `opa` binary; dry run writes the exact commands | `logs/parity_opa_backend_check.log` |
| 4 | regopy `with input as` probes | trivial query returns `undefined`; with `admission.rego` it segfaults (exit 139) | `logs/regopy_with_keyword_probe.log` |
| 5 | literal `docker build -f deploy/Dockerfile -t pbti:v2 .` (plus `--progress=plain`), clean copy | **FAILED** at step 5/6 `pip install` | `logs/build_v2_attempt1.log` |
| 6 | same Dockerfile with a one-line environment shim (CA secret mount for the pip step) → `pbti:v2-envshim` | built, 76 s | `logs/build_v2_attempt2_envshim.log`, `logs/dockerfile_v2_vs_envshim.diff` |
| 7 | checks in `pbti:v2-envshim`: env, `make test`, smoke, MQTT/TLS e2e | 70 passed; smoke `0 0`; e2e PBTI failed in run 1 of 3 (harness race) | `logs/v2envshim_*.log` |
| 8 | `docker compose -f deploy/docker-compose.yml config` (static check only, not `up`) | valid | `logs/compose_config_v2.txt` |
| 9 | `deploy/Dockerfile.v3` (hardened) → `pbti:v3` | built, 136 s | `logs/build_v3.log` |
| 10 | same checks in `pbti:v3`, plus shutdown, healthcheck, hardened runtime flags | all passed | `logs/v3_*.log` |
| 11 | `Dockerfile.v3.dockerignore` canary test (`FROM scratch` export of the context) | 5/5 canaries excluded, 166/166 repo files kept | `logs/dockerignore_canary_test.log` |

## 2. Task 1: Rego / JSON policy parity

Full details are in `README.md`; the machine-readable record is `parity_results.json` (every mismatch is listed, 458 entries).

* **Implementations compared:** Python `PDP.evaluate(did, aid, wid, sch, origin_kind, t)` and
  `data.pbti.admission.{allow,reason}`, evaluated by rego-cpp through regopy.
* **Policy history:** five versions, each derived from `build("S01_normal","PBTI",1).policy_doc`:
  * v1: S01 as built.
  * v2: `pa-c3-d06` moved from cell 3 to cell 2 with `scenarios.move_device`.
  * v3: device `pa-c2-d03` set inactive.
  * v4: workload cell 4 set inactive.
  * v5: both re-activated. Its digest is identical to v2's.
* **Results:**
  * **Grid** (6,912 combinations × 5 versions = 34,560 cases): allow/deny parity **34,560/34,560**. Exact
    (allow + reason) parity 34,286/34,560 (274 reason mismatches). 0 errors, 0 version-selection errors.
  * **Well-formed boundary cases** (189 cases: unknown device or workload, asset not assigned, schema not allowed,
    origin-kind mismatch, inactive device or workload, moved device, clock boundary of version selection):
    allow parity 189/189, exact parity 127/189.
  * **Missing fields, wrong types, empty strings** (115 cases):
    * Rego denied every case and never errored.
    * Python raised `TypeError: unhashable type` in 40 cases (list or object values). In 24 of those, the exception
      comes only from the memo-cache key.
    * There were 0 cases where only one side permitted.
    * In the verifier pipeline, these inputs are rejected earlier by `envelope.pbti_parse`.
  * **Malformed policy document** (47 cases, beyond the request): **27 cases where only one side permits.**
    * In 8, Rego permits and Python denies. These are non-boolean `active` values such as `null`, `0`, `""`.
    * In 19, Python permits and Rego denies. In 7 of them, `assets`/`schemas`/`relay` is a string, so `in` becomes a
      substring test. In 12, the `origin` requirement is not in {device, gateway}, and Python accepts any
      `origin_kind`.
    * Python also raised 8 exceptions (`KeyError`/`AttributeError`).
* **Reason codes are not equivalent.** The Rego defines reasons only for PERMIT, ASSET_NOT_ASSIGNED and
  PATH_NOT_AUTHORIZED, so every other denial falls through to the default `DEVICE_NOT_REGISTERED`. Across all 383 reason
  mismatches, the Python reasons were `ORIGIN_SIGNER_TOO_WEAK` 205, `WORKLOAD_NOT_REGISTERED` 104,
  `SCHEMA_NOT_ALLOWED` 45 and `ORIGIN_SIGNER_INVALID` 29. Swapping the PDP would change the `UNAUTHORIZED:<reason>`
  written into evidence records, but no permit/deny decision.
* **Categories that are not policy-layer decisions in this codebase** were not tested, and `README.md` and
  `parity_results.json → scope` say so explicitly:
  * Valid/invalid credentials. Only the derived origin kind reaches the PDP, and that is tested.
  * Expired credentials and rotation grace.
  * Revocation and taint.
  * Quarantine and recovery. Only policy re-activation is tested.
  * Freshness/clock checks (skew, horizon). Only the PDP's version selection by `t` is tested.
  * Partly PDP decisions: legacy *devices* and unknown *did/wid* are tested; aged legacy *data* and unknown *keys*
    are verifier checks.
* **OPA:** not run, by policy, and none is installed. The harness supports `--backend opa` (batch or per-case
  `opa eval`) but that path was **not executed**. The Rego semantics therefore rest on rego-cpp, not on OPA.

## 3. Task 2: Containers

### 3.1 Released `deploy/Dockerfile`: build

* **Literal build failed.** It failed at `RUN pip install --no-cache-dir -r requirements.txt` with
  `SSL: CERTIFICATE_VERIFY_FAILED … self-signed certificate in certificate chain`.
  * Steps 1–4 succeeded.
  * `python:3.13-slim` resolved to `sha256:ae14d4ce8771606477a81446e7ef429edd6762305fc50c84507c1041fa8285d1`
    (Python 3.13.18, Debian 13 trixie, created 2026-10-28).
  * `apt-get` installed mosquitto 2.0.21-1 and make 4.4.1-2 over plain HTTP.
  * **Cause:** the sandbox re-terminates outbound TLS with its own CA, which the base image does not trust. This is an
    environment blocker, not a defect of the Dockerfile.
* **Environment-shim build succeeded** (`deploy/Dockerfile.v2-envshim`).
  * The only change is in the pip step: `RUN --mount=type=secret,id=pipca … PIP_CERT=/run/secrets/pipca pip install …`.
    The CA is never stored in a layer.
  * Tag: `pbti:v2-envshim`. No `pbti:v2` tag was created, because the literal file did not build.
  * Image ID / manifest-list digest: `sha256:f70b7107978d10f45d954c7f809d883f12aaff499cade8dae69f26091c48a925`
    (config `sha256:db24c487fdce9d91cfbcb0109d34d437f056cef78d6d561628d212ba4f5e6fb2`).
  * Size: 770,724,272 B (771 MB unpacked; 181 MB content).
  * Layers: 9.
  * User: root.

### 3.2 Checks in `pbti:v2-envshim` (each with a timeout and `--cpus=1`)

* **`make test`:** **70 passed** in 168 s.
* **Smoke scenario** (the exact command given): prints **`0 0`**, i.e. `nonlegit_auth=0`, `legit_missing=0`.
* **MQTT/TLS e2e smoke:** `experiments/run_mqtt_e2e.py --rates 20 --reps 1 --warm 1 --measure 3 --drain 1 --out /out/...`.
  This is one rate and one repetition; the orchestrator always runs all four systems. It uses the real Mosquitto
  2.0.21 broker with mutual TLS, a per-gateway ACL, and MQTT v5 QoS 1.
  * **Run 1:** B1, B2 and B3 each delivered 80/80 (60 measured, `ACCEPT/INSERT` 80). The **PBTI verifier crashed**
    with `JSONDecodeError` reading the measurement-window file, so its row carries `FileNotFoundError` and the latency
    is `nan`.
  * **Two unchanged repeats:** all 4 systems succeeded, PBTI `ACCEPT/COMMITTED` 80/80.
  * **Diagnosis:** a race in the harness. The publisher writes the window file with a non-atomic
    `Path.write_text`, while the verifier polls `exists()` and then reads it. The fix is to write to a temporary file
    and `os.replace` it, or to retry on `JSONDecodeError`. The released `results/raw/mqtt_e2e.jsonl` has no error rows.
* **`docker stop`** of the default CMD (`make` as PID 1, no init) took 0.23 s, exit code 2. The log shows
  `make: *** [Makefile:25: test] Terminated`: make exited on SIGTERM and pytest was terminated, so no stop delay was
  observed.
* **Healthcheck:** none (`no-healthcheck`).

### 3.3 Inspection of `deploy/Dockerfile` and `deploy/docker-compose.yml`

* **Base image pinning.** The Dockerfile uses the tag `python:3.13-slim`, which floats across patch releases and
  Debian refreshes. It is not pinned by digest.
* **Dependency pinning.**
  * Debian packages are unpinned.
  * `requirements.txt` pins the 9 top-level packages with `==` but has **no hashes and no transitive pins**. At build
    time, 14 transitive packages were resolved: cffi 2.1.1, contourpy 1.4.0, cycler 0.12.1, fonttools 4.68.0,
    iniconfig 2.3.1, kiwisolver 1.5.1, packaging 26.3, pillow 13.0.0, pluggy 1.7.0, pycparser 3.12, Pygments 2.21.0,
    pyparsing 3.3.3, python-dateutil 4.0.0, tzdata 2026.6.
  * `pyproject.toml` declares looser ranges such as `cryptography>=42`.
  * All pinned versions exist on PyPI with cp313 wheels.
* **Non-root execution.** None: there is no `USER`, so everything runs as root, and the bind-mounted `results/` on the
  host ends up root-owned.
* **Secrets handling.** No secrets are baked in, and none is needed.
  * The e2e harness generates a throw-away TLS PKI under `/tmp` at run time. Its private keys are unencrypted and
    deliberately `chmod 0644` so that a root-started Mosquitto that drops privileges can read them. That is acceptable
    for a sandbox, but they are world-readable inside the container.
  * Device and gateway signing keys are derived deterministically from the seed, by design.
  * **There is no `.dockerignore`**, so `COPY . .` would copy anything that happens to be in the checkout (local
    `.env`, keys, caches, `.git`). The clean copy held exactly 166 files.
* **Health checks.** None in the Dockerfile or in compose.
* **Startup/shutdown.**
  * There is no ENTRYPOINT. The CMD `make test campaign perf e2e analysis` is a multi-hour batch job, and `make` runs
    as PID 1.
  * SIGTERM shutdown worked in the test (0.23 s).
  * Not tested: zombie reaping of orphaned e2e subprocesses (broker, verifier, publisher) when `make` is PID 1.
  * Compose sets no `init`, `user` or resource limits.
* **Broker connectivity.**
  * No external broker; compose has no broker service and publishes no ports.
  * The e2e harness starts its own Mosquitto on `127.0.0.1:8883` inside the container. That path was verified by the
    e2e smoke (see the race above).
  * `deploy/mosquitto/*.template` claim to be used by `run_mqtt_e2e.py`, but nothing references them. The harness
    writes an equivalent config inline.
* **Data persistence.**
  * Compose bind-mounts `../results` onto `/opt/pbti/results`, which is the **repository's own `results/`**. A
    `make campaign` run opens the `results/raw/<campaign>.jsonl` files with mode `w` and so **overwrites the published
    raw results**.
  * `make analysis` writes `paper/generated` and `paper/figures`. These are not mounted, so they are lost with the
    container.
  * The e2e SQLite databases are temporary by design.
* **Reproducibility.**
  * A floating base tag, unpinned apt packages and unpinned transitive dependencies mean that a later rebuild can
    produce a different image.
  * There is no hash verification, and no `SOURCE_DATE_EPOCH` or other image-level provenance.
  * Run manifests do record the source-tree SHA-256 and the package versions, which is good.
  * The header comments of both files say they were never executed. Section 3.1 shows that they do work once the pip
    TLS environment issue is bypassed.

### 3.4 Hardened `deploy/Dockerfile.v3`, in this folder only

Design:

* **Base image:** `python:3.13.18-slim-trixie@sha256:ae14d4ce…85d1`. This is the digest both `3.13-slim` and
  `3.13.18-slim-trixie` resolved to (`logs/base_image_digest_inspect.txt`).
* **apt pins:** `mosquitto=2.0.21-1`, `make=4.4.1-2`, `tini=0.19.0-3+b8`.
* **Python dependencies:** `requirements.lock.txt` holds all 23 resolved packages with 843 SHA-256 hashes, covering
  every file PyPI lists. It was generated by `scripts/make_lock.py`, which asserts that the 9 top-level pins equal
  `requirements.txt`. The install uses `pip install --require-hashes --no-deps --only-binary=:all:` followed by
  `pip check`.
* **Ownership and user:** the code is root-owned and read-only for the runtime user. Only `results/` and
  `paper/{generated,figures}` are writable. The runtime user is `USER 10001:10001`.
* **Health, startup and shutdown:** a `HEALTHCHECK` imports `pbti`, paho and cryptography and checks for the
  `mosquitto` binary. The entrypoint is `ENTRYPOINT ["/usr/bin/tini","-g","--"]` with `STOPSIGNAL SIGTERM`. The CMD is
  the same as in the released Dockerfile.
* **Other:** OCI labels. The image contains no secrets. The optional `pipca` secret mount (`required=false`) exists only
  for TLS-intercepting networks.
* **Ignore file:** `Dockerfile.v3.dockerignore` mirrors `.gitignore` and adds common secret-file patterns. The canary
  test confirmed that none of these patterns excludes a repository file.

Results:

* **Build:** succeeded in 136 s with `--build-context pbti_deploy=<this deploy dir>` and
  `--secret id=pipca,src=/root/.ccr/ca-bundle.crt`.
  * `pbti:v3` digest: `sha256:93d2ed9f2ce4f190b1ac83080d110f3776d84073a2dcb6fc25c0759cacbf110d`.
  * Size: 768,668,378 B (769 MB unpacked; 181 MB content). Layers: 11.
  * User: `10001:10001`.
* **Installed packages:** the `pip freeze` output is identical to `pbti:v2-envshim`.
* **Source tree:** `/opt/pbti` holds the 166 released files with matching SHA-256 in both images. In v3 the runtime
  user cannot write the code tree, but can write `results/` and `paper/generated`.
* **Checks** (each with a timeout and `--cpus=1`):
  * `make test` as uid 10001: **70 passed** in 141 s.
  * Smoke: **`0 0`**.
  * e2e smoke: **all 4 systems passed**, 80/80 messages each (PBTI `ACCEPT/COMMITTED` 80). p50 latency was
    1.3–2.3 ms at 20 msg/s, which is indicative only.
  * `docker stop`: 0.26 s, exit 143 (SIGTERM forwarded by tini to the process group).
  * Healthcheck (with a 5 s interval override): `starting` → `healthy`.
* **Extra hardened-runtime check:** `--read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges`.
  The smoke run printed `0 0`, and the e2e smoke passed for all 4 systems, which means non-root Mosquitto works with
  no capabilities and a read-only root filesystem.

### 3.5 Recommendations not implemented (no hardened compose file was written)

* Do not bind-mount the repository's `results/` directory. Mount a separate output directory, or pass `--out`.
* Run as `user: "<uid>:<gid>"` matching the host directory.
* Add `init: true` (or use v3's tini), CPU limits that match `WORKERS`, and `read_only: true` with a tmpfs for `/tmp`
  and volumes for the output directories.
* For bit-for-bit apt reproducibility, use `snapshot.debian.org`.
* Fix the e2e window-file race described in 3.2.

## 4. What remains unverified

* **OPA:** not run, so Rego semantics are those of rego-cpp 1.5.2. The `--backend opa` code path was never executed
  against a real binary.
* **Containers:** only short runs were made. The full container CMD (`campaign`, `perf`, the full `e2e`,
  `analysis`) and `make paper` were **not** run. The e2e smoke used 20 msg/s for 3 s and is not a performance
  measurement. Timings come from a CPU-contended host.
* **Literal pbti:v2:** the literal released Dockerfile never built in this environment. The environment-shim image
  differs from it by one line in the pip step.
* **docker-compose.yml:** validated statically (`config`) only; `docker compose up` was not run.
* **Not tested:**
  * zombie reaping without an init process
  * arm64 builds; the lock contains hashes for all platforms, but only linux/amd64 was built
  * apt pin longevity on the Debian mirror
  * bit-for-bit image reproducibility
  * the MQTT harness under higher rates or more repetitions
* **Verifier-side parity categories** (credentials, expiry, revocation, quarantine, freshness) were not tested. They are
  outside the PDP; see section 2.

## 5. Files (all under `/home/claude/PBTI_v3/02_work/policy_container/`)

* **Parity (Task 1):** `parity_test.py`, `parity_results.json`, `README.md`.
* **Container artifacts:**
  * `deploy/Dockerfile.v3`, `deploy/Dockerfile.v3.dockerignore`, `deploy/requirements.lock.txt`
  * `deploy/Dockerfile.v2-envshim`
* **Scripts:** `scripts/run_container_checks.sh`, `scripts/extra_container_checks.sh`, `scripts/make_lock.py`.
* **Logs (`logs/`):**
  * build logs, `*_image_inspect.json`, `*_image_history.txt`
  * check logs: `v2envshim_*`, `v3_*`, including the `hardened_*`, `shutdown`, `healthcheck` and `e2e_repeat*` runs
  * parity and regopy logs, integrity checks
* **Container outputs:** `container_out/*/mqtt_e2e_smoke.jsonl` and `*.manifest.json`.
* **Build context:** `build/pbti-iiot` (verified clean copy).
* **Scratch:** `scratch/` (regopy probes, the OPA dry-run files, the dockerignore test).
* **Docker images left in the local daemon:** `pbti:v2-envshim`, `pbti:v3`, and the base `python@sha256:ae14d4ce…`.
