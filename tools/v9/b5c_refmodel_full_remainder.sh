#!/bin/bash
# Extends the validation-scale differential check (tools/v9/b5c_refmodel_campaign.sh ... validation) to the scale of
# the V7 reference-model campaign (stale_into_held 0-400, rand_small 0-2500, s05/s08/s12/s99-like 0-100), appending to
# the same files.  Runs at the lowest CPU priority.
set -e
cd "$(dirname "$0")/../.."
OUT=${1:-results/v9/b5c_refmodel}
run() { fam=$1; lo=$2; hi=$3; step=$4
  for ((s=lo; s<hi; s+=step)); do e=$((s+step)); [ $e -gt $hi ] && e=$hi
    nice -n 19 python3 tools/v9/b5c_refmodel_diff.py --family $fam --seeds $s:$e --out "$OUT/$fam.jsonl"
  done; }
date -u +"start %FT%TZ"
run rand_small 500 2500 250
run s08_like 10 100 30; run s12_like 10 100 30; run s05_like 10 100 30; run s99_like 10 100 30
date -u +"end %FT%TZ"
