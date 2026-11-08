#!/usr/bin/env python3
"""Internal-consistency checks over every stored V4 row (no simulation):
  C1  n_reachable == tm_reach
  C2  O2 (legit_missing) == tm_never_avail + tm_withdrawn_end   (holds unless a commit lands exactly at T_end,
      or content-based and pair-based availability differ)
  C3  O1 (nonlegit_auth) == tm_nl_auth_end                     (content-based vs pair-based at the end)
  C4  AV1 <= AV5 <= AV30 <= AV60 <= 1 - never/reach
  C5  W >= 0; tm_wh_rec_s >= 0; NLX >= 0
  C6  legit_quarantined + legit_lost_unrecoverable == legit_missing
  C7  tm_end_state_matches_authoritative
"""
import json, collections, sys
REPO = "/home/claude/PBTI_v7/scratch/oracle_audit/repo"
out = {}
viol = collections.defaultdict(list)
for camp in ["A0_core", "A1_review", "A3_selective", "A3_factorial", "A3_scenarios"]:
    for line in open(f"{REPO}/results/v4/raw/{camp}.jsonl"):
        r = json.loads(line)
        if "error" in r:
            viol["error"].append(camp); continue
        tag = (camp, r["arm"], r.get("point") or r.get("scenario"), r["seed"])
        if r["n_reachable"] != r["tm_reach"]: viol["C1"].append(tag)
        d2 = r["legit_missing"] - (r["tm_never_avail"] + r["tm_withdrawn_end"])
        if d2 != 0: viol["C2"].append((tag, d2))
        d3 = r["nonlegit_auth"] - r["tm_nl_auth_end"]
        if d3 != 0: viol["C3"].append((tag, d3))
        n = max(1, r["tm_reach"])
        av = [r["tm_avail_1s"], r["tm_avail_5s"], r["tm_avail_30s"], r["tm_avail_60s"], 1 - r["tm_never_avail"] / n]
        if any(av[i] > av[i + 1] + 1e-12 for i in range(4)): viol["C4"].append(tag)
        if r["tm_wh_rec_s"] < 0 or r["tm_nl_rec_s"] < 0: viol["C5"].append(tag)
        if r["legit_quarantined"] + r["legit_lost_unrecoverable"] != r["legit_missing"]: viol["C6"].append(tag)
        if not r["tm_end_state_matches_authoritative"]: viol["C7"].append(tag)
        out[camp] = out.get(camp, 0) + 1
print("rows", out)
for k in ["error", "C1", "C2", "C3", "C4", "C5", "C6", "C7"]:
    v = viol.get(k, [])
    print(k, len(v), v[:6])
if viol.get("C2"):
    c = collections.Counter((t[0][0], t[0][1], t[0][2] if t[0][0] != "A3_selective" else "grid") for t in viol["C2"])
    print("C2 by campaign/arm/scenario:", c.most_common(20))
    print("C2 deltas:", collections.Counter(t[1] for t in viol["C2"]).most_common(10))
if viol.get("C3"):
    print("C3 deltas:", collections.Counter(t[1] for t in viol["C3"]).most_common(10))
json.dump({k: [list(map(str, x)) if isinstance(x, tuple) else x for x in v] for k, v in viol.items()},
          open("/home/claude/PBTI_v7/results/oracle_audit/stored_consistency.json", "w"), indent=1, default=str)
