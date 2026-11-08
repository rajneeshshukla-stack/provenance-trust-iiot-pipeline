#!/bin/sh
# Build the article and the supplement with stable cross-document references.
# Usage: sh tools/manuscript/build_all.sh PAPER_DIR      (PAPER_DIR contains parts/, generated/, main.tex, supplementary.tex)
set -e
P="$1"
T="$(cd "$(dirname "$0")" && pwd)"
cd "$P"
cat parts/p1_front_to_s4.tex parts/p2_s5_s6.tex parts/p3_s7_end.tex > main.tex
touch generated/supp_xref.tex generated/main_xref.tex
python3 -I "$T/xref_maps.py" .
for pass in 1 2 3; do
  latexmk -pdf -interaction=nonstopmode -halt-on-error supplementary.tex > build_supplementary.log 2>&1 || { tail -n 40 build_supplementary.log; exit 1; }
  latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex > build_main.log 2>&1 || { tail -n 40 build_main.log; exit 1; }
  if python3 -I "$T/xref_maps.py" . --check > /dev/null; then
    echo "cross-references stable after pass $pass"
    exit 0
  fi
  python3 -I "$T/xref_maps.py" . > /dev/null
done
echo "cross-references not stable after 3 passes" >&2
exit 1
