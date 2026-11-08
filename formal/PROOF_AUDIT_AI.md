> Automated audit written by an AI agent of the research process on 5 November 2026 (not a human review). Workspace paths of the auditing session were replaced by repository-relative paths; the content is otherwise unchanged.

# Independent audit of Proposition 1 (locality of Rule L)

Auditor: AI agent (proof-audit task), 2026-11-05. This is an automated audit. It does not replace the human review
that the journal standard requires. The companion checklist for a human author is
`formal/PROOF_REVIEW_CHECKLIST.md`.

**Verdict in one paragraph.** The mathematics is correct. Lemma (a) and (b), Corollary 1 (lifecycle-free class and
PBTI authority) and Corollary 2 follow from the update definition. I found no counterexample: 0 violations in
4,068,762,624 (evidence state, batch) cases of an independent pure-model checker, and 0 violations in 1,000 random
histories (10,803 receipts) on the unmodified `PBTIVerifier` with real Ed25519 signatures. The printed text has
precision gaps:
- the paper's Proposition says more (the "Rule L class" includes LOST) and assumes less (no reviewer-decision clause)
  than the proof note;
- one sentence of the paper's printed proof is false as written ("a class depends only on V(e) ∪ I(e)");
- the proof note's class definition is not a well-formed case distinction;
- the claim "the bound is attained when the 2k identities are pairwise distinct" is wrong if it is read as a claim
  about identities that *change*;
- the proof's admission/disposition correspondence is wrong for B5;
- the paper's Algorithm 1 differs from the implementation in two details.

None of these breaks the result, and each has a short fix. No human has reviewed the proof, so the paper's "as we
prove" / "is proved" / "provably" do not yet meet the stated standard (finding F1).

## 1. Scope

| Item | Detail |
|---|---|
| Proof audited | `formal/LOCALITY_PROOF.md` (SHA-256 `56a80c16b09d6492ed978bcfa1810635b6b943b7ed39f24fced7873cb02c2aa7`) |
| Paper | `paper/main.tex` (`7c07415970ebc1f8…`): lines 66, 91, 164–169, 181–186, 366, 372, 382; `paper/supplementary.tex` (`8a7fb1f265752ba5…`): lines 85–106, 334–353 |
| Other documents read | `formal/README.md`; `formal/v4_locality_lifecycle_check.py` and `results/v4/formal/v4_locality_lifecycle_check.json` (read and understood, not reused); `docs/PROTOCOL_SPECIFICATION.md` §5.1 |
| Code | `src/pbti/registry.py` (`0160acfc…`), `verifier.py` (`9c2deed4…`), `b5.py` (`19dc1166…`), `selective.py` (`dc66ac8d…`), `envelope.py` (`6a1027d8…`), `identity.py`, `processor.py`, `review.py`, `audit.py` |
| Working copy | a scratch copy of the repository in the auditing workspace. Byte-identical to the read-only original: 521 files compared, 0 differences, before and after the audit. No file in the original was written; no `__pycache__` was created there. |
| New tools | `tools/proof_audit/model_check.py` (`91bb118e…`), `impl_check.py` (`1388395b…`); results in `tools/proof_audit/results/` |
| Not in scope | ProVerif models; B5 and PBTI-SH as designs (used only for contrast); experiment results |

## 2. Proof audit

Verdicts: **Correct**; **Implicit** (true, but uses an unstated assumption); **Imprecise** (wording needs
correction, substance fine); **Wrong** (false as stated).

| # | Item (location in LOCALITY_PROOF.md) | Statement | Verdict | Comment |
|---|---|---|---|---|
| D1 | Identities, predecessor (l.11–12) | e = (d,p,q), q ∈ ℕ; pred(e) = (d,p,q−1) for q > 0; none for q = 0 | Correct | Same as `verifier.py:318–319` and `b5.py:95–96`. The parser enforces non-negative integers (`envelope.py:101–102`). Links never cross devices or epochs. |
| D2 | Statements (l.13–14) | cd(s) = SHA-256 of the canonical observation "(payload, prev, key id)"; prev(s) is a digest or ⊥ | Correct; parenthetical incomplete | cd also covers did, ep, seq, ts, aid, sch, v and typ (`envelope.py:57–59`). The parser restricts prev to null or a 43-character string (`envelope.py:104`) and requires prev = null at q = 0 (`envelope.py:105`). The lemma needs no property of cd. |
| D3 | Evidence state (l.15–16) | E = (V, I), finite sets, initially empty | Correct | `Slot.versions` keys and `Slot.implied` (`registry.py:29–30`); a missing slot means ∅. |
| D4 | Admission update adm (l.17–21) | V(e) ∪= {cd}; I(pred e) ∪= {prev} iff q > 0 ∧ prev ≠ ⊥ | Correct | Same as `verifier.py:311, 318–324` and `b5.py:90, 95–99`. The paper's Algorithm 1 shows no guard (F9). |
| A1 | Only writes to V, I (l.23–25) | Only `_history` of PBTIVerifier and B5 writes V and I; ablations excluded | Correct (checked by code search) | The only writes are `verifier.py:311, 322–324` and `b5.py:90, 97–99`. PBTI-SH calls PBTI's `_history` (`selective.py:110`). The ablation guards are at `verifier.py:285–288, 295–296, 318`. |
| A2 | Admission = disposition (l.26) | ACCEPT/CONFLICT receipts are admissions; DUPLICATE/QUARANTINE/REJECT receipts do not change E | Correct for PBTI and PBTI-SH; **Wrong for B5** | B5 returns QUARANTINE/FEED_FORK_HOLD after it has written V and I (`b5.py:90–99` then `123–126`). My B5 runs had 355 such receipts; scenario X8 (F7). For PBTI: 0 mismatches in 14,036 receipts. |
| A3 | Release (l.27) | A reviewed release re-runs admission; if it reaches Rule L, it is an admission | Correct for PBTI; Imprecise | `verifier.py:487–497` calls `ingest(waive=…)`. "Reaches Rule L" should say "reaches the V write": a re-run can still end as DUPLICATE or as a quarantine for a reason that was not waived. A B5 FEED_FORK_HOLD release does not re-run admission and changes authority directly (`b5.py:164–184`). |
| D5 | Rule L classes (l.28–31) | ABSENT if V = ∅; COMMITTED if \|V∪I\| = 1; CONTESTED if \|V∪I\| ≥ 2; LOST excluded | **Imprecise (ill-formed as written)** | When V(e) = ∅ and I(e) ≠ ∅, two cases apply at once. This happens whenever a successor arrives before its predecessor; 36,975 of the 65,536 states of a 4-identity universe contain such an identity. The intended reading (an ordered case distinction) matches `registry.py:47–52` and the paper (main.tex:169, "a slot with an admitted version"). F4. |
| D6 | Authority (l.32–33) | PBTI: COMMITTED ∧ ¬τ, where τ changes only through revocation processing; B5 additionally requires e ∉ H | Correct; Implicit | `verifier.py:380–381`, `b5.py:63–64`. τ is written only at `verifier.py:156`, plus the T7 registry-tampering simulation (`audit.py:293–296`), which lies outside the trusted computing base (TCB) (main.tex:114); this TCB assumption is implicit. PBTI-SH's extra gate (`selective.py:52–53`) is mentioned only in E5. The paper's main text never defines "authority" or "admitted". |
| L0 | Lemma setting (l.37–40) | Any E, any finite S, applied sequentially; A(S) defined | Correct | The lemma also covers unreachable states, which makes it stronger. |
| La | Lemma (a) (l.42) | V′(x) = V(x) and I′(x) = I(x) for every x ∉ A(S) | Correct | 0 violations (check M1). |
| Lb1 | Lemma (b) bound (l.42–43) | \|A(S)\| ≤ k + m ≤ 2k | Correct | 0 violations (check M2). |
| Lb2 | Lemma (b) attainment (l.43–45) | \|A(S)\| = 2k exactly when the 2k identities are distinct (conditions listed) | Correct; one redundant clause | "No two share a predecessor" follows from "no two share an identity", because pred is injective. The equivalence held for every enumerated batch (M2). It is a statement about \|A(S)\| only, not about how many identities change (F5). |
| Pa | Proof of (a), induction (l.47–49) | Each step writes only e(s_{j+1}) and possibly pred(e(s_{j+1})) | Correct | The invariant could be stated explicitly: E_j agrees with E outside A(s_1…s_j) ⊆ A(S). |
| Pb | Proof of (b) (l.49–50) | Union of k and m singletons | Correct | |
| C1 | Corollary 1 (l.54–57) | With no lifecycle transition (gap closure, revocation processing, reviewer decision other than the re-run admission), cls and PBTI auth are unchanged outside A(S) | Correct for the lifecycle-free class; Implicit | Covers only the lifecycle-free class, not LOST (F3). In the code, "between E and E′" includes the time ticks that every `ingest()` runs first (`verifier.py:166`) (F10). |
| C1w | "In words" (l.59–61) | k statements change class and authority of at most 2k identities whatever the feed length; one contest withdraws at most the contested identity and its predecessor | Correct as a bound; Imprecise | Precise form: "the statement's own identity and its predecessor". |
| C2 | Corollary 2 (l.63–67) | adm is commutative and idempotent; CONTESTED absorbing; COMMITTED → CONTESTED only; ABSENT → COMMITTED/CONTESTED | Correct (model) | "COMMITTED can only become CONTESTED" means "stays COMMITTED or becomes CONTESTED". Holds for a fixed admitted set; that admission itself depends on order is stated (E1). 0 violations (M4, M5). |
| T | Tightness (l.69–71) | k gap-fill alternatives at non-adjacent q contest 2k identities | **Imprecise** | Needs two qualifiers: an uncontested genuine version at each e(s_i) (an equivocation, not a gap-fill), and a committed, uncontested predecessor whose digest differs from prev(s_i). For a gap-fill without a successor link, 2k classes change but only k are contested (construction [T]). F6. |
| B5c | B5 contrast (l.75–81) | B5 holds q ≥ f, up to n − f + 1 identities | Correct (matches code) | `b5.py:111–126, 133–161, 193–204`. Authority changed outside A(S′) in 77 of 300 B5 batches. |
| E1 | Admission decisions | Not covered by the lemma | Correct | Checks at `verifier.py:222–251, 300–308`; sequencing state at `verifier.py:330–335`. |
| E2 | Lifecycle transitions | Gap closure marks "a whole closed range" LOST; taint; review decisions | Correct in substance; detail inaccurate | Only slots that already exist are marked LOST (`verifier.py:126–131`). F11. |
| E3–E6 | Derived processing, undetected contamination, PBTI-SH, replication | Not covered by the lemma | Correct | E5 confirmed: for PBTI-SH, evidence and class are local (0 violations) and authority is not (89 of 300 batches). |
| M | Mechanical cross-checks (§6) | Reported as bounded checks, separate from the proof | Correct (descriptive) | Not reused here. |
| Lv | Liveness L1–L3 (§7) | Kept separate from safety | Correct | The proof uses none of L1–L3. Locality is a frame property: it says what cannot change and asserts no progress. |

**Boundary cases.** A q = 0 statement contributes only its own identity; its prev is ignored in the model. The
implementation rejects q = 0 with a non-null prev at parsing (`envelope.py:105`; scenario X1: `REJECT/MALFORMED`, no
state change). For q > 0 with prev = ⊥, no predecessor is touched; model and code agree (`verifier.py:318`). Overlapping
identities are deduplicated because A(S) is a set; adjacent statements share identities, which lowers the bound.

## 3. Paper vs proof statement

| Aspect | Proof note (LOCALITY_PROOF.md) | Paper, Proposition 1 (main.tex:181–186) | Supplement (supplementary.tex:334) | Match? |
|---|---|---|---|---|
| Hypothesis | Lemma: none. Corollary 1: no gap closure, no revocation processing, no reviewer decision other than the re-run admission | "with no gap closure or revocation processing in between" | Lists exclusions | **No.** The paper omits the reviewer-decision clause; harmless for PBTI (REJECT and STALE_REVIEW leave the registry unchanged, scenario X5), but the statements differ (F2). |
| Configuration | Main configuration; ablations `no_prev_link`, `no_conflict`, `edge_event_id` excluded | Not mentioned | "ablations that change the update" | **No** (F2) |
| A(S) | Defined as exactly the set | "Let A(S) **contain** …" | as proof | Imprecise: "contain" allows supersets, for which \|A(S)\| ≤ 2k would fail (F2) |
| Evidence | (a) | "V and I change only on A(S)" | as proof | Yes |
| Bound | \|A(S)\| ≤ k+m ≤ 2k; equality iff 2k distinct | "\|A(S)\| ≤ 2k"; "attained when the 2k identities are pairwise distinct (for example, gap-fill forgeries …)" | "change … only of the at most 2k identities … the bound is attained when these identities are pairwise distinct" | The bound matches. The attainment sentence is wrong if read as being about changed identities (F5). |
| Class | Lifecycle-free class; LOST explicitly excluded | "the Rule L class", which per main.tex:169 includes LOST | "class" | **No.** The paper claims more than the proof shows. The claim is true, because LOST is written only by gap closure, but the printed proofs omit this step (F3). |
| Proof step | "cls(x) depends only on V(x) and I(x)" | "a class depends only on V(e) ∪ I(e)" | "classes depend only on V(e) ∪ I(e)" | **Paper and supplement wrong as written:** V = ∅, I = {a} (ABSENT) and V = {a}, I = ∅ (COMMITTED) have the same union (F3) |
| Authority | PBTI: COMMITTED ∧ ¬τ (B5 differs; PBTI-SH only class) | "the authority" (not defined in the main text) | "authority" | Implicit (F12). Scope to PBTI is stated only indirectly (PBTI-SH excluded after the proposition; B5 given as contrast). |
| Exclusions | E1–E6 | main.tex:186 lists E1–E6 in short form | E1–E6 plus ablations | Mostly yes; the paper lacks ablations and reviewer decisions |
| Liveness | L1–L3, separate | Not stated next to the proposition (main.tex:169 gives the conditional "contested once … admitted") | Stated as separate | Acceptable |
| Claims citing it | – | main.tex:66 "as we prove, changes the **state** of at most 2k event identities" (no exclusions); :366 "withdraws at most two identities per contradictory statement"; :382 "provably changes the **state** …" | – | "State" is wider than class and authority, and :66 omits the hypothesis (F8) |

## 4. Implementation correspondence

All writes to V, I and to the flags that determine class and authority, found by searching all of `src/` (search
results reproduced in the audit session):

| Mechanism | File:line | What it writes | Effect outside A(S) | Covered by | Stated in paper? |
|---|---|---|---|---|---|
| PBTI admission | `verifier.py:281–351` (V `:311`; I `:318–324`; derived add `:336–341`; COMMITTED→CONTESTED removal for own **and predecessor** slot `:347–350`) | V, I, derived | none (0 violations, 1,000 histories) | Lemma | yes |
| Per-feed sequencing | `verifier.py:330–335`, `registry.py:67–90` | high-water mark, open gaps, max epoch | none directly; enables later STALE_SLOT, SEQ_JUMP, STALE_EPOCH and gap closure | E1 | yes ("gaps, horizons, epochs") |
| Admission checks | `verifier.py:222–251` (revocation, expiry, policy, freshness), `:300–308` | nothing | none | E1 | yes |
| Gap closure | `verifier.py:119–131` (`sl.lost = True` at `:130`), in `_tick` | lost flag | ABSENT → LOST (existing slots only) | E2 / hypothesis | yes |
| Revocation processing | `verifier.py:116–118, 146–159` (τ at `:156`, derived removal `:159`) | τ, derived | authority loss for every qualifying committed slot of the key | E2 / hypothesis | yes ("taint") |
| Lifecycle run inside admission and review | `ingest` → `advance(t)` at `verifier.py:166`; also `open_review` `:422`, `apply_review` `:437`, `finalize` `:140` | via `_tick` | as the two rows above | Hypothesis must cover these ticks | **no** (F10) |
| Reviewed release | `verifier.py:487–497` (re-run `ingest(waive)` at `:489`) | via admission | none (X5: release, failed release, LOST release) | admission | yes |
| Reject / stale review | `verifier.py:464–469` | case state only | none (X5) | proof: excluded; paper: not mentioned | partially (F2) |
| Parser | `envelope.py:101–105` | – | q = 0 with prev ≠ ⊥ rejected | consistent with adm | Algorithm 1 does not show it (F9) |
| B5 admission | `b5.py:67–131` (V `:90`; I `:95–99`) | V, I | evidence and class local (0 violations, 300 histories) | Lemma (a) | – |
| B5 hold receipt | `b5.py:123–126` | QUARANTINE issued after V and I were written | – | contradicts A2 (F7) | no |
| B5 feed hold | `b5.py:111–118, 133–161` (held `:148`, derived removal `:151`) | held set H | authority loss for every identity with q ≥ f (77 of 300 batches) | §4; Corollary 1 is PBTI-only | yes (contrast, main.tex:186) |
| B5 hold release, resume | `b5.py:164–184, 193–204` | H, derived | authority gain without admission | "reviewer decision" exclusion | implicitly |
| PBTI-SH gate | `selective.py:59–68, 107–139` (feed-wide provisional `:127–133`), `:142–149` (timeout) | prov, derived | authority changes across the feed (89 of 300 batches) | E5 | yes |
| T7 tamper simulation | `audit.py:293–296` | τ | arbitrary | outside TCB | TCB stated (main.tex:114) |

Answers to the task's questions:
- **Other writers of V and I:** none. The proof's claim is correct.
- **Release:** an admission. Its effects stay inside A({s}) (X5).
- **Gap closure and taint:** they change class or authority outside A(S). Both are excluded and stated in the paper.
  But they run inside `ingest()`, which neither the paper nor the proof says (F10).
- **Epoch handling:** changes only admission decisions (E1, stated).
- **B5 feed holds:** change authority, not class, outside A(S). Stated as the contrast, and Corollary 1 is
  PBTI-only. B5 breaks the disposition-based admission correspondence (F7).

## 5. Independent checker

Both checkers were written from the lemma statement only. Neither imports or adapts the project's
`formal/*check*.py`.

### 5a. Pure model (`tools/proof_audit/model_check.py`)

**Design.** Each identity has the digest alphabet {0, 1}. Its evidence is one nibble (two V bits, two I bits).
**Every** evidence state is enumerated, including states that no history can produce.

- Statement alphabet per identity: cd ∈ {0, 1} × prev ∈ {⊥, 0, 1}. This includes a non-null prev at q = 0, the
  boundary case that adm ignores.
- Batches: **all ordered sequences with repetition** of k ≤ 3 statements.
- Two engines:
  - a scalar engine that transcribes the definitions literally, using frozensets;
  - a numpy-vectorised engine.

  On 2 × 20,000 random pairs they gave 0 mismatches.
- Checks:
  - M1: lemma (a).
  - M2: \|A(S)\| ≤ k + m ≤ 2k, and \|A(S)\| = 2k ⇔ the proof's literal attainment condition.
  - M3: class and authority unchanged outside A(S), with τ ≡ false. This is the worst case: any τ makes the set of
    authority changes a subset of the class changes.
  - M4: every permutation gives the same E′.
  - M5: absorption and monotonicity.
- Counts: histograms of changed evidence, class and authority.

**Bounds and results** (0 violations everywhere):

| Universe | States | Batches | Cases | Max classes changed (k = 1 / 2 / 3) | 2k classes changed | \|A(S)\| = 2k but fewer than 2k classes changed |
|---|---|---|---|---|---|---|
| 1 device, 1 epoch, q 0–3 (4 identities) | all 65,536 | all 14,424 sequences | 945,291,264 | 2 / 4 / 4* | k=1: 36,864; k=2: 4,608 | k=1: 749,568 of 786,432; k=2: 2,092,544 of 2,097,152 |
| 1 device, 2 epochs, q 0–1 | all 65,536 | all 14,424 | 945,291,264 | 2 / 4 / 4* | k=1: 24,576; k=2: 4,608 | k=2: 2,092,544 of 2,097,152 |
| 2 devices, 1 epoch, q 0–1 | all 65,536 | all 14,424 | 945,291,264 | 2 / 4 / 4* | k=1: 24,576; k=2: 4,608 | k=2: 2,092,544 of 2,097,152 |
| 2 devices, 2 epochs, q 0–3 (16 identities), sampled states | random pool of 4,096 (1,024 for k=3) | all sequences k ≤ 2; 20,000 random k=3 batches with all 118,169 of their orders | 159,147,008 | 2 / 4 / 6 | k=3: 810 | k=3: 7,875,798 of 7,876,608 |
| 1 device, 1 epoch, q 0–5 (6 identities) | all 16,777,216 | the 64 k=3 batches with \|A(S)\| = 6 | 1,073,741,824 | – / – / 6 | 110,592 (0.010 %) | 1,073,631,232 |

\* \|A(S)\| ≤ 4 in 4-identity universes.

- **Total:** 4,068,762,624 cases, 0 violations. Run time 304.6 s (Python 3.13.18, numpy 2.5.3), on 2 vCPUs shared
  with the long job (load average about 2–3 when sampled before and after the run).
- **Order independence:** M4 held for every multiset; all permutations were compared.
- **Ill-formed class definition:** 36,975 of 65,536 states of each 4-identity universe contain an identity where
  the literal definition gives two classes (F4).
- **Tightness construction**, 16-identity universe, k = 1…8 at non-adjacent q:

  | Variant | Classes changed | Identities contested |
  |---|---|---|
  | equivocations whose prev contradicts a committed predecessor | 2k | 2k |
  | gap-fill (no genuine version), no successor link | 2k | k |
  | gap-fill with a successor link | 2k | 2, 3, 5, 6, 8, 9, 11, 12 for k = 1…8 |

### 5b. Real implementation (`tools/proof_audit/impl_check.py`)

**Design.**
- Universe: 104 real signed statements over 16 identities (2 devices × 2 epochs × q 0–3). Per identity with q > 0:
  contents {G, F} × prev ∈ {genuine predecessor digest, forged predecessor digest, null, a digest that names
  nothing}.
- Signatures are built with the library's public constructors (`LogicalObs`, `pbti_sign_obs`, `pbti_wire`), as in
  `tests/test_v4_oracle_traces.py`.
- Each history: a fresh verifier, a random base delivered in random order, then a batch of 1–3 random statements.
- Per identity, before and after the batch: (V, I, class, authority, derived presence, taint, lost).
- S′ = the admitted batch statements. Checks R1–R7: evidence, class, authority and derived presence change only on
  A(S′); \|A(S′)\| and the number of changed identities ≤ 2\|S′\|; registry V/I and class equal my own adm and Rule L
  applied to everything admitted; authority = COMMITTED ∧ ¬TAINTED = derived presence; ACCEPT/CONFLICT ⇔ V written;
  no slot outside the universe is created.

**Results** (7.6 s in total; source unchanged during the run):

| Run | Histories / receipts | Unexpected violations | Changed identities per batch (max, by number of admitted statements 1 / 2 / 3) | 2k′ reached |
|---|---|---|---|---|
| PBTIVerifier, main configuration | 1,000 / 10,803 | **0** | 2 / 4 / 5 | k′=1: 91 of 398; k′=2: 16 of 350; k′=3: 0 of 202 (k′=0: 50 batches, 0 changes) |
| PBTIVerifier, lifecycle active (`gap_close_ms` = 300; revocation before 30 % of batches) — hypothesis deliberately violated | 300 / 3,233 | 0 unexplained | up to 10 identities changed in batches with **no** admitted statement | 224 of 300 batches had changes outside A(S′), comprising 316 identity changes from gap closure, 292 from taint, 0 unexplained |
| B5FeedLevel (admission = V write) | 300 / 3,176 | 0 (evidence and class) | – | 355 QUARANTINE/FEED_FORK_HOLD receipts wrote V (F7); authority changed outside A(S′) in 77 batches (107 identities), as the design intends |
| SelectiveHoldVerifier | 300 / 3,358 | 0 (evidence and class) | – | authority changed outside A(S′) in 89 batches (108 identities), as E5 states |

Targeted scenarios on the real verifier:

| ID | Scenario | Result |
|---|---|---|
| X1 | q = 0 with non-null prev | `REJECT/MALFORMED:obs-prev-at-epoch-start`; no state change |
| X2 | G0 committed, then F1 whose prev matches nothing | `ACCEPT/COMMITTED` for (1); predecessor (0) goes COMMITTED → CONTESTED and leaves derived data (F9) |
| X3 | Bound reached: k = 1…8 equivocations (prev = forged predecessor) at non-adjacent q | exactly 2k identities changed and lost authority each time; 0 outside A(S) |
| X4 | Pairwise-distinct A(S) without 2k changes: empty state, S = (G1, G3) with genuine prevs | \|A(S)\| = 4, evidence changed at 4 identities, class at 2 (F5) |
| X5 | Review decisions | Release of a STALE_TS case, failed release (CONFLICT), LOST release (STALE_SLOT waived): all changes inside A({s}). REJECT and STALE_REVIEW: registry unchanged. |
| X6 | A gap older than the horizon closes during an unrelated delivery | (devA,0,2) goes ABSENT → LOST outside A(S); `lost_declared` = 2 but (devA,0,1) has no slot (F10, F11) |
| X7 | A revocation published before an unrelated delivery | all four committed devA slots tainted inside that delivery's `ingest()` (F10) |
| X8 | B5: hold receipt | `QUARANTINE/FEED_FORK_HOLD` after V(3) and I(2) were written (F7) |

Reproduction:

```
python3 -I tools/proof_audit/model_check.py          # about 5 min on 2 shared vCPUs
python3 -I tools/proof_audit/impl_check.py --n 1000 --n-contrast 300   # about 8 s
```

Exit status:
- `model_check.py` exits 0 if and only if there are no violations and no engine mismatches.
- `impl_check.py` exits 0 if and only if the two PBTIVerifier runs have no unexpected violation. The B5 and PBTI-SH
  unexpected counts, which do not affect the exit status, were also 0.

Both exited 0.

## 6. Findings

| ID | Severity | Description | Suggested correction |
|---|---|---|---|
| F1 | MAJOR | **Proof not reviewed by a human.** The paper says "as we prove" (main.tex:66), "Proof." (:184), "is proved" (:372), "provably" (:382) and "is proved in formal/LOCALITY_PROOF.md" (supplementary.tex:334). Under the stated standard these words need a complete, reviewed proof; no human has reviewed this one. The mathematics is correct (§2, §5), so this is about review status, not a defect in the result. | Before submission, a named author works through `PROOF_REVIEW_CHECKLIST_FOR_AUTHORS.md` and signs it off. Until then, use the wording in §7. |
| F2 | MINOR | **The paper's hypothesis and scope differ from the proof's.** Proposition 1 (main.tex:182) excludes only "gap closure or revocation processing". The proof's Corollary 1 also excludes reviewer decisions other than the re-run admission. The paper does not mention the ablation exclusion (it is in the proof and supplementary.tex:334). "Authority" is implicitly PBTI's, and A(S) is said to "contain" the identities instead of being defined as that set. For PBTI the missing reviewer clause is harmless (X5), so this is a consistency fix. | Use the corrected statement in the appendix: no lifecycle transition (gap closure, revocation processing, or a reviewer decision other than the admission it re-runs); PBTI main configuration; "Let A(S) be the set of …". |
| F3 | MINOR | **The printed proofs have two gaps.** (i) The paper claims "the Rule L class" is unchanged, and that class includes LOST (main.tex:169), but the proof covers only the lifecycle-free class ("LOST … is excluded from the lemma", LOCALITY_PROOF.md:30–31). (ii) The paper's proof (main.tex:184) and the supplement (:334) say "a class depends only on V(e) ∪ I(e)". This is false: V = ∅, I = {a} gives ABSENT and V = {a}, I = ∅ gives COMMITTED, with the same union. The conclusion still holds. | Write: "The class of x is a function of V(x), I(x) and the gap-closure flag λ(x); λ is written only by gap closure (`verifier.py:130`) and τ only by revocation processing (`verifier.py:156`), both excluded." |
| F4 | MINOR | **Class definition ill-formed** (LOCALITY_PROOF.md:29). When V(e) = ∅ and I(e) ≠ ∅, both "ABSENT" and "COMMITTED/CONTESTED" apply. Such states arise whenever a successor arrives first (Worked example 4 in the checklist). | "ABSENT if V(e) = ∅; otherwise COMMITTED if \|V(e) ∪ I(e)\| = 1 and CONTESTED if \|V(e) ∪ I(e)\| ≥ 2." |
| F5 | MINOR | **The attainment claim is wrong if read as being about changes.** "The bound is attained when the 2k identities are pairwise distinct" (main.tex:186), and in the supplement (:334) the same claim about the identities whose "evidence, class and authority" change. Distinctness is necessary and sufficient for \|A(S)\| = 2k, but it is not sufficient for 2k identities to change: over all 16^6 states, only 110,592 of 1,073,741,824 distinct-A(S) cases change all 6 classes. Minimal counterexample: empty state, S = (G1, G3) changes 2 classes (X4). Evidence counterexample: base {G1}, S = (F1 with prev g0) leaves I(0) unchanged. | "\|A(S)\| = 2k exactly when these identities are pairwise distinct. The number of identities whose class and authority change can also reach 2k, e.g. for k equivocations at pairwise non-adjacent sequence numbers whose prev contradicts a committed predecessor, but distinctness alone does not imply it." |
| F6 | MINOR | **Tightness paragraph lacks qualifiers** (LOCALITY_PROOF.md:69–71). "k such statements … contests 2k identities" holds only for equivocations at committed, uncontested identities with committed, uncontested predecessors whose digest ≠ prev. Gap-fills without successor links change 2k classes but contest only k. | State these qualifiers; call the construction "equivocation". |
| F7 | MINOR | **The disposition-based identification of admission is wrong for B5** (LOCALITY_PROOF.md:23–27). B5's `_history` is explicitly covered, yet it issues QUARANTINE/FEED_FORK_HOLD after writing V and I (`b5.py:90–99, 123–126`; 355 receipts; X8). B5 hold releases change authority without admission (`b5.py:164–184`). Lemma (a) still holds for B5 if admission means "the V write". | Define admission as "reaching the V write (`verifier.py:311`, `b5.py:90`)". Add: "for PBTI this coincides with ACCEPT/CONFLICT receipts; for B5 it also includes FEED_FORK_HOLD receipts". |
| F8 | MINOR | **"State" overclaims, and the contribution statement drops the hypothesis.** main.tex:66 ("as we prove, changes the state of at most 2k event identities", no exclusions) and :382 ("provably changes the state of at most two identities"). What is proved concerns V/I, the Rule L class and PBTI authority, without lifecycle transitions. An admission also changes per-feed state (`verifier.py:330–335`), on which a later gap closure may act for up to `max_seq_jump` identities. | "changes the Rule L class and authority of at most 2k event identities for k admitted statements, in the absence of lifecycle transitions (Proposition 1)". |
| F9 | MINOR | **Algorithm 1 differs from the implementation and from adm** (main.tex:164–166). (i) Line 164 adds prev to slot(seq−1).implied with no q > 0 / prev ≠ ⊥ guard. The code guards at `verifier.py:318`, and the parser rejects prev ≠ ⊥ at q = 0 (`envelope.py:105`). `docs/PROTOCOL_SPECIFICATION.md:150` has the q > 0 guard but not the prev ≠ ⊥ guard. (ii) Lines 165–166 imply that slots are contested and removed from derived data only on CONFLICT, but an ACCEPT can contest the predecessor (`verifier.py:318–327, 347–350`; X2). | Add the guard. After both branches add: "every slot that changed COMMITTED → CONTESTED (own or predecessor) is removed from derived data". |
| F10 | NOTE | **Lifecycle transitions run inside admission.** `ingest()` first calls `advance(t)` (`verifier.py:166`), which runs revocation processing, taint and gap closure; `open_review` and `apply_review` do the same (`:422`, `:437`). So "no gap closure or revocation processing in between" is a condition on time and schedule, not a property of admission. Without it, batches with zero admitted statements changed up to 10 identities (lifecycle-active run; X6, X7). | One sentence in the paper next to the proposition. |
| F11 | NOTE | **Gap closure marks LOST only on existing slots** (`verifier.py:126–131`). Other identities in the closed range get no slot and are reported ABSENT by state-based views, while admission treats them as closed (STALE_SLOT, `:301–302`) and `lost_declared` counts them (X6). E2 ("marks a whole closed range LOST") and the LOST definition (main.tex:169) are inaccurate at slot level. Outside the lemma. | Reword E2, or create LOST slots for the whole range. |
| F12 | NOTE | **Minor precision points.** (i) cd covers more than "payload, prev, key id". (ii) Redundant clause in (b). (iii) "Reaches Rule L" should be "reaches the V write". (iv) "Authority" and "admitted" are not defined in the paper's main text. (v) The verifier-integrity (TCB) assumption is implicit; the T7 tamper simulation writes τ (`audit.py:295`). (vi) The induction invariant is not stated. (vii) "COMMITTED can only become CONTESTED" should read "… or stay COMMITTED". | Editorial. |

No CRITICAL finding: neither the model checker nor the real verifier produced a counterexample to the proposition
under its hypothesis.

## 7. Recommendation on "prove" / "provably"

**Pending human review, the words are not justified by the stated standard (F1). After review and corrections they
are justified for the model-level statement.** The argument is elementary and, with F2–F6 fixed, complete. It is a
frame property of a set-union update, and it holds for PBTI's implementation by code inspection (§4) and the
independent checks (§5). "Provably" in the conclusion should then be limited to the Rule L class and authority under
the stated exclusions. The link from model to code is code inspection plus bounded checks; the paper should say so
rather than "does not depend on any bounded check" alone.

Suggested wording, usable **now**, before review:
- main.tex:66: "… and under which k admitted statements change the Rule L class and authority of at most 2k event
  identities when no lifecycle transition intervenes (Proposition 1; a short argument from the update definition is
  given in Section 3.4)".
- main.tex:184: "*Proof sketch.*" instead of "*Proof.*", and add the λ/τ sentence from F3.
- main.tex:372: "Proposition 1 follows from the update definition alone (argument in Section 3.4 and
  `formal/LOCALITY_PROOF.md`); it does not depend on any bounded check. That the reference implementation realizes
  this update rests on code inspection and the bounded checks."
- main.tex:382: "Per-identity containment, under which one admitted contradictory statement changes the Rule L class
  and authority of at most two identities (Proposition 1, under its stated exclusions), kept …"
- main.tex:186 and supplementary.tex:334: the attainment wording from F5.

After a named author signs the checklist with "accepted" or "accepted with corrections" (corrections applied),
"as we prove" and "Proof." can be restored, and "provably" can be kept with "(Proposition 1, with its exclusions)".

## Appendix A. Suggested corrected statement and proof (for the paper)

> **Proposition 1 (Locality of Rule L).** Let (V, I) be an evidence state, τ the taint flags and λ the gap-closure
> flags, and let S be a sequence of k statements admitted by PBTI in its main configuration (ablations excluded),
> with no lifecycle transition (gap closure, revocation processing, or a reviewer decision other than the admission
> it re-runs) in between. Let A(S) be the set consisting of the identity of every statement in S and, for each
> statement with a positive sequence number and a non-null prev, its predecessor identity. Then V and I change only
> on A(S); |A(S)| ≤ 2k, with equality exactly when these 2k identities are pairwise distinct; and the Rule L class
> (including LOST) and the authority (COMMITTED and not TAINTED) of every identity outside A(S) are unchanged.
>
> *Proof.* Admitting s adds cd(s) to V only at e(s) and, if q(e(s)) > 0 and prev(s) ≠ ⊥, adds prev(s) to I only at
> pred(e(s)) (Algorithm 1). By induction over S, V and I are unchanged outside A(S). The class of x is a function of
> V(x), I(x) and λ(x), and authority is in addition a function of τ(x). λ is written only by gap closure and τ only
> by revocation processing, and both are excluded. A(S) is the union of at most k statement identities and at most
> k predecessors. ∎
