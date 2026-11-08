# PBTI: symbolic (ProVerif) and bounded-exhaustive (Rule L) evidence

> V3 final run: the Rule L bounded check was re-run on the final source (verifier.py e41e26cf…, policy.py a578f211…;
> log `results/formal/rule_l_bounded_check_final.log`). The first run, on a pre-final verifier.py (7ddffbfe…) while other
> files were still being edited, is kept in `results/formal/superseded/rule_l_bounded_check_pre_final_source.log`.

This folder holds formal-methods evidence for the PBTI admission protocol. There are two parts:

1. **Symbolic model checked with ProVerif 2.05.** These are authentication and agreement properties of the
   cryptographic layer (device signature, relay countersignature, key-subject binding, path policy). They hold in
   the Dolev-Yao model, for unbounded sessions, with adaptive key compromise.
2. **Bounded-exhaustive check of Rule L on the reference implementation.** The delivery-history classification
   (`src/pbti/registry.py`, `PBTIVerifier._history`) is checked over every admitted set and every arrival order
   within a stated bound. Part of this runs on the unmodified `PBTIVerifier` with real Ed25519 signatures.

Neither part is a proof about the deployed system. Section 6 lists exactly what was and was not established.
Nothing under `01_repo_v3` or `01_repo_base` was modified.

## 0. Files

| File | Content |
|---|---|
| `pbti.pv` | main symbolic model **M-A**: authentic device→workload (OT) link, adaptive compromise of any device or workload key |
| `pbti_variant_nocompromise.pv` | **M-C**: M-A without compromise, with relay fields fixed; witnesses pure replay |
| `pbti_variant_otlink_attacker.pv` | **M-B**: M-A with an attacker-controlled OT link (and a relay that checks the device signature) |
| `run_proverif.sh` | regenerates `proverif_output.txt` |
| `proverif_output.txt` | provenance header, all `RESULT` lines, then the full unedited ProVerif output of the three models |
| `proverif_install.log` | how ProVerif was installed (apt → opam → opam cache mirror) |
| `rule_l_bounded_check.py` | the Rule L bounded checker |
| `rule_l_bounded_check_final.log` (in `results/formal/`) | its full log on the final source, ending with a JSON summary (the first run is in `results/formal/superseded/`) |

Sources read (read-only): `docs/PROTOCOL_SPECIFICATION.md`, `docs/THREAT_MODEL.md`, `docs/STATE_MACHINE.md`, and
`src/pbti/{envelope,verifier,registry,crypto,canonical,identity,policy,sim,attacks}.py`, plus the tests
`tests/test_evidence_and_envelope.py` and `tests/test_registry_rules.py`.

**Code version caveat.** Other V3 work edited `01_repo_v3/src/pbti` while this work ran. `verifier.py` changed at
least twice: it gained a quarantine-release `waive` path and V3 LOST marking. `policy.py` and other files changed
during the Rule L run (Section 5.6).
- The Rule L run records SHA-256 digests of every source file at start and end.
- The `_history` Rule L core is identical in revision 2 (`01_repo_base`) and V3. The only differences are the
  `waive` guards, and those are inactive with an empty `waive`.
- `rule_l_bounded_check.py` disables bytecode writing (`sys.dont_write_bytecode`). The repository's git-ignored
  `__pycache__` was being refreshed by concurrent jobs. I cannot exclude that one of my early interactive imports
  refreshed a `.pyc` file there; no source file was touched.

## 1. Principals, keys and trust assumptions

| Principal | Key | Signs | Certified as (`certs` table / X.509 in code) | Trusted for |
|---|---|---|---|---|
| Signing device D (`did`) | `skD` (Ed25519) | `osig = Sig(skD, "PBTI-v1/observation\0" ‖ JCS(obs))` | kind `device`, subject `did` (`urn:pbti:device:<did>`) | nothing beyond its key; content truthfulness is out of scope |
| Legacy device | none | — | — (policy origin `gateway`) | nothing (its readings are unauthenticated) |
| Edge workload W (`wid`, SPIFFE ID) | `skW` | `rsig = Sig(skW, "PBTI-v1/relay\0" ‖ JCS(rel))`; for legacy devices also `osig` | kind `workload`, subject `wid` | relaying; origin of gateway-attested data |
| Broker / network | — | — | — | **nothing** (attacker) |
| Verifier V | (`k_V` evidence key, not modelled) | — | — | correct execution of Algorithm 1 |
| CA / identity plane | CA key | certificates | — | **integrity**: certificates only for genuine (kid, kind, subject, pk) bindings |
| Policy store / PDP | — | — | — | **integrity** of the path policy (`did` may be relayed by `wid`; origin kind of `did`) |

Assumptions used by the symbolic model, all stated in the `pbti.pv` header:

- Ed25519 is an ideal signature scheme. SHA-256 is a free one-way, collision-free function.
- `JCS(·)` with a domain prefix is an injective, disjoint encoding per statement type. This is justified because the
  domain strings are prefix-free and NUL-terminated, canonical JSON never contains a raw NUL byte, and `osig` has a
  fixed length of 64 bytes, so `JCS(obs)‖osig` is uniquely decodable.
- Certificate chain validation is replaced by a trusted table.
- **M-A only:** the D→W link is authentic. The attacker reads everything D sends but cannot inject into W's input.
  This matches the simulator: `sim.py` hands device items to `_gw_accept` directly, and attacks inject at the broker.

## 2. Message formats (code → model)

| Code (`src/pbti/envelope.py`) | Model |
|---|---|
| `obs = {v, typ, did, aid, ep, seq, ts, sch, pl, prev, kid}` | `obsT(did, body, kid)`. `v`/`typ` are the constructor; `body` abstracts `aid, ep, seq, ts, sch, pl, prev` |
| `osig = Ed25519(k, DOMAIN_OBS ‖ JCS(obs))` | `sign(dobs(obs), k)` |
| `odig = b64u(SHA-256(JCS(obs) ‖ osig))` | `h(obs, osig)` |
| `rel = {v, typ, wid, wkid, odig, rts, mode}` | `relT(wid, wkid, odig, extra)`. `extra` abstracts `rts, mode` |
| `rsig = Ed25519(k_w, DOMAIN_REL ‖ JCS(rel))` | `sign(drel(rel), skW)` |
| wire `{obs, osig, rel, rsig}` | 4-tuple on the public channel `c` |

The verifier process follows `PBTIVerifier.ingest` in this order:
1. Resolve `wkid` (workload kind, subject = `rel.wid`).
2. Verify `rsig`.
3. Check `odig = h(obs, osig)`.
4. Resolve `kid`.
5. Verify `osig`.
6. Branch on the origin key kind:
   - **Device branch:** kind `device`, subject `obs.did`, and some policy entry `(did, wid, ·)`.
   - **Gateway branch:** kind `workload`, subject `rel.wid`, and a policy entry `(did, wid, gateway)`.

The model omits these checks: freshness, `nbf`/`exp`/grace, revocation, the asset and schema rules of the PDP, and
the Rule L history. Each omitted check only *rejects* receipts, so dropping it over-approximates acceptance. That is
sound for the correspondence (authentication) queries below. It is not sound for anything that depends on V's state
or on time.

## 3. Adversary and compromise rules (symbolic model)

- **Dolev-Yao attacker on the broker channel `c`.** It can read, drop, delay, reorder, replay, inject, and compute
  with any public function. It can claim any `wid` or `did`, and it chooses every device content (`body`) and every
  relay field (`extra`). Making the honest device sign environment-chosen contents strengthens the attacker, so
  every concrete device behaviour is covered.
- **Unbounded topology.** Any number of cells (one workload each), signing devices per cell, legacy devices per
  cell, and parallel verifier sessions.
- **Adaptive compromise.** For every device and every workload, a process may at any time emit
  `DevKeyLeaked(did)` / `RelayKeyLeaked(wid)` and publish the private key. Leaked keys are never revoked.
- **Policy.** The attacker may add arbitrary extra relay authorizations `(did, w2, device)` for signing devices
  (event `RelayAuthorized`). So the results do not depend on how many relays a device is authorized for. The
  attacker cannot change a device's origin kind and cannot create certificates.
- **M-B only:** the attacker also writes to W's input (an unauthenticated OT link). W there is *stricter* than the
  implementation, because it verifies `osig` against the device certificate before countersigning. The
  implementation does no such check (`sim.py` `_wrap`).

## 4. Safety properties and ProVerif results

ProVerif 2.05 ran on all three models, taking 0.03–0.15 s each. `true` means proved for the model, for unbounded
sessions. `false` means an attack trace was reconstructed. `cannot be proved` is inconclusive.
`event(A) ==> event(B)` means that in every trace, each execution of A is preceded by an execution of B.

### 4.1 Main model M-A (`pbti.pv`)

| Id | Query | Expected | Result |
|---|---|---|---|
| N1 | `not event(VerifierAccepted(did,wid,o))` (non-vacuity) | reachable | **false** (honest acceptance reachable) |
| N2 | `not event(VerifierAcceptedGw(did,wid,o))` (non-vacuity, legacy) | reachable | **false** (reachable) |
| Q1 | `VerifierAccepted(did,wid,o) ==> DeviceSigned(did,o) ∨ DevKeyLeaked(did)` | true | **true** |
| Q1-any | `VerifierAcceptedAny(did,wid,o) ==> DeviceSigned(did,o) ∨ DevKeyLeaked(did) ∨ LegacyDevice(did,wid)` (covers the gateway branch too) | true | **true** |
| Q2 | `VerifierAccepted(did,wid,o) ==> RelayCountersigned(wid,h(o,s)) ∨ RelayKeyLeaked(wid)` (`s` existential) | true | **true** |
| Q2-exact | `VerifierAcceptedSig(did,wid,o,s) ==> RelayCountersigned(wid,h(o,s)) ∨ RelayKeyLeaked(wid)` (the accepted `osig`) | true | **true** |
| Q2-rel | `VerifierAcceptedRel(wid,r) ==> RelaySigned(wid,r) ∨ RelayKeyLeaked(wid)` (agreement on `rts`, `mode`) | true | **true** |
| Q3 | `VerifierAccepted(did,wid,o) ==> DeviceSigned(did,o) ∨ (DevKeyLeaked(did) ∧ RelayKeyLeaked(wid))` | true | **true** |
| Q3-any | as Q3 for either branch, `∨ LegacyDevice(did,wid)` | true | **true** |
| Q3-relay | `VerifierAccepted(did,wid,o) ==> DeviceSigned(did,o) ∨ RelayKeyLeaked(wid)` | true | **true** |
| Q4 | `VerifierAccepted(did,wid,o) ==> DeviceSigned(did,o)` | false (attack) | **false** |
| Q5 | `inj-event(VerifierAccepted(did,wid,o)) ==> inj-event(DeviceSigned(did,o))` | false | **false** (already non-injectively false by Q4) |
| Q5-replay | `inj VerifierAccepted ==> inj DeviceSigned ∨ DevKeyLeaked(did) ∨ RelayKeyLeaked(wid)` | false (replay) | **cannot be proved** (see below) |
| Q6 | `VerifierAcceptedGw(did,wid,o) ==> GatewayAttested(wid,o) ∨ RelayKeyLeaked(wid)` | true | **true** |
| Q6-policy | `VerifierAcceptedGw(did,wid,o) ==> LegacyDevice(did,wid)` | true | **true** |
| Q6-attack | `VerifierAcceptedGw(did,wid,o) ==> GatewayAttested(wid,o)` | false (attack) | **false** |
| Q7 | `VerifierAccepted(did,wid,o) ==> SigningDevice(did,wid) ∨ RelayAuthorized(did,wid)` (path authorization) | true | **true** |

**Q4 attack trace** (`proverif_output.txt`, M-A section):
1. The attacker obtains `skW` of `wid_6` (`RelayKeyLeaked(wid_6)`) and `skD` of `did_5` (`DevKeyLeaked(did_5)`).
2. It adds the relay authorization `(did_5, wid_6)`.
3. It builds `obsT(did_5, a_3, kidD)` with an arbitrary `body` and signs it with `skD`.
4. It builds and signs the relay statement for `wid_6` with `skW`.
5. V executes `VerifierAccepted(did_5, wid_6, obsT(did_5,a_3,kidD))`, although no `DeviceSigned` event occurred.

The trace uses both leaks, as Q3 requires of any such attack. ProVerif happened to pick a cross-cell relay; the trace
for the device's own cell was not generated separately.

**Q5-replay.** ProVerif found derivations but could not reconstruct a trace. Its candidate derivations either made W
countersign one OT message twice, which is not executable, or used leaked keys, which does not falsify this query.
A confirmed pure-replay trace was obtained in M-C instead (Section 4.2). Every M-C trace is also an M-A trace: in
M-A the attacker can supply the constant `ext0` as the relay input and never trigger a leak. Therefore the M-C trace
also falsifies Q5-replay in M-A. **This trace-inclusion step is my argument, not a ProVerif output.**

**Q6-attack trace.** Only `RelayKeyLeaked(wid_6)` occurs. The attacker signs a legacy observation for `didL_3` with
`skW` and V accepts it through the gateway branch. This is the documented residual risk for gateway-attested data
(spec Section 13; experiment E15).

### 4.2 Variant M-C, no compromise (`pbti_variant_nocompromise.pv`)

| Id | Query | Result |
|---|---|---|
| C0 | `not event(VerifierAccepted(...))` | **false** (reachable) |
| C1 | `VerifierAccepted(did,wid,o) ==> DeviceSigned(did,o)` | **true** |
| C2 | `VerifierAcceptedSig(did,wid,o,s) ==> RelayCountersigned(wid,h(o,s))` | **true** |
| C3 | `VerifierAcceptedAny(did,wid,o) ==> DeviceSigned(did,o) ∨ LegacyDevice(did,wid)` | **true** |
| C5 | `inj-event(VerifierAccepted(did,wid,o)) ==> inj-event(DeviceSigned(did,o))` | **false**: pure replay |

The C5 trace contains one `DeviceSigned(did_4, o)` and one relay countersignature. The attacker delivers the same
4-tuple to two verifier sessions, producing two `VerifierAccepted(did_4, wid_5, o)` events and no leak events.
Replay is therefore **not** prevented by the cryptographic layer.

### 4.3 Variant M-B, attacker-controlled OT link (`pbti_variant_otlink_attacker.pv`)

| Id | Result | Meaning |
|---|---|---|
| N1, N2 | false (reachable) | non-vacuity |
| Q1, Q1-any, Q2, Q2-exact, Q2-rel, Q6, Q6-policy, Q7 | **true** | V's own checks do not depend on the OT link |
| Q3, Q3-any, **Q3-relay** | **false** | the trace has only `DevKeyLeaked(did_6)`. The honest W checks the (validly forged) device signature and countersigns, and V accepts. **The device key alone suffices** |
| Q4, Q5, Q6-attack | false | as expected |
| Q5-replay | **false** | no leaks. The attacker feeds one device-signed statement to two honest, authorized relays (`wid_9`, `wid_7`), and V accepts it twice |

**Consequence.** The "both keys are needed" claim (spec Section 13, threat-model row AP3+AP4) holds only if the
attacker cannot inject into the workload's device-side input. The repository documents do not state this assumption
explicitly. A relay that checks the device signature, as M-B's relay does, does not restore the claim.

### 4.4 Authentication and agreement claims (what the results mean)

In M-A, for a signing-capable device:

- **V agrees with D on `(did, obs)`, non-injectively, unless `did`'s key leaked before acceptance** (Q1). This
  includes key binding: the key of another device, or a workload key, cannot be used for `did` (Q1-any).
- **V agrees with W on `(wid, odig)`, hence on the exact pair `(obs, osig)`, and on the whole relay statement
  including `rts` and `mode`, unless `wid`'s key leaked** (Q2, Q2-exact, Q2-rel). So a relay statement cannot be
  re-bound to another observation, and a broker cannot set `mode = buffered` without the relay key.
- **Every accepted `(did, wid)` path is authorized by the policy** (Q7).
- **Accepting an observation D never signed requires both D's key and the key of the relaying, authorized W**
  (Q3, Q3-relay).
- **No injective agreement and no freshness.** These are absent by design (Q5, C5). PBTI delegates idempotency to
  Rule L (Section 5).
- **For legacy devices,** V agrees with W on the attested content unless W's key leaked (Q6). W's key alone is
  enough to forge (Q6-attack). Only devices declared legacy for that `wid` can be accepted through the gateway branch
  (Q6-policy).

### 4.5 Replay and compromise behaviour

- **Replay.** At the cryptographic layer, replay always succeeds (C5). In the implementation the replayed statement
  has the same content digest, so Rule L classifies it as `DUPLICATE` (`RETRY` or `SUSPECTED_REPLAY` by context)
  and no state changes (S4, Section 5). One exception: a byte-identical retransmission of a statement that was
  previously *quarantined* is not a duplicate and can be admitted later (Section 5.5, D2).
- **Device key only.** No forgery is accepted in M-A (Q3-relay). In M-B the device key alone is sufficient.
- **Relay key only.** The attacker cannot forge device content (Q1). It can re-countersign device-signed statements,
  choose `rts` and `mode`, and forge everything for legacy devices relayed by that W (Q6-attack).
- **Both keys.** The attacker can fully impersonate the device (Q4). Rule L detects this only if the forgery
  contradicts admitted genuine evidence (S3 and the residual risk in Section 5.4).
- **Not modelled:** revocation (REV-1), compromise-window taint (REV-2), rotation and grace.

### 4.6 Liveness

**No liveness property was proved, and none was attempted.** ProVerif correspondence queries are safety properties.
Availability claims, such as the recovery invariant I8 (every buffered observation is eventually committed exactly
once) or "the genuine successor eventually arrives", depend on unproven assumptions:
- eventual delivery and fair scheduling by the broker;
- a durable, non-overflowing edge buffer;
- arrival within `h_max` and within the clock skew;
- no permanent partition;
- a verifier that eventually processes every receipt.

The non-vacuity queries show only that acceptance is *possible*.

## 5. Rule L bounded check (`rule_l_bounded_check.py`)

### 5.1 What is checked

Rule L as specified (PROTOCOL_SPECIFICATION.md 5.1; STATE_MACHINE.md M2) works per event identity `(did, ep, seq)`:
- `versions` holds the digests of admitted statements.
- `implied` holds the `prev` digests asserted by admitted successors.
- The slot is ABSENT if there is no version. It is COMMITTED if `versions ∪ implied` has exactly one digest, and
  CONTESTED if it has two or more.

In the implementation, a statement is *admitted* when `_history` reaches `slot.versions[cd] = …`. Its disposition
is then ACCEPT or CONFLICT. DUPLICATE, QUARANTINE and REJECT receipts add nothing.

| Id | Property |
|---|---|
| S0 | after every arrival sequence the implementation's slot states and committed digests equal Rule L evaluated on the admitted set (an independent oracle written from the spec text) |
| S1 | all permutations of the same admitted set give identical final states and committed digests, also across feeds |
| S2 | CONTESTED is absorbing; a slot with a version never returns to ABSENT; a COMMITTED slot never changes its digest. Checked along every arrival path and over the inclusion lattice (every explored pair A ⊂ A∪{c}) |
| S3a | ≥ 2 distinct admitted contents for one slot ⇒ CONTESTED |
| S3b | an admitted alternative `F_k` together with the admitted genuine successor `G_{k+1}` ⇒ CONTESTED |
| S3b' | gap-fill proper: `F_k` admitted, `G_k` withheld, `G_{k+1}` admitted ⇒ CONTESTED |
| S3c | an alternative is authoritative (COMMITTED) only if neither `G_k` nor `G_{k+1}` was admitted |
| S4 | re-delivering an admitted statement yields DUPLICATE and leaves the registry snapshot unchanged (versions, implied, state, `t_first`, epochs/hw/gaps) |

S4 is checked at every node. A duplicate therefore changes nothing at any position, so the following deliveries
behave as if it never happened. By induction, the S0–S3 results extend to every interleaving of duplicates within
the bound.

### 5.2 Bound and enumeration

- **Feed.** One device (`d1`), one epoch, `seq` 0..N−1, with genuine statements `G_k`. Here `prev(G_k) = cd(G_{k−1})`
  and `prev(G_0) = null`.
- **Alternatives.** Each slot has at most one alternative statement `F_k` (a different payload), so there are at
  most 2 contents per slot.
  - *Standard* mode: `prev(F_k) ∈ {cd(G_{k−1}), cd(F_{k−1})}`.
  - *Extended* mode: additionally `prev(F_k) = null` for k ≥ 1, which `pbti_parse` accepts.
  - N = 4 gives 34 standard feeds (14 distinct contents) and 97 extended feeds (20 distinct contents).
- **Enumeration.** For each feed with universe U, every subset of U is a candidate admitted set and every
  permutation of it is an arrival order. The checker walks the prefix tree of U, whose nodes are exactly the
  (subset, permutation) pairs, Σ_j |U|!/(|U|−j)! of them.
- **Fixed environment.** Default policy parameters; receipts at t = 20 000 + i ms; one authorized relay. With these
  settings every first delivery is admitted, and the checker asserts this.
- **Not covered:** cross-slot effects (they cannot occur, because `_history` only touches `(did, ep, seq)` and
  `(did, ep, seq−1)`) and multi-epoch effects.

### 5.3 Engines

- **mirror.** A line-by-line re-implementation of `_history` (no ablations, empty `waive`). It runs on the real
  `Registry`, `Slot` and `EpochState` classes with the real `Slot.state()` and real content digests, and is used for
  the exhaustive N = 4 walks. Its clone was validated against `copy.deepcopy`.
- **real.** The unmodified `PBTIVerifier` is fed real signed wires: an X.509 trust registry and Ed25519 device and
  relay signatures, built as in `tests/test_evidence_and_envelope.py`. After every receipt, its registry snapshot
  and disposition are compared with the mirror, and its state with Rule L.
- **oracle.** Rule L from the spec text, used for S0.

### 5.4 Results

**Every run has 0 violations in every category** (ADMIT, S0, S1, S2, S2-digest, S3a, S3b, S3b', S3c, S4-disp,
S4-state, MIRROR-disp, MIRROR-state, EVENTS, LOST). In addition, `clone_registry` matches `copy.deepcopy` on 400
random reachable registries.

| Run | Feeds | Nodes = (set, order) pairs checked | Distinct admitted sets | Distinct (set, order) pairs | Duplicate re-deliveries checked | Lattice pairs | Time |
|---|---|---|---|---|---|---|---|
| B mirror, standard, N=4, exhaustive | 34 (sizes 4–8) | 1,060,190 | 1,088 | 769,165 | 7,217,566 | 4,800 | 102.5 s |
| B mirror, extended, N=4, exhaustive | 97 (sizes 4–8) | 3,540,885 | 2,624 | 2,418,401 | 24,154,864 | 12,128 | 373.3 s |
| C real `PBTIVerifier`, standard, N=3, all permutations, duplicates after every prefix | 13 | 24,144 prefix checks (3,558 permutations, 131,994 receipts); covers all 9,669 prefix-tree nodes | 160 | — | 111,408 | — | 70.1 s |
| C real `PBTIVerifier`, extended, N=3, same | 26 | 53,904 prefix checks (7,926 permutations, 295,050 receipts); covers all 21,540 nodes | 288 | — | 249,072 | — | 160.6 s |
| C real `PBTIVerifier`, standard, N=4, all permutations, duplicates at the end of every 16th permutation | 34 (sizes 4–8) | 3,435,240 prefix checks (390,024 permutations, i.e. every permutation of every feed universe; 3,425,892 receipts); covers all 1,060,190 prefix-tree nodes | 1,088 | — | 380,676 | — | 2,553.9 s |

Notes on the table:
- "Nodes" counts a (set, order) pair once per feed it occurs in. Distinct pairs are counted after deduplicating
  admitted sets across feeds, as Σ |A|!.
- In the real runs, every receipt's disposition and registry snapshot equalled the mirror's.
- The only state transition the verifier recorded was COMMITTED→CONTESTED (`state_events`).
- Duplicates were classified RETRY or SUSPECTED_REPLAY by context only (N=3 standard: 20,080 / 91,328). Both
  byte-identical retransmissions and the same content under a new relay statement were tested.

**Exactly which state spaces were fully explored:**

| Bound (one device, one epoch, ≤ 2 contents per slot) | Mirror on real `Registry`/`Slot` | Unmodified `PBTIVerifier`, real signatures |
|---|---|---|
| N = 3, standard and extended | covered (subsumed by N = 4: the N = 3 nodes are the N = 4 nodes without seq 3) | **every (set, order) node**, S4 after every prefix |
| N = 4, standard | **every node**, S4 at every node | **every node** (all permutations); S4 only at the end of every 16th permutation |
| N = 4, extended | **every node**, S4 at every node | **not run** |
| N ≥ 5, > 2 contents per slot, > 1 epoch or device, non-default parameters (except D1/D2), gap closure / LOST, V3 `waive` release path, ablations | not run | not run |

The premises are not vacuous. In the standard N=4 walk, counted over nodes × slots:
- 3,082,596 equivocation instances;
- 2,322,744 instances of an alternative together with its genuine successor;
- 284,130 gap-fills proper (genuine withheld, genuine successor admitted).

**Residual risk (S3c): 553 of the 1,088 standard admitted sets (1,431 of 2,624 extended) leave an alternative
content authoritative.** In every one of them neither `G_k` nor `G_{k+1}` is in the admitted set. This is the
documented negative result "gap-fill with a lost successor" (C07); Rule L cannot detect a forgery nothing
contradicts. The count also covers last-slot alternatives, which in the bound can only be contradicted by `G_k`
itself.

### 5.5 Admission non-determinism (unmodified verifier, real signatures)

Order independence is a property of the admitted set only. *Which* statements are admitted depends on arrival time
and, through the sequence-jump guard, on arrival order. Every final state below equals Rule L evaluated on that
run's admitted set. Replaying all permutations of each admitted set promptly on fresh verifiers gives exactly one
final state per set.

**D1, time: freshness horizon** (`h_max_ms` = 10 000, other parameters default). The statements are:
- G0 (ts 1000);
- G1 (ts 2000, `prev` = cd(G0));
- F1 (an alternative for seq 1: other payload, `prev` = cd(G0));
- G2 (ts 3000, `prev` = cd(G1)).

| Schedule (arrival order @ verifier time, ms) | Dispositions | Admitted set | Final slot states |
|---|---|---|---|
| a: G0@5000, G1@5001, F1@5002, G2@5003 | ACCEPT, ACCEPT, CONFLICT/EQUIVOCATION, ACCEPT | {G0, G1, F1, G2} | 0 COMMITTED(G0), **1 CONTESTED**, 2 COMMITTED(G2) |
| b: same order, F1@12001, G2@12002 | ACCEPT, ACCEPT, QUARANTINE/STALE_TS, ACCEPT | {G0, G1, G2} | all COMMITTED (genuine) |
| c: G0@5000, F1@5001, G1@12500, G2@13500 | ACCEPT, ACCEPT, QUARANTINE/STALE_TS, QUARANTINE/STALE_TS | {G0, F1} | 0 COMMITTED(G0), **1 COMMITTED(alternative F1)**, 2 ABSENT |

These are the same four statements with three different timings, which produce three different admitted sets and
outcomes. In (c) the alternative becomes authoritative, because the contradicting genuine evidence arrived beyond
the horizon and was quarantined. Quarantined evidence never enters Rule L; V3's review-based release is another
admission path, not exercised here.

**D2, order: sequence-jump guard** (`max_seq_jump` = 1, all receipts within 5 ms). The statements are G0, G1, G2 and
F2 (an alternative for seq 2, `prev` = cd(G1)). The 24 arrival orders of these four statements give **5 different
(admitted set, final state) outcomes**:

| Orders | Admitted set | Final states | Example order |
|---|---|---|---|
| 12 | {G0} | 0 COMMITTED, 1–2 ABSENT | G1 G0 F2 G2: G1 arrives with hw = −1, so SEQ_JUMP; later statements also jump |
| 6 | {G0, G1} | 0–1 COMMITTED, 2 ABSENT | G0 F2 G2 G1 (F2 and G2 jump at hw = 0) |
| 2 | {G0, G1, F2, G2} | **2 CONTESTED** | G0 G1 F2 G2 |
| 2 | {G0, G1, G2} | all genuine COMMITTED | G0 F2 G1 G2 (F2 jumps) |
| 2 | {G0, G1, F2} | **2 COMMITTED(alternative)** | G0 G2 G1 F2 (genuine G2 jumps) |

In addition, after G0, F2 (SEQ_JUMP), G1 and G2, a **byte-identical retransmission of F2** is no longer a jump. It
is admitted as CONFLICT/EQUIVOCATION and slot 2 becomes CONTESTED. So "exact duplicates never change state" (S4)
holds for duplicates of *admitted* statements only, not for retransmissions of quarantined ones.

### 5.6 Run record

- **Command:** `python3 rule_l_bounded_check.py --workers 2`. The defaults are N = 4 mirror (standard and extended),
  N = 3 real (standard and extended, every-prefix duplicates), N = 4 real (standard, all permutations, end
  duplicates every 16th permutation), and D1/D2.
- **Started:** 2026-11-04T05:20:31Z. Host: 2 vCPUs, shared with other V3 jobs (load ≈ 4–5 during the run).
  Software: Python 3.13.18, cryptography 50.0.1.
- **Total wall time:** 3,260.8 s (≈ 54 min; slowed by CPU contention).
- **Source:** `01_repo_v3/src/pbti`, tree digest `97bfea56…158f8`. The run also recorded `registry.py` `0160acfc…`,
  `verifier.py` `7ddffbfe…` and `envelope.py` `30cf8e57…`. Files changed on disk by concurrent V3 work during the run: `b5.py`, `dataset.py`, `policy.py`, `realtime.py`, `sweep.py`. Modules are imported once at start, and the verifier imports none of `b5`, `dataset`, `realtime` or `sweep`. The `policy.py` the run loaded (`03d9c4b1…`) is byte-identical to revision 2 (`01_repo_base`). The V3 version written during the run (`a578f211…`, policy-document schema validation) is not covered.
- **Script change after the start.** The line `sys.dont_write_bytecode = True` was added to the script after this
  run had started. It changes no behaviour; it only prevents `.pyc` files being written into the source tree.
- **Re-run:** `python3 rule_l_bounded_check.py --workers 2`, or smaller bounds via `--n`, `--n-ext`, `--real-n`,
  `--real-n-full` and `--real-sample`. The exit status is 0 if and only if there are no violations.

## 6. What was verified, and what was not

**Verified (by a tool, within the stated model or bound):**
- ProVerif results for M-A, M-B and M-C, exactly as listed in Section 4, under the abstractions in the model
  headers.
- Rule L S0–S4 for the bound in Section 5.2, on the code with the digests recorded in the log, with 0 violations.
  The mirror engine was run exhaustively at N = 4 (standard and extended). The unmodified `PBTIVerifier` was run
  over all permutations at N = 3 (standard and extended, duplicates after every prefix) and at N = 4 (standard,
  duplicates after every 16th permutation). Section 5.4 states exactly which state spaces were fully explored.
- Two concrete admission-non-determinism examples (time and order).

**Not verified:**
- Computational soundness (the results are symbolic).
- The actual JSON/JCS parser and canonicalizer. They are assumed perfect in the model; see Section 7 for a
  divergence.
- Time and freshness, `nbf`/`exp`/grace, revocation (REV-1), compromise-window taint (REV-2, TAINTED), and policy
  versions and policy changes. The asset/schema PDP rules are absent from the symbolic model.
- Rule L beyond the bound: more than 2 contents per slot, more than 4 slots, several epochs (STALE_EPOCH), gap
  closure / LOST / STALE_SLOT, non-default `max_seq_jump`, ablations, the V3 quarantine-release (`waive`) path, and
  `prev` values that point to no known content.
  - The general argument (monotone set unions; state is a function of the sets) is a manual sketch, not
    machine-checked.
- Derived processing (windows, current value, lineage, corrections), the evidence log, Merkle checkpoints, the
  witness and the auditor.
- Any liveness or availability property, confidentiality, side channels, and DoS.
- The CA and SPIFFE issuance process (assumed honest).

## 7. Observations made while doing this work

1. **"Both keys" depends on the OT-link assumption** (Section 4.3). The edge workload countersigns every
   `(obs, osig)` it receives without checking it (`sim.py` `_wrap`). Even a checking relay would not help against a
   leaked device key once the attacker can write to the relay's input.
2. **Uncaught exception on out-of-range numbers.** This is outside the formal results; it was reproduced read-only
   against the current V3 code.
   - **Trigger.** A broker modifies a captured message so that it contains an integer above 2^53 (for example
     `obs.ts`), a `NaN` literal, or `1e400` in `pl`. No keys are needed.
   - **Cause.** `pbti_parse` accepts these values, but `canonical_bytes(obs)` then raises `ValueError` inside
     `PBTIVerifier.ingest`. This happens after key resolution and before signature verification.
   - **Effect.** No evidence record is written, although the receipt was already appended to `receipt_log`. This
     contradicts "every receipt produces one evidence record".
   - **Harnesses (code reading only, not run).** Neither `sim.World.receive` nor the subscriber loop in
     `experiments/run_mqtt_e2e.py` catches exceptions around `ingest`, so one such message would end those runs.
   - **Reproduction.** Take any valid wire, set `obs.ts = 2**60`, and call `ingest`.
3. **Transient authority.** An alternative content that arrives before contradicting evidence is ACCEPTed and enters
   derived processing. It is removed again when the genuine content or successor arrives (CONTEST_CORRECTION). This
   is detection and containment, not prevention. If neither ever arrives, the alternative stays authoritative (S3c;
   C07 "gap-fill with lost successor").
4. **`prev = null` at `seq > 0`** is accepted by the parser. Such a statement asserts nothing about its predecessor.
   This is covered by the extended mode.
5. **LOST marking.** In revision 2 nothing ever sets `Slot.lost`, so LOST is unreachable through `Slot.state()`.
   The current V3 `_tick` sets it on gap closure, but only for slot objects that already exist (`sl is not None`,
   that is, slots known through a successor's `prev`). Other identities in a closed gap stay ABSENT in the registry.
   Admission is unaffected, because STALE_SLOT uses `EpochState.closed`. This is code reading only; it was not
   exercised.
6. **Signature bytes do not affect the content digest.** `cd` excludes `osig`, so the same content under different
   signature bytes is a duplicate. `kid` is inside `obs`, so the same content re-signed under a rotated key is a
   conflict (as the spec states).
