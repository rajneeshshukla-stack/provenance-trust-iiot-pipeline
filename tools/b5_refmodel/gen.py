"""Stream generators for the differential test: random small feeds and scaled-down shapes of the paper's
scenarios.  A stream spec is a plain dict (see harness.build); every statement is named, prev links refer to
names (or to an external digest), and arrivals are (t_ms, name, wrap, mode)."""
from __future__ import annotations

import random


class SpecBuilder:
    def __init__(self, devices, h_max_ms=20_000):
        self.devices = list(devices)
        self.h_max_ms = h_max_ms
        self.stmts, self.arrivals, self.names = [], [], set()
        self.kind_counts = {}

    def stmt(self, name, did, ep, seq, ts, prev, val, legit):
        assert name not in self.names, name
        self.names.add(name)
        self.stmts.append({"name": name, "did": did, "ep": ep, "seq": seq, "ts": int(ts), "prev": prev,
                           "val": round(float(val), 3), "legit": legit})
        return name

    def arrive(self, t, name, wrap=0, mode="live"):
        self.arrivals.append((int(t), name, wrap, mode))

    def note(self, kind, n=1):
        self.kind_counts[kind] = self.kind_counts.get(kind, 0) + n

    def spec(self, t_end, family, seed):
        return {"devices": self.devices, "h_max_ms": self.h_max_ms, "stmts": self.stmts,
                "arrivals": self.arrivals, "t_end": int(t_end), "family": family, "seed": seed,
                "kinds": dict(self.kind_counts)}


def _delay(rng, k):
    d = k.get("base", 20) + rng.expovariate(1.0 / k.get("jitter", 10))
    if rng.random() < k.get("p_reorder", 0):
        d += rng.uniform(200, k.get("reorder_max", 3_000))
    if rng.random() < k.get("p_long", 0):
        d += rng.uniform(k.get("long_min", 20_000), k.get("long_max", 90_000))
    return int(d)


def feed(b: SpecBuilder, rng, did, ep, n, t0, k, label=""):
    """One (did, ep) feed of n productions at ~1 Hz with faults and attacks drawn from knobs k.
    Returns the time of the last production."""
    seq, prev = 0, None
    t = t0
    imp_from = k.get("impersonate_from")            # index from which the device is impersonated
    fprev = None
    for i in range(n):
        t = t0 + i * k.get("period", 1_000) + int(rng.uniform(0, k.get("prod_jitter", 0)))
        name = f"{did}/{ep}/{seq}/g{i}"
        b.stmt(name, did, ep, seq, t, prev, 50 + 10 * rng.random(), True)
        bug = rng.random() < k.get("p_seqbug", 0) and i < n - 1
        if bug:
            b.note("seq_reuse")
        if imp_from is not None and i >= imp_from:
            # full impersonation: genuine suppressed, forged chain re-linked to forged predecessors
            fname = f"{did}/{ep}/{seq}/imp{i}"
            fp = prev if i == imp_from else fprev
            b.stmt(fname, did, ep, seq, t, fp, 99 + rng.random(), False)
            b.arrive(t + _delay(rng, k), fname)
            fprev = fname
            b.note("impersonation")
            prev = name
            seq = seq if bug else seq + 1
            continue
        delivered = True
        r = rng.random()
        if r < k.get("p_gapfill", 0):
            delivered = False
            f = b.stmt(f"{did}/{ep}/{seq}/gf{i}", did, ep, seq, t, prev, -5 - rng.random(), False)
            b.arrive(t + _delay(rng, k), f)
            b.note("gapfill")
        elif r < k.get("p_gapfill", 0) + k.get("p_supp", 0):
            delivered = False
            b.note("suppressed")
        ta = t + _delay(rng, k)
        if delivered:
            b.arrive(ta, name, 0, "buffered" if ta - t > 5_000 else "live")
            if rng.random() < k.get("p_dup", 0):
                late = rng.random() < k.get("p_dup_late", 0.1)
                b.arrive(ta + (rng.uniform(10_000, 80_000) if late else rng.uniform(1, 500)), name)
                b.note("duplicate")
            if rng.random() < k.get("p_rewrap", 0):
                b.arrive(ta + rng.uniform(1_000, 30_000), name, 1, "buffered")
                b.note("rewrap")
        if rng.random() < k.get("p_equiv", 0):
            f = b.stmt(f"{did}/{ep}/{seq}/eq{i}", did, ep, seq, t, prev, 200 + rng.random(), False)
            mode = rng.choice(k.get("equiv_modes", ("front", "back", "late")))
            if mode == "front":
                tf = ta - rng.randint(1, 50)
            elif mode == "back":
                tf = ta + 50
            else:
                tf = ta + rng.uniform(5_000, 70_000)
            b.arrive(tf, f)
            b.note("equivocation_" + mode)
        if rng.random() < k.get("p_badlink", 0):
            f = b.stmt(f"{did}/{ep}/{seq + 1}/bl{i}", did, ep, seq + 1, t + 500,
                       {"ext": f"{did}{ep}{seq}{i}{rng.random()}"}, 300 + rng.random(), False)
            b.arrive(t + 500 + _delay(rng, k), f)
            b.note("badlink")
        b.note("genuine")
        prev = name
        if not bug:
            seq += 1
    return t


def partition(b: SpecBuilder, rng, did, ep, n, t0, k, p_from, p_to, rate_ms=17):
    """Feed whose relay is disconnected from p_from to p_to (ms): productions in the window are buffered and
    delivered in order at reconnection at about 60 per second; those older than h_max are STALE_TS."""
    seq, prev, t = 0, None, t0
    backlog = []
    for i in range(n):
        t = t0 + i * k.get("period", 1_000)
        name = f"{did}/{ep}/{seq}/g{i}"
        b.stmt(name, did, ep, seq, t, prev, 50 + 10 * rng.random(), True)
        if p_from <= t < p_to:
            backlog.append(name)
        else:
            if rng.random() < k.get("p_equiv", 0):
                f = b.stmt(f"{did}/{ep}/{seq}/eq{i}", did, ep, seq, t, prev, 200 + rng.random(), False)
                b.arrive(t + _delay(rng, k) + rng.choice((-30, 50)), f)
                b.note("equivocation")
            ta = max(t, p_to + rate_ms * len(backlog)) + _delay(rng, k) if t >= p_to else t + _delay(rng, k)
            b.arrive(ta, name)
        b.note("genuine")
        prev = name
        seq += 1
    for j, name in enumerate(backlog):
        b.arrive(p_to + rate_ms * j + _delay(rng, {"base": 20, "jitter": 5}), name, 0, "buffered")
        if rng.random() < k.get("p_dup", 0):
            b.arrive(p_to + rate_ms * j + 2_000 + rng.uniform(0, 100), name, 0, "buffered")
            b.note("duplicate")
    b.note("backlog", len(backlog))
    return t


# ------------------------------------------------------------------------------------------------ families
def rand_small(seed):
    rng = random.Random(seed)
    devs = [f"d{i}" for i in range(1, rng.choice((1, 1, 2, 2, 3)) + 1)]
    b = SpecBuilder(devs, h_max_ms=rng.choice((20_000, 20_000, 3_600_000)))
    last = 0
    for did in devs:
        t0 = rng.randint(0, 3_000)
        for ep in range(rng.choice((1, 1, 2))):
            k = {"p_reorder": rng.choice((0, 0.1, 0.3)), "p_long": rng.choice((0, 0, 0.05, 0.15)),
                 "long_min": 15_000, "long_max": 90_000,
                 "p_dup": rng.choice((0, 0.1, 0.25)), "p_dup_late": 0.2, "p_supp": rng.choice((0, 0.05, 0.15)),
                 "p_equiv": rng.choice((0, 0.1, 0.2, 0.35)), "p_gapfill": rng.choice((0, 0.05, 0.15)),
                 "p_badlink": rng.choice((0, 0, 0.05)), "p_seqbug": rng.choice((0, 0, 0.05, 0.1)),
                 "p_rewrap": rng.choice((0, 0, 0.05)), "prod_jitter": rng.choice((0, 300))}
            n = rng.randint(4, 20)
            t_last = feed(b, rng, did, ep, n, t0, k)
            last = max(last, t_last)
            t0 = t_last + rng.randint(1_000, 5_000)
    t_arr = max(t for t, *_ in b.arrivals) if b.arrivals else 0
    return b.spec(max(t_arr, last) + rng.choice((75_000, 100_000, 140_000)), "rand_small", seed)


def s05_like(seed, n=90):
    """Stolen device and relay keys: equivocation (forged after / before the genuine), gap-fill, impersonation."""
    rng = random.Random(seed)
    devs = ["eqb", "eqf", "gap", "imp", "ok"]
    b = SpecBuilder(devs, h_max_ms=3_600_000)
    a0, a1 = 10, n - 10
    for did in devs:
        t0 = rng.randint(0, 999)
        k = {"p_dup": 0.0}
        if did == "eqb":
            k.update(p_equiv=0.10, equiv_modes=("back",))
        elif did == "eqf":
            k.update(p_equiv=0.10, equiv_modes=("front",))
        elif did == "gap":
            k.update(p_gapfill=0.10)
        elif did == "imp":
            k.update(impersonate_from=n // 2)
        if did in ("eqb", "eqf", "gap"):
            kk = dict(k)
            kk_quiet = {key: v for key, v in k.items() if not key.startswith("p_")}
            feed_segments(b, rng, did, 0, n, t0, kk_quiet, kk, a0, a1)
        else:
            feed(b, rng, did, 0, n, t0, k)
    return b.spec(n * 1_000 + 90_000, "s05_like", seed)


def feed_segments(b, rng, did, ep, n, t0, k_quiet, k_attack, a0, a1):
    """A feed whose attack knobs apply only between production index a0 and a1 (as in the scenarios)."""
    seq, prev = 0, None
    for i in range(n):
        k = k_attack if a0 <= i < a1 else k_quiet
        t = t0 + i * 1_000
        name = f"{did}/{ep}/{seq}/g{i}"
        b.stmt(name, did, ep, seq, t, prev, 50 + 10 * rng.random(), True)
        r = rng.random()
        delivered = True
        if r < k.get("p_gapfill", 0):
            delivered = False
            f = b.stmt(f"{did}/{ep}/{seq}/gf{i}", did, ep, seq, t, prev, -5 - rng.random(), False)
            b.arrive(t + _delay(rng, k), f)
            b.note("gapfill")
        ta = t + _delay(rng, k)
        if delivered:
            b.arrive(ta, name)
        if rng.random() < k.get("p_equiv", 0):
            f = b.stmt(f"{did}/{ep}/{seq}/eq{i}", did, ep, seq, t, prev, 200 + rng.random(), False)
            mode = rng.choice(k.get("equiv_modes", ("back",)))
            b.arrive(ta - rng.randint(1, 50) if mode == "front" else ta + 50, f)
            b.note("equivocation_" + mode)
        b.note("genuine")
        prev = name
        seq += 1


def s08_like(seed, n=100):
    """Benign sequence reuse: the device counter is not advanced once, twice per feed, on two devices."""
    rng = random.Random(seed)
    devs = ["bug1", "bug2", "ok"]
    b = SpecBuilder(devs, h_max_ms=3_600_000)
    for j, did in enumerate(devs):
        t0 = rng.randint(0, 999)
        seq, prev = 0, None
        bug_at = {25 + 13 * j, 65 + 10 * j} if did != "ok" else set()
        for i in range(n):
            t = t0 + i * 1_000
            name = f"{did}/0/{seq}/g{i}"
            b.stmt(name, did, 0, seq, t, prev, 50 + 10 * rng.random(), True)
            b.arrive(t + _delay(rng, {}), name)
            prev = name
            if i in bug_at:
                b.note("seq_reuse")
            else:
                seq += 1
            b.note("genuine")
    return b.spec(n * 1_000 + 90_000, "s08_like", seed)


def s12_like(seed, n=120):
    """Beyond-horizon backlog: relay partitioned longer than h_max; backlog drained at reconnection."""
    rng = random.Random(seed)
    devs = ["p1", "p2", "ok"]
    b = SpecBuilder(devs, h_max_ms=30_000)
    for did in devs:
        t0 = rng.randint(0, 999)
        if did == "ok":
            feed(b, rng, did, 0, n, t0, {})
        else:
            partition(b, rng, did, 0, n, t0, {"p_dup": 0.05}, 20_000, 70_000 + rng.randint(0, 10_000))
    return b.spec(n * 1_000 + 90_000, "s12_like", seed)


def s99_like(seed, n=100):
    """Mixed: equivocation, gap-fill, seq reuse, beyond-horizon partition with a fork in the same feed,
    reordering, duplicates and long delays."""
    rng = random.Random(seed)
    devs = ["m1", "m2", "m3", "m4"]
    b = SpecBuilder(devs, h_max_ms=30_000)
    base = {"p_reorder": 0.10, "p_long": 0.01, "long_min": 30_000, "long_max": 90_000, "p_dup": 0.05}
    for did in devs:
        t0 = rng.randint(0, 999)
        if did == "m1":
            feed(b, rng, did, 0, n, t0, dict(base, p_equiv=0.10, equiv_modes=("front", "back")))
        elif did == "m2":
            feed(b, rng, did, 0, n, t0, dict(base, p_gapfill=0.05, p_seqbug=0.02))
        elif did == "m3":
            partition(b, rng, did, 0, n, t0, dict(base, p_equiv=0.08), 15_000, 60_000 + rng.randint(0, 15_000))
        else:
            t_last = feed(b, rng, did, 0, n // 2, t0, dict(base, p_equiv=0.05))
            feed(b, rng, did, 1, n // 2, t_last + 2_000, dict(base, p_supp=0.05))
    return b.spec(n * 1_000 + 100_000, "s99_like", seed)


def stale_into_held(seed):
    """Targeted shape: a fork followed by beyond-horizon (STALE_TS) arrivals with seq >= fork point, and stale
    duplicates of already admitted wires (exercises the release-into-a-held-feed path)."""
    rng = random.Random(seed)
    b = SpecBuilder(["s1"], h_max_ms=10_000)
    did, ep, seq, prev = "s1", 0, 0, None
    n = rng.randint(8, 30)
    fork_i = rng.randint(1, n // 2)
    for i in range(n):
        t = i * 1_000
        name = f"{did}/{ep}/{seq}/g{i}"
        b.stmt(name, did, ep, seq, t, prev, 50 + rng.random(), True)
        r = rng.random()
        if i > fork_i and r < 0.3:
            b.arrive(t + rng.uniform(11_000, 40_000), name, 0, "buffered")          # stale
            b.note("stale")
        else:
            ta = t + 20 + rng.uniform(0, 30)
            b.arrive(ta, name)
            if rng.random() < 0.15:
                b.arrive(t + rng.uniform(10_500, 40_000), name, 0, "buffered")      # stale duplicate
                b.note("stale_duplicate")
        if i == fork_i or rng.random() < 0.05:
            f = b.stmt(f"{did}/{ep}/{seq}/eq{i}", did, ep, seq, t, prev, 200 + rng.random(), False)
            b.arrive(t + 60 + rng.uniform(0, 3_000), f)
            b.note("equivocation")
        b.note("genuine")
        prev = name
        seq += 1
    return b.spec(n * 1_000 + 130_000, "stale_into_held", seed)


FAMILIES = {"rand_small": rand_small, "s05_like": s05_like, "s08_like": s08_like, "s12_like": s12_like,
            "s99_like": s99_like, "stale_into_held": stale_into_held}
