#!/bin/bash
# Survey of B5 re-holds across campaign points (instrumented B5, behaviour unchanged). Sequential, niced.
R=/home/claude/PBTI_v7/scratch/audit_core/repo
T=/home/claude/PBTI_v7/tools/audit_core/run_variant.py
OUT=/home/claude/PBTI_v7/results/audit_core/rehold_survey.jsonl
: > $OUT
EV='{"review_mode": "event", "review_delay_ms": 0, "review_rule": "defer"}'
D0C1='{"review_delay_ms": 0, "review_every_ms": 1000, "review_rule": "defer"}'
cd $R
for seed in 21 22; do
  for p in '{"equivocation": 0.05, "delay": 0.01}' '{"equivocation": 0.05, "delay": 0.05}' '{"equivocation": 0.05, "delay": 0.1}' \
           '{"equivocation": 0.1, "missing": 0.1}' '{"equivocation": 0.05, "missing_long": 0.05}' run8 run9 run14 run15 run3; do
    nice -n 10 python3 $T $R instr B5 "$p" $seed >> $OUT
    nice -n 10 python3 $T $R instr B5 "$p" $seed "$EV" >> $OUT
    nice -n 10 python3 $T $R instr B5 "$p" $seed "$D0C1" >> $OUT
  done
done
for seed in 21 22; do
  for cfg in '{}' "$EV" "$D0C1"; do
    nice -n 10 python3 $T $R instr B5 S99_mixed $seed "$cfg" >> $OUT
  done
done
echo done
