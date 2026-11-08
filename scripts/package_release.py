#!/usr/bin/env python3
"""Create a GitHub-ready archive of the repository (sources, configuration, data, raw results, paper sources and PDFs).

Excluded: version-control metadata, caches, build intermediates, local logs and LaTeX auxiliary files.
Usage: python3 scripts/package_release.py [output.zip]
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCL_DIRS = {".git", "__pycache__", ".pytest_cache", "build", "logs", "dist", ".mypy_cache", ".ruff_cache"}
EXCL_SUFFIX = {".aux", ".log", ".fls", ".fdb_latexmk", ".out", ".blg", ".toc", ".synctex.gz", ".pyc", ".db", ".db-wal", ".db-shm"}


def keep(p: Path) -> bool:
    rel = p.relative_to(ROOT)
    if any(part in EXCL_DIRS for part in rel.parts):
        return False
    name = p.name
    return not any(name.endswith(s) for s in EXCL_SUFFIX)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "pbti-iiot.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and keep(p) and p.resolve() != out.resolve())
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            z.write(p, Path("pbti-iiot") / p.relative_to(ROOT))
    print(f"{out}: {len(files)} files, {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
