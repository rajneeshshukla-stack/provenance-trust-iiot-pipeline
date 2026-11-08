# Unified threat and failure model

## 1. Protected assets
Industrial observations (payload), event identity `(did, ep, seq)`, source timestamps and sequence
information, provenance links (`prev`, relay binding), raw committed observations, admission policy and its
history, credentials (device, workload, verifier evidence key), lineage, derived datasets and current-value
state, and audit evidence (receipt log, evidence log, checkpoints).

## 2. Trusted computing base (minimum)
* Ed25519/SHA-256 implementations; RFC 8785 canonicalizer.
* Plant root CA and the revocation publication path (integrity, not necessarily timeliness).
* The verifier process at decision time, its clock, and its evidence key (until compromise scenario T5).
* Policy history integrity (signed or administratively protected).
* At least one witness that stores checkpoint copies outside the verifier's administrative domain.
* For signing-capable devices: non-extractable key storage (except in explicit key-compromise scenarios).

### 2a. Device-to-gateway link (V3, made explicit)

The claim that a stolen device key alone cannot get a forged observation admitted (relay statement, E5) assumes that
the attacker cannot write into the gateway's device-side input: the device-to-gateway link is an authenticated
fieldbus or device session, or physically protected. The ProVerif variant `formal/pbti_variant_otlink_attacker.pv`
shows that without this assumption the device key alone suffices, because the honest gateway countersigns whatever
arrives on that link (results/formal/proverif_output.txt). Gateways in deployments that cannot meet the assumption
should authenticate the device session before relaying, which the reference gateway does not model.

## 3. Untrusted or potentially compromised components
Messaging layer (broker/Kafka), network, edge gateways and their workloads, individual devices, cloud
storage administrators (insiders without the verifier key; with the key in T5), downstream processing jobs.

## 4. Attacker positions and capabilities (as implemented in `src/pbti/attacks.py`, `scenarios.py`)

| Id | Position | Capability | Scenarios |
|---|---|---|---|
| AP1 | BROKER (on-path) | read, modify without keys, inject, drop, delay, replay; claim any publisher identity towards the subscriber | E2, E3, E6, E15 |
| AP2 | unknown producer | own keys/credentials not registered | E4 |
| AP3 | stolen device key `K_dev` | sign observation statements for one device; inject at BROKER | E5, E14, ABL |
| AP4 | compromised edge workload `K_gw` | sign relay statements and gateway-attested observations; suppress, delay, replay its own traffic; forge for other cells (lateral) | E4, E15 |
| AP3+AP4 | `K_dev` + authorized `K_gw` | equivocation (front/back-running), gap-fill, full impersonation, back/future dating | E5, E14, ABL |
| AP5 | compromised device (valid key, wrong measurements) | — | out of detection scope (stated) |
| AP6 | cloud insider without verifier key | modify/delete raw, evidence, derived, registry state | E16 T1–T4, T6, T7 |
| AP6' | insider with verifier evidence key | rewrite and re-sign evidence | E16 T5 |
| AP7 | policy abuse | modify policy | partially (A2 static policy; history integrity assumed) |

## 5. Distributed-system failure classes
Transport duplicates/redelivery, acknowledgement loss → retransmission, message loss, reordering, long delay,
link partition with store-and-forward, gateway restart (unpersisted acknowledgements, OT-side resend),
device reboot (epoch change), clock freeze/backward step, device sequence-reuse bug, credential rotation
during disconnection, buffering beyond the admission horizon.

## 6. Observational equivalence (why one model is needed)

| Externally observed | Benign cause(s) | Malicious cause(s) | Distinguishable by content? | PBTI treatment |
|---|---|---|---|---|
| identical message twice | retry, redelivery, restart resend | exact replay | **No** (byte-identical) | DUPLICATE either way; class by context only; no state change |
| same identity, different content | sequence-reuse bug, non-canonical re-encoding (prevented by JCS) | equivocation with stolen key | No | CONTESTED (safe), producer flagged |
| missing sequence numbers | loss, suppression by failure | suppression by compromised relay | No | gap evidence (open gaps), LOST after horizon |
| very old observation | long disconnection | back-dated forgery, stale replay | No | QUARANTINE beyond horizon (archived; releasable only through signed review, see the correction note at the end) |
| observation from unexpected path | device re-cabled, policy lag | lateral movement | No | REJECT unless policy updated (dynamic policy) |
| out-of-order arrival | network reordering, backlog drain | delay attack | No | state independent of delivery order for a fixed admitted evidence set (Rule L, event-time windows) |

## 7. Outcome taxonomy
Prevention (never authoritative), Detection (classified/flagged; may have been authoritative transiently),
Containment (removed from derived data after detection, e.g., contest or taint), Recovery (legitimate data
eventually committed), Evidence (re-verifiable record exists).

## 8. Excluded threats (and why)
Breaking Ed25519/SHA-256; compromise of the root CA and all witnesses; manipulation of the physical process or
of a sensor before signing (authenticity ≠ truthfulness); safety/actuation paths; hardware supply chain and
side channels; denial of service by flooding (rejected receipts are still logged — a storage DoS vector noted
as a limitation); confidentiality and privacy of telemetry.

> **Correction (V7, 5 November 2026).** Earlier copies of this document said that quarantine release was "not implemented". That was true when the text was first written and stopped being true when the signed review-and-release workflow was added (`src/pbti/review.py`, `src/pbti/verifier.py`; transitions in `docs/STATE_MACHINE.md`, rows 8', 11 and the LOST/ABSENT release rows). Quarantined observations are archived and can be released only through a signed decision by an authorized reviewer, which re-runs admission with only the case's quarantine reason waived. The PBTI arm of the main evaluation runs without a reviewer, so in that stage quarantined data stay archived; the PBTI-R arms and the B5 comparators run with the automated reviewer. Only the phrase was corrected; no result, configuration or code changed.
