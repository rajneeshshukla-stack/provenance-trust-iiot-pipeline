> **V9 note (read first).** This checklist and the automated audit it accompanies (`formal/PROOF_AUDIT_AI.md`)
> were written by the automated research process on 5 November 2026, before V9. The proof they refer to,
> `formal/LOCALITY_PROOF.md`, is unchanged in V9 (SHA-256 `56a80c16b09d6492ed978bcfa1810635b6b943b7ed39f24fced7873cb02c2aa7`), and so are
> `src/pbti/verifier.py`, `registry.py`, `b5.py` and `envelope.py` (hashes in the table below). Two things differ:
>
> 1. **Manuscript references.** References of the form `main.tex:N` and `supplementary.tex:N` point to the manuscript
>    version that was audited (SHA-256 `7c074159…`, kept in the historical baseline of the V7 package, not in this
>    repository). Later versions rewrote several of the passages the audit flagged. In the V9 manuscript
>    (`manuscript/`), the passages of section 8 are: W-a, the contribution C2 in the Introduction; W-b, the Rule L row
>    of Table 1; W-c and W-d, Proposition 1 and its proof sketch (Section 4.2); W-e, the paragraph after the proof
>    sketch; W-f, RQ1 in the Discussion; W-g, Section 4.5; W-h, the second paragraph of the Conclusions; W-i, the
>    paragraph "Locality of Rule L" in Section S2 of Document S1. Check every item against the V9 text, not against
>    the audited version.
> 2. **Corrected comparator.** V9 adds `src/pbti/b5_corrected.py`, whose `_history` method overrides that of
>    `B5FeedLevel` and performs the same two writes to V and I (`slot.versions[cd]` and `ps.implied.add(prev)`,
>    guarded by `seq > 0 and prev is not None`). Include it in item A1 (expected writes: `verifier.py`, `b5.py` and
>    `b5_corrected.py`). Proposition 1 concerns PBTI in its main configuration, so the comparator does not enter
>    the statement.
>
> One sentence of the original introduction was corrected in V9: it said that the sign-off is the human review the
> journal standard requires, which the package cannot confirm; what the manuscript states is that no human review of
> the proof has taken place.
>
> Nothing in this file records a human review. The sign-off in section 11 is blank on purpose.

# Proof review checklist for authors: Proposition 1 (locality of Rule L)

This checklist is for a human author who has not seen the proof before. When you finish it, you will have checked
by hand every definition, assumption and step of the locality proof. Then you decide whether the paper may say
"as we prove", "is proved" and "provably". The proof and the paper text were written by an AI pipeline, and an AI
agent audited them. Your sign-off is the human review that the manuscript currently states has not taken place. Do not tick a box because
the audit says the item is fine: tick it only after you have checked it yourself.

- **Time needed:** about 1.5 to 2 hours.
- **You need:** paper and pencil, and the files below.
- **If an item fails:** write "NO" next to it, add a note, and decide in the sign-off whether it needs a
  correction.

| File (in the released repository) | SHA-256 of the version audited |
|---|---|
| `formal/LOCALITY_PROOF.md` (the proof) | `56a80c16b09d6492ed978bcfa1810635b6b943b7ed39f24fced7873cb02c2aa7` |
| `paper/main.tex` (lines 66, 91, 164–186, 366, 372, 382) | `7c07415970ebc1f8b6704418ac7c7df5068554b3870c3ffbfd7ba7d0fe1468ff` |
| `paper/supplementary.tex` (line 334) | `8a7fb1f265752ba531cfdc7731a39a08bbb795b7875c6a5c7d426c42fc32f454` |
| `src/pbti/verifier.py`, `registry.py`, `b5.py`, `envelope.py` (to confirm code claims) | `9c2deed4…`, `0160acfc…`, `19dc1166…`, `6a1027d8…` |
| Automated audit report (context only) | `formal/PROOF_AUDIT_AI.md` |

If any file has changed since this audit, re-check the items that refer to it.

---

## 1. The model in plain terms

- **Events and identities.** Every observation a device sends has an *identity* e = (d, p, q): the device d, an
  *epoch* p (a numbered run of the device, e.g. after a reboot) and a *sequence number* q = 0, 1, 2, … within the
  epoch.
- **Predecessor.** The predecessor of (d, p, q) is (d, p, q − 1). An identity with q = 0 has no predecessor.
  Predecessors never cross epochs or devices.
- **Statements and digests.** A *statement* is a signed observation. Its *content digest* cd is a SHA-256 hash of its
  content. Every statement also carries a field `prev`: either the digest it claims for its predecessor's
  observation, or nothing (⊥, "null").
- **Evidence.** For each identity e the verifier keeps two sets of digests:
  - **V(e)**, the versions admitted for e;
  - **I(e)**, the digests that admitted *successors* claim for e through their `prev` field.
- **Admitting a statement s at identity e** does exactly two things:
  - add cd(s) to V(e);
  - if q > 0 and prev(s) is not null, add prev(s) to I(pred(e)).

  Nothing else in V or I is touched.
- **Classes (Rule L).** An identity is:
  - ABSENT if V(e) is empty;
  - otherwise COMMITTED if V(e) ∪ I(e) contains exactly one digest;
  - otherwise CONTESTED (two or more digests).

  LOST is a further label for an ABSENT identity whose gap was closed by a timer (a *lifecycle transition*, see
  below).
- **Authority.** An identity is *authoritative* (its observation is used downstream) if it is COMMITTED and not
  TAINTED. TAINTED is set when a key is revoked with a compromise time (revocation processing).
- **Lifecycle transitions** are operations other than admissions:
  - *gap closure*: a timer declares missing sequence numbers LOST;
  - *revocation processing*: taints data committed under a revoked key;
  - *reviewer decisions*: release, reject, stale-snapshot refusal.

  A release re-runs the normal admission, and that admission counts as an admission.
- **The claim (Proposition 1).** Admit k statements, with no lifecycle transition in between. Let A(S) be the set of
  their identities plus, for each statement with q > 0 and a non-null prev, its predecessor. Then:
  - V and I change only on A(S);
  - A(S) has at most 2k elements;
  - every identity outside A(S) keeps its class and its authority.

  In words: one admitted statement, contradictory or not, can change the status of at most two identities: its own
  and its predecessor's.

Why this matters: a feed-level design (B5) withholds every later observation of a feed after one contradiction.
Proposition 1 says PBTI's rule does not.

---

## 2. Definitions

| # | Item | What to check | ✓ |
|---|---|---|---|
| D1 | Identity and predecessor (proof §1, lines 11–12) | pred(d,p,q) = (d,p,q−1) only for q > 0; no predecessor at q = 0; never across epochs or devices. Check in code that the predecessor key is `(did, ep, seq - 1)` and is used only when `seq > 0` (`src/pbti/verifier.py:318–319`). | [ ] |
| D2 | Statement, cd, prev (lines 13–14) | cd is a hash of the signed observation (it also covers the identity fields and the timestamp, not only "payload, prev, key id"; see `src/pbti/envelope.py:57–59`). prev is a digest or null. The parser rejects a non-null prev at q = 0 (`envelope.py:105`). Confirm that the proof needs no property of the hash. | [ ] |
| D3 | Evidence state E = (V, I) (lines 15–16) | Both are maps from identities to finite sets of digests, empty at the start. In code: `Slot.versions` and `Slot.implied` (`src/pbti/registry.py:29–30`); a missing slot counts as empty. | [ ] |
| D4 | Admission update adm (lines 17–21) | V(e) gains cd(s); I(pred e) gains prev(s) **only if** q > 0 and prev ≠ null. Compare with `verifier.py:311` (V) and `:318–324` (I). Note that the paper's Algorithm 1, line 164 (`main.tex:164`), omits the "q > 0 and prev ≠ null" condition. | [ ] |
| D5 | Rule L classes (line 29) | Read the definition literally. If V(e) = ∅ and I(e) = {a}, is the identity ABSENT or COMMITTED? As written, both conditions hold. Confirm that the intended reading is an ordered case distinction: "ABSENT if V(e) = ∅; **otherwise** COMMITTED if \|V∪I\| = 1, CONTESTED if \|V∪I\| ≥ 2". Compare `registry.py:47–52`. Decide whether the proof text must be corrected. | [ ] |
| D6 | LOST (lines 30–31) | The proof leaves LOST out of the lemma, but the paper's Rule L (`main.tex:169`) includes LOST, and Proposition 1 speaks of "the Rule L class". Check whether the proof covers LOST; see item P6. | [ ] |
| D7 | Authority (lines 32–33) | PBTI: authoritative ⇔ COMMITTED and not TAINTED (`verifier.py:380–381`). B5 additionally requires "not held" (`b5.py:63–64`). PBTI-SH additionally requires "not provisional" (`selective.py:52–53`). Note that the paper's main text never defines "authority"; decide whether one sentence should be added near Proposition 1. | [ ] |
| D8 | A(S) (proof line 40; paper `main.tex:182`) | A(S) must be **exactly** the set of the statements' identities plus predecessors (q > 0, prev ≠ null). The paper says "Let A(S) **contain** …"; a superset would break the bound \|A(S)\| ≤ 2k. Confirm the intended meaning. | [ ] |

## 3. Assumptions

| # | Item | What to check | ✓ |
|---|---|---|---|
| A1 | Only two writers (line 23–25) | The proof says V and I are written only in `PBTIVerifier._history` and `B5FeedLevel._history`. Search the code yourself: `grep -rn "versions\[\|implied" src/pbti/`. Expected writes: `verifier.py:311, 322–324` and `b5.py:90, 97–99`, and none elsewhere. | [ ] |
| A2 | Ablations excluded (line 25) | The ablations `no_prev_link`, `no_conflict` and `edge_event_id` change the update (`verifier.py:285–288, 295–296, 318`). Confirm that the paper's results that cite Proposition 1 use the main configuration. | [ ] |
| A3 | Admission = ACCEPT or CONFLICT receipt (line 26) | True for PBTI: every return after the V write is ACCEPT or CONFLICT (`verifier.py:336–346`). **Check B5**: `b5.py:123–126` returns QUARANTINE (FEED_FORK_HOLD) *after* V and I were written at `b5.py:90–99`. Decide how to restate this sentence (suggestion: "admission = reaching the V write"). | [ ] |
| A4 | Release (line 27) | A reviewed release re-runs admission (`verifier.py:487–497`, call at `:489`). Check that "if it reaches Rule L" should read "if it reaches the V write": a re-run can still end as DUPLICATE or as a quarantine for a reason that was not waived. | [ ] |
| A5 | Taint is written only by revocation processing (line 33) | `s.tainted = True` occurs only at `verifier.py:156` (`_apply_taints`), apart from the insider-tampering simulation in `audit.py:295`, which is outside the trusted computing base. Confirm that the paper's TCB statement (`main.tex:114`) covers this. | [ ] |
| A6 | LOST is written only by gap closure | `sl.lost = True` occurs only at `verifier.py:130` (in `_tick`). This assumption is needed for P6 but is **not stated** in the proof. | [ ] |
| A7 | Lifecycle transitions happen inside admission | `ingest()` first calls `advance(t)` (`verifier.py:166`), which can run revocation processing and gap closure. `open_review` and `apply_review` do the same (`:422`, `:437`). Confirm that the hypothesis "no gap closure or revocation processing in between" is a condition on time and schedule that the reader must understand this way. Decide whether to say so in the paper. | [ ] |

## 4. Inferences (proof steps)

| # | Step | What to check | ✓ |
|---|---|---|---|
| P1 | Lemma (a) by induction (lines 47–49) | Step: adm(E_j, s_{j+1}) differs from E_j only at e(s_{j+1}) (V) and possibly pred(e(s_{j+1})) (I), and both lie in A(S). State the invariant to yourself: "E_j equals E outside A(s_1, …, s_j) ⊆ A(S)". Is the base case k = 0 right? | [ ] |
| P2 | Lemma (b) counting (lines 49–50) | \|A(S)\| ≤ (number of statement identities ≤ k) + (number of predecessors m ≤ k) ≤ 2k. | [ ] |
| P3 | Equality condition (lines 43–45) | \|A(S)\| = 2k iff every statement has q > 0 and a non-null prev and all 2k identities are distinct. Note: "no two share a predecessor" already follows from "no two share an identity", since pred is one-to-one. | [ ] |
| P4 | "Class depends only on …" | The proof note says cls(x) depends only on V(x) and I(x): correct. The **paper** (`main.tex:184`) and the supplement (`:334`) say "a class depends only on V(e) ∪ I(e)". Check with V = ∅, I = {a} versus V = {a}, I = ∅: the unions are equal but the classes differ (ABSENT vs COMMITTED). Decide whether to correct the sentence. | [ ] |
| P5 | Corollary 1, authority (lines 54–57) | Authority = COMMITTED and not TAINTED; TAINTED is unchanged because revocation processing is excluded (A5). | [ ] |
| P6 | Corollary 1 for LOST (missing step) | The paper's statement covers LOST. Check that the following one-line argument suffices and should be added: LOST(x) = (lost flag set and V(x) = ∅); the lost flag is written only by gap closure (A6), which is excluded; V(x) is unchanged outside A(S). | [ ] |
| P7 | Corollary 2 (lines 63–67) | Unions commute and are idempotent, so the order of S does not matter. Because V and I only grow: CONTESTED stays CONTESTED; COMMITTED stays COMMITTED or becomes CONTESTED; ABSENT can become anything except LOST. This holds only for a fixed admitted set; whether a statement is admitted can depend on order (E1). | [ ] |
| P8 | Tightness (lines 69–71) | "k such statements at pairwise non-adjacent sequence numbers contest 2k identities." Check that this needs: (i) a genuine, uncontested version already at each statement's identity (so the statement is an *equivocation*), and (ii) a committed, uncontested predecessor whose digest differs from the statement's prev. Without (i), for a gap-fill without a successor link, 2k classes change but only k identities become CONTESTED. Worked example W1 is the correct construction. | [ ] |
| P9 | "Attained when pairwise distinct" (`main.tex:186`, `supplementary.tex:334`) | Pairwise distinctness gives \|A(S)\| = 2k. Does it also give 2k *changed* identities? Work through W3: it does not. Decide on the wording. | [ ] |
| P10 | "In words" (lines 59–61) | "One contest withdraws at most the contested identity and its predecessor": check that the precise statement is "at most the statement's own identity and its predecessor". | [ ] |

## 5. Paper statement versus proof statement

| # | Item | What to check | ✓ |
|---|---|---|---|
| S1 | Hypothesis | Paper (`main.tex:182`): "no gap closure or revocation processing in between". Proof, Corollary 1: also "no reviewer decision other than the re-run admission". Decide which wording the paper uses. For PBTI, reject and stale-snapshot decisions do not touch V, I, taint or LOST (`verifier.py:464–469`), so the omission is harmless, but the two statements should match. | [ ] |
| S2 | Configuration | The proof excludes ablations; the paper's Proposition 1 does not mention them (the supplement does). | [ ] |
| S3 | Class | The paper says "the Rule L class" (which includes LOST); the proof excludes LOST. Resolve via P6. | [ ] |
| S4 | Scope of "authority" | Proposition 1 holds for PBTI's authority. It does not hold for B5 (feed holds) or PBTI-SH (selective holds). The paper excludes PBTI-SH right after the proposition and presents B5 as a contrast. Confirm this is clear enough. | [ ] |
| S5 | Exclusions list | `main.tex:186` lists admission decisions, lifecycle transitions, downstream fan-out, undetected contamination, PBTI-SH and replicated verifiers. Compare with proof §5 (E1–E6). | [ ] |

## 6. Worked examples (verify by hand)

Notation: one device, epoch 0; identity (q) means (d, 0, q). g_q is the genuine version at q, f_q a forged or
alternative version, and x, y are digests that match nothing. A genuine statement G_q has digest g_q and
prev = g_{q−1} (prev = null at q = 0). For each example: compute A(S), apply the update statement by statement,
write the classes before and after, and compare with the expected result.

### W1: bound attained (k = 2)

Start: G0, G1, G2, G3 admitted.

| q | V | I | class |
|---|---|---|---|
| 0 | {g0} | {g0} | COMMITTED |
| 1 | {g1} | {g1} | COMMITTED |
| 2 | {g2} | {g2} | COMMITTED |
| 3 | {g3} | ∅ | COMMITTED |

Batch S = (F1 at identity 1 with digest f1 and prev x; F3 at identity 3 with digest f3 and prev y), where x ≠ g0 and
y ≠ g2.

Expected:
- A(S) = {0, 1, 2, 3}, so \|A(S)\| = 4 = 2k.
- After the batch: V(1) = {g1, f1}, I(0) = {g0, x}, V(3) = {g3, f3}, I(2) = {g2, y}.
- **All four identities become CONTESTED and lose authority: 4 = 2k changes.**
- Variation: move the second statement to identity 2 (adjacent to the first). Then A(S) = {0, 1, 2} and at most 3
  identities can change.

(On the real verifier, with k = 1 to 8 such statements across 2 devices × 2 epochs, exactly 2k identities changed;
audit scenario X3.)

[ ] My hand computation agrees.

### W2: the q = 0 boundary

Start: G0 and G1 admitted, so V(0) = {g0}, I(0) = {g0} (COMMITTED) and V(1) = {g1}, I(1) = ∅ (COMMITTED).

Batch S = (F0 at identity 0 with digest f0 and prev null).

Expected:
- A(S) = {0}: an identity with q = 0 has no predecessor.
- After the batch: V(0) = {g0, f0}, so (0) is CONTESTED.
- (1) is unchanged and stays COMMITTED: F0 asserts nothing about (1).
- One change, which is at most 2k = 2. At q = 0 the bound cannot be attained.
- Variation (a): F0 carries a non-null prev z. In the model the prev is ignored, so A(S) = {0} still. The
  implementation rejects such a statement at parsing (`REJECT/MALFORMED:obs-prev-at-epoch-start`,
  `envelope.py:105`): nothing is admitted and nothing changes.
- Variation (b): a statement at q = 1 with prev null has A(S) = {1} only.

[ ] My hand computation agrees.

### W3: distinct identities but fewer than 2k changes

Start: nothing admitted. Batch S = (G1 with prev g0; G3 with prev g2).

Expected:
- A(S) = {0, 1, 2, 3}: four pairwise distinct identities, \|A(S)\| = 2k.
- After the batch: V(1) = {g1} and V(3) = {g3}, so (1) and (3) become COMMITTED.
- I(0) = {g0} and I(2) = {g2}, but V(0) = V(2) = ∅, so (0) and (2) **stay ABSENT**.
- Evidence changed at 4 identities, class at only 2.

This shows that "the bound is attained when the 2k identities are pairwise distinct" is true for \|A(S)\| but not for
the number of identities that change. In a six-identity feed (all 16^6 evidence states, all 64 batches of three
statements with six distinct identities in A(S)), only about 0.01 % of the state–batch combinations change all six
classes (audit §5a).

[ ] My hand computation agrees.

### W4: successor first; order independence; an ABSENT identity with a known digest

Start: G0 admitted, so V(0) = {g0} (COMMITTED). The genuine G1 is never delivered. Two statements arrive:
- G2 at identity 2, digest g2, prev g1;
- the forgery F1 at identity 1, digest f1, prev g0 (it copies the genuine predecessor link).

Compute both orders.

| Step | Order A: F1 then G2 | Order B: G2 then F1 |
|---|---|---|
| after 1st | V(1) = {f1}, I(1) = ∅ → (1) COMMITTED (forgery authoritative for now); I(0) = {g0} → (0) stays COMMITTED | V(2) = {g2} → (2) COMMITTED; I(1) = {g1}, V(1) = ∅ → (1) ABSENT, with an "expected digest" known |
| after 2nd | V(2) = {g2} → (2) COMMITTED; I(1) = {g1} → (1) CONTESTED | V(1) = {f1}, I(1) = {g1} → (1) CONTESTED; I(0) = {g0} → (0) unchanged |
| final | (0) COMMITTED, (1) CONTESTED, (2) COMMITTED | same |

Check also:
- Each single admission changed only identities in its own A: A({F1}) = {0, 1} and A({G2}) = {1, 2}.
- In order B after step 1, the proof note's literal class definition (D5) gives two answers for (1): ABSENT and
  COMMITTED. The intended answer is ABSENT.

(The same trace is in `tests/test_v4_oracle_traces.py::test_gap_fill_contested_in_both_successor_orders`.)

[ ] My hand computation agrees.

---

## 7. Exclusions and liveness assumptions to confirm

The proposition says nothing about the following. For each, confirm that it is outside the claim and that the paper
says so.

| # | Exclusion / assumption | What to check | ✓ |
|---|---|---|---|
| X1 | E1 admission decisions | Whether a statement is admitted depends on earlier admissions and on time: high-water mark, gaps, epoch drain, `max_seq_jump`, freshness, key validity, revocation, policy version. One admission can open a gap of up to `max_seq_jump` identities that a later gap closure marks LOST. Stated at `main.tex:186` ("gaps, horizons, epochs"). | [ ] |
| X2 | E2 gap closure | Marks LOST outside A(S) (`verifier.py:119–131`). Note: only identities that already have a slot object are marked; the others in the closed range get no slot (audit F11). | [ ] |
| X3 | E2 revocation processing / taint | Taints every qualifying committed identity of a revoked key (`verifier.py:146–159`). Not bounded by 2k. | [ ] |
| X4 | E2 reviewer decisions | Only the admission that a release re-runs is covered. Reject and stale-snapshot refusals do not change V, I or classes in PBTI. In B5, a FEED_FORK_HOLD release changes authority without any admission (`b5.py:164–184`). | [ ] |
| X5 | Lifecycle inside `ingest()` | See A7. Example from the audit: an unrelated delivery whose `ingest()` first closes an old gap changes an identity outside A(S) from ABSENT to LOST, or taints every committed slot of a revoked key. These are not counterexamples, because the hypothesis is violated, but they show why the hypothesis is needed. | [ ] |
| X6 | E3 derived processing | One class change can change the derived windows that contain the identity; downstream fan-out is not bounded. | [ ] |
| X7 | E4 undetected contamination | A forged version that no contradicting version or successor link ever reaches stays COMMITTED (`tests/test_v4_oracle_traces.py::test_missing_successor_leaves_forgery_committed`). | [ ] |
| X8 | E5 PBTI-SH | Evidence and class locality hold; authority locality does not (feed-wide holds, `selective.py:127–133`). | [ ] |
| X9 | B5 | Evidence and class locality hold; authority does not (feed holds, `b5.py:133–161`). | [ ] |
| X10 | E6 replication | Multiple verifiers, evidence exchange and recovery are not modelled. | [ ] |
| X11 | Ablations | `no_prev_link`, `no_conflict`, `edge_event_id` change the update. | [ ] |
| L1 | Liveness: contest needs evidence | A gap-fill or equivocation is contested only if a contradicting version or successor link is admitted within the horizons. The proposition does not promise that this happens. | [ ] |
| L2 | Liveness: release needs a reviewer | A quarantined or held observation is released only if a reviewer runs and the required evidence exists. | [ ] |
| L3 | Liveness: taint needs a revocation | Retroactive containment needs a published revocation with t_comp; its precision depends on how well t_comp is known. | [ ] |
| L4 | Safety/liveness separation | Confirm that the proof uses none of L1–L3: locality only says what cannot change. | [ ] |

## 8. Where the paper says "prove", "proved", "provably" or "Proof"

For each place, decide whether the wording can stay once you have signed off, and what it must say until then.
Suggested replacements are in `formal/PROOF_AUDIT_AI.md` §7.

| # | Location | Current text (abridged) | Keep / change to | ✓ |
|---|---|---|---|---|
| W-a | `main.tex:66` (Introduction, C2) | "… which, as we prove, changes the **state** of at most 2k event identities for k admitted statements (Proposition 1)": no hypothesis; "state" is wider than class and authority | | [ ] |
| W-b | `main.tex:91` (Table 1) | "at most 2k identities affected by k statements (Proposition 1)" | | [ ] |
| W-c | `main.tex:181–183` | Proposition 1 statement (see S1–S4, D8) | | [ ] |
| W-d | `main.tex:184` | "*Proof.* … a class depends only on V(e) ∪ I(e) …" (see P4, P6) | | [ ] |
| W-e | `main.tex:186` | "The bound is attained when the 2k identities are pairwise distinct …" (see P9) | | [ ] |
| W-f | `main.tex:366` | "Per-identity containment withdraws at most two identities per contradictory statement (Proposition 1)" | | [ ] |
| W-g | `main.tex:372` | "Proposition 1 is proved from the update definition and does not depend on any bounded check." The model-to-code link rests on code inspection and the bounded checks. | | [ ] |
| W-h | `main.tex:382` (Conclusions) | "… whose conflict rule **provably** changes the state of at most two identities per contradictory statement (Proposition 1, with its exclusions) …" | | [ ] |
| W-i | `supplementary.tex:334` | "Proposition 1 … is proved in formal/LOCALITY_PROOF.md … classes depend only on V(e) ∪ I(e) … the bound is attained when these identities are pairwise distinct" | | [ ] |
| W-j | `formal/LOCALITY_PROOF.md:3, 47, 56` | "This note proves …", "*Proof.*" | | [ ] |

Uses of "proof" that are **not** about Proposition 1 and need no action: `main.tex:78` (Lavoie, "a proof of it"),
`:102` ("never proof of time"), `:171` ("not a proof of when an observation was created"), `:173` ("not proof that
the observation existed"), `:372` ("we provide no computational proof of the complete system").

## 9. Issues raised by the automated audit (accept or reject each)

| Audit ID | Severity (audit) | Short description | Your decision | ✓ |
|---|---|---|---|---|
| F1 | MAJOR | Proof not yet reviewed by a human; "prove"/"provably" wording | | [ ] |
| F2 | MINOR | Paper's hypothesis and scope differ from the proof's (reviewer decisions, ablations, "contain") | | [ ] |
| F3 | MINOR | Printed proofs omit LOST; "class depends only on V ∪ I" is false as written | | [ ] |
| F4 | MINOR | Class definition not a well-formed case distinction | | [ ] |
| F5 | MINOR | "Attained when pairwise distinct" wrong if read as being about changes | | [ ] |
| F6 | MINOR | Tightness paragraph lacks qualifiers | | [ ] |
| F7 | MINOR | Admission identified by disposition: wrong for B5 | | [ ] |
| F8 | MINOR | "State" overclaims; the contribution statement omits the hypothesis | | [ ] |
| F9 | MINOR | Algorithm 1 omits the q > 0 / prev ≠ null guard; ACCEPT can contest the predecessor | | [ ] |
| F10 | NOTE | Lifecycle transitions run inside `ingest()` | | [ ] |
| F11 | NOTE | Gap closure marks LOST only on existing slots | | [ ] |
| F12 | NOTE | Editorial precision points | | [ ] |

## 10. Optional: re-run the independent checkers

The automated audit wrote two checkers from the lemma statement only. Running them is optional. Your review should
rest on sections 2–7 above, not on these runs.

```
python3 -I tools/proof_audit/model_check.py        # pure model, about 5 minutes
python3 -I tools/proof_audit/impl_check.py         # real verifier, about 10 seconds
```

Audit results:
- Model checker: 4,068,762,624 (evidence state, batch) cases, 0 violations.
- Real verifier: 1,000 random histories, 0 violations.
- The bound 2k was reached for k = 1 to 8 (scenario X3).

[ ] Re-run (optional): results reproduced / not reproduced (circle one).

---

## 11. Sign-off (to be completed by the human reviewer; left blank on purpose)

```
Reviewer name:                     ____________________________________________
Role / relation to the paper:      ____________________________________________
Date:                              ____________________________________________
Files reviewed (SHA-256 if
different from the table above):   ____________________________________________

Result (tick one):
    [ ] accepted
    [ ] accepted with corrections
    [ ] rejected

Corrections required (item numbers from sections 2-9):
                                   ____________________________________________
                                   ____________________________________________

May the paper say "as we prove" / "is proved" / "provably" after these corrections?
    [ ] yes    [ ] yes, with the wording changes listed above    [ ] no

Notes:
                                   ____________________________________________
                                   ____________________________________________
                                   ____________________________________________

Signature:                         ____________________________________________
```
