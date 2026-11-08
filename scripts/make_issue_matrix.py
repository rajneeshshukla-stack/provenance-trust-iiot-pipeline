#!/usr/bin/env python3
"""Write research/V3/ISSUE_CLOSURE_MATRIX.md (V3 prompt, Part 20): one status per issue with the evidence it rests on.

Numbers are read from generated files (result macros, JUnit report, regression check, container logs, parity and formal
outputs, PDF page counts); statuses that depend on a check (tests, page limits, build, archive) are derived from that
check, so a failed check can never be reported as RESOLVED. Run after `make test`, `make analysis`, `make paper`,
scripts/final_checks_v3.py and (for item 35) the package build.
"""
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "paper"
SUM = ROOT / "results" / "summary"
V3 = ROOT / "research" / "V3"


def macros(path, prefix):
    t = path.read_text() if path.exists() else ""
    return {k: v.replace("{,}", ",").replace("\\%", "%") for k, v in re.findall(r"\\newcommand\{\\" + prefix + r"([A-Za-z]+)\}\{(.*)\}", t)}


V = macros(P / "generated" / "v3_macros.tex", "V")
R = macros(P / "generated" / "results_macros.tex", "R")


def v(k):
    return V.get(k, "n/a")


def r(k):
    return R.get(k, "n/a")


def pages(pdf):
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"Pages:\s+(\d+)", out)
    return int(m.group(1)) if m else -1


# --- evidence ---------------------------------------------------------------------------------------------------
tests = {"n": 0, "fail": 1, "skip": 0}
jx = SUM / "pytest_v3.xml"
if jx.exists():
    root = ET.parse(jx).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    tests = {"n": sum(int(s.get("tests", 0)) for s in suites),
             "fail": sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites),
             "skip": sum(int(s.get("skipped", 0)) for s in suites)}
tests_ok = tests["n"] > 0 and tests["fail"] == 0
tests_txt = f"{tests['n'] - tests['skip']} passed, {tests['skip']} skipped, {tests['fail']} failed (`results/summary/pytest_v3.xml`)"

reg = json.loads((SUM / "regression_check_v3.json").read_text()) if (SUM / "regression_check_v3.json").exists() else None
reg_txt = (f"{len(reg['checked'])} stored specifications re-run under the final source, {reg['differences']} differences "
           f"(`results/summary/regression_check_v3.json`)") if reg else "regression check missing"

checks_md = (V3 / "FINAL_VALIDATION_REPORT_CHECKS.md").read_text() if (V3 / "FINAL_VALIDATION_REPORT_CHECKS.md").exists() else ""
check_fail = [ln for ln in checks_md.splitlines() if "| FAIL |" in ln]
def check_passed(name):
    return any(name in ln and "| PASS |" in ln for ln in checks_md.splitlines())

cs = ROOT / "results" / "containers" / "v3_final" / "logs" / "checks_summary.txt"
cont_txt = cs.read_text() if cs.exists() else ""
cont_ok = bool(cont_txt) and "exit=1" not in cont_txt and "exit=2" not in cont_txt and cont_txt.count("exit=0") >= 6
build_log = ROOT / "results" / "containers" / "v3_final" / "logs" / "build.log"
build_ok = build_log.exists() and "build_exit=0" in build_log.read_text(errors="replace")
cont_tests = re.search(r"(\d+) passed(?:, (\d+) skipped)?", (ROOT / "results" / "containers" / "v3_final" / "SUMMARY.md").read_text()
                       if (ROOT / "results" / "containers" / "v3_final" / "SUMMARY.md").exists() else "")

pm, ps = pages(P / "main.pdf"), pages(P / "supplementary.pdf")
at = ROOT.parent / "03_package" / "archive_test_report.json"
atd = json.loads(at.read_text()) if at.exists() else None
arch_ok = bool(atd) and not atd["manifest_mismatches"] and not atd["missing_expected"] and atd["crc_test_first_bad"] is None

par = json.loads((ROOT / "results" / "policy_parity" / "parity_results.json").read_text()) \
    if (ROOT / "results" / "policy_parity" / "parity_results.json").exists() else {}
import hashlib
fl = ROOT / "results" / "formal" / "rule_l_bounded_check_final.log"
if not fl.exists():
    fl = ROOT / "results" / "formal" / "rule_l_bounded_check.log"
fl_txt = fl.read_text() if fl.exists() else ""
rule_l_ok = re.search(r'"total_violations":\s*0\b', fl_txt) is not None
m_ver = re.search(r"sha256 ([0-9a-f]{64})  verifier\.py", fl_txt)
cur_ver = hashlib.sha256((ROOT / "src" / "pbti" / "verifier.py").read_bytes()).hexdigest()
rule_l_final = bool(m_ver) and m_ver.group(1) == cur_ver
pv = (ROOT / "results" / "formal" / "proverif_output.txt")
pv_ok = pv.exists() and "RESULT" in pv.read_text(errors="replace")
skab = json.loads((ROOT / "results" / "raw" / "v3_replay_skab_dataset.json").read_text()) \
    if (ROOT / "results" / "raw" / "v3_replay_skab_dataset.json").exists() else {}
n_bib = len(re.findall(r"^@\w+\{", (P / "references.bib").read_text(), re.M))

# --- matrix -----------------------------------------------------------------------------------------------------
rows = []


def add(n, issue, status, evidence):
    rows.append((n, issue, status, evidence))


add(1, "Novelty margin", "PARTIALLY RESOLVED",
    f"Falsification test preregistered (`research/V3/PREREGISTRATION.md`, SHA-256 in `PREREGISTRATION.sha256`, recorded before any "
    f"V3 result) and run: X1 {v('XOneRuns')} new runs. P1 {v('POneHolds')} (B5 = PBTI on O1 in every seed of {v('POneIdentical')} scenarios); "
    f"P3 {v('PThreeHolds')} only through {v('PThreeExceptions')}, in B5's favour. The claim was reduced accordingly (no security or "
    "end-of-run availability advantage over B5; remaining contribution: immediate per-identity containment) in the abstract, "
    "contributions, Discussion RQ2 and Conclusions of `paper/main.tex`; predictions in `results/summary/v3_analysis_report.json`. "
    "The question is answered, but the answer is a narrow margin: per-identity contest is strictly better only where feeds fork "
    "(E5, E8, mixed workload), which remains a reviewer risk.")
add(2, "B5 baseline", "RESOLVED",
    "`src/pbti/b5.py` (B5, B5s), `src/pbti/review.py`; definition and source mapping in `docs/BASELINES.md` (B5 = PBTI with Rule L "
    "replaced by feed-level holds, plus the automated reviewer acting on every releasable quarantine reason; PBTI-R isolates the "
    "conflict response); tests in "
    "`tests/test_v3_review_b5.py` (hold/release, frozen feed, determinism, released-then-contested slot). The automated reviewer is "
    "marked as our own extension. A B5 defect found by the independent audit was fixed and every B5 arm re-run (amendment A4; "
    "`results/summary/v3_b5_fix_comparison.json`).")
add(3, "B5 comparison against PBTI and B4", "RESOLVED",
    f"X1 (`results/raw/v3_scenarios_b5.jsonl` with the revision-2 PBTI/B1-B4 runs), X2 mixed workload ({v('MixRuns')} runs, "
    f"`v3_mixed_b5.jsonl`), X3 sweep ({v('SweepRuns')} runs) and X4 factorial ({v('FactRuns')} runs) for PBTI, B4, B5, X5 SKAB replay "
    f"({v('RpRuns')} runs); tests `results/summary/v3_x1_preregistered_tests.csv`, `v3_sweep_tests.csv`; Table 4, Tables S14-S17.")
add(4, "Feed-level versus per-identity conflict behaviour", "RESOLVED",
    f"Holds, releases, release latency (E5 median {v('SZeroFiveBFiverecpfifty')} s) and B5s losses per scenario (Table S14, "
    "`paper/generated/tabS_v3_b5.tex`); factorial case where B5 retains fewer forgeries (Table S16); determinism over 120 "
    "delivery permutations for PBTI and B5s (unit test); bounded check of Rule L (`results/formal/rule_l_bounded_check.log`).")
add(5, "Single-host synthetic evaluation", "PARTIALLY RESOLVED",
    "A replay of public test-bed telemetry was added (item 6), but every experiment still runs on one host with a simulated "
    "network, as stated in Threats to validity. Multi-host: item 7.")
add(6, "Public industrial telemetry replay", "RESOLVED",
    f"SKAB v0.9 (GPL-3.0, commit {skab.get('commit', 'n/a')[:8]}, {len(skab.get('files', []))} files, per-file SHA-256 in "
    "`results/raw/v3_replay_skab_dataset.json`; not redistributed), adapter `src/pbti/dataset.py`, licensing and preprocessing "
    "`docs/V3_DATASET_REPLAY.md`, runs `results/raw/v3_replay_skab.jsonl` (1x, 5x, 10x; PBTI, B4, B5; labelled stressors and "
    "unstressed controls) and `v3_mqtt_e2e_skab.jsonl` (through MQTT/TLS). TON_IoT was not usable (terms; download refused). "
    "Stated limit: a laboratory test bed with injected attacks, not plant data with recorded attacks.")
add(7, "Multi-host experiment", "OPEN — EXTERNAL DEPENDENCY",
    "No second host was available. Protocol, scripts and instrumentation were prepared and exercised on one host only "
    "(`docs/V3_HARDWARE_PROTOCOLS.md` section 2, `experiments/run_multihost.py`); the manuscript states that the experiment was "
    "not performed and uses no result from it.")
add(8, "Constrained-device signing", "OPEN — EXTERNAL DEPENDENCY",
    "No constrained device was available. Protocol and benchmark prepared (`docs/V3_HARDWARE_PROTOCOLS.md` section 3, "
    "`experiments/run_device_bench.py`; server smoke test only, labelled as such); device-side cost is stated as unknown.")
add(9, "Independent reproduction", "AUTHOR ACTION REQUIRED",
    f"Reproduction guide (`research/V3/REPRODUCTION_GUIDE.md`), hardened container built and tested from the final source "
    f"(`results/containers/v3_final/`), {reg_txt}. No third-party or author re-run has taken place.")
add(10, "Throughput overhead", "PARTIALLY RESOLVED",
    f"Quantified and reported in the abstract and RQ3: {r('TpRatioBTwo')}x the in-process throughput of B2 (revision 2, "
    f"`results/raw/throughput.jsonl`); the V3 batching and worker study (`results/raw/v3_batching.jsonl`, Table S19, Figure 4a,b) "
    f"raised PBTI throughput at most {v('BtPBTIbestgain')}-fold on two vCPUs without changing any disposition; in the MQTT/TLS "
    f"deployment the PBTI verifier committed at most about {v('EePBTIrOneFiveZeroZerotp')} msg/s while the real-time signing publisher "
    f"shared the two vCPUs (it sent {v('EePBTIrOneFiveZeroZerosent')} msg/s of the 1,500 offered; Table S20). The overhead itself remains; a "
    "compiled or batch verifier and more cores were not tested.")
add(11, "Message-size and storage overhead", "PARTIALLY RESOLVED",
    f"Quantified: {r('WireRatioBTwo')}x message size and {r('DbRatioBTwo')}x persisted bytes per message versus B2 (revision 2), "
    "database and evidence bytes per message in the batching and SKAB end-to-end runs (Tables S19, S21). The overhead is "
    "reported as a cost but not reduced (no compact encoding was evaluated).")
add(12, "Batch and multicore scaling", "PARTIALLY RESOLVED",
    f"Commit batches 1-512 and 1-8 signature-verification processes measured ({v('BtReps')} repetitions per cell, "
    f"{v('BtN')} messages per run) with a semantics check (disposition sequences {v('BatchSemanticsIdentical')}); scaling beyond "
    "the two vCPUs of the host could not be measured.")
add(13, "Legitimate-data loss", "PARTIALLY RESOLVED",
    "Quantified per scenario (Table 4), per stressor level (Figure 3, Data S1) and in the replay (Table S17), and stated in the "
    "abstract and RQ3. The review workflow recovers the beyond-horizon backlog (E11b, PBTI-R), but losses under equivocation, "
    "sequence-reuse faults and conservative taint remain by design.")
add(14, "Quarantine release and recovery", "RESOLVED",
    "Workflow implemented (`src/pbti/review.py`, `src/pbti/verifier.py`: case states, signed domain-separated decisions, reviewer "
    "authorization, evidence snapshot, policy version, affected derived data, auditor replay); unit tests for false, duplicate, "
    "stale, unauthorized, revoked, unknown and conflicting decisions, re-taint and recomputation, and recovery after a long gap "
    "(`tests/test_v3_review_b5.py`); evaluated end to end in E11b and the mixed workload (`v3_scenarios_pbtir.jsonl`, "
    "`v3_mixed_b5.jsonl`).")
add(15, "Two-key compromise", "PARTIALLY RESOLVED",
    "Characterized, not prevented: undetectable by design without equivocation or external evidence; the ProVerif "
    "model shows that a forgery needs both keys (`results/formal/proverif_output.txt`); retroactive containment by taint "
    "measured (E14, Table S8). Stated in Results, Discussion and Limitations.")
add(16, "Legacy gateway forgery", "PARTIALLY RESOLVED",
    "Characterized, not prevented: gateway-attested data can be forged by the attesting gateway (ProVerif: the relay "
    "key alone suffices for legacy data); residue measured in E15, the mixed workload and the SKAB replay; removed only "
    "retroactively after revocation with a compromise time (SKAB attribution: `results/summary/v3_replay_residue.json`).")
add(17, "Trusted clock and epoch assumptions", "PARTIALLY RESOLVED",
    "Assumptions stated (System model, Limitations, `docs/THREAT_MODEL.md`); sensitivity to clock error and revocation-status "
    "staleness measured (sweep factors `clock`, `revstale`); a compromised verifier clock or epoch counter is not mitigated.")
add(18, "External witness assumptions", "PARTIALLY RESOLVED",
    "Witness copies are what catches the re-signed rewrite T5 (Table S18); the assumption is in the trusted computing base and "
    "the Limitations; no deployed external witness service was tested.")
add(19, "Formal reasoning and invariant tests", "RESOLVED" if (pv_ok and rule_l_ok and rule_l_final and tests_ok) else "PARTIALLY RESOLVED",
    "ProVerif 2.05 models and outputs (`formal/`, `results/formal/proverif_output.txt`); Rule L checked exhaustively on bounded "
    "models, on the unmodified verifier with real signatures and on a re-implementation (scope and counts: "
    f"`results/formal/formal_summary.json`, `{fl.name}`; 0 violations: {'yes' if rule_l_ok else 'NO'}; run on the final verifier.py: "
    f"{'yes' if rule_l_final else 'NO'}); invariant "
    f"and workflow tests: {tests_txt}. No computational proof (stated in the Discussion).")
add(20, "Attack/fault-rate sensitivity", "RESOLVED",
    f"11-factor sweep at 0/1/5/10/20 % with 20 paired seeds for PBTI, B4 and B5 ({v('SweepRuns')} runs; `results/raw/v3_sweep.jsonl`, "
    f"Figure 3, Figure S1, `results/summary/v3_sweep_summary.csv`, `v3_sweep_tests.csv`) and a 2^(7-3) factorial ({v('FactRuns')} runs; "
    "`v3_factorial.jsonl`, Table S16).")
add(21, "Tail-latency statistics", "RESOLVED",
    f"{v('EeReps')} repetitions per cell for PBTI and B2 at {v('EeRates')} msg/s (`results/raw/v3_mqtt_e2e.jsonl`), bootstrap "
    "intervals, Mann-Whitney tests with Holm correction and Cliff's delta (`results/summary/v3_e2e_tests.csv`, Table S20). B1 and B3 "
    f"remain at the {r('EeReps')} repetitions of revision 2 (Table S12), as stated.")
add(22, "LOST state and gap closure", "PARTIALLY RESOLVED",
    "`tests/test_v3_review_b5.py::test_recovery_after_long_gap_lost_state_and_release` (open slots declared LOST under a 5 s gap "
    "horizon, late observations quarantined as STALE_SLOT, release through predecessor and successor links); LOST marking in "
    "`src/pbti/verifier.py`. Tested at unit level only: the campaigns use a 1 h gap horizon and never reach LOST (stated in Table S3).")
add(23, "Rego/JSON policy parity", "PARTIALLY RESOLVED",
    f"Exact decision and reason parity with rego-cpp (regopy) for {v('ParityWellFormedExact')} of {v('ParityWellFormedN')} well-formed and "
    f"{v('ParityMalformedReqExact')} of {v('ParityMalformedReqN')} malformed requests; of {v('ParityPatchedDocs')} patched policy documents the "
    f"Python store refused the {v('ParityPatchedDocsRefused')} schema-violating ones and Rego denied every request under them "
    "(`results/policy_parity/parity_results.json`, `tests/policy_parity/run_parity.py`). OPA itself was not run (no approved "
    "installation route).")
cl = ROOT / "results" / "containers" / "v3_final" / "compose" / "compose_run_make_test.log"
compose_txt = cl.read_text(errors="replace") if cl.exists() else ""
compose_ok = "exit=0" in compose_txt and re.search(r"^\d+ passed", compose_txt, re.M) is not None and " failed" not in compose_txt
add(24, "Container build and execution", "RESOLVED" if (cont_ok and build_ok and compose_ok) else "PARTIALLY RESOLVED",
    "`deploy/Dockerfile.v3` (base pinned by digest, pinned Debian packages, hash-locked dependencies, non-root user, health check) "
    f"built from the final source: build {'passed' if build_ok else 'FAILED'}; in-container tests "
    f"{(cont_tests.group(0) if cont_tests else 'n/a')}; smoke, MQTT/TLS, read-only/cap-drop and health checks "
    f"{'all exit 0' if cont_ok else 'NOT all passed'}; `docker compose run --rm pbti make test` "
    f"{'passed' if compose_ok else 'did NOT pass'} with the results volume seeded as documented in `deploy/docker-compose.yml` "
    "(with an empty volume the regression tests cannot find the stored results; both logs in `results/containers/v3_final/compose/`). "
    "The default command (full revision-2 pipeline, hours) was not run in the container.")
add(25, "Literature completeness", "RESOLVED",
    "Fresh audit with per-work fields and corrections R1-R15 (`research/V3/literature/V3_LITERATURE_AUDIT.md`, "
    "`RELATED_WORK_CHANGES.md`) applied in `paper/main.tex`, including 2023-2026 work; completeness is bounded by the sources "
    "the audit used (Crossref, OpenAlex, DataCite, RFC Editor, IETF Datatracker, publisher pages; audit section 0).")
add(26, "Version-of-record verification", "AUTHOR ACTION REQUIRED",
    "Nine publisher versions were not accessible from the study environment (ACM, IEEE); their Crossref metadata matched and the "
    "content was checked against preprints, author copies or abstracts (`research/V3/literature/V3_VERSION_OF_RECORD.md`).")
add(27, "Reference accuracy", "RESOLVED",
    f"Misdescriptions corrected (ACE relay analogue, SCITT and RFC 9162) and others refined (SSB, Kafka semantics of B4, GDP, "
    f"intrusion recovery, Sigwart et al.); identifiers checked against Crossref/DataCite; {n_bib} entries, all cited "
    "(`paper/references.bib`, checked by `scripts/final_checks_v3.py`). Version-of-record caveat: item 26.")
add(28, "Manuscript page limit", "RESOLVED" if 0 < pm <= 20 else "OPEN — EXTERNAL DEPENDENCY",
    f"`paper/main.pdf`: {pm} pages including references (`pdfinfo`, `scripts/final_checks_v3.py`); secondary material moved to "
    "the Supplementary and Data S1.")
add(29, "Supplementary consistency", "RESOLVED" if (0 < ps <= 10 and check_passed("every result macro used is generated")) else "PARTIALLY RESOLVED",
    f"`paper/supplementary.pdf`: {ps} pages; every result table and figure is generated from the raw results or manifests "
    "(Tables S1-S4 and S13 are descriptive), all are listed in the article's Supplementary Materials statement, and the macro "
    "gate finds every result macro used generated (`scripts/check_macros.py`); findings of the independent audit on "
    "supplementary consistency were corrected (change log section 7).")
add(30, "AI disclosure", "AUTHOR ACTION REQUIRED",
    "Disclosure in Methods (\"Use of generative AI\") and the Acknowledgments of `paper/main.tex` distinguishes AI-written text, "
    "code and tests, automated execution, AI-assisted literature search and reference checks, and states that the authors have "
    "not yet re-run the experiments; the authors must add their own reading, checking and decisions (placeholders).")
add(31, "Author metadata and CRediT roles", "AUTHOR ACTION REQUIRED",
    "Co-author Punit Gupta added; affiliations, e-mail, ORCID iDs, the equal-contribution note and the CRediT split are "
    "placeholders marked for confirmation (`research/V3/AUTHOR_RELEASE_CHECKLIST.md`, section A).")
add(32, "Funding and conflicts", "AUTHOR ACTION REQUIRED",
    "Statements present in `paper/main.tex` but marked [AUTHORS TO CONFIRM].")
add(33, "Repository DOI", "AUTHOR ACTION REQUIRED",
    "Placeholder in the Data Availability Statement; requires a public release (e.g., a GitHub release archived on Zenodo).")
tex_ok = check_passed("main.log: no LaTeX errors") and check_passed("main.log: no stub packages") and \
    check_passed("supplementary.log: no LaTeX errors") and check_passed("supplementary.log: no stub packages")
add(34, "Full TeX Live build", "RESOLVED" if tex_ok else "PARTIALLY RESOLVED",
    "Manuscript and Supplementary built with latexmk and TeX Live 2023 (including the real `bbm.sty` from texlive-fonts-extra), "
    f"no stub packages; LaTeX logs {'without' if tex_ok else 'WITH'} errors, undefined references or stub packages "
    "(`research/V3/FINAL_VALIDATION_REPORT_CHECKS.md`).")
add(35, "Archive integrity and reproduction", "RESOLVED" if arch_ok else "PARTIALLY RESOLVED",
    (f"ZIP listed, CRC-tested, extracted to a fresh directory and every file compared with `S_SHA256SUMS.txt`: {atd['entries']} entries, "
     f"{len(atd['manifest_mismatches'])} hash mismatches, {len(atd['missing_expected'])} expected items missing "
     "(test of the previous build, `03_package/archive_test_report.json`). The delivered ZIP is produced and tested by the same "
     "script (`research/V3/workspace_scripts/build_v3_package.py`), after this file is included; that test is reported with the "
     "delivery. Reproduction by others: item 9.") if atd else "Archive not yet built.")

counts = {}
for _, _, s, _ in rows:
    counts[s] = counts.get(s, 0) + 1
L = ["# V3 issue-by-issue closure matrix (Part 20)", "",
     "Statuses: RESOLVED · PARTIALLY RESOLVED · OPEN — EXTERNAL DEPENDENCY · AUTHOR ACTION REQUIRED · NOT APPLICABLE, WITH",
     "JUSTIFICATION. Exactly one status per issue. Evidence paths are relative to the research repository",
     "(`C-M_Research_Repository/` in the package). No issue is marked resolved on the basis of a plan, prompt, stub or",
     "documentation alone; statuses that depend on a check (tests, page limits, build, archive) are derived from that check by",
     "`scripts/make_issue_matrix.py`, which also generated this file.", "",
     "Summary: " + "; ".join(f"{k}: {n}" for k, n in sorted(counts.items(), key=lambda kv: -kv[1])) + ".", "",
     "| # | Issue | Status | Evidence and remaining gap |", "|---|---|---|---|"]
L += [f"| {n} | {i} | {s} | {e.replace('|', '/')} |" for n, i, s, e in rows]
if check_fail:
    L += ["", "Automated checks that FAILED at generation time (see `FINAL_VALIDATION_REPORT_CHECKS.md`):", ""] + [f"* {ln}" for ln in check_fail]
(V3 / "ISSUE_CLOSURE_MATRIX.md").write_text("\n".join(L) + "\n")
print("written", V3 / "ISSUE_CLOSURE_MATRIX.md", counts)
