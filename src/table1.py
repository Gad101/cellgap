"""Reproduce Table 1 of the Option 2 handout (week 1, checkpoint 1).

Maps each required design on the usable and the reduced HD library with
scripts A and B, using exactly the commands of handout section 2, and compares
the area that `stat -liberty` prints with the handout's numbers.

    python3 src/table1.py [design ...]        (default: the six required designs)
writes results/table1.csv, results/table1.md and the Yosys logs in
results/logs/table1/.
"""
from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import DESIGNS, GIVEN, REQUIRED, ROOT, SCRIPTS, TABLE1, files   # noqa: E402

YOSYS = os.environ.get("YOSYS", "yosys")
LIBS = {
    "usable": os.path.join(GIVEN, "hd_usable.lib"),
    "reduced": os.path.join(GIVEN, "hd_reduced.lib"),
}
TOLERANCE = 0.005   # 0.5 %: counts as reproduced


def map_design(name: str, lib: str, script: str, log: str) -> tuple[float, dict]:
    """Run the handout's commands; return (chip area, cell counts)."""
    top, _, flags = DESIGNS[name]
    reads = "\n".join("read_verilog %s %s" % (flags, f) for f in files(name))
    cmds = f"""{reads}
synth -flatten -top {top}
dfflibmap -liberty {lib}
abc -liberty {lib} -script {script}
opt_clean -purge
stat -liberty {lib}
"""
    os.makedirs(os.path.dirname(log), exist_ok=True)
    ys = log[:-4] + ".ys"
    with open(ys, "w") as f:
        f.write(cmds)
    r = subprocess.run([YOSYS, "-l", log, "-q", "-s", ys], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("yosys failed on %s (see %s):\n%s" % (name, log, r.stderr[-2000:]))
    text = open(log).read()
    m = re.findall(r"Chip area for (?:top )?module '\\?[^']*':\s*([0-9.]+)", text)
    if not m:
        raise RuntimeError("no 'Chip area' line in %s" % log)
    return float(m[-1]), {}


def main(argv):
    names = argv[1:] or REQUIRED
    out_rows = []
    all_ok = True
    for name in names:
        ref = TABLE1.get(name)
        row = {"design": name}
        for i, (script, lib) in enumerate((("A", "usable"), ("A", "reduced"), ("B", "usable"), ("B", "reduced"))):
            log = os.path.join(ROOT, "results", "logs", "table1", "%s_%s_%s.log" % (name, script, lib))
            t0 = time.time()
            area, _ = map_design(name, LIBS[lib], SCRIPTS[script], log)
            key = "%s_%s" % (script, lib)
            row[key] = round(area, 1)
            if ref:
                d = (area - ref[i]) / ref[i]
                row[key + "_handout"] = ref[i]
                row[key + "_diff_pct"] = round(100 * d, 3)
                all_ok &= abs(d) <= TOLERANCE
            print("%-10s script %s %-8s %10.1f  (handout %s)  %.0fs"
                  % (name, script, lib, area, ref[i] if ref else "-", time.time() - t0), flush=True)
        if "A_usable" in row:
            row["reduction_cost_A_pct"] = round(100 * (row["A_reduced"] - row["A_usable"]) / row["A_usable"], 3)
            row["reduction_cost_B_pct"] = round(100 * (row["B_reduced"] - row["B_usable"]) / row["B_usable"], 3)
        out_rows.append(row)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    keys = sorted({k for r in out_rows for k in r}, key=lambda k: (k != "design", k))
    with open(os.path.join(ROOT, "results", "table1.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(out_rows)
    with open(os.path.join(ROOT, "results", "table1.md"), "w") as f:
        f.write("# Table 1 reproduced (um2), Yosys %s\n\n" % YOSYS)
        f.write("| Design | A usable | A reduced | B usable | B reduced | max diff vs handout |\n|---|---|---|---|---|---|\n")
        for r in out_rows:
            diffs = [abs(r.get(k + "_diff_pct", 0)) for k in ("A_usable", "A_reduced", "B_usable", "B_reduced")]
            f.write("| %s | %s | %s | %s | %s | %.3f%% |\n" % (r["design"], r["A_usable"], r["A_reduced"],
                                                            r["B_usable"], r["B_reduced"], max(diffs)))
    print("TABLE 1", "REPRODUCED" if all_ok else "DIFFERS (see results/table1.md)")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
