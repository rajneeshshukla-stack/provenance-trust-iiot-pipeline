"""pytest wrapper for the hand-computed oracle/temporal cases (hand_cases.py).

Run:  cd /home/claude/PBTI_v7/tools/oracle_audit && python3 -m pytest -q test_hand_cases.py -p no:cacheprovider

Every expected value was derived by hand (see the comments in hand_cases.py). Each case asserts that the repository's
oracle/temporal output AND the independent reference equal the hand value for every field, except the secondary
counters listed in KNOWN_DEFECTS, for which the test asserts that the repository DIFFERS from the hand value (the
defect is reproduced; fix it and these assertions will fail, flagging that the list must be updated)."""
import pytest

import hand_cases as H

KNOWN_DEFECTS = {
    # B5 `holds` counts an admission twice when the receipt's own fork evidence makes _fork() hold its slot first
    ("case_E_b5_hold_then_release", "holds"), ("case_E2_b5_rehold_after_release", "holds"),
    # run_v4.py held_distinct_ever only sees holds that emit a HELD state event (retroactive), not admission holds
    ("case_E_b5_hold_then_release", "held_distinct_ever"),
    # oracle legit_quarantined depends on store history, not current state
    ("case_E2_b5_rehold_after_release", "legit_quarantined"),
    ("case_E2_b5_rehold_after_release", "legit_lost_unrecoverable"),
    ("case_O_pbti_sh_provisional_to_end", "legit_quarantined"),
    ("case_O_pbti_sh_provisional_to_end", "legit_lost_unrecoverable"),
}


@pytest.mark.parametrize("fn", H.CASES, ids=[f.__name__ for f in H.CASES])
def test_case(fn):
    w, rx, exp, exp_rx = fn()
    repo, ref = w.finish()
    assert rx == exp_rx, "receipt dispositions differ from the hand-derived trace"
    for f, e in exp.items():
        got = repo.get(f)
        if (fn.__name__, f) in KNOWN_DEFECTS:
            assert not H._eq(e, got), f"{f}: defect no longer reproduced (update KNOWN_DEFECTS)"
            continue
        assert H._eq(e, got), f"{fn.__name__}: {f} expected {e} (hand), repository {got}"
        rk = H.RMAP.get(f)
        if rk is not None:
            assert H._eq(e, ref.get(rk)), f"{fn.__name__}: {f} expected {e} (hand), reference {ref.get(rk)}"
        if f == "tm_transitions":
            assert len(w.poller.trans_call) == e
