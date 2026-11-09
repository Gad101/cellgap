"""Do risc8, pic16 and p16c5x (one instruction set) favour the same new cells? (handout 9.3)

    python3 src/isa_compare.py            after `make isa` has written results/isa/<design>/
For each design, candidates.py was run on that design alone, so its ranking is that design's own.
This script compares the three rankings and writes results/isa_compare.{csv,md}:
  - the top-N candidate classes of each design and how many they share;
  - for every class that is a candidate in any of the three: its rank and estimated saving in each design.
A second view does not depend on the saving estimate: the most frequent classes that HD lacks (kept = yes in
each design's own redundancy_report.csv), by number of cuts, top N per design, with their overlap.
Only files the flow wrote are read; nothing is estimated here.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import ROOT                                       # noqa: E402

ISA = ["risc8", "pic16", "p16c5x"]
DIR = os.path.join(ROOT, "results", "isa")


def load(d: str, top: int | None = None) -> list[dict]:
    c = json.load(open(os.path.join(DIR, d, "candidates.json")))["candidates"]
    return c[:top] if top else c


def overlap(a: list[str], b: list[str]) -> tuple[int, float]:
    """(shared classes, Jaccard index) of two lists of classes."""
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    return inter, round(inter / len(sa | sb), 3) if sa | sb else 0.0


def frequent(d: str, top: int) -> list[tuple[str, int]]:
    """(class, cuts) of the `top` most frequent kept classes of design d (kept = candidate after Table 3)."""
    with open(os.path.join(DIR, d, "redundancy_report.csv")) as f:
        rows = [r for r in csv.DictReader(f) if r["kept"] == "yes"]
    rows.sort(key=lambda r: (-int(r["cuts_" + d]), r["class_table"]))
    return [(r["class_table"], int(r["cuts_" + d])) for r in rows[:top]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args(argv)
    cands = {d: load(d) for d in ISA}
    by = {d: {c["class_table"]: c for c in cands[d]} for d in ISA}
    allc = sorted(set().union(*[set(by[d]) for d in ISA]),
                  key=lambda c: min(by[d][c]["rank"] for d in ISA if c in by[d]))
    rows = [{"class_table": c, **{"rank_" + d: by[d][c]["rank"] if c in by[d] else "-" for d in ISA},
             **{"saving_" + d: by[d][c]["estimated_saving_um2"] if c in by[d] else "-" for d in ISA}} for c in allc]
    with open(os.path.join(ROOT, "results", "isa_compare.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    md = ["# risc8, pic16, p16c5x: the same new cells?", "",
          "| Pair | Candidate classes in both (all) | Jaccard (all) | Shared in top %d | Jaccard (top %d) |" % (a.top, a.top),
          "|---|---|---|---|---|"]
    for x, y in combinations(ISA, 2):
        n, j = overlap(list(by[x]), list(by[y]))
        nt, jt = overlap([c["class_table"] for c in cands[x][:a.top]], [c["class_table"] for c in cands[y][:a.top]])
        md.append("| %s / %s | %d | %.3f | %d | %.3f |" % (x, y, n, j, nt, jt))
    md += ["", "Candidates per design: " + ", ".join("%s %d" % (d, len(cands[d])) for d in ISA) + ".", "",
           "| Class | " + " | ".join("%s rank (saving um2)" % d for d in ISA) + " |", "|---|" + "---|" * len(ISA)]
    md += ["| %s | %s |" % (r["class_table"], " | ".join(
        "-" if r["rank_" + d] == "-" else "%s (%s)" % (r["rank_" + d], r["saving_" + d]) for d in ISA)) for r in rows]
    fr = {d: frequent(d, a.top) for d in ISA}
    md += ["", "## Most frequent new classes (cuts), top %d per design" % a.top, "",
           "| Pair | Shared in top %d | Jaccard |" % a.top, "|---|---|---|"]
    for x, y in combinations(ISA, 2):
        n, j = overlap([c for c, _ in fr[x]], [c for c, _ in fr[y]])
        md.append("| %s / %s | %d | %.3f |" % (x, y, n, j))
    allf = sorted({c for d in ISA for c, _ in fr[d]},
                  key=lambda c: -sum(dict(fr[d]).get(c, 0) for d in ISA))
    md += ["", "| Class | " + " | ".join("%s cuts" % d for d in ISA) + " |", "|---|" + "---|" * len(ISA)]
    md += ["| %s | %s |" % (c, " | ".join(str(dict(fr[d]).get(c, "-")) for d in ISA)) for c in allf]
    md += ["", "A dash means the class is not among that design's top %d (it may still occur there)." % a.top]
    open(os.path.join(ROOT, "results", "isa_compare.md"), "w").write("\n".join(md) + "\n")
    print("results/isa_compare.{csv,md}: %d classes over %s" % (len(rows), ", ".join(ISA)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
