#!/usr/bin/env bash
# Re-runs every ProVerif model in this folder and writes the full, unedited outputs to proverif_output.txt.
# ProVerif 2.05 was installed with opam (switch ocaml-system); see README.md "Tooling".
set -u
cd "$(dirname "$0")"
export PATH=/root/.opam/ocaml-system/bin:$PATH
OUT=../results/formal/proverif_output.txt   # V3 repository layout
MODELS="pbti.pv pbti_variant_nocompromise.pv pbti_variant_otlink_attacker.pv"
{
  echo "# ProVerif outputs for the PBTI symbolic models"
  echo "# generated: $(date -u +%Y-%m-%dT%H:%M:%SZ) on $(uname -srm)"
  echo "# proverif: $(command -v proverif)  ($(proverif -help 2>&1 | head -1))"
  echo "# opam package proverif $(opam show proverif --field=version 2>/dev/null); upstream url block from the opam file:"
  opam show proverif --raw 2>/dev/null | sed -n '/^url/,/^}/p' | sed 's/^/#     /'
  echo "# (the archive itself was retrieved from https://opam.ocaml.org/cache and checked by opam against this checksum)"
  echo "# models (sha256):"
  for m in $MODELS; do echo "#   $(sha256sum "$m")"; done
  echo "#"
  echo "# Summary of RESULT lines (the full outputs follow):"
  for m in $MODELS; do
    echo "## $m"
    timeout 600 proverif "$m" 2>&1 | grep '^RESULT' | sed 's/^/#   /'
  done
  for m in $MODELS; do
    echo
    echo "=================================================================================================="
    echo "== proverif $m"
    echo "=================================================================================================="
    start=$(date +%s.%N)
    timeout 600 proverif "$m" 2>&1
    rc=$?
    end=$(date +%s.%N)
    echo "== exit code $rc, wall time $(echo "$end - $start" | bc) s"
  done
} > "$OUT"
echo "wrote $OUT ($(wc -l < "$OUT") lines)"
grep -c '^RESULT' "$OUT"
