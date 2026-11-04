"""Table 5 of the Option 2 handout (section 7), with estimated areas.

    python3 src/write_table5.py [--tag estimated]
Reads results/mapping_areas.csv (make mapping) and results/mapping_equivalence.csv
(make mapping-equivalence); every number comes from those files.
  Reduction    = (baseline - with new cells) / baseline; positive = smaller.
  Best of both = the smaller of scripts A and B on each side.
Writes results/table5_<tag>.md and results/table5_<tag>.csv.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import REQUIRED, ROOT             # noqa: E402

RESULTS = os.path.join(ROOT, "results")


def pct(base: float, new: float) -> float:
    return round(100 * (base - new) / base, 2)


def read_csv(name: str) -> list[dict]:
    with open(os.path.join(RESULTS, name)) as f:
        return list(csv.DictReader(f))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="estimated")
    a = ap.parse_args(argv)
    area = {(r["design"], r["library"], r["script"]): r for r in read_csv("mapping_areas.csv")}
    equiv = {(r["design"], r["library"], r["script"]): r for r in read_csv("mapping_equivalence.csv")}
    designs = list(dict.fromkeys(r[0] for r in area))

    rows, best = [], []
    for d in designs:
        for s in "AB":
            b, n = float(area[d, "baseline", s]["area_um2"]), float(area[d, "est", s]["area_um2"])
            ok = equiv[d, "baseline", s]["equivalence"] == "pass" and equiv[d, "est", s]["equivalence"] == "pass"
            rows.append({"design": d, "script": s, "baseline_um2": b, "with_new_cells_um2": n,
                         "reduction_pct": pct(b, n),
                         "new_cell_instances": int(area[d, "est", s]["new_cell_instances"]),
                         "equivalence": "pass" if ok else "FAIL",
                         "method": equiv[d, "est", s]["method"]})
        bb = min(float(area[d, "baseline", s]["area_um2"]) for s in "AB")
        bn = min(float(area[d, "est", s]["area_um2"]) for s in "AB")
        best.append({"design": d, "baseline_um2": bb, "with_new_cells_um2": bn, "reduction_pct": pct(bb, bn)})
    req = [r for r in best if r["design"] in REQUIRED]
    tb, tn = sum(r["baseline_um2"] for r in req), sum(r["with_new_cells_um2"] for r in req)

    with open(os.path.join(RESULTS, "table5_%s.csv" % a.tag), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    md = ["# Table 5, %s areas" % a.tag, "",
          "| Design | Script | Baseline (um2) | With new cells (um2) | Reduction | New-cell instances | Equivalence |",
          "|---|---|---|---|---|---|---|"]
    md += ["| %s | %s | %.1f | %.1f | %.2f%% | %d | %s |" % (r["design"], r["script"], r["baseline_um2"],
           r["with_new_cells_um2"], r["reduction_pct"], r["new_cell_instances"], r["equivalence"]) for r in rows]
    md += ["", "Best of both (the smaller of scripts A and B on each side):", "",
           "| Design | Baseline (um2) | With new cells (um2) | Reduction |", "|---|---|---|---|"]
    md += ["| %s | %.1f | %.1f | %.2f%% |" % (r["design"], r["baseline_um2"], r["with_new_cells_um2"],
                                            r["reduction_pct"]) for r in best]
    md += ["| **Total, required designs** | **%.1f** | **%.1f** | **%.2f%%** |" % (tb, tn, pct(tb, tn)), "",
           "Reduction = (baseline - with new cells) / baseline; positive means smaller. Baseline: hd_reduced.lib; "
           "with new cells: libs/hd_reduced_plus_new_cells_est.lib. Equivalence: ABC cec against the RTL "
           "(dsec for designs with flip-flops), results/mapping_equivalence.csv. SPM and mul also pass "
           "Tutorial 4's gate-level testbenches: results/gate_level_testbenches.csv."]
    with open(os.path.join(RESULTS, "table5_%s.md" % a.tag), "w") as f:
        f.write("\n".join(md) + "\n")
    print("results/table5_%s.md: total over the required designs %.1f -> %.1f um2 (%.2f%%)"
          % (a.tag, tb, tn, pct(tb, tn)))
    return 0 if all(r["equivalence"] == "pass" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
