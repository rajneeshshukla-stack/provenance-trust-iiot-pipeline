"""Print the arrival list and the authority/decision differences of one stream and setting (debug aid)."""
import sys

import harness as H
import refmodel as M
from gen import FAMILIES
from run_diff import SETTINGS


def short(x):
    return x[:6] if isinstance(x, str) else x


def main(family, seed, setting, variant="spec", only=None):
    spec = FAMILIES[family](int(seed))
    b = H.build(spec)
    P = SETTINGS[setting]
    if variant == "impl":
        P = P.impl_choices()
    elif variant != "spec":
        P = P.impl_choices(**dict(kv.split("=") for kv in variant.split(",")))
    events = M.schedule(b.model_stmts, P, b.t_end)
    real = H.run_real(b, P, events)
    mod = H.run_model(b, P, events)
    names = {v: k for k, v in b.cd.items()}
    print("arrivals:")
    for (t, e, cd, d_real), (_, _, _, d_mod) in zip(real["dispositions"], mod["dispositions"]):
        if only and e[0] != only:
            continue
        q = [s.qreason for s in b.model_stmts if s.t == t and s.digest == cd]
        print(f"  {t:7d} {names.get(cd, cd[:6]):28s} real={d_real:28s} model={d_mod} {q[0] or ''}")
    c = H.compare(mod, real)
    print("cmp:", {k: v for k, v in c.items() if k != "iv_diff_sample"})
    keys = sorted(set(mod["intervals"]) | set(real["intervals"]))
    for k in keys:
        a, r = mod["intervals"].get(k, []), real["intervals"].get(k, [])
        if a != r and (not only or k[0][0] == only):
            print(f"  IV {names.get(k[1], k[1][:6]):28s} model={a} real={r}")
    md = sorted((t, e, names.get(cd), "REL" if 1 else "") for t, e, cd, _ in mod["releases"])
    rd = sorted((t, e, names.get(cd)) for t, dec, out, reason, e, cd in real["decisions"] if dec == "RELEASE")
    print("releases model-only:", [x for x in md if x[:3] not in [y[:3] for y in rd]][:20])
    print("releases real-only:", [x for x in rd if x[:3] not in [y[:3] for y in md]][:20])
    mj = sorted((t, e, names.get(cd)) for t, e, cd, _ in mod["rejections"])
    rj = sorted((t, e, names.get(cd)) for t, dec, out, reason, e, cd in real["decisions"] if dec == "REJECT")
    print("rejections model-only:", [x for x in mj if x not in rj][:20])
    print("rejections real-only:", [x for x in rj if x not in mj][:20])
    print("resumes model:", mod["resumes"][:20])
    print("resumes real :", real["resumes"][:20])
    print("real outcomes:", real["review_outcomes"])
    print("counters real:", real["counters"], "model-impl:", mod["impl_counters"])
    print("release_failed model:", [(t, e, names.get(cd), k, r) for t, e, cd, k, r in mod["release_failed"]][:10])


if __name__ == "__main__":
    main(*sys.argv[1:])
