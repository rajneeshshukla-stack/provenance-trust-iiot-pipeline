# PBTI V4 preregistration — Amendment 1 (A3 factorial cells)

Status: written after the freeze of `research/V4/PREREGISTRATION_V4.md` (frozen 2026-11-05T05:39:30Z; that file is
unchanged, see `PREREGISTRATION_V4.sha256`) and **before** any confirmatory A3 run was executed; the A0 replication
was running when this amendment was written. Its SHA-256 and that of its configuration file are recorded in
`research/V4/PREREGISTRATION_V4_AMENDMENT_1.sha256` (self-recorded time).

## Reason (disclosed data dependence)

The A3 pilot (seed 101, error check) was inspected beyond its error status: in the preregistered joint grid
(equivocation × suppressed runs, delayed successors, long suppression runs) PBTI retained a non-legitimate
observation at only one of 21 points (equivocation 5 % with long suppression runs 5 %: 3 per run), and every arm,
including B5S and PBTI-SH, retained the same 3 there. The V3 result that motivated A3 (PBTI 2.3 versus B5 0.9
retained forgeries per run) came from the fractional-factorial cells in which equivocation and suppressed runs were
both high **together with the factorial's other delivery factors** (loss, duplicates, reordering, long delay, clock
error); the joint grid does not contain those factors. This amendment adds those cells. Seed 101 is disjoint from the
confirmatory seeds 21–40, so the added test remains a test on fresh data, but the choice of cells is informed by the
V3 factorial (seeds 1–20) and by the pilot.

## Added campaign

* `experiments/v4_configs/amendment1/A3_factorial.json` (`A3_factorial`): the eight cells of the V3 2^(7-3)_IV design
  with equivocation high (runs 2, 3, 4, 5, 8, 9, 14, 15; high level 10 %), of which runs 3, 4, 8 and 15 also have
  suppressed runs high ("FG cells"); the same seven arms as A3_selective (PBTI, PBTI-SH, PBTI-SH-T30, B5-hist,
  B5-event, B5S, PBTI-R-hist); 120 s production, 180 s drain; seeds 21–40; audit on seeds 21–22; 1,120 runs.

## Hypotheses, family and gates

* Comparisons H3a (PBTI-SH vs PBTI), H3b (PBTI-SH vs B5-hist, B5-event, B5S, PBTI-R-hist) and H3c (PBTI-SH-T30 vs
  PBTI-SH) on all eight cells, for O1, O2, NLX, W and AV5, with the margins and the classification of the original
  preregistration (Section 4). Separate family: campaign `A3F` × outcome (Holm within it).
* **G3F**: "selective holds reduce retained forgeries in the condition that motivated them" only if H3a classifies O1
  (or NLX) as *better beyond margin* in at least two of the four FG cells (runs 3, 4, 8, 15).
* **G4F**: G3F and, at those cells, PBTI-SH not *worse beyond margin* than B5-hist on W.
* The original gates G3 and G4 (joint grid) are evaluated unchanged and reported regardless of the outcome here.
  The manuscript may present PBTI-SH as a useful extension only if G4 or G4F holds, stating which.

## Execution

Run after the frozen chain (A0, A1, A3_selective, A3_scenarios) completes, with the frozen source; outputs
`results/v4/raw/A3_factorial.jsonl`.
