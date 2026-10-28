"""The class table of HD (checkpoint 1, Option 2 handout section 9.2).

Groups every single-output combinational HD cell of up to 4 inputs by its class
up to input order and output inversion (PO), and lists for each class: the
cells (all drives), the P and NPN class names, whether one CMOS stage can build
it and with how many transistors (at most 3 in series), and the x1 area.
Cells with 5 or 6 inputs cannot be a 4-input class; they are listed at the end
because the Contained test of step 5 still uses them.

    python3 src/hd_class_table.py [out_prefix]     (default results/hd_class_table)
writes <out_prefix>.csv and <out_prefix>.md.
"""
from __future__ import annotations

import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cmos import one_stage_transistors           # noqa: E402
from redundancy import ROOT, index, short        # noqa: E402
from tt import canon, support, to_hex            # noqa: E402


def family(name: str) -> str:
    """sky130_fd_sc_hd__a21oi_2 -> a21oi"""
    return re.sub(r"_\d+$", "", short(name))


def build(lib_path=None):
    hd = index(lib_path) if lib_path else index()
    classes: dict[int, dict] = {}
    wide = []
    for c in hd.cells:
        if c["n_inputs"] > 4:
            wide.append(c)
            continue
        t = c["tt"]
        po = canon(t, "PO")
        k = classes.setdefault(po, {"po": po, "cells": [], "families": set(), "areas": {}})
        k["cells"].append(c["name"])
        fam = family(c["name"])
        k["families"].add(fam)
        k["areas"].setdefault(fam, []).append(c["area"])
        k["n"] = len(support(t))
    rows = []
    for po, k in sorted(classes.items(), key=lambda kv: (kv[1]["n"], kv[0])):
        y = po
        nt = one_stage_transistors(y) or one_stage_transistors(y ^ 0xFFFF)
        rows.append({
            "po_class": to_hex(po),
            "inputs_used": k["n"],
            "p_classes": " ".join(sorted({to_hex(canon(t, "P")) for t in (po, po ^ 0xFFFF)})),
            "npn_class": to_hex(canon(po, "NPN")),
            "one_stage_T": nt if nt else "",
            "families": " ".join(sorted(k["families"])),
            "n_cells": len(k["cells"]),
            "min_area_um2": min(min(a) for a in k["areas"].values()),
        })
    return rows, wide


def main(argv):
    prefix = argv[1] if len(argv) > 1 else os.path.join(ROOT, "results", "hd_class_table")
    rows, wide = build()
    os.makedirs(os.path.dirname(prefix), exist_ok=True)
    with open(prefix + ".csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    n_cells = sum(r["n_cells"] for r in rows)
    with open(prefix + ".md", "w") as f:
        f.write("# Class table of sky130_fd_sc_hd (single-output combinational cells)\n\n")
        f.write("Class = smallest 16-bit truth table up to input order and output inversion (PO).\n")
        f.write("`one_stage_T`: transistors of one static CMOS stage for the class (Y or !Y),\n")
        f.write("at most 3 in series; empty = needs more than one stage.\n\n")
        f.write("- %d cells with <= 4 inputs, in %d PO classes and %d NPN classes\n"
                % (n_cells, len(rows), len({r["npn_class"] for r in rows})))
        f.write("- %d cells with 5 or 6 inputs (used only by the Contained test): %s\n\n"
                % (len(wide), " ".join(sorted({family(c["name"]) for c in wide}))))
        f.write("| " + " | ".join(rows[0]) + " |\n|" + "---|" * len(rows[0]) + "\n")
        for r in rows:
            f.write("| " + " | ".join(str(v) for v in r.values()) + " |\n")
    print("HD: %d cells (<= 4 inputs) in %d PO classes, %d NPN classes; %d wider cells"
          % (n_cells, len(rows), len({r['npn_class'] for r in rows}), len(wide)))
    print("wrote %s.csv and %s.md" % (prefix, prefix))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
