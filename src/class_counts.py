"""Classes found over all analysed designs (handout 9.3, "Classes").

    python3 src/class_counts.py
For the AIGs of `make aigs`, before and after ABC: distinct classes of every cut up to input order and
output inversion (PO, the CMOS count) and NPN, over all cuts and over cuts whose function uses all 4
inputs. Writes results/class_counts.csv.
"""
from __future__ import annotations

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aiger                                   # noqa: E402
import cuts                                    # noqa: E402
from designs import ANALYSED, ROOT             # noqa: E402
from tt import canon, support                  # noqa: E402


def main() -> int:
    rows = []
    for graph, suffix in (("before", ".aag"), ("after_abc", "_abc.aig")):
        sets = {k: set() for k in ("po", "npn", "po_4in", "npn_4in")}
        for d in ANALYSED:
            g = aiger.read(os.path.join(ROOT, "build", "aig", d + suffix))
            c = cuts.enumerate_cuts(g)
            for v in g.ands:
                for _, t in c[v][1:]:
                    four = len(support(t)) == 4
                    for kind in ("PO", "NPN"):
                        sets[kind.lower()].add(canon(t, kind))
                        if four:
                            sets[kind.lower() + "_4in"].add(canon(t, kind))
        rows.append({"graph": graph, "designs": " ".join(ANALYSED), **{k: len(v) for k, v in sets.items()}})
        print("%-9s PO %d, NPN %d; using all 4 inputs: PO %d, NPN %d"
              % (graph, len(sets["po"]), len(sets["npn"]), len(sets["po_4in"]), len(sets["npn_4in"])))
    with open(os.path.join(ROOT, "results", "class_counts.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
