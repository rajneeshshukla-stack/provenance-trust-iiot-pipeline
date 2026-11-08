# Locality of Rule L: statement, proof and exclusions (V4, memo R07/A4)

This note proves a scoped locality property of PBTI's delivery-history rule (Rule L) and states, for contrast, the
corresponding property of the feed-level comparator B5. The proof is a short pen-and-paper argument from the update
definition; it does not depend on the bounded checks, which are reported separately (Section 6) as an independent
cross-check of the implementation. The result is elementary by design: its value is a precise statement of what
"per-identity containment" means and of what it does not cover.

## 1. Model

* **Identities.** An event identity is e = (d, p, q): device d, epoch p, sequence number q ∈ ℕ. For q > 0,
  pred(e) = (d, p, q − 1); identities with q = 0 have no predecessor.
* **Statements.** An admitted statement s has identity e(s), content digest cd(s) (SHA-256 of the canonical
  observation, which covers the payload, the `prev` field and the signing key id) and prev(s), a digest or ⊥.
* **Evidence state.** E = (V, I) with V, I : Identities → finite sets of digests; V(e) are the admitted versions of e,
  I(e) the digests that admitted successors assert for e through their `prev` field. Initially V ≡ I ≡ ∅.
* **Admission update.** For an admitted statement s with e = e(s):

      adm(E, s) = ( V[e ↦ V(e) ∪ {cd(s)}],
                    I[pred(e) ↦ I(pred(e)) ∪ {prev(s)}]   if q(e) > 0 and prev(s) ≠ ⊥,
                    I                                      otherwise ).

  In the implementation these are the only writes to V and I: `PBTIVerifier._history` (src/pbti/verifier.py,
  `slot.versions[cd] = ...` and `ps.implied.add(obs["prev"])`) and the B5 subclass's `_history`
  (src/pbti/b5.py), in the main configuration (ablations `no_prev_link`, `no_conflict` and `edge_event_id` change the
  update and are excluded). A receipt with disposition ACCEPT or CONFLICT is an admission; DUPLICATE, QUARANTINE and
  REJECT receipts do not change E. A reviewed release re-runs admission and, if it reaches Rule L, is an admission.
* **Rule L classes (lifecycle-free part).**
  cls_E(e) = ABSENT if V(e) = ∅; COMMITTED if |V(e) ∪ I(e)| = 1; CONTESTED if |V(e) ∪ I(e)| ≥ 2.
  The class LOST (an ABSENT identity in a gap closed after the gap horizon) is produced by a lifecycle transition and
  is excluded from the lemma (Section 5).
* **Authority.** PBTI: auth_E(e) ⇔ cls_E(e) = COMMITTED ∧ ¬τ(e), where the taint flag τ is changed only by
  revocation processing. B5: auth additionally requires e ∉ H, the held set (Section 4).

## 2. Lemma (evidence locality)

Let E be any evidence state and S = (s_1, …, s_k) any finite sequence of admitted statements, and let
E' = adm(… adm(adm(E, s_1), s_2) …, s_k). Define the affected set

    A(S) = { e(s_i) : 1 ≤ i ≤ k } ∪ { pred(e(s_i)) : q(e(s_i)) > 0 and prev(s_i) ≠ ⊥ }.

Then (a) V'(x) = V(x) and I'(x) = I(x) for every identity x ∉ A(S); and (b) |A(S)| ≤ k + m ≤ 2k, where m is the
number of statements with q > 0 and prev ≠ ⊥. The bound 2k is attained exactly when all of e(s_1), …, e(s_k) and
their predecessors are 2k distinct identities (no statement has q = 0 or prev = ⊥, and no two statements share an
identity or a predecessor, and no statement's identity is another's predecessor).

*Proof.* (a) By induction on k. For k = 0, E' = E. For the step, adm(E_j, s_{j+1}) differs from E_j only in the
entry V(e(s_{j+1})) and, if q > 0 and prev ≠ ⊥, the entry I(pred(e(s_{j+1}))); both identities lie in A(S). An
identity outside A(S) is therefore never written. (b) A(S) is the union of k singletons and m further singletons,
so |A(S)| ≤ k + m ≤ 2k; equality |A(S)| = 2k requires m = k and all 2k identities to be distinct. ∎

## 3. Consequences

**Corollary 1 (class and authority locality).** If no lifecycle transition (gap closure, revocation processing,
reviewer decision other than the re-run admission itself) occurs between E and E', then cls_{E'}(x) = cls_E(x)
and, for PBTI, auth_{E'}(x) = auth_E(x) for every x ∉ A(S). *Proof.* cls(x) depends only on V(x) and I(x), which are
unchanged by the lemma; τ(x) changes only under revocation processing, which is excluded. ∎

In words: k admitted statements, contradictory or not, change the Rule L class and the PBTI authority of at most 2k
identities, whatever the length of the feed. A single equivocation or gap-fill contest withdraws at most the
contested identity and its predecessor; the feed's later observations keep their authority.

**Corollary 2 (order independence and absorption for a fixed admitted set; restated from V3).** adm is commutative
and idempotent on (V, I) (it only forms set unions), so every permutation of S yields the same E'. Because V and I
only grow, |V(e) ∪ I(e)| ≥ 2 is preserved: CONTESTED is absorbing under admissions; COMMITTED can only become
CONTESTED; ABSENT can become COMMITTED or CONTESTED. This is a statement about a fixed admitted set; *which*
statements are admitted can depend on arrival order and time (Section 5, E1).

**Tightness.** The bound is attained: a gap-fill alternative F at (d, p, q) whose prev names a digest different from
the admitted predecessor's version contests both (d, p, q) (if a genuine version is there) and (d, p, q − 1); a
batch of k such statements at pairwise non-adjacent sequence numbers contests 2k identities.

## 4. Contrast: the feed-suffix response of B5

B5 (src/pbti/b5.py, `_fork` and `_history`) holds, on the first fork evidence at sequence number f in feed (d, p),
every identity of that feed with q ≥ f that already has a version, and every later admitted identity with q ≥ f while
the fork is unresolved (until review resolves all held cases, `_maybe_resume`). For a feed whose admitted identities
reach n, a single contradictory statement at f therefore removes up to n − f + 1 identities from authority until
review; the number is not bounded by any constant independent of the feed length. This is a property of the
specified comparator, not a lower bound for feed-level designs in general; its cost in time is what the A1 review
schedules measure.

## 5. Exclusions (what the lemma does not state)

* **E1 Admission decisions.** Whether a statement is admitted depends on state that earlier admissions change (epoch
  high-water mark, open and closed gaps, `max_seq_jump`, the epoch drain rule) and on time (freshness horizon, key
  validity and grace, revocation, policy versions). An admission can thereby enable or prevent later admissions
  (e.g., a STALE_SLOT quarantine after gap closure). The lemma speaks only about the effect of admitted statements.
* **E2 Lifecycle transitions.** Gap closure marks a whole closed range LOST; revocation processing taints every
  qualifying committed identity of the revoked origin key (decision D05: re-run on revised records); neither is
  bounded by 2k. A reviewer's decision is an operation on a case; only the re-run admission it triggers is covered.
* **E3 Derived processing.** A class change at e changes the derived windows that contain e (one tumbling window per
  asset in the reference processor) and whatever consumes them; downstream dependency fan-out is not bounded here.
* **E4 Undetected contamination.** The lemma bounds the effect of evidence, not the effect of its absence: a forged
  version for which no contradictory version or successor link is ever admitted stays COMMITTED (Section 7, L1).
* **E5 PBTI-SH.** The selective-hold extension (src/pbti/selective.py) deliberately makes authority depend on
  feed-level suspicion; for PBTI-SH, parts (a) and the class part of Corollary 1 hold, the authority part does not.
* **E6 Replication.** Multiple verifier replicas, evidence exchange between them and durable recovery are not
  modelled; set-based slot state does not by itself provide a replicated protocol.

## 6. Mechanical cross-checks (separate from the proof)

`formal/v4_locality_lifecycle_check.py` (results in `results/v4/formal/v4_locality_lifecycle_check.json`):

* **M (model enumeration):** an implementation-independent transition model of (V, I); for every base set of two
  statement universes (one epoch, q ∈ {0, 1, 2}, contents {G, F}, prev ∈ {G, F, ⊥}: 14 statements; two epochs,
  q ∈ {0, 1}, prev ∈ {G, F}: 12 statements) and every batch of one or two further statements: changed classes ⊆
  A(S), |A(S)| ≤ 2|S|, both orders equal, CONTESTED absorbing.
* **L (implementation):** the unmodified `PBTIVerifier` with real Ed25519 signatures; every base set of the
  two-epoch universe with every single further statement, plus a seeded sample of batches of two or three statements;
  per identity (class, authority, presence in derived processing) changes only inside A(S'), S' being the batch
  statements the verifier admitted.
* **C (bounded lifecycle combinations):** every operation sequence of length ≤ 4 over a 13-symbol alphabet
  (deliveries over two epochs including a forged alternative and a rotated-key statement; gap closure; revocation
  with early or late compromise time; release with a fresh or stale snapshot; rejection) and a seeded sample of longer
  sequences, with nine invariants (evidence conformance, absorbing contest, authority and derived data, taint
  exactness, no ordinary admission under a revoked key, release safety, stale-snapshot refusal, per-delivery
  locality, rotation grace). The check found one defect, fixed before the confirmatory runs (decision D05:
  a revised revocation record with an earlier compromise time was ignored); the counterexample is kept in
  `results/v4/formal/counterexamples/`.

These are bounded checks; they are reported as "checked within the stated bounds", not as proofs.

## 7. Liveness assumptions (separate from safety)

* **L1** A gap-fill or equivocating version at e is contested only if a contradictory version of e or a successor
  statement whose prev names a different digest for e is admitted (within the freshness, gap and epoch horizons).
* **L2** A quarantined or held observation is released only if a reviewer runs (scheduler, review delay, cadence) and
  the release evidence its policy requires is available (hash-link corroboration for the automated reviewer; a
  witness token for the A5 `witness` policy).
* **L3** Retroactive containment requires a revocation carrying t_comp to be published and processed; its precision
  depends on how accurately t_comp is known (A5 interval experiment).
No rule detects a contradiction that never becomes observable.
