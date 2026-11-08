# Experiment plan (as executed)

All experiments are executable with the commands in `Makefile`. Scenario code: `src/pbti/scenarios.py`; runners:
`experiments/run_campaign.py`, `experiments/run_throughput.py`, `experiments/run_mqtt_e2e.py`; analysis:
`analysis/analyze.py`. Hypotheses are directional expectations stated *before* execution; they were not used as targets,
and outcomes contradicting them are reported (e.g., E8).

## Common design

* **Independent variable:** pipeline ∈ {B1, B2, B3, PBTI} (ablation study: PBTI variant ∈ {full, A1…A12}).
* **Controlled variables:** topology (4 gateways × 6 devices, 1 legacy per gateway), 1 Hz, 300 s + 180 s drain,
  network base delay 20 ms + Exp(10 ms) jitter, RTO 2 s, drain 60 msg/s, verifier parameters (PROTOCOL_SPECIFICATION §12),
  shared storage/processor/policy code.
* **Pairing:** common random numbers — separate RNG streams for production, network, attacker decisions and
  system-specific rendering; seed *s* gives identical schedules for every pipeline.
* **Oracle:** `src/pbti/oracle.py` (ground truth from the generator; definitions in its docstring).
* **Pipelines:** B1-B3 and PBTI; revision 2 adds B4, the strongest combination of existing techniques (docs/BASELINES.md),
  run on all 15 scenarios and the mixed workload with the same 20 seeds (`scenarios_part3_b4.jsonl`, `ablations_part3_b4.jsonl`).
* **Repetitions:** 20 seeds per scenario × pipeline (1,200 runs for B1-B3/PBTI plus 300 for B4; seeds 1–10 in `scenarios.jsonl`, 11–20 in `scenarios_part2.jsonl`; increased from 10 so that Holm correction across all scenarios of a metric is attainable); 20 seeds per ablation configuration (seeds 11–20 in `ablations_part2.jsonl`); 20 seeds × 4 refresh
  intervals for the E14 sweep (seeds 11–20 in `revocation_part2.jsonl`); 5 seeds × 7 tamper classes × {B3, PBTI} for E16; wall-clock: 10 repetitions (in-process), 5 repetitions × 4
  loads (MQTT).
* **Statistics:** mean, SD, 95 % percentile bootstrap CI (10,000 resamples, fixed seed); paired Wilcoxon signed-rank
  (PBTI vs each baseline per scenario; Holm within metric family; matched-pairs rank-biserial effect size); identical
  outcomes in all seeds reported descriptively; wall-clock: Kruskal–Wallis, pairwise Mann–Whitney (Holm), Cliff's δ,
  Shapiro–Wilk reported.
* **Validity concerns (all experiments):** single host; synthetic telemetry; Python implementation; baselines are
  approximations of practice; attack renderings are ours.

## Per-experiment specification

| Exp. | RQ | Hypothesis (directional) | Injection | Primary dependent variables | Expected PBTI behaviour (oracle) | Expected baseline behaviour |
|---|---|---|---|---|---|---|
| E1 normal | RQ3 | all pipelines correct; PBTI slower | none | correctness counts; cost | 0 missing, 0 dup, 0 non-legit | same correctness |
| E2 payload tamper | RQ2 | PBTI/B3 reject, B1/B2 admit | broker modifies 5 % payloads (no keys) | nonlegit_auth, legit_missing, win_corrupt | REJECT BINDING_MISMATCH; 0 non-legit; tampered originals lost (broker acked) | B1/B2 admit; B3 rejects |
| E3 metadata tamper | RQ2 | B2 partially protected by policy/freshness | 2 % each: asset, ts, seq/mid | same | 0 non-legit | B1 admits all; B2 rejects asset, some ts |
| E4 unauthorized | RQ2 | path binding needed against lateral forgery | 100 unknown-producer + 100 lateral forgeries via gw2 | nonlegit_auth | REJECT UNKNOWN_KEY / INTEGRITY_OBS / UNAUTHORIZED | B1 admits lateral; B3 admits legacy lateral |
| E5 stolen key | RQ2 | relay binding stops broker injection; contest stops equivocation and gap-fill (gap-fill only if the genuine successor arrives); impersonation undetectable | broker injection with device key (100); equivocation 10 %, gap-fill 10 %, impersonation from 150 s | nonlegit_auth by label; contested slots; legit_missing | 0 non-legit except impersonation stream | all admit |
| E6 replay | RQ2 | exact replays harmless everywhere; refreshed replays only harmful without signatures | exact 5 %, refreshed 3 %, delays 5–150 s | nonlegit_auth, cv_wrong_rate; RETRY vs SUSPECTED_REPLAY counts | DUPLICATE (no state change); refreshed REJECT | B1/B2 admit refreshed |
| E7 duplicates | RQ2 | all handle benign duplicates | redelivery 10 %, ack loss 10 %, loss 2 % | dup_auth, legit_missing | 0 dup | 0 dup |
| E8 seq-reuse bug | RQ2 | PBTI pays an availability cost | sequence counter not advanced (2 devices × 2) | legit_missing | contest of reused and preceding slot (negative result) | unaffected |
| E9 reordering | RQ2 | event-time processing correct everywhere | 30 % delayed ≤ 3 s | win_exact, cv_wrong_rate | exact | exact |
| E10 late + clock | RQ2 | business keys break under clock faults | 2 % delayed 30–90 s; freeze 5 s; step −30 s | legit_missing, cv_wrong_rate | 0 missing | merged observations, transient CV errors |
| E11/E12 recovery | RQ2 | all recover with durable buffers; PBTI rarely labels recovery traffic as replay | 120 s partition, reboot, gateway restart, ack loss 5 % | legit_missing, dup_auth, SUSPECTED_REPLAY on legit (metric) | 0/0; label rate reported | 0/0 |
| E11b beyond horizon | RQ2/RQ3 | horizon trades availability for freshness | 150 s partition, h_max 120 s | legit_missing, legit_quarantined | QUARANTINE (archived; releasable only through signed review, see the correction note at the end) | B2 rejects; B1/B3 accept |
| E13 rotation | RQ2 | grace prevents rotation loss | 90 s SVIDs renewed every 60 s; device rotation during 120 s partition | legit_missing | 0 (KEY_IN_GRACE) | B3 rejects expired-key data |
| E14 revocation | RQ2 | only PBTI removes pre-revocation forgeries | impersonation + legacy forgery 120–200 s; revocation at 200 s (t_comp 120 s); rekey 205 s; continued attacks; Δ ∈ {0, 1, 5, 30} s | post-revocation admissions; nonlegit_auth; taint count; legit_missing | 0 post-revocation (Δ=0); 0 non-legit; taint over-approximation | B1 admits post-revocation; B2/B3 keep pre-revocation forgeries |
| E15 edge compromise | RQ2 | device signatures stop gateway forgery of signing devices | forgeries for own devices, 5 % suppression, replays | nonlegit_auth by label, gaps_open | REJECT INTEGRITY_OBS for signing devices; legacy forgery admitted (limitation) | B1/B2 admit all forgeries |
| E16 insider | RQ2 | evidence log + witness detect all classes | T1–T7 after E5 runs | audit detection | all detected (T5 via witness) | B3: T1–T3 only |
| ABL | RQ1/RQ3 | each mechanism removes a specific failure | mixed workload | all correctness metrics; µs/msg | full PBTI minimal | — |
| E17 throughput | RQ3 | PBTI throughput lower (≈2 Ed25519 verifications) | 20,000 msgs closed loop, SQLite group commit | msg/s, service p50/p99, CPU, bytes | measured | measured |
| E18 device scaling | RQ3 | throughput roughly independent of device count | 10–2,000 devices | msg/s, p99 | measured | measured |
| E-MQTT | RQ3 | similar median latency at low load (batching wait); PBTI expected to saturate first (observed: only PBTI saturated at 1500 msg/s) | Mosquitto mTLS, QoS 1, 200–1500 msg/s | latency p50/p95/p99, achieved throughput, CPU | measured | measured |

## Metric definitions
See `src/pbti/oracle.py` (docstring) and the manuscript, Section 3.7.

## Not executed (planned extensions)
Multi-host deployment; Kafka transport; constrained-device signing cost; OPC UA source; HAI dataset replay; OPA-based PDP
equivalence test; long-duration (hours) runs with gap closure; formal model checking of Rule L.

> **Correction (V7, 5 November 2026).** Earlier copies of this document said that quarantine release was "not implemented". That was true when the text was first written and stopped being true when the signed review-and-release workflow was added (`src/pbti/review.py`, `src/pbti/verifier.py`; transitions in `docs/STATE_MACHINE.md`, rows 8', 11 and the LOST/ABSENT release rows). Quarantined observations are archived and can be released only through a signed decision by an authorized reviewer, which re-runs admission with only the case's quarantine reason waived. The PBTI arm of the main evaluation runs without a reviewer, so in that stage quarantined data stay archived; the PBTI-R arms and the B5 comparators run with the automated reviewer. Only the phrase was corrected; no result, configuration or code changed.
