#!/usr/bin/env bash
# Step 1 of the Option 2 handout: synthesize a design and write it as an AIG.
#   src/make_aig.sh <design.v> <top> <out.aag> [extra read_verilog flags]
# Flip-flops with asynchronous resets cannot be written to AIGER, so they are
# converted with async2sync and dffunmap first (handout section 4, step 1).
set -euo pipefail
YOSYS=${YOSYS:-yosys}
v=$1; top=$2; out=$3; flags=${4:-}
mkdir -p "$(dirname "$out")"
$YOSYS -q -l "${out%.*}.log" -p "
  read_verilog $flags $v
  synth -flatten -top $top
  async2sync
  dffunmap
  aigmap
  opt_clean
  write_aiger -ascii -map ${out%.*}.map $out
  stat
"
head -1 "$out"
