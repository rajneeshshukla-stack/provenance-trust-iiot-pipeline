#!/usr/bin/env python3
"""Write the V9 research-package repository: the working repository without logs, drafts, obsolete PDFs, packaging
tools and caches, plus the V9 manuscript sources in manuscript/. Nothing under results/ is changed or dropped except
the progress logs of the V9 reruns (every row and manifest is kept); historical run logs that are part of recorded
evidence (hashed in provenance files) stay where they are.

Usage: python3 -I tools/v9/build_release_tree.py SRC_REPO MANUSCRIPT_DIR OUT_DIR
Writes OUT_DIR (must not exist) and OUT_DIR/RELEASE_TREE_MANIFEST.json (what was excluded and why).
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import shutil
import sys
from pathlib import Path

SRC, MAN, OUT = (Path(a).resolve() for a in sys.argv[1:4])
if OUT.exists():
    raise SystemExit(f"{OUT} exists")

# (pattern relative to the repository root, reason); a pattern ending in / excludes a directory
EXCLUDE = [
    ("logs/", "development and campaign console logs of earlier stages (not evidence referenced by any record)"),
    ("paper/", "earlier manuscript drafts and PDFs; the frozen analysis scripts recreate paper/generated and paper/figures as output directories"),
    ("paper_v7/", "earlier manuscript draft, PDFs and a copy of the earlier Data S1; recreated as an output directory by tools/v9/regenerate_analysis.sh"),
    ("research/V3/manuscript/", "earlier manuscript drafts"),
    ("research/V4/manuscript/", "earlier manuscript drafts"),
    ("research/V3/workspace_scripts/", "packaging scripts of an earlier deliverable"),
    ("research/COVER_LETTER.md", "submission administration draft of an earlier version"),
    ("research/V3/COVER_LETTER_DRAFT.md", "submission administration draft of an earlier version"),
    ("research/V3/AUTHOR_RELEASE_CHECKLIST.md", "superseded by the V9 author-completion list (response folder)"),
    ("research/README_RESEARCH.md", "superseded overview of an earlier manuscript stage"),
    ("research/RESULTS_TEMPLATE.md", "superseded planning template (marked as such)"),
    ("research/OPEN_RESEARCH_ITEMS.md", "superseded open-item list (marked historical); current items: V9 author-completion list"),
    ("research/REVIEWER_STRESS_TEST.md", "superseded internal review notes of an earlier stage"),
    ("research/EVIDENCE_MATRIX.md", "superseded claim matrix of an earlier manuscript; current mapping: Document S1, principal findings table"),
    ("research/V3/PACKAGE_CONTENTS.md", "contents list of an earlier deliverable"),
    ("tools/v7/build_package_v7.py", "packaging tool of an earlier deliverable"),
    ("tools/v7/export_manuscript_v7.py", "editing-copy export of an earlier manuscript"),
    ("tools/v7/check_v7_manuscript.py", "checks of an earlier manuscript; replaced by tools/manuscript/check_manuscript.py"),
    ("tools/v7/docx_normalize.py", "editing-copy export of an earlier manuscript"),
    ("tools/v7/abstract_words.py", "word count of an earlier abstract"),
    ("results/v9/*.log", "progress logs of the V9 reruns (rows, manifests and the verification record carry the evidence)"),
    ("logs_v9_*.txt", "console output of the regeneration"),
    ("*/__pycache__/", "cache"), ("__pycache__/", "cache"), (".pytest_cache/", "cache"), ("*/.pytest_cache/", "cache"),
    ("*.pyc", "cache"), (".ipynb_checkpoints/", "cache"), ("*.egg-info/", "build product"),
]


def excluded(rel: str, is_dir: bool):
    for pat, why in EXCLUDE:
        if pat.endswith("/"):
            p = pat[:-1]
            if is_dir and (fnmatch.fnmatch(rel, p) or rel == p):
                return why
        elif not is_dir and fnmatch.fnmatch(rel, pat):
            return why
    return None


log = {"excluded": {}, "manuscript_files": 0}


def copy_tree(src: Path, dst: Path, root: Path, rec: bool = True):
    dst.mkdir(parents=True, exist_ok=True)
    for p in sorted(src.iterdir()):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            raise SystemExit(f"symlink in source tree: {rel}")
        why = excluded(rel, p.is_dir()) if rec else None
        if why:
            log["excluded"].setdefault(why, []).append(rel + ("/" if p.is_dir() else ""))
            continue
        if p.is_dir():
            copy_tree(p, dst / p.name, root, rec)
        else:
            shutil.copy2(p, dst / p.name)


copy_tree(SRC, OUT, SRC)

# manuscript sources (V9): LaTeX, generated tables and macros, figures with their data, class files; no build products
M = OUT / "manuscript"
M.mkdir()
for name in ("main.tex", "supplementary.tex", "references.bib"):
    shutil.copy2(MAN / name, M / name)
for d in ("parts", "generated", "Definitions", "figures"):
    shutil.copytree(MAN / d, M / d, ignore=shutil.ignore_patterns("*.aux", "*.log", "*.synctex.gz", "*.fls",
                                                                    "*.fdb_latexmk", "__pycache__"))
log["manuscript_files"] = sum(1 for p in M.rglob("*") if p.is_file())

n_files = sum(1 for p in OUT.rglob("*") if p.is_file())
size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
h = hashlib.sha256()
for p in sorted(OUT.rglob("*")):
    if p.is_file():
        h.update(p.relative_to(OUT).as_posix().encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
log.update({"files": n_files, "bytes": size, "tree_sha256": h.hexdigest(),
            "note": "tree_sha256 hashes the sorted (path, file SHA-256) pairs, excluding this manifest"})
(OUT / "RELEASE_TREE_MANIFEST.json").write_text(json.dumps(log, indent=1, sort_keys=True))
print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in log.items() if k != "excluded"}))
print({k: len(v) for k, v in log["excluded"].items()})
