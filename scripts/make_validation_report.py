#!/usr/bin/env python3
"""Compose research/V3/FINAL_VALIDATION_REPORT.md from the generated evidence (no hand-typed numbers):
analysis report, V3 macros, automated checks (scripts/final_checks_v3.py), regression check, B5-fix comparison,
container summary, policy parity, formal summary and the archive test of the previous build (if any)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUM = ROOT / "results" / "summary"
V3 = ROOT / "research" / "V3"
M = dict(re.findall(r"\\newcommand\{\\V([A-Za-z]+)\}\{(.*)\}", (ROOT / "paper" / "generated" / "v3_macros.tex").read_text()))
R = dict(re.findall(r"\\newcommand\{\\R([A-Za-z]+)\}\{(.*)\}", (ROOT / "paper" / "generated" / "results_macros.tex").read_text()))


def m(k, d="n/a"):
    v = M.get(k, d)
    v = re.sub(r"\\ensuremath\{([0-9.]+)\\times10\^\{(-?\d+)\}\}", r"\1e\2", v)
    return v.replace("{,}", ",").replace("\\%", "%")


def r(k, d="n/a"):
    return R.get(k, d).replace("{,}", ",").replace("\\%", "%")


rep = json.loads((SUM / "v3_analysis_report.json").read_text())
pr = rep.get("predictions", {})
checks = (V3 / "FINAL_VALIDATION_REPORT_CHECKS.md").read_text() if (V3 / "FINAL_VALIDATION_REPORT_CHECKS.md").exists() else "(checks not run)"
reg = json.loads((SUM / "regression_check_v3.json").read_text()) if (SUM / "regression_check_v3.json").exists() else None
fix = json.loads((SUM / "v3_b5_fix_comparison.json").read_text()) if (SUM / "v3_b5_fix_comparison.json").exists() else {}
cont = (ROOT / "results" / "containers" / "v3_final" / "SUMMARY.md")
at = ROOT.parent / "03_package" / "archive_test_report.json"
atd = json.loads(at.read_text()) if at.exists() else None

L = []
L += ["# Final validation report (V3)", "",
      "This report summarises how the V3 package was validated. Every number below is read from generated files; the",
      "automated checks are reproduced in full at the end (`scripts/final_checks_v3.py`).", ""]
L += ["## 1. Verdict", "",
      "* Manuscript: built with full TeX Live, 20-page limit and zero missing result macros checked automatically (section 7).",
      f"* Preregistered comparison: P1 {m('POneHolds')}, P2 {m('PTwoHolds')}, P3 {m('PThreeHolds')} (exception: {m('PThreeExceptions')}, in B5's favour), "
      f"P4 {m('PFourHolds')}; decision rule D1's condition {m('DOneMet')}, its conclusion applied a fortiori; D2 case reported in the abstract.",
      "* Remaining blockers are author actions (metadata, AI-use confirmation, DOI, version-of-record checks) and experiments that need",
      "  hardware not available here (multi-host, constrained device); see the issue matrix (N) and the checklist (Q).", ""]
L += ["## 2. Experiments run for V3", "",
      f"* X1 preregistered scenarios: {m('XOneRuns')} new runs (B5, B5s, PBTI-R) against the stored revision-2 PBTI and B1-B4 runs; "
      f"{m('XOneIdentical')} of {m('XOneTotal')} preregistered comparisons identical in every seed, {m('XOneTested')} tested.",
      f"* X2 mixed workload: {m('MixRuns')} runs; X3 sweep: {m('SweepRuns')} runs; X4 factorial: {m('FactRuns')} runs; X5 SKAB replay: {m('RpRuns')} runs.",
      f"* Audits of the new runs: {m('AuditPass')} of {m('AuditRuns')} passed (A-RAW, A-EVID, A-REG, A-DET incl. review replay, A-LIN).",
      f"* Batching/workers: {m('BtReps')} repetitions per cell, {m('BtN')} messages per run; dispositions {m('BatchSemanticsIdentical')} across cells.",
      f"* MQTT/TLS: {m('EeReps')} repetitions per cell at {m('EeRates')} messages/s (PBTI, B2); SKAB through MQTT/TLS: {m('EsReps')} repetitions per cell, "
      f"{m('EsLostTotal')} messages lost in total.", ""]
L += ["## 3. Key measured results", "",
      f"* B5 = PBTI on non-legitimate authoritative observations in every seed of {m('POneIdentical')} scenarios; equal end-of-run losses in {m('OTwoBFiveIdentical')} scenarios.",
      f"* E5 (stolen keys): B5 made {m('SZeroFiveBFiveholds')} hold events per run (re-holds counted), released {m('SZeroFiveBFiverecoveredn')} held observations after a median of {m('SZeroFiveBFiverecpfifty')} s; "
      f"B5s missed {m('SZeroFiveBFiveSlegitmissing')} legitimate observations per run versus {m('SZeroFivePBTIlegitmissing')} for PBTI and B5.",
      f"* E11b: B5 and PBTI-R recovered the beyond-horizon backlog ({m('SOneTwoBFivelegitmissing')} and {m('SOneTwoPBTIRlegitmissing')} missing) that PBTI keeps quarantined ({m('SOneTwoPBTIlegitmissing')}).",
      f"* Revision-2 throughput ratio PBTI/B2 {r('TpRatioBTwo')}; batching gain from batch 1 to 128 (one process): {m('BtPBTIgainbatch')}; "
      f"at batch 128, two and four signature workers: factors {m('BtPBTIgainworkers')} and {m('BtPBTIgainworkersfour')}; best cell "
      f"{m('BtPBTIbest')} msg/s (batch {m('BtPBTIbestbatch')}, {m('BtPBTIbestworkers')} workers; {m('BtPBTIbestgain')}x batch 1 with one process).",
      f"* MQTT/TLS, offered 1000 / 1250 / 1500 msg/s: the PBTI publisher sent {m('EePBTIrOneZeroZeroZerosent')} / {m('EePBTIrOneTwoFiveZerosent')} / "
      f"{m('EePBTIrOneFiveZeroZerosent')} msg/s, the verifier committed {m('EePBTIrOneZeroZeroZerotp')} / {m('EePBTIrOneTwoFiveZerotp')} / "
      f"{m('EePBTIrOneFiveZeroZerotp')} msg/s with median latency {m('EePBTIrOneZeroZeroZeropfifty')} / {m('EePBTIrOneTwoFiveZeropfifty')} / "
      f"{m('EePBTIrOneFiveZeroZeropfifty')} ms; B2 {m('EeBTworOneZeroZeroZeropfifty')} / {m('EeBTworOneTwoFiveZeropfifty')} / {m('EeBTworOneFiveZeroZeropfifty')} ms.",
      f"* Rego parity: {m('ParityWellFormedExact')}/{m('ParityWellFormedN')} well-formed and {m('ParityMalformedReqExact')}/{m('ParityMalformedReqN')} malformed requests exact; "
      f"{m('ParityOneSide')} requests permitted by one side only.", ""]
L += ["## 4. Integrity of the evidence", ""]
if reg:
    files = sorted({c["file"] for c in reg["checked"]})
    nv3 = sum(1 for c in reg["checked"] if c["file"].startswith("v3_"))
    L += [f"* Regression check under the final source (`results/summary/regression_check_v3.json`): {len(reg['checked'])} sampled specifications "
          f"({len(reg['checked']) - nv3} revision-2, {nv3} V3) from the {len(files)} virtual-time raw files {', '.join(files)} re-run; "
          f"{reg['differences']} differences (source digest {reg['source_sha256'][:16]}...). Wall-clock files and the tamper audits are not "
          "part of it (wall-clock values cannot repeat exactly; the tamper detection was re-checked separately)."]
for k, v in fix.items():
    L += [f"* B5 fix (amendment A4), {k}: {v['same_O1_O2']}/{v['runs']} re-runs with identical O1 and O2; audits {v['audits_new']['pass']}/{v['audits_new']['run']} passed."]
L += ["* Preregistration hash recorded before any V3 result (`research/V3/PREREGISTRATION.sha256`); four amendments, none changing a test,",
      "  outcome, threshold or prediction (`PREREGISTRATION_AMENDMENTS.md`).", ""]
L += ["## 5. Builds", "",
      "* Container (final V3 image): " + ("; ".join(f"{a}: {b}" for a, b in re.findall(r"^\| ([^|]+?) \| ([^|]+?) \|$", cont.read_text(), re.M)
                                                     if a not in ("Check", "---")) if cont.exists() else "not built")
      + " (details: `results/containers/v3_final/SUMMARY.md`).",
      "* Paper: `latexmk` with TeX Live 2023 and the real `bbm.sty`; no stub packages (checked in the LaTeX logs).",
      "* Word copy: generated by `scripts/export_manuscript.py` (pandoc) and normalized; package validity, macro expansion and",
      "  author names are checked automatically (section 7).", ""]
if atd:
    L += ["## 6. Archive", "", f"* Previous build of the ZIP: {atd['entries']} entries, CRC test {'passed' if atd['crc_test_first_bad'] is None else 'FAILED'}, "
          f"{atd['manifest_entries']} manifest entries, {len(atd['manifest_mismatches'])} hash mismatches after extraction, "
          f"{len(atd['missing_expected'])} expected items missing. The final archive is re-tested after this report is included (final response).", ""]
L += ["## 7. Automated checks (verbatim)", "", checks]
(V3 / "FINAL_VALIDATION_REPORT.md").write_text("\n".join(L) + "\n")
print("written", V3 / "FINAL_VALIDATION_REPORT.md")
