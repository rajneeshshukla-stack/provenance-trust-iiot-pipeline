#!/usr/bin/env python3
"""V3 final quality gate and validation report (run after `make test`, `make analysis` and `make paper`).

Writes research/V3/FINAL_VALIDATION_REPORT_CHECKS.md (machine-generated section of the final validation report) and
prints PASS/FAIL per check. Checks: test report; macros; page limits; LaTeX logs (errors, undefined references and
citations, overfull boxes counted); bibliography cited/defined; stub packages not used; figure and table files present;
V3 audits; regression check; policy parity; container checks; formal artefacts; preregistered predictions; archive test
(if present). Author placeholders are listed, not failed.
"""
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "paper"
SUM = ROOT / "results" / "summary"
rows = []


def check(name, passed, detail="", info=False):
    rows.append((name, "INFO" if info else ("PASS" if passed else "FAIL"), detail))
    print(f"[{rows[-1][1]}] {name}" + (f" -- {detail}" if detail else ""))


def pages(pdf):
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"Pages:\s+(\d+)", out)
    return int(m.group(1)) if m else -1


# tests
jx = SUM / "pytest_v3.xml"
if jx.exists():
    r = ET.parse(jx).getroot()
    suites = [r] if r.tag == "testsuite" else list(r)
    n = sum(int(s.get("tests", 0)) for s in suites)
    fail = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    skip = sum(int(s.get("skipped", 0)) for s in suites)
    check("test suite (pytest, JUnit report)", fail == 0, f"{n} tests, {fail} failures/errors, {skip} skipped")
else:
    check("test suite (pytest, JUnit report)", False, "results/summary/pytest_v3.xml missing")
r = subprocess.run([sys.executable, "scripts/check_macros.py"], cwd=ROOT, capture_output=True, text=True)
check("every result macro used is generated (\\R and \\V)", r.returncode == 0, r.stdout.strip().splitlines()[0] if r.stdout else "")
mm = (P / "generated" / "missing_macros.tex").read_text()
check("missing_macros.tex has no placeholder definitions", "\\providecommand" not in mm)
pm, ps = pages(P / "main.pdf"), pages(P / "supplementary.pdf")
check("main manuscript <= 20 pages (incl. references)", 0 < pm <= 20, f"{pm} pages")
check("supplementary <= 10 pages", 0 < ps <= 10, f"{ps} pages")
for log in ("main.log", "supplementary.log"):
    t = (P / log).read_text(errors="replace") if (P / log).exists() else ""
    und = re.findall(r"(Reference|Citation) `([^']+)' on page \d+ undefined", t)
    check(f"{log}: no undefined references or citations", not und, ", ".join(sorted({u[1] for u in und}))[:200])
    check(f"{log}: no LaTeX errors", "\n! " not in t)
    stub = "texstubs" in t
    check(f"{log}: no stub packages loaded (full TeX Live)", not stub)
    ob = len(re.findall(r"Overfull \\hbox", t))
    check(f"{log}: overfull hboxes", True, f"{ob}", info=True)
# clean-room build: copy the LaTeX sources without any build products and compile from scratch
import shutil
import tempfile
with tempfile.TemporaryDirectory() as td:
    dst = Path(td) / "paper"
    shutil.copytree(P, dst, ignore=shutil.ignore_patterns("*.aux", "*.bbl", "*.blg", "*.fdb_latexmk", "*.fls", "*.log", "*.out",
                                                          "main.pdf", "supplementary.pdf", "*.synctex.gz"))
    ok_build = True
    for tex in ("main.tex", "supplementary.tex"):
        rr = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", tex], cwd=dst, capture_output=True, text=True)
        lg = (dst / tex.replace(".tex", ".log")).read_text(errors="replace") if (dst / tex.replace(".tex", ".log")).exists() else ""
        ok_build &= (rr.returncode == 0 and "\n! " not in lg and "texstubs" not in lg
                     and not re.search(r"(Reference|Citation) `[^']+' on page \d+ undefined", lg))
    cm, cs = pages(dst / "main.pdf"), pages(dst / "supplementary.pdf")
    check("clean-room LaTeX build from the sources alone (latexmk, full TeX Live)", ok_build and cm == pm and cs == ps,
          f"main {cm} pages, supplementary {cs} pages")
bib = (P / "references.bib").read_text()
keys = set(re.findall(r"^@\w+\{([^,]+),", bib, re.M))
cited = {k.strip() for c in re.findall(r"\\cite\{([^}]+)\}", (P / "main.tex").read_text()) for k in c.split(",")}
check("every bibliography entry cited", keys <= cited, ", ".join(sorted(keys - cited))[:200])
check("every citation in bibliography", cited <= keys, ", ".join(sorted(cited - keys)))
check("references cited", True, f"{len(cited)}", info=True)
figs = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", (P / "main.tex").read_text() + (P / "supplementary.tex").read_text())
check("all included figures exist", all((P / f).exists() for f in figs), ", ".join(f for f in figs if not (P / f).exists()))
tabs = re.findall(r"\\input\{(generated/[^}]+)\}", (P / "main.tex").read_text() + (P / "supplementary.tex").read_text())
pend = [t for t in tabs if "RESULT PENDING" in (P / (t if t.endswith(".tex") else t + ".tex")).read_text()]
check("no pending generated tables", not pend, ", ".join(pend))
# V3 evidence
rep = json.loads((SUM / "v3_analysis_report.json").read_text()) if (SUM / "v3_analysis_report.json").exists() else {}
for k in ("x1_audits", "x2_audits", "x5_audits"):
    a = rep.get(k)
    if a:
        check(f"V3 audits {k[:2].upper()}", a.get("pass") == a.get("runs"), f"{a.get('pass')}/{a.get('runs')} passed")
pr = rep.get("predictions", {})
if pr:
    check("preregistered predictions evaluated", True, "; ".join(f"{p}: {'held' if pr[p]['holds'] else 'did not hold'}" for p in ("P1", "P2", "P3", "P4"))
          + f"; D1 condition {'met' if pr.get('D1_condition_met') else 'not met'}; D2 cases {pr.get('D2_cases')}", info=True)
rc = SUM / "regression_check_v3.json"
if rc.exists():
    d = json.loads(rc.read_text())
    check("stored V2 and V3 results reproduce under the final source (sample)", d["differences"] == 0,
          f"{len(d['checked'])} specifications, {d['differences']} differences, source {d['source_sha256'][:16]}")
else:
    check("stored results reproduce under the final source", False, "regression_check_v3.json missing")
fx = SUM / "v3_b5_fix_comparison.json"
if fx.exists():
    d = json.loads(fx.read_text())
    check("B5 fix (amendment A4): O1/O2 of the re-runs equal the superseded runs", all(v["same_O1_O2"] == v["runs"] for v in d.values()),
          "; ".join(f"{k}: {v['same_O1_O2']}/{v['runs']} identical O1 and O2, audits {v['audits_new']['pass']}/{v['audits_new']['run']}" for k, v in d.items()))
par = ROOT / "results" / "policy_parity" / "parity_results.json"
if par.exists():
    h = json.loads(par.read_text()).get("headline", {})
    wf = h.get("well_formed_requests_on_well_formed_policy", {})
    check("Rego/Python parity on well-formed requests", wf.get("exact_match") == wf.get("n"), f"{wf.get('exact_match')}/{wf.get('n')} exact")
    check("no request permitted by only one side", h.get("all_cases", {}).get("permit_by_one_side_only", 1) == 0)
cs = ROOT / "results" / "containers" / "v3_final" / "logs" / "checks_summary.txt"
if cs.exists():
    t = cs.read_text()
    check("container (final V3 image): all checks exit 0", "exit=1" not in t and "exit=2" not in t and t.count("exit=0") >= 6, t.replace("\n", "; ")[:200])
fo = ROOT / "results" / "formal" / "proverif_output.txt"
check("ProVerif outputs present", fo.exists() and "RESULT" in fo.read_text(errors="replace"))
import hashlib
fl = ROOT / "results" / "formal" / "rule_l_bounded_check_final.log"
if fl.exists():
    ft = fl.read_text()
    m = re.search(r'"total_violations":\s*(\d+)', ft)
    check("Rule L bounded check (final source): 0 violations", m is not None and m.group(1) == "0")
    mv = re.search(r"sha256 ([0-9a-f]{64})  verifier\.py", ft)
    cur = hashlib.sha256((ROOT / "src" / "pbti" / "verifier.py").read_bytes()).hexdigest()
    check("Rule L bounded check ran on the final verifier.py", bool(mv) and mv.group(1) == cur, (mv.group(1)[:12] if mv else "?") + " vs " + cur[:12])
else:
    check("Rule L bounded check on the final source", False, "results/formal/rule_l_bounded_check_final.log missing")
at = ROOT.parent / "03_package" / "archive_test_report.json"
if at.exists():
    d = json.loads(at.read_text())
    check("archive integrity (previous build)", not d["manifest_mismatches"] and not d["missing_expected"] and d["crc_test_first_bad"] is None,
          f"{d['entries']} entries, {d['manifest_entries']} manifest entries, sha256 {d['zip_sha256'][:16]}")
src_tex = (P / "main.tex").read_text() + (P / "supplementary.tex").read_text()
left = sorted(set(re.findall(r"[A-Z]*PLACEHOLDER[A-Z]*|\bTODO\b|\bFIXME\b|\bXXX\b", src_tex)))
check("no drafting markers left in the LaTeX sources", not left, ", ".join(left))
GENERATED = {"FINAL_VALIDATION_REPORT.md", "FINAL_VALIDATION_REPORT_CHECKS.md", "ISSUE_CLOSURE_MATRIX.md"}
md_left = sorted({f"{f.relative_to(ROOT)}: {m}" for f in list((ROOT / "research" / "V3").glob("*.md")) + list((ROOT / "docs").glob("*.md"))
                  if f.name not in GENERATED
                  for m in re.findall(r"\b(?:REGTIME|RESTIME|[A-Z]*PLACEHOLDER)\b", f.read_text())})
check("no drafting markers left in research/V3 and docs Markdown", not md_left, "; ".join(md_left))
# Word copy (scripts/export_manuscript.py): valid OOXML package, macros expanded, co-author present
import zipfile
dx = ROOT / "research" / "V3" / "manuscript" / "Provenance-Bound_Trust-Aware_Ingestion_V3_Manuscript.docx"
if dx.exists():
    try:
        with zipfile.ZipFile(dx) as z:
            bad_zip = z.testzip()
            doc = z.read("word/document.xml").decode("utf-8", "replace")
        text = re.sub(r"<[^>]+>", "", doc)
        unexpanded = sorted(set(re.findall(r"\\[VR][A-Z][A-Za-z]+", text)))[:5]
        check("Word copy: valid package, all result macros expanded, both authors named",
              bad_zip is None and not unexpanded and "Punit Gupta" in text and "Rajneesh Shukla" in text,
              f"{len(text.split())} words" + (f"; unexpanded: {unexpanded}" if unexpanded else ""))
    except (zipfile.BadZipFile, KeyError) as e:
        check("Word copy: valid package, all result macros expanded, both authors named", False, repr(e))
else:
    check("Word copy present", False, str(dx.relative_to(ROOT)))
ph = sorted(set(re.findall(r"\[(?:AUTHORS?[^\]]*|Department[^\]]*|e-mail[^\]]*|repository name[^\]]*)\]", (P / "main.tex").read_text())))
check("author placeholders to complete", True, f"{len(ph)}", info=True)
out = ["# Final validation: automated checks", "", f"Generated by `scripts/final_checks_v3.py`.", "",
       "| Check | Result | Detail |", "|---|---|---|"]
out += [f"| {n} | {s} | {d.replace('|', '/')} |" for n, s, d in rows]
out += ["", "Author placeholders:", ""] + [f"* `{p}`" for p in ph]
(ROOT / "research" / "V3" / "FINAL_VALIDATION_REPORT_CHECKS.md").write_text("\n".join(out) + "\n")
bad = [r for r in rows if r[1] == "FAIL"]
print("OVERALL:", "PASS" if not bad else f"FAIL ({len(bad)})")
sys.exit(0 if not bad else 1)
