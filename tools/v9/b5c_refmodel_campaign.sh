#!/bin/bash
# V9 differential check of the corrected B5 against the reference model (corrected choices).
# usage: tools/v9/b5c_refmodel_campaign.sh <out_dir> <scale: validation|full>
set -e
cd "$(dirname "$0")/../.."
OUT=${1:-results/v9/b5c_refmodel}; SCALE=${2:-validation}
mkdir -p "$OUT"
run() { fam=$1; lo=$2; hi=$3; step=$4
  for ((s=lo; s<hi; s+=step)); do e=$((s+step)); [ $e -gt $hi ] && e=$hi
    nice -n 5 python3 tools/v9/b5c_refmodel_diff.py --family $fam --seeds $s:$e --out "$OUT/$fam.jsonl"
  done; }
date -u +"start %FT%TZ"
if [ "$SCALE" = full ]; then
  run stale_into_held 0 400 100; run rand_small 0 2500 250
  run s08_like 0 100 25; run s12_like 0 100 25; run s05_like 0 100 25; run s99_like 0 100 25
else
  run stale_into_held 0 400 100; run rand_small 0 500 250
  run s08_like 0 10 10; run s12_like 0 10 10; run s05_like 0 10 10; run s99_like 0 10 10
fi
date -u +"end %FT%TZ"
