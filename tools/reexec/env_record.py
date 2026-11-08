#!/usr/bin/env python3
"""Record the execution environment of a re-execution run (memo/prompt item 1.4).

Writes one JSON file with: UTC and local time, CPU model and count, memory, operating system, Python version,
versions of the packages the experiments use, the git commit if the repository is a git checkout, per-file SHA-256
of the source, experiment, analysis and formal code, an aggregate source digest, and SHA-256 of every configuration
file. It deliberately does not record the host name, user name or any path outside the repository.

Usage: python3 env_record.py REPO_DIR OUT_JSON [--label TEXT]
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path

PACKAGES = ["cryptography", "numpy", "scipy", "pandas", "matplotlib", "PyYAML", "psutil", "paho-mqtt", "pytest"]
CODE_DIRS = ["src/pbti", "experiments", "analysis", "formal", "scripts"]
CONFIG_GLOBS = ["experiments/v4_configs/*.json", "experiments/v4_configs/amendment1/*.json", "config/*"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def mem_total_gib():
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return round(int(line.split()[1]) / 1024 / 1024, 2)
    except OSError:
        pass
    return None


def os_release() -> str:
    try:
        kv = dict(l.split("=", 1) for l in Path("/etc/os-release").read_text().splitlines() if "=" in l)
        return kv.get("PRETTY_NAME", "").strip('"')
    except OSError:
        return platform.platform()


def git_commit(repo: Path):
    if not (repo / ".git").exists():
        return None
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=20).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("out")
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    files = {}
    for d in CODE_DIRS:
        for p in sorted((repo / d).rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            files[str(p.relative_to(repo))] = sha256(p)
    agg = hashlib.sha256("".join(f"{k}\0{v}\n" for k, v in sorted(files.items())).encode()).hexdigest()
    src_only = {k: v for k, v in files.items() if k.startswith("src/pbti/")}
    src_agg = hashlib.sha256("".join(f"{k}\0{v}\n" for k, v in sorted(src_only.items())).encode()).hexdigest()
    configs = {}
    for g in CONFIG_GLOBS:
        for p in sorted(repo.glob(g)):
            if p.is_file():
                configs[str(p.relative_to(repo))] = sha256(p)
    pk = {}
    for name in PACKAGES:
        try:
            pk[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pk[name] = None
    now = dt.datetime.now(dt.timezone.utc)
    rec = {
        "label": a.label,
        "time_utc": now.isoformat(timespec="seconds"),
        "time_local": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "cpu_model": cpu_model(),
        "logical_cpus": os.cpu_count(),
        "memory_gib": mem_total_gib(),
        "os": os_release(),
        "kernel": platform.release(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "packages": pk,
        "git_commit": git_commit(repo),
        "source_sha256_src_pbti_aggregate": src_agg,
        "code_sha256_aggregate": agg,
        "code_files_sha256": files,
        "config_sha256": configs,
        "note": "host name, user name and absolute paths are intentionally not recorded",
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("time_utc", "cpu_model", "logical_cpus", "memory_gib", "os", "python",
                                          "source_sha256_src_pbti_aggregate")}, indent=1))


if __name__ == "__main__":
    main()
