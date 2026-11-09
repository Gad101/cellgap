"""Step 12 of the handout: how much does the result depend on the area estimate?

    python3 src/sensitivity.py [--cell NAME] [--factor 0.7] [--jobs N]
Takes the final set, makes ONE cell's area 30% smaller (factor 0.7) in the Liberty, remaps the
required designs with scripts A and B and compares with the final-set mapping (estimated
areas). ABC sees only the numbers in the Liberty, so a changed area can change which cells it
picks. Default cell: the final-set cell with most instances in the estimated final mappings
(ties: lowest request id), read from results/final/mapping_areas_final.csv.

Writes results/sensitivity_30pct.csv, results/sensitivity_30pct.md and libs/hd_reduced_plus_final_set_30pct.lib.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import final_flow as ff                                        # noqa: E402
from designs import REQUIRED, ROOT                             # noqa: E402

RES = os.path.join(ROOT, "results")


def parse_cells(s: str) -> dict[str, int]:
    return {k: int(v) for k, v in (t.rsplit(":", 1) for t in s.split())} if s else {}


def most_used(rows: list[dict], names: list[str]) -> str:
    """Final-set cell with most instances over the required designs and both scripts (list order breaks ties)."""
    n = Counter()
    for r in rows:
        if r["library"] == "est" and r["design"] in REQUIRED:
            n.update(parse_cells(r["new_cells"]))
    return max(names, key=lambda c: (n[c], -names.index(c)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", default=None)
    ap.add_argument("--factor", type=float, default=0.7, help="area multiplier (0.7 = 30%% smaller)")
    ap.add_argument("--jobs", type=int, default=None)
    a = ap.parse_args(argv)
    fs = json.load(open(os.path.join(RES, "final_set.json")))
    rows = list(csv.DictReader(open(os.path.join(RES, "final", "mapping_areas_final.csv"))))
    est = {(r["design"], r["script"]): r for r in rows if r["library"] == "est"}
    cell = a.cell or most_used(rows, fs["cells"])
    if cell not in fs["cells"]:
        sys.exit("%s is not in the final set" % cell)
    reqs = [ff.with_area_scale(r, a.factor) if r["name"] == cell else r for r in fs["requests"]]
    lib = os.path.join(ROOT, "libs", "hd_reduced_plus_final_set_30pct.lib")
    sha = ff.build_lib(reqs, lib)
    new = ff.map_all(lib, sha, REQUIRED, os.path.join(ROOT, "results", "logs", "sensitivity"), jobs=a.jobs)
    old_area = next(r["estimated_area_um2"] for r in fs["requests"] if r["name"] == cell)
    out = []
    for d in REQUIRED:
        for s in "AB":
            n_old = parse_cells(est[d, s]["new_cells"]).get(cell, 0)
            n_new = new[d, s][1].get(cell, 0)
            out.append({"design": d, "script": s, "cell": cell, "cell_area_est_um2": old_area,
                        "cell_area_scaled_um2": round(old_area * a.factor, 4),
                        "area_est_um2": est[d, s]["area_um2"], "area_scaled_um2": round(new[d, s][0], 1),
                        "change_um2": round(new[d, s][0] - float(est[d, s]["area_um2"]), 1),
                        "instances_of_cell_est": n_old, "instances_of_cell_scaled": n_new})
    tot_old = sum(min(float(est[d, "A"]["area_um2"]), float(est[d, "B"]["area_um2"])) for d in REQUIRED)
    tot_new = ff.best_total(new, REQUIRED)
    with open(os.path.join(RES, "sensitivity_30pct.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    md = ["# Sensitivity: %s made %d%% smaller" % (cell, round((1 - a.factor) * 100)), "",
          "Cell area %.4f -> %.4f um2. Other cells unchanged.\n" % (old_area, old_area * a.factor),
          "| Design | Script | Area, estimate (um2) | Area, scaled (um2) | Change | Instances est -> scaled |",
          "|---|---|---|---|---|---|"]
    md += ["| %s | %s | %s | %.1f | %+.1f | %d -> %d |" % (r["design"], r["script"], r["area_est_um2"],
           r["area_scaled_um2"], r["change_um2"], r["instances_of_cell_est"], r["instances_of_cell_scaled"]) for r in out]
    md += ["", "Total best-of-both over the required designs: %.1f -> %.1f um2 (%+.1f)." % (tot_old, tot_new, tot_new - tot_old)]
    open(os.path.join(RES, "sensitivity_30pct.md"), "w").write("\n".join(md) + "\n")
    print("%s x%.2f: total %.1f -> %.1f um2" % (cell, a.factor, tot_old, tot_new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
