#!/usr/bin/env bash
# Step 1, second part: write the graph after ABC has restructured it (strash; dch)
# and check it is equivalent to the graph it came from.
#   src/abc_after.sh <before.aig> <after.aig>        (binary AIGER: ABC reads no .aag)
# The last strash drops dch's choice nodes, which write_aiger would otherwise
# emit as ANDs that drive nothing (cpu8: 850 of 1,959).
set -euo pipefail
ABC=${ABC:-yosys-abc}
in=$1; out=$2
$ABC -c "read_aiger $in; strash; dch; strash; write_aiger $out" > "${out%.*}.log" 2>&1
"$(dirname "$0")/aig_equiv.sh" "$in" "$out" >> "${out%.*}.log"
