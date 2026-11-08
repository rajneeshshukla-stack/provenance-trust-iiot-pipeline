"""Check that the current refmodel.py with default switches behaves exactly like the phase-1 snapshot
(phase1_snapshot/refmodel.py) on generated streams (model only; symbolic digests)."""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import refmodel as CUR  # noqa: E402
from gen import FAMILIES  # noqa: E402

spec1 = importlib.util.spec_from_file_location("refmodel_phase1", os.path.join(HERE, "phase1_snapshot", "refmodel.py"))
P1 = importlib.util.module_from_spec(spec1)
sys.modules["refmodel_phase1"] = P1
spec1.loader.exec_module(P1)


def abstract(spec, mod):
    st = {s["name"]: s for s in spec["stmts"]}
    out = []
    for t, name, wrap, mode in sorted(spec["arrivals"], key=lambda a: a[0]):
        s = st[name]
        p = s["prev"]
        prev = None if p is None else ("ext:" + p["ext"] if isinstance(p, dict) else p)
        q = "STALE_TS" if t - s["ts"] > spec["h_max_ms"] else None
        out.append(mod.Stmt(int(t), s["did"], s["ep"], s["seq"], name, prev, q))
    return out


def settings(mod):
    return {"hist": mod.Params.hist(), "B5S": mod.Params.strict(), "d0c1": mod.Params.defer(0, 1),
            "d5c10": mod.Params.defer(5, 10), "d60c10": mod.Params.defer(60, 10), "event": mod.Params.event(),
            "oneshot_d0c10": mod.Params("oneshot", 0, 10_000, "periodic", True)}


KEYS = ("authoritative", "timeline", "fork_events", "hold_events", "held_identities", "feed_holds", "releases",
        "rejections", "resumes", "pending", "held_at_end", "dispositions")


def main(n_per_family=60):
    n = bad = 0
    for fam, gen in FAMILIES.items():
        for seed in range(n_per_family):
            spec = gen(10_000 + seed)
            legit = [((s["did"], s["ep"], s["seq"]), s["name"]) for s in spec["stmts"] if s["legit"]]
            s_cur, s_p1 = abstract(spec, CUR), abstract(spec, P1)
            for name in settings(CUR):
                a = CUR.run(s_cur, settings(CUR)[name], t_end=spec["t_end"], legit=legit)
                b = P1.run(s_p1, settings(P1)[name], t_end=spec["t_end"], legit=legit)
                n += 1
                diff = [k for k in KEYS if json.dumps(a[k], default=str) != json.dumps(b[k], default=str)]
                # phase-1 intervals did not drop zero-length intervals; compare withheld totals instead
                if a["W_ms_total"] != b["W_ms_total"] or a["nlx_ms_total"] != b["nlx_ms_total"]:
                    diff.append("W/NLX")
                if diff:
                    bad += 1
                    print("DIFF", fam, seed, name, diff)
    print(f"{n} model runs compared, {bad} differ")
    return bad


if __name__ == "__main__":
    sys.exit(1 if main(int(sys.argv[1]) if len(sys.argv) > 1 else 60) else 0)
