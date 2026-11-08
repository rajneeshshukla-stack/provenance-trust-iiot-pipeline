# Baseline-claims register (revision 2 -> V3)

Created 3 November 2026, before any V3 change to code, results or manuscript. Source of truth: the V2 bundle
(`v2_bundle_as_received.zip`, SHA-256 0971a0a3...; inner Final Package SHA-256 7fe053ce..., byte-identical to the
package delivered at the end of revision 2). Repository baseline: `01_repo_base/pbti-iiot` (166 files, hashes in
`01_repo_base_SHA256.txt`). Source-tree digest of the code that produced the revision-2 B4 results: 7a711eb8...

Every claim below is preserved in V3 unless new evidence contradicts it; any change is recorded in the V3 change log
with the code change or experiment that caused it.

| # | Claim in revision 2 (manuscript location) | Evidence in V2 | Status carried into V3 |
|---|---|---|---|
| C01 | Session-level Zero Trust does not reach individual data objects in brokered IIoT pipelines (Introduction) | literature (NIST SP 800-207/207A, MQTT single-hop guarantees) | preserved |
| C02 | Transport/session trust is distinguished from trust in individual data objects (Sections 1-3) | design | preserved |
| C03 | Rule L: slot state is a function of admitted versions and successor-implied digests; order independence holds for a fixed admitted evidence set only; admission itself depends on time, policy version, freshness and revocation (Section 3.3, Table S4/I9) | permutation unit test (60 permutations), design argument | preserved; V3 adds separate admission-determinism and state-determinism tests |
| C04 | Paired seeds (common random numbers), Wilcoxon signed-rank, Holm per scenario and globally, rank-biserial effects, identical pairs reported as identical (Section 3.7) | analysis/analyze.py | preserved |
| C05 | Independent audit of every PBTI run (A-RAW, A-EVID, A-REG, A-DET, A-LIN); 300/300 runs passed | results/raw/scenarios*.jsonl | preserved |
| C06 | In the 15 scenarios, no tampered, replayed, unauthorized, equivocated or gap-filled observation remained authoritative in PBTI (Abstract, 4.1) | scenarios*.jsonl, attribution JSON | preserved |
| C07 | Undetected: impersonation with device+relay keys (E5: 150/run), gateway forgery of legacy data (E15: 15.8/run), gap-fill with lost successor (mixed: 0.15/run) | attribution JSON | preserved (negative results) |
| C08 | Revocation with a compromise time removed all affected commits (E14: PBTI 0 non-legitimate) at the cost of more legitimate loss (270.1 vs 190.2 for B4) | scenarios, revocation sweep | preserved |
| C09 | B4 (mainstream combination) matched PBTI in 11 of 14 attack/fault scenarios; differed in E5, E8, E14; equal losses in E11b | scenarios_part3_b4.jsonl | preserved; V3 adds B5 |
| C10 | Legitimate-data costs: contested equivocations withhold the genuine reading (E5 222.6 vs 198.8 for B1); sequence reuse loses more than B4 (12 vs 4, E8); conservative taint (E14) | scenarios | preserved |
| C11 | Quarantine beyond the horizon is an archive; no release workflow implemented (E11b) | src/pbti/verifier.py | to be superseded only if a release workflow is implemented and tested in V3 |
| C12 | LOST state implemented but never exercised (1 h gap-closure horizon) | src, results | to be superseded only if exercised by tests and experiments in V3 |
| C13 | Verifier throughput 0.19x of B2 (2,067 vs 10,707 msg/s, single core, durable group commit); messages 2.91x; persisted bytes 1.35x; edge signing 291 us/msg on x86 | throughput.jsonl | preserved; V3 adds batching/worker measurements |
| C14 | MQTT/TLS on two shared vCPUs: PBTI saturated first among four measured pipelines at 1,500 msg/s; p99 differences not significant with 5 repetitions | mqtt_e2e.jsonl | preserved; V3 repeats with >= 30 repetitions where feasible |
| C15 | Insider tampering: seven classes detected by the independent auditor (Table 5) | audit.jsonl | preserved |
| C16 | Ablations on the mixed workload (12 mechanisms; Table S9) | ablations*.jsonl | preserved |
| C17 | Trust assumptions: trusted verifier clock, roots of trust, reliable epoch counters, witness outside the verifier's control; authenticated data is not necessarily physically correct | design | preserved and analysed further in V3 |
| C18 | Standards mapping is alignment, not compliance; no conformance testing | Table S13 | preserved |
| C19 | Contribution: integration of mechanisms with published analogues plus one narrow refinement (Rule L) and a joint evaluation; no 'first' claims | Table 1, literature audit | preserved or reduced further depending on B5 |
| C20 | Evaluation is a single-host simulation with synthetic telemetry (4 gateways, 24 devices, 1 Hz, 300 s) | design | preserved; any new dataset replay is labelled precisely |
| C21 | Rego policy and container files were never executed | repo | to be superseded only by actual execution in V3 |
| C22 | 70 unit and invariant tests pass | pytest | preserved; V3 adds tests |
