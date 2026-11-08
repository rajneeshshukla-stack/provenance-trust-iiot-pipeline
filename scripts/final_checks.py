#!/usr/bin/env python3
"""Final quality gate for the submission package (run after `make paper`).

Checks: unit tests; zero missing result macros; page limits (main <= 20, supplementary <= 10);
no undefined references/citations in the LaTeX logs; every bibliography entry cited; author placeholders listed.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "paper"
ok = True


def report(name, passed, detail=""):
    global ok
    ok &= passed
    print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True)
report("unit/invariant tests", r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[-200:])
r = subprocess.run([sys.executable, "scripts/check_macros.py"], cwd=ROOT, capture_output=True, text=True)
report("all result macros generated", r.returncode == 0, r.stdout.strip().splitlines()[0])


def pages(pdf):
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    m = re.search(r"Pages:\s+(\d+)", out)
    return int(m.group(1)) if m else -1


report("main manuscript <= 20 pages", 0 < pages(P / "main.pdf") <= 20, f"{pages(P / 'main.pdf')} pages")
report("supplementary <= 10 pages", 0 < pages(P / "supplementary.pdf") <= 10, f"{pages(P / 'supplementary.pdf')} pages")
for log in ("main.log", "supplementary.log"):
    t = (P / log).read_text(errors="replace") if (P / log).exists() else ""
    und = re.findall(r"(Reference|Citation) `([^']+)' on page \d+ undefined", t)
    report(f"no undefined refs/cites in {log}", not und, ", ".join(sorted({u[1] for u in und}))[:200])
    report(f"no LaTeX errors in {log}", "\n! " not in t)
bib = (P / "references.bib").read_text()
keys = set(re.findall(r"^@\w+\{([^,]+),", bib, re.M))
cited = {k.strip() for c in re.findall(r"\\cite\{([^}]+)\}", (P / "main.tex").read_text()) for k in c.split(",")}
report("every bibliography entry cited", keys <= cited, ", ".join(sorted(keys - cited)))
report("every citation in bibliography", cited <= keys, ", ".join(sorted(cited - keys)))
ph = sorted(set(re.findall(r"\[(?:AUTHORS?[^\]]*|Co-author[^\]]*|Department[^\]]*|e-mail|X\.X\.|repository name[^\]]*)\]", (P / "main.tex").read_text())))
print(f"[INFO] author placeholders to complete before submission: {len(ph)}")
for p in ph:
    print("       ", p[:110])
print("OVERALL:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
