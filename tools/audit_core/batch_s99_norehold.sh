#!/bin/bash
# no-re-hold B5 variant (temporal on) for the two near-margin A1 arms on S99, seeds 21-40
R=/home/claude/PBTI_v7/scratch/audit_core/repo
T=/home/claude/PBTI_v7/tools/audit_core/run_variant.py
OUT=/home/claude/PBTI_v7/results/audit_core/s99_norehold_A1seeds.jsonl
: > $OUT
cd $R
for cfg in '{"review_delay_ms": 1000, "review_every_ms": 10000, "review_rule": "defer"}' \
           '{"review_delay_ms": 5000, "review_every_ms": 1000, "review_rule": "defer"}'; do
  for seed in $(seq 21 40); do
    nice -n 10 python3 $T $R norehold B5 S99_mixed $seed "$cfg" >> $OUT
  done
done
echo done
