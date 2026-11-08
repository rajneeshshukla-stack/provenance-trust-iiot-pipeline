#!/bin/bash
R=/home/claude/PBTI_v7/scratch/audit_core/repo
T=/home/claude/PBTI_v7/tools/audit_core/run_variant.py
OUT=/home/claude/PBTI_v7/results/audit_core/rehold_fix_s99.jsonl
: > $OUT
cd $R
for seed in 21 22; do
  for cfg in '{"review_delay_ms": 0, "review_every_ms": 1000, "review_rule": "defer"}' \
             '{"review_delay_ms": 0, "review_every_ms": 10000, "review_rule": "defer"}' \
             '{"review_delay_ms": 1000, "review_every_ms": 1000, "review_rule": "defer"}'; do
    for v in instr norehold; do
      nice -n 10 python3 $T $R $v B5 S99_mixed $seed "$cfg" >> $OUT
    done
  done
done
echo done
