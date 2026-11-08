#!/bin/bash
# V9: rerun every comparison family that contains B5 or B5S rows with the corrected B5, on the frozen
# specifications and seeds (priority order: review-timing comparison, V3 main evaluation, mixed workload, A0, A3,
# sweep and factorial, SKAB replay).  Resumable: rows already present are skipped.  Outputs: results/v9/raw/.
# usage: experiments/v9/run_all_b5c.sh [SKAB_DIR]     (SKAB_DIR: clone of https://github.com/waico/SKAB at
#        commit b2c0d46c2971dcbfe71e26087b6d231998bb91c2; per-file SHA-256 in results/raw/v3_replay_skab_dataset.json)
set -e
cd "$(dirname "$0")/../.."
SKAB=${1:-}
W=${WORKERS:-2}
OUT=results/v9/raw
mkdir -p $OUT
python3 scripts/verify_prereg_hashes.py > /dev/null
V4="python3 experiments/v9/run_v4_b5c.py"; V3="python3 experiments/v9/run_v3_b5c.py"
date -u +"start %FT%TZ"
$V4 experiments/v4_configs/A1_review.json --systems B5 --out $OUT/A1_review_B5c.jsonl --workers $W
$V3 scenarios --systems B5  --out $OUT/v3_scenarios_B5c.jsonl  --workers $W
$V3 ablations --systems B5  --out $OUT/v3_mixed_B5c.jsonl      --workers $W
$V3 scenarios --systems B5S --out $OUT/v3_scenarios_B5Sc.jsonl --workers $W
$V3 ablations --systems B5S --out $OUT/v3_mixed_B5Sc.jsonl     --workers $W
$V4 experiments/v4_configs/A0_core.json --systems B5 B5S --out $OUT/A0_core_B5c.jsonl --workers $W
$V4 experiments/v4_configs/A3_selective.json --systems B5 B5S --out $OUT/A3_selective_B5c.jsonl --workers $W
$V4 experiments/v4_configs/amendment1/A3_factorial.json --systems B5 B5S --out $OUT/A3_factorial_B5c.jsonl --workers $W
$V3 sweep     --systems B5  --out $OUT/v3_sweep_B5c.jsonl      --workers $W
$V3 factorial --systems B5  --out $OUT/v3_factorial_B5c.jsonl  --workers $W
if [ -n "$SKAB" ]; then
  $V3 replay --systems B5 --skab-dir "$SKAB" --out $OUT/v3_replay_skab_B5c.jsonl --workers $W
fi
date -u +"end %FT%TZ"
