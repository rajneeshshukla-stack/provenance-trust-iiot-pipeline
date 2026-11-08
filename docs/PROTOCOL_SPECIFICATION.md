# PBTI — Provenance-Bound Trust-Aware Ingestion: Protocol Specification (v1, research prototype)

Status: research specification matching the reference implementation in `src/pbti/` (source digest recorded
in every `results/raw/*.manifest.json`). Name and version are provisional.

## 1. Purpose, scope and non-goals

PBTI defines how an industrial observation is admitted into an enterprise/cloud data platform so that the
platform can later *prove*, for every authoritative raw observation and every derived analytical record:

1. which producer signed the observation (device, or edge workload for legacy devices);
2. which edge workload relayed it, and that this relay path was authorized for the device and asset;
3. that the protected content was not modified after signing;
4. which admission decision was taken, under which policy version and credential status;
5. how the event's delivery history was classified (new, retry, suspected replay, conflict, late, recovered,
   stale), and that repeated or reordered delivery could not create, overwrite or remove authoritative state;
6. which derived records depend on it, and how they were corrected when it was contested or tainted.

**Non-goals.** PBTI does not establish that a measurement is physically *true*: an authenticated device can be
faulty, physically manipulated, or compromised before signing. PBTI does not provide confidentiality (TLS or
payload encryption are orthogonal), safety-function protection, intrusion detection, or availability against
flooding. It introduces no new cryptographic primitive and has no formal cryptographic proof (Section 13).

## 2. Entities, trust roots and keys

| Entity | Key material | Role |
|---|---|---|
| Plant root CA (identity authority) | Ed25519 CA key (offline in deployment) | Issues X.509 device certificates (`urn:pbti:device:<did>` URI SAN) and short-lived workload certificates (X.509-SVID-style `spiffe://<trust-domain>/<path>` URI SAN); publishes revocations with effective time `t_rev` and optional compromise time `t_comp`. |
| Signing-capable device `d` | Ed25519 device key `k_d` (secure element/TPM in deployment) | Origin signer of observation statements. |
| Legacy device | none | Cannot sign; the relaying edge workload becomes the *gateway-attested* origin signer. |
| Edge workload `w` (collector on gateway `g`) | Ed25519 workload key `k_w` (short-lived, rotated) | Relay signer; for legacy devices also origin signer; maintains the durable buffer. |
| Messaging layer (MQTT broker or Kafka) | transport TLS only | **Untrusted for integrity** in the PBTI threat model; may drop, duplicate, delay, reorder, inject or replay. |
| Ingestion verifier `V` | Ed25519 evidence key `k_V` | PEP for data objects; maintains registry, raw store, quarantine, evidence log. |
| PDP / policy store | — (policy history append-only, integrity assumed or signed by policy admin) | Evaluates the path-bound admission policy. |
| Witness | stores copies of signed checkpoints | External anchor outside the verifier's administrative domain. |
| Auditor | public keys, policy history, trust history | Offline verification and decision re-execution. |

Key identifiers (`kid`, `wkid`) select certificates; certificates are chain-validated at first use and cached.
Revocation status is refreshed every `status_refresh_ms` (0 = per event).

## 3. Wire format

A PBTI message is the RFC 8785 canonical JSON object `{ "obs", "osig", "rel", "rsig" }` (max 4096 bytes).

### 3.1 Observation statement `obs` (signed by origin signer)

`osig = Ed25519(k_origin, "PBTI-v1/observation\x00" || JCS(obs))`

| Field | Type | Purpose | Security property | Correctness property | Threat addressed |
|---|---|---|---|---|---|
| `v` | int (=1) | protocol version | prevents version confusion | parser selection | downgrade/misparse |
| `typ` | `"pbti.obs"` | statement type | domain separation (with signature domain) | — | cross-protocol reuse |
| `did` | string | producer identity | binds key subject to producer | partitioning of event identity | impersonation via key substitution |
| `aid` | string | asset scope | authorization scope (device→asset) | attribution of data to asset | metadata tampering, mis-attribution |
| `ep` | int ≥ 0 | boot/session epoch | — | distinguishes sequence resets after reboot | false conflicts after legitimate reboot; stale-epoch injection |
| `seq` | int ≥ 0 | sequence within epoch | replay/gap evidence | **deterministic event identity** `(did, ep, seq)`; gap detection | duplicates, gap-fill, suppression |
| `ts` | int (ms) | source event time | freshness bounds (not proof of time against a key holder) | event-time windowing | back/future-dating (bounded by horizon) |
| `sch` | string | schema id/version | policy may restrict schema per asset | correct decoding | schema confusion |
| `pl` | object | measurements | integrity | payload | tampering |
| `prev` | b64u(SHA-256) or null | digest of the previous statement in the same epoch (null iff `seq = 0`) | fork / gap-fill evidence | offline stream-completeness audit | gap-fill forgery, history rewriting |
| `kid` | string | origin key reference | key binding (no key substitution) | rotation support | key confusion |

Privacy: `did`, `aid`, `ts` and payload may reveal operational patterns; confidentiality is out of scope
(use TLS/payload encryption; signatures are computed over plaintext canonical form).

### 3.2 Relay statement `rel` (signed by relaying edge workload)

`rsig = Ed25519(k_w, "PBTI-v1/relay\x00" || JCS(rel))`,  `odig = b64u(SHA-256(JCS(obs) || osig))`

| Field | Purpose | Security property |
|---|---|---|
| `v`, `typ` (`"pbti.relay"`) | version, domain separation | as above |
| `wid` | relaying workload identity (SPIFFE ID) | path binding: identity reaches the verifier *through* the broker |
| `wkid` | workload key reference | key binding, rotation |
| `odig` | binds exactly one signed observation (content **and** signature) | prevents re-binding a relay statement to another observation |
| `rts` | relay (buffer-in) time, gateway clock | evidence only; not used for authorization |
| `mode` | `live` or `buffered` | classification only (RECOVERED annotation; revoked+buffered → quarantine). A forged `buffered` flag can only move a receipt from REJECT to QUARANTINE, never into authoritative state. |

The relay statement is signed once when the observation enters the durable buffer, so retransmissions are
byte-identical (deterministic Ed25519, canonical serialization).

### 3.3 Canonicalization assumptions

RFC 8785 JCS: object keys sorted by UTF-16 code units (the prototype restricts keys to ASCII), ECMAScript
number serialization (verified against all RFC 8785 Appendix B vectors in `tests/test_canonical.py`),
integers within ±2^53, no NaN/Infinity. Benign re-encoding (key order, whitespace, `5.0` vs `5`) therefore
yields identical digests and cannot produce false conflicts. The content digest is
`cd = SHA-256(JCS(obs))` (excludes the signature, so the same content re-signed under a rotated key would be
a *conflict*; devices sign each observation exactly once).

## 4. Edge procedures

* **Device (signing-capable):** on each observation, `seq ← seq + 1`; on boot, `ep ← ep + 1`, `seq ← 0`,
  `prev ← null` (persistent boot counter assumed). Signs `obs`, keeps a short local history for
  at-least-once delivery to the gateway.
* **Edge workload:** for a signing device, wraps the received `(obs, osig)`; for a legacy device, assigns
  `(ep, seq, prev)` itself in an epoch namespace unique to the workload (`ep = 1000·g + boot_g`) and signs
  `obs` with `k_w`. Appends the wire bytes to a **durable buffer**; transmits when connected; retransmits
  unacknowledged entries after `RTO`; drains backlogs under a rate limit; on restart reloads the buffer and
  resends entries whose acknowledgement was not yet persisted (duplicates are expected and harmless).
* **Workload credentials** are short-lived and renewed; buffered entries keep the key valid at buffer-in
  time (rotation grace, Section 6).

## 5. Verifier admission algorithm (Algorithm 1)

Input: wire bytes `m`, verifier time `t`. Output: one disposition and one evidence record.
Checks are applied in this order; the first failing check determines the disposition.

```
ADMIT(m, t):
  advance ticks to t                                 # gap closure, taint application, checkpoints
  (obs, osig, rel, rsig) ← PARSE(m)                  else REJECT MALFORMED
  K_o ← key(obs.kid);  K_w ← key(rel.wkid)           else REJECT UNKNOWN_KEY
  require K_w.kind = workload ∧ K_w.subject = rel.wid           else REJECT KEY_SUBJECT_MISMATCH
  origin ← device   if K_o.kind = device   ∧ K_o.subject = obs.did
           workload if K_o.kind = workload ∧ K_o.subject = rel.wid  else REJECT KEY_SUBJECT_MISMATCH
  VERIFY(K_w, rsig, rel)                              else REJECT INTEGRITY_RELAY
  rel.odig = H(JCS(obs) || osig)                      else REJECT BINDING_MISMATCH
  VERIFY(K_o, osig, obs)                              else REJECT INTEGRITY_OBS
  for K in {K_o, K_w}:
     if revoked(K, t):  if REVOKED_BUFFERED ∈ waive ∧ RELEASE_EVIDENCE_OK(obs, K, revocation(K)):
                            annotate RELEASED_PRE_COMPROMISE        # authorized release only (Section 6)
                        else QUARANTINE REVOKED_BUFFERED if rel.mode = buffered ∧ policy says so
                        else REJECT REVOKED
     if t < K.nbf:      REJECT KEY_NOT_YET_VALID
     if t > K.exp:      annotate KEY_IN_GRACE if t − K.exp ≤ grace else QUARANTINE KEY_EXPIRED
  (permit, reason, pv) ← PDP(obs.did, obs.aid, rel.wid, obs.sch, origin, t)
  permit                                              else REJECT UNAUTHORIZED:reason
  obs.ts ≤ t + skew_max                               else QUARANTINE FUTURE_TS
  t − obs.ts ≤ h_max                                  else QUARANTINE STALE_TS
  return HISTORY(obs, rel, t)                         # Section 5.1
```

### 5.1 Delivery-history classification (Rule L)

Event identity `e = (did, ep, seq)`; content digest `cd`. Each slot keeps `versions` (admitted digests) and
`implied` (digests asserted for this slot by successors' `prev`). Slot state is a pure function of that
evidence: ABSENT (no version), COMMITTED (exactly one distinct digest), CONTESTED (≥ 2 distinct digests),
LOST (gap closed after `gap_close_ms`).

```
HISTORY(obs, rel, t):
  s ← slot(e)
  if cd ∈ s.versions:
       DUPLICATE RETRY            if s COMMITTED ∧ same relay workload ∧ t − s.t_first ≤ retry_window
       DUPLICATE SUSPECTED_REPLAY otherwise                       # no state change in either case
  if e lies in a closed (LOST) gap:                 QUARANTINE STALE_SLOT
  if ep < max_ep(did) ∧ t − open_time(max_ep) > epoch_drain:   QUARANTINE STALE_EPOCH
  if seq > hw(did, ep) + max_seq_jump:              QUARANTINE SEQ_JUMP
  add cd to s.versions;  if seq > 0: add obs.prev to slot(did, ep, seq−1).implied
  if state(s) = COMMITTED:  ACCEPT (annotations: IN_ORDER | AHEAD | LATE ; LIVE | RECOVERED)
                            → raw commit, derived processing
  else:                     CONFLICT (EQUIVOCATION | LINK_MISMATCH); evidence kept in quarantine
  any slot whose state changes COMMITTED → CONTESTED is removed from derived processing
```

Consequences (tested): exact retransmissions never change state (I3); two validly signed contents for one
identity are never silently resolved (I4); a forged statement inserted into a gap is contested as soon as the
successor's `prev` is known; the final state depends only on the *set* of admitted evidence (I9).
Retry and replay are byte-identical, so their classification depends on context only and **cannot affect
authoritative state** — safety does not rely on distinguishing them.

## 6. Credential lifecycle

* **Rotation:** an expired but unrevoked key is accepted for `rotation_grace_ms` after expiry (buffered data
  signed before expiry), otherwise quarantined (KEY_EXPIRED; not a releasable reason for the automated reviewer).
* **Revocation (REV-1):** after the verifier observes a revocation of key `K`, no statement signed or relayed
  under `K` is admitted by *ordinary* admission; buffered statements may be quarantined (REVOKED_BUFFERED) instead
  of rejected. An authorized reviewer may release such a case; the re-run admission waives REVOKED_BUFFERED only if
  `RELEASE_EVIDENCE_OK` holds: policy `none` (never), `discretionary` (V3 default and all reported campaigns:
  `obs.ts < t_comp`; a self-asserted timestamp, i.e. a policy condition and not evidence of pre-compromise
  existence), or `witness` (a token from a time-stamping witness outside the verifier for the exact statement digest
  with witness time + clock uncertainty < `t_low`, the earliest plausible compromise time; `src/pbti/timewitness.py`).
* **Revised records (V4, D05):** a key stays revoked from its first revocation; a revised record can only make
  `t_comp` earlier (conservative merge) and is reported to the verifier again, which re-runs the taint selector.
* **Retroactive containment (REV-2):** if the revocation carries `t_comp`, every COMMITTED slot whose origin
  key is `K` and whose verifier commit time is `≥ t_comp` is flagged TAINTED (raw bytes untouched), removed
  from derived processing and recomputed (TAINT_CORRECTION). Device-signed observations merely *relayed*
  by a compromised workload are not tainted: the relay cannot alter them (taint precision). A slot committed by an
  authorized REVOKED_BUFFERED release is exempt from this selector only while `RELEASE_EVIDENCE_OK` still holds
  under the current revocation record (V4, D05); a revision that invalidates it taints the slot.
* **Review release (V3):** a release re-runs ADMIT with only the case's quarantine reason waived; every other check
  applies, including Rule L. If the re-run returns CONFLICT, the version is recorded as evidence (the slot is or
  becomes CONTESTED) and the case is closed as RELEASE_FAILED; nothing becomes authoritative.

## 7. Policy model

Versioned JSON document (append-only history; each evidence record stores `pv`):
`devices[did] = {assets, origin ∈ {device, gateway}, schemas, active}`,
`workloads[wid] = {relay: [did], active}`, and parameters (Section 12). The PDP decision is a pure function
of `(policy version, did, aid, wid, sch, origin kind)`; it is memoized per version.

## 8. Commitment and evidence

* **Raw store:** content-addressed (`SHA-256(wire)`) write-once blobs; accepted statements in namespace
  `raw`, all other receipts in `q` (quarantine/forensic archive).
* **Evidence log:** one canonical record per receipt `{rid, t, w, tid, kid, wkid, eid, cd, pv, disp, why,
  ann, ns}`; leaf `SHA-256(0x00‖record)`; batches of ≤ 512 records (and at least every 5 s) form an
  RFC 9162 Merkle tree; checkpoint `{n, first, count, root, prev, t}` signed with `k_V`, chained by `prev`,
  copied to the witness.
* **Receipt log:** `(t, wire digest, transport id)` per receipt; with the blob store it is the replayable input
  from which an auditor re-derives every decision and the registry (decision determinism, I10).

## 9. Derived processing and lineage

Event-time tumbling windows (10 s) per asset with count/mean/min/max per metric, and a current-value table
ordered by `(ep, seq)`. Every derived version stores its sorted input references and their Merkle root,
and a cause (NEW, LATE_CORRECTION, CONTEST_CORRECTION, TAINT_CORRECTION). Earlier versions are retained.
An optional W3C PROV export maps: raw observation → `prov:Entity`; device/workload → `prov:Agent`
(`prov:actedOnBehalfOf` for relay); admission and aggregation → `prov:Activity`; derived record
`prov:wasDerivedFrom` raw observations. PBTI-specific semantics with no PROV equivalent: disposition,
contest/taint status, policy version, credential status at admission.

## 10. Audit procedure

A-RAW, A-EVID, A-REG, A-DET, A-LIN as implemented in `src/pbti/audit.py` (see STATE_MACHINE.md for the
invariants they check).

## 11. Transport mapping

MQTT v5 (QoS 1; topic `pbti/<gateway>/<did>`; broker mTLS and ACLs remain as defence in depth but are not
trusted for data-object decisions). Kafka: one record per message; Kafka's idempotent producer suppresses
broker-level retries but does not provide end-to-end origin binding; PBTI identity remains authoritative.

## 12. Parameters (defaults)

| Parameter | Default | Meaning |
|---|---|---|
| `skew_max_ms` | 5 000 | tolerated source-clock lead |
| `h_max_ms` | 3 600 000 | admission horizon (buffering age) |
| `retry_window_ms` | 30 000 | duplicate within window via same path ⇒ RETRY |
| `rotation_grace_ms` | 3 600 000 | grace for expired, unrevoked keys |
| `max_seq_jump` | 100 000 | sequence jump quarantined above high-water mark |
| `epoch_drain_ms` | 3 600 000 | older epoch accepted after a newer epoch opened |
| `gap_close_ms` | 3 600 000 | open gaps declared LOST |
| `on_revoked_buffered` | quarantine | or reject |
| checkpoint batch | 512 records / 5 s | evidence batching |
| `status_refresh_ms` | 0 | revocation status propagation delay |

## 13. Security assumptions and limitations

Ed25519 and SHA-256 are assumed secure; the root CA and at least one witness are uncompromised; private keys
are not extractable except in explicitly modelled compromise scenarios; the verifier clock is trusted for
horizon and taint decisions; policy history integrity is assumed. A holder of *both* a device key and its
authorized relay key can impersonate that device completely (no equivocation ⇒ nothing to detect) until
revocation; REV-2 then bounds the damage to the declared compromise window. Gateway-attested (legacy) data
is only as trustworthy as the edge workload. No formal proof is provided; properties are stated as testable
invariants and evaluated experimentally.
