"""Step 11 hook: put the generator's real Liberty cells in place of the estimated entries.

    python3 src/real_lib.py [--cells libs/real] [--out libs/hd_reduced_plus_final_set_real.lib]
DIR holds one file per final cell, <cell name>.lib: cellweaver's characterization_rc/tt/<name>.lib,
copied there by src/run_cellweaver.py. Only its `cell (<name>) { ... }` group is used (its library
header, with the same time/capacitance/leakage units as HD, and its templates are ignored). Each estimated
group in libs/hd_reduced_plus_final_set_est.lib is replaced by the real one. A cell with no file
is an error: a half-real library would make the "real" column meaningless.
Then Yosys must import 189 + the number of final cells, and every real cell's function must still
give its request's truth table (same checks as the estimated library). Also writes
results/real_vs_estimated_area.csv: estimated area, real area and their ratio per cell.
NOTE: tested only on a hand-made cell group in the same format as cellweaver's; run it on a real file.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import ROOT                                       # noqa: E402
import write_liberty_with_new_cells as wl                      # noqa: E402


def group(text: str, name: str) -> tuple[int, int]:
    """(start, end) of the `cell ("name") { ... }` group, found by matching braces."""
    m = re.search(r'cell\s*\(\s*"?%s"?\s*\)\s*\{' % re.escape(name), text)
    if not m:
        raise ValueError("no cell group for %s" % name)
    depth, i = 0, m.end() - 1
    while i < len(text):
        depth += (text[i] == "{") - (text[i] == "}")
        if depth == 0:
            return m.start(), i + 1
        i += 1
    raise ValueError("unbalanced braces in the group of %s" % name)


def replace_cells(lib_text: str, real: dict[str, str]) -> str:
    """lib_text with each named group replaced by the real group text."""
    for name, txt in real.items():
        s, e = group(lib_text, name)
        lib_text = lib_text[:s] + txt.strip() + lib_text[e:]
    return lib_text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", default=os.path.join(ROOT, "libs", "real"))
    ap.add_argument("--est", default=os.path.join(ROOT, "libs", "hd_reduced_plus_final_set_est.lib"))
    ap.add_argument("--out", default=os.path.join(ROOT, "libs", "hd_reduced_plus_final_set_real.lib"))
    a = ap.parse_args(argv)
    names = json.load(open(os.path.join(ROOT, "results", "final_set.json")))["cells"]
    real = {}
    for n in names:
        p = os.path.join(a.cells, n + ".lib")
        if not os.path.exists(p):
            sys.exit("missing %s: the generator has not returned this cell" % p)
        s, e = group(open(p).read(), n)
        real[n] = open(p).read()[s:e]
    text = replace_cells(open(a.est).read(), real)
    open(a.out, "w").write(text)
    fs = json.load(open(os.path.join(ROOT, "results", "final_set.json")))
    bad = wl.check_functions(fs["requests"], a.out)
    for b in bad:
        print("FUNCTION CHECK FAILED", b)
    with open(os.path.join(ROOT, "results", "real_vs_estimated_area.csv"), "w") as f:
        f.write("cell,estimated_um2,real_um2,real_over_estimated\n")
        for r in fs["requests"]:
            real_a = float(re.search(r"\barea\s*:\s*([0-9.eE+-]+)", real[r["name"]]).group(1))
            f.write("%s,%s,%s,%.3f\n" % (r["name"], r["estimated_area_um2"], real_a, real_a / r["estimated_area_um2"]))
    got, want = wl.yosys_cell_count(a.out), wl.BASE_CELLS + len(names)
    print("%s: %d real cells; Yosys imported %d cell types (want %d)" % (os.path.relpath(a.out, ROOT), len(names), got, want))
    return 0 if got == want and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
