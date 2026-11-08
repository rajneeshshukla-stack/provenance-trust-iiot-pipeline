#!/bin/sh
# Minimal re-execution of selected seeds of every confirmatory and main campaign, compared field by field with the
# stored results (prompt item 1.4). Intended to be run by an author on an author-controlled machine; the same script
# was also run in the automated cloud workspace, which is NOT an author-controlled machine.
#
# Usage: sh reproduce_subset.sh REPO_DIR OUT_DIR [LABEL]
#   REPO_DIR  an assembled repository (06_Reproducibility/assemble_repository.sh) with the stored results/
#   OUT_DIR   new, empty output directory (the stored results are never written to)
#   LABEL     free text recorded in the report, e.g. "author R.S., own laptop"
# Environment: PY (default python3), WORKERS (default 2).
# Run time on two vCPUs: about 45 minutes (754 simulation runs, test suite, lifecycle matrix, bounded checks).
set -u
REPO=$(cd "$1" && pwd)
mkdir -p "$2"
OUT=$(cd "$2" && pwd)
LABEL=${3:-"unlabelled re-execution"}
PY=${PY:-python3}
WORKERS=${WORKERS:-2}
HERE=$(cd "$(dirname "$0")" && pwd)
SCRATCH="$OUT/scratch_repo"
STEPS="$OUT/steps.tsv"
: > "$STEPS"

step() {  # step NAME COMMAND...  (runs in the scratch copy, records exit code and UTC times)
  name=$1; shift
  start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  ( cd "$SCRATCH" && "$@" ) > "$OUT/$name.log" 2>&1
  rc=$?
  end=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$rc" "$start" "$end" "$*" >> "$STEPS"
  echo "[$end] $name exit=$rc"
}

echo "copying repository to $SCRATCH (the stored results stay untouched)"
rm -rf "$SCRATCH"
cp -R "$REPO" "$SCRATCH"
"$PY" "$HERE/env_record.py" "$SCRATCH" "$OUT/environment.json" --label "$LABEL"

step pytest "$PY" -m pytest -q tests/

step A0_core "$PY" experiments/run_v4.py experiments/v4_configs/A0_core.json --seeds 1 2 --workers "$WORKERS" \
     --out "$OUT/A0_core_subset.jsonl"
step A1_review "$PY" experiments/run_v4.py experiments/v4_configs/A1_review.json --seeds 21 22 --workers "$WORKERS" \
     --out "$OUT/A1_review_subset.jsonl"
step A3_selective "$PY" experiments/run_v4.py experiments/v4_configs/A3_selective.json --seeds 21 22 \
     --workers "$WORKERS" --out "$OUT/A3_selective_subset.jsonl"
step A3_scenarios "$PY" experiments/run_v4.py experiments/v4_configs/A3_scenarios.json --seeds 1 2 \
     --workers "$WORKERS" --out "$OUT/A3_scenarios_subset.jsonl"
step A3_factorial "$PY" experiments/run_v4.py experiments/v4_configs/amendment1/A3_factorial.json --seeds 21 22 \
     --workers "$WORKERS" --out "$OUT/A3_factorial_subset.jsonl"
step A5_matrix "$PY" scripts/a5_lifecycle_matrix.py
cp "$SCRATCH/results/v4/summary/A5_lifecycle_matrix.json" "$OUT/A5_lifecycle_matrix.json" 2>/dev/null
step formal_check "$PY" formal/v4_locality_lifecycle_check.py --out "$OUT/v4_locality_lifecycle_check.json"

"$PY" "$HERE/compare_reexec.py" --stored-repo "$REPO" --new "$OUT" \
      --out-json "$OUT/reexecution_comparison.json" --out-md "$OUT/REEXECUTION_REPORT.md"
echo "report: $OUT/REEXECUTION_REPORT.md"
echo "you may delete $SCRATCH after reading the report"
