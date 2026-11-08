"""Shared helpers of the V9 runners (corrected-B5 reruns and the E04 robustness campaign).

install_corrected_b5() replaces, in the running process only, the B5 class that sim.World instantiates for the
systems "B5" and "B5S" by the corrected implementation (src/pbti/b5_corrected.py).  The historical modules are not
modified (their SHA-256 values are checked against the preregistration freeze files before every campaign).
Every row written by a V9 runner carries the implementation identifier, the SHA-256 of the corrected module and of
the historical b5.py, and the source-tree digest; manifests record the command line, configuration and environment.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

FROZEN_HASH_FILES = ("research/V4/PREREGISTRATION_V4.sha256", "research/V4/PREREGISTRATION_V4_AMENDMENT_1.sha256")


def sha256_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_frozen() -> dict:
    """Every file listed in the preregistration freeze files must still have its recorded SHA-256."""
    out = {}
    for hf in FROZEN_HASH_FILES:
        lines = [l for l in (ROOT / hf).read_text().splitlines() if l and not l.startswith("#")]
        bad = [p for h, p in (l.split(None, 1) for l in lines) if sha256_file(ROOT / p) != h]
        out[hf] = {"files": len(lines), "changed": bad}
    if any(v["changed"] for v in out.values()):
        raise SystemExit("frozen files changed: " + json.dumps(out))
    return out


def impl_record() -> dict:
    import run_campaign as rc
    return {"b5_impl": "b5_corrected_v9",
            "b5_corrected_sha256": sha256_file(ROOT / "src/pbti/b5_corrected.py"),
            "b5_historical_sha256": sha256_file(ROOT / "src/pbti/b5.py"),
            "source_sha256": rc.source_digest()}


def install_corrected_b5():
    """sim.World builds B5/B5S from the module name pbti.sim.B5FeedLevel; point it to the corrected class and give
    the verifier the world's review mode (periodic or event-driven), which the corrected class needs to keep a
    hold case opened during a periodic review pass for the next pass."""
    import pbti.sim as sim
    from pbti.b5_corrected import B5Corrected
    if getattr(sim.World.__init__, "_v9", False):
        return B5Corrected
    sim.B5FeedLevel = B5Corrected
    orig_init = sim.World.__init__

    def init(self, cfg, *a, **kw):
        orig_init(self, cfg, *a, **kw)
        if isinstance(self.sys, B5Corrected):
            self.sys.set_review_mode(self.cfg.review_mode)
    init._v9 = True
    sim.World.__init__ = init
    return B5Corrected


def w_split(world) -> dict:
    """Exploratory split of the registered withheld time W (same definitions as tools/v7/w_decomposition.py):
    W_delay = withheld time of gateway-accepted legitimate observations that are authoritative at T_end,
    W_loss  = withheld time (from gateway acceptance to T_end) of those that are not authoritative at T_end.
    Computed from the run's own tracer log; W_delay + W_loss equals the registered sum exactly (checked)."""
    from pbti import temporal as T
    tr = world.tracer
    if tr is None:
        return {}
    t_end = world.cfg.duration_ms + world.cfg.drain_ms
    iv = T.intervals_from_log(tr.log, t_end)["iv"]
    d_ms = l_ms = n_end = n_not = n_delayed = 0
    for rec in world.truth:
        o = rec["o"]
        if not o.meta.get("gw_accepted"):
            continue
        pairs = {(tuple(e), rec["ck"]) for e in (o.meta.get("eids") or [])}
        u = T._union([x for p in pairs for x in iv.get(p, ())])
        t_acc = o.meta.get("t_acc", rec["t"])
        wh = (t_end - t_acc) - T._measure(u, t_acc, t_end)
        if u and u[-1][1] == t_end:
            d_ms += wh
            n_end += 1
            n_delayed += int(wh > 0)
        else:
            l_ms += wh
            n_not += 1
    n = max(1, n_end + n_not)
    return {"wd_reach": n_end + n_not, "wd_n_auth_end": n_end, "wd_n_not_auth_end": n_not,
            "wd_n_delayed_auth_end": n_delayed, "wd_delay_ms": d_ms, "wd_loss_ms": l_ms,
            "W_delay_s_per_obs": d_ms / 1000.0 / n, "W_loss_s_per_obs": l_ms / 1000.0 / n}


def manifest(campaign: str, args: dict, extra: dict | None = None) -> dict:
    import cryptography, numpy, scipy, pandas, psutil  # noqa: E401
    try:
        cpu = [l for l in open("/proc/cpuinfo") if l.startswith("model name")][0].split(":")[1].strip()
    except Exception:  # noqa: BLE001
        cpu = platform.processor()
    m = {"campaign": campaign, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "args": args,
         "command": " ".join([os.path.basename(sys.executable)] + sys.argv),
         "python": sys.version, "platform": platform.platform(), "cpu": cpu, "logical_cpus": os.cpu_count(),
         "ram_gb": round(psutil.virtual_memory().total / 2 ** 30, 2),
         "versions": {"cryptography": cryptography.__version__, "numpy": numpy.__version__,
                      "scipy": scipy.__version__, "pandas": pandas.__version__},
         "frozen_files_check": check_frozen()}
    m.update(impl_record())
    if extra:
        m.update(extra)
    return m


def run_pool(todo, job, out: Path, key_of, workers: int, label: str):
    """Run job over todo with a fork pool; resumable: specifications whose key is already in `out` are skipped."""
    import multiprocessing as mp
    done = set()
    if out.exists():
        for l in open(out):
            try:
                r = json.loads(l)
            except Exception:  # noqa: BLE001
                continue
            if "error" not in r:
                done.add(key_of(r))
    todo = [t for t in todo if key_of(t) not in done]
    print(f"[{label}] {len(done)} rows present, {len(todo)} to run", flush=True)
    if not todo:
        return 0
    t0 = time.time()
    n = errors = 0
    with open(out, "a") as fh, mp.get_context("fork").Pool(workers, maxtasksperchild=8) as pool:
        for r in pool.imap_unordered(job, todo):
            fh.write(json.dumps(r, default=str) + "\n")
            fh.flush()
            n += 1
            errors += "error" in r
            if n % 25 == 0 or n == len(todo):
                print(f"[{label}] {n}/{len(todo)} runs, {errors} errors, {time.time() - t0:.0f}s", flush=True)
    return errors
