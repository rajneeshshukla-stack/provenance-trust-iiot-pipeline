#!/usr/bin/env python3
"""Copy the generated LaTeX files of an analysis tree into the manuscript under neutral names.

The analysis scripts name their outputs after the stage that introduced them (v3_, v4_, v7_, v9_); the manuscript
sources use names that describe the content instead. Contents are copied byte for byte; only the file names change.
Files without an entry below keep their names. The mapping is the only place where the two sets of names meet.

Usage: python3 -I import_generated.py SRC_GENERATED_DIR PAPER_DIR
"""
import shutil
import sys
from pathlib import Path

NAMES = {
    "results_macros.tex": "macros_R.tex", "v3_macros.tex": "macros_V.tex", "v4_macros.tex": "macros_W.tex",
    "v7_macros.tex": "macros_X.tex", "v9_macros.tex": "macros_Y.tex",
    "tab_v7_primary.tex": "tab_primary.tex", "tab_v7_effects.tex": "tab_effects.tex",
    "tab_v7_messagebytes.tex": "tab_messagebytes.tex", "tabS_v7_reexec.tex": "tabS_reexec.tex",
    "tab_outcomes_v3.tex": "tab_outcomes_main.tex", "tabS_v3_b5.tex": "tabS_holds.tex",
    "tabS_v3_batching.tex": "tabS_batching.tex", "tabS_v3_e2e.tex": "tabS_e2e_reps.tex",
    "tabS_v3_e2e_skab.tex": "tabS_e2e_skab.tex", "tabS_v3_factorial.tex": "tabS_factorial.tex",
    "tabS_v3_replay.tex": "tabS_replay.tex", "tabS_v3_tests.tex": "tabS_registered_tests.tex",
    "tabS_v4_a1_tests.tex": "tabS_review_tests.tex", "tabS_v4_a3.tex": "tabS_selective_grid.tex",
    "tabS_v4_a3_gates.tex": "tabS_selective_gates.tex", "tabS_v4_a3_scenarios.tex": "tabS_selective_controls.tex",
    "tabS_v4_a3f.tex": "tabS_selective_cells.tex", "tabS_v4_a5.tex": "tabS_lifecycle.tex",
    "tabS_v4_temporal.tex": "tabS_reexec_temporal.tex",
    "tabS_v9_classchanges.tex": "tabS_correction_classes.tex", "tabS_v9_runs.tex": "tabS_correction_runs.tex",
    "tabS_v9_wsplit.tex": "tabS_wsplit.tex", "tabS_v9_e04_cells.tex": "tabS_attacker_cells.tex",
    "tabS_v9_e04_cmp.tex": "tabS_attacker_cmp.tex", "tabS_v9_e04_controls.tex": "tabS_attacker_controls.tex",
}

if __name__ == "__main__":
    src, dst = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve() / "generated"
    dst.mkdir(parents=True, exist_ok=True)
    targets = {}
    for p in sorted(src.glob("*.tex")):
        n = NAMES.get(p.name, p.name)
        if n in targets:
            raise SystemExit(f"name collision: {p.name} and {targets[n]} -> {n}")
        targets[n] = p.name
        shutil.copyfile(p, dst / n)
    print(f"imported {len(targets)} generated files into {dst}")
