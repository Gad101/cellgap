"""AIG size, number of cuts and number of classes for every design (handout 9.2).

    python3 src/design_stats.py build/aig/cpu8.aag build/aig/cpu8_abc.aig ...
Runs the cut enumerator with its check on each AIG and writes
results/design_stats.csv and results/cuts/<file>.json. A file named <design>_abc
is the graph after ABC's strash; dch (row "after_abc"), the rest are "before".
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aiger                                   # noqa: E402
import cuts                                    # noqa: E402
from designs import ROOT                       # noqa: E402
from tt import canon                           # noqa: E402


def stats(path: str) -> dict:
    t0 = time.time()
    g = aiger.read(path)
    c = cuts.enumerate_cuts(g)
    s = cuts.summarize(g, c)
    p = Counter(canon(t, "P") for v in g.ands for _, t in c[v][1:])
    n = Counter(canon(t, "NPN") for v in g.ands for _, t in c[v][1:])
    errs = cuts.check_cuts(g, c)
    name = os.path.splitext(os.path.basename(path))[0]
    after = name.endswith("_abc")
    s.update(file=name, design=name[:-4] if after else name, graph="after_abc" if after else "before",
             p_classes=len(p), npn_classes=len(n),
             check="pass" if not errs else "fail (%d)" % len(errs), seconds=round(time.time() - t0, 1))
    return s


def main(paths):
    rows = []
    os.makedirs(os.path.join(ROOT, "results", "cuts"), exist_ok=True)
    for p in paths:
        s = stats(p)
        with open(os.path.join(ROOT, "results", "cuts", s["file"] + ".json"), "w") as f:
            json.dump(s, f, indent=1)
        rows.append({k: s[k] for k in ("design", "graph", "inputs", "latches", "ands", "cuts", "p_classes",
                                        "po_classes", "npn_classes", "check", "seconds")})
        print("%-12s %-9s ANDs %6d  cuts %7d  classes P/PO/NPN %4d/%4d/%3d  check %s  %.1fs"
              % (s["design"], s["graph"], s["ands"], s["cuts"], s["p_classes"], s["po_classes"], s["npn_classes"],
                 s["check"], s["seconds"]), flush=True)
    with open(os.path.join(ROOT, "results", "design_stats.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return 0 if all(r["check"] == "pass" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
