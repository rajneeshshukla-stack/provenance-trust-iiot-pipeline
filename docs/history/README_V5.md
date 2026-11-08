# PBTI-IIoT — Provenance-Bound Trust-Aware Ingestion for Industrial IoT edge-to-cloud pipelines (V5)

Reference implementation, baselines, reproducible evaluation testbed, raw results and manuscript sources for the
article *"Provenance-Bound Trust-Aware Ingestion for Industrial IoT Edge-to-Cloud Pipelines: Per-Identity Conflict
Containment and Its Security–Availability Trade-offs"* (manuscript prepared for submission to *Future Internet*, MDPI;
V5 release of the V4 revision; V3 title: *"Provenance-Bound Trust-Aware Ingestion: Data-Level Zero Trust and Resilience
for Industrial IoT Edge-to-Cloud Data Pipelines"*).
Authors: Rajneesh Shukla and Punit Gupta.

**V4 additions (released as V5 with the combined title and a V3-style opening).** Matched review schedules for B5 and PBTI-R (deferring rule, minimum case age and cadence, event-driven
review; `src/pbti/review.py`, `src/pbti/sim.py`), a transition tracer with time-dependent outcomes
(`src/pbti/temporal.py`), selective evidence-gated holds PBTI-SH (`src/pbti/selective.py`), release-evidence policies
with a testbed time witness (`src/pbti/verifier.py`, `src/pbti/timewitness.py`), the locality proof of Rule L and
extended bounded checks (`formal/LOCALITY_PROOF.md`, `formal/v4_locality_lifecycle_check.py`), preregistered campaigns
(`experiments/run_v4.py`, `experiments/v4_configs/`) and their analysis (`analysis/analyze_v4.py`,
`analysis/validate_v4_stats.py`). Records: `research/V4/` (preregistration and amendment with hashes, decision log,
deviations, crosswalk, change log). Reproduction: `make all-v4`, or the V4 reproduction guide of the package
(`06_Reproducibility/REPRODUCTION_GUIDE_V4.md`). V4 results: `results/v4/`; the V2/V3 results are unchanged.

**V3 additions.** A preregistered literature-informed feed-level baseline (B5, `src/pbti/b5.py`; B5s without recovery;
PBTI-R = PBTI with the same automated reviewer), a signed quarantine review-and-release workflow (`src/pbti/review.py`),
an 11-factor stressor sweep and a 2^(7-3) factorial (`src/pbti/sweep.py`), a replay of the public SKAB test-bed telemetry
(`src/pbti/dataset.py`; data not redistributed), batching and signature-worker measurements, 30-repetition MQTT/TLS
latency, Rego policy parity, a hardened container, ProVerif models and Rule L bounded checks (`formal/`). Start with
`research/V3/REPRODUCTION_GUIDE.md`; the V3 change log, issue matrix and validation report are in `research/V3/`. The
layout below is the revision-2 core; V3 files are listed in `research/V3/PACKAGE_CONTENTS.md`.

PBTI extends Zero-Trust decisions from sessions to individual industrial data objects:

* every observation carries an **observation statement** signed by the device (or by the edge workload for legacy devices)
  with a deterministic event identity `(device, boot epoch, sequence)` and a hash link to its predecessor;
* the relaying edge workload adds a **relay statement** binding its SPIFFE-style workload identity to exactly one signed
  observation, so identity crosses an untrusted broker;
* a cloud **verifier** admits each event under a versioned path-bound policy and the credential lifecycle (rotation grace,
  revocation with compromise window), classifies its delivery history with **Rule L** (slot state is a pure function of the
  admitted evidence set), commits it to content-addressed storage, records Merkle-checkpointed evidence, and maintains
  lineage that supports **taint propagation** after retroactive revocation;
* an independent **auditor** re-verifies raw objects, evidence, lineage, and replays every admission decision.

> Scope: PBTI provides verifiable evidence about identity, integrity, authorization, provenance and processing history
> within its threat model. It does **not** establish that a measurement is physically correct.

## Repository layout

```
src/pbti/            reference implementation
  canonical.py         RFC 8785 JSON canonicalization (tested against RFC 8785 Appendix B vectors)
  crypto.py            Ed25519 / SHA-256 with domain separation
  identity.py          X.509 CA, device and SPIFFE-style workload certificates, rotation, revocation (t_rev, t_comp)
  policy.py            versioned path-bound admission policy and PDP
  envelope.py          wire formats for PBTI and the baselines
  registry.py          event registry, Rule L slots, epochs, gaps
  verifier.py          PBTI admission pipeline (+ ablation switches A1-A12)
  evidence.py          RFC 9162 Merkle trees, signed chained checkpoints, witness
  processor.py         event-time windows, current-value table, lineage, corrections
  baselines.py         B1 conventional, B2 Zero-Trust access-controlled, B3 provenance-focused,
                       B4 strongest combination of existing techniques (revision 2)
  sim.py               deterministic virtual-time testbed (devices, gateways, durable buffers, faulty network)
  attacks.py           attack rendering per wire format using only held keys
  scenarios.py         experiment scenarios E1-E15 and the mixed ablation workload
  oracle.py            ground-truth metrics
  audit.py             independent auditor and insider-tampering classes T1-T7
  realtime.py          shared set-up for wall-clock experiments
experiments/         campaign runner, in-process throughput, MQTT/mTLS end-to-end harness
scripts/             macro gate, submission gate, non-legitimate attribution, reference verification, manuscript export,
                     release packaging, sample data, and the shell chains used to run the measurements
tools/texstubs/      local LaTeX build stub (bbm.sty) for systems without texlive-fonts-extra; not part of the submission
config/              where every parameter lives (scenario, testbed, verifier, policy, campaign matrices)
analysis/            statistics, figures, generated LaTeX tables and macros
results/raw/         per-run JSON lines + manifests (hardware, versions, source digest, parameters)
results/summary/     aggregated JSON summaries
tests/               70 unit, property and invariant tests
policies/            example admission policy (JSON) and a Rego formulation of it (never executed or tested for equivalence)
data/sample/         samples of the synthetic workload, of each wire format, and a PROV-JSON lineage example
deploy/              Mosquitto configuration template and container files (not executed in this study)
docs/                protocol specification, state machine, threat model, baselines, experiment plan
research/            evidence matrix, closest prior work, novelty assessment, reference verification,
                     reviewer stress test, open research items, results template, literature records
paper/               MDPI LaTeX manuscript, supplementary materials, figures, bibliography
```

## Quick start

```bash
python3 -m pip install -r requirements.txt      # Python >= 3.11
make test                                        # 70 tests
python3 -c "import sys; sys.path.insert(0,'src'); from pbti.scenarios import build; from pbti.oracle import evaluate; \
w=build('S05_stolen_key','PBTI',1); w.run(); print({k:v for k,v in evaluate(w).items() if not k.startswith('rx[')})"
```

## Reproducing the paper

```bash
make campaign     # ~2.5 h on 2 cores: 1,500 scenario, 340 ablation, 320 revocation and 70 audit runs
make attribution  # per-label attribution of non-legitimate authoritative observations (~25 min)
make perf         # in-process throughput and device scaling
make e2e          # needs the 'mosquitto' binary (Ubuntu: apt-get install mosquitto)
make analysis     # statistics, figures, paper/generated/*.tex
make check        # every \R... macro used in the paper must be generated from results
make paper        # paper/main.pdf and paper/supplementary.pdf (TeX Live + latexmk + cm-super)
make final        # submission gate: tests, macros, page limits, LaTeX logs, citations
```

Virtual-time runs are fully determined by the seed and the source digest recorded in each manifest; wall-clock
results depend on hardware. **Authors must re-run `make all` on their own hardware before submission.**

## Results at a glance
See `paper/main.pdf` (Section 4) and `results/summary/`. All numbers in the manuscript are produced by
`analysis/analyze.py` from `results/raw/*.jsonl`.

## Limitations
Single-host testbed with synthetic telemetry; Python implementation; baselines are approximations of common practice;
no formal proof; constrained devices and multi-host deployments not measured. See `research/OPEN_RESEARCH_ITEMS.md`.

## License and citation
Code: Apache License 2.0 (`LICENSE`). Please cite the article (see `CITATION.cff`) once published.
The MDPI LaTeX class in `paper/Definitions/` is provided by MDPI for manuscript preparation only.
