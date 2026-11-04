#!/usr/bin/env bash
# Are two binary AIGs equivalent? ABC's cec (latches matched by order); exit 1 if not.
#   src/aig_equiv.sh <a.aig> <b.aig>
set -euo pipefail
ABC=${ABC:-yosys-abc}
r=$($ABC -c "cec $1 $2" 2>&1)
echo "$r"
grep -q "Networks are equivalent" <<<"$r" || { echo "NOT EQUIVALENT: $1 $2" >&2; exit 1; }
