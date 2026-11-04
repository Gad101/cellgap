"""Step 9: map every design with and without the new cells (Option 2 handout, section 7).

    python3 src/map_with_and_without_new_cells.py [--lib libs/hd_reduced_plus_new_cells_est.lib] [--designs cpu8,spm]
For each design: the baseline (hd_reduced.lib) and the extended library, each
with scripts A and B, using the commands of section 2 through table1.map_design
(the same machinery as Table 1; only the library changes). A write_verilog after
stat saves the mapped netlist; it cannot change the area.

Writes results/logs/mapping/<design>_<baseline|est>_<A|B>.{ys,log},
results/netlists/<same>.v and results/mapping_areas.csv. Exits 1 if a baseline
area differs from handout Table 1 (reduced columns).
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import ANALYSED, GIVEN, ROOT, SCRIPTS, TABLE1      # noqa: E402
from table1 import map_design                                  # noqa: E402

NEW_CELL = re.compile(r"^\s+(dd2_\w+)\s+(\d+)\s*$", re.M)


def new_cell_counts(log: str) -> dict[str, int]:
    """Instances of each new cell (dd2_...) in the last stat of a mapping log."""
    with open(log) as f:
        text = f.read()
    block = text[text.rindex("Number of cells"):]
    return {name: int(n) for name, n in NEW_CELL.findall(block)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lib", default=os.path.join(ROOT, "libs", "hd_reduced_plus_new_cells_est.lib"))
    ap.add_argument("--designs", default=",".join(ANALYSED))
    ap.add_argument("--baseline-only", action="store_true",
                    help="only the baseline mappings (logs for the ranking); writes no CSV")
    a = ap.parse_args(argv)
    libs = {"baseline": os.path.join(GIVEN, "hd_reduced.lib"), "est": os.path.abspath(a.lib)}
    if a.baseline_only:
        del libs["est"]
    logs = os.path.join(ROOT, "results", "logs", "mapping")
    nets = os.path.join(ROOT, "results", "netlists")
    os.makedirs(nets, exist_ok=True)
    rows, bad = [], []
    for d in a.designs.split(","):
        for lib in libs:
            for script in "AB":
                tag = "%s_%s_%s" % (d, lib, script)
                net = os.path.join(nets, tag + ".v")
                area, _ = map_design(d, libs[lib], SCRIPTS[script], os.path.join(logs, tag + ".log"),
                                     extra="write_verilog -noattr %s\n" % net)
                cells = new_cell_counts(os.path.join(logs, tag + ".log"))
                rows.append({"design": d, "library": lib, "script": script, "area_um2": round(area, 1),
                             "new_cell_instances": sum(cells.values()),
                             "new_cells": " ".join("%s:%d" % kv for kv in sorted(cells.items())),
                             "netlist": os.path.relpath(net, ROOT)})
                ref = TABLE1.get(d)
                if lib == "baseline" and ref:
                    want = ref[1] if script == "A" else ref[3]          # Table 1 reduced columns
                    if round(area, 1) != want:
                        bad.append("%s script %s baseline %.1f, Table 1 says %.1f" % (d, script, area, want))
                print("%-10s %-8s script %s %10.1f um2  new-cell instances %d"
                      % (d, lib, script, area, sum(cells.values())), flush=True)
    if a.baseline_only:
        return 0 if not bad else 1
    with open(os.path.join(ROOT, "results", "mapping_areas.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for b in bad:
        print("BASELINE DIFFERS FROM TABLE 1:", b)
    print("baseline = Table 1 for the required designs" if not bad else "BASELINE CHECK FAILED")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
