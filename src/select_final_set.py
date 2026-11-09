"""Step 10 of the Option 2 handout: choose the final set of new cells greedily.

    python3 src/select_final_set.py [--max-cells 10] [--jobs N]
Rule (handout): take the candidates in the order of results/cell_requests (the tool's ranking,
C-001 first). Add the next candidate to the cells kept so far, remap the required designs with
scripts A and B, and keep the candidate only if the total best-of-both area of the required
designs drops by more than 0.05 um2. Stop after 10 kept cells or when the list is exhausted.

The order is the ranking by *estimated* saving, so a candidate is tried once, in that order;
a candidate dropped early is not retried after later cells are kept (see the report's Limits).

Writes results/greedy_log.csv (every try), results/final_set.json (the kept cells and the
total after each) and libs/hd_reduced_plus_final_set_est.lib. Mapping logs: build/greedy/.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import final_flow as ff                                        # noqa: E402
from designs import REQUIRED, ROOT                             # noqa: E402

WORK = os.path.join(ROOT, "build", "greedy")


def pct(base: float, new: float) -> float:
    return round(100 * (base - new) / base, 3)


def greedy(reqs: list[dict], max_cells: int, jobs: int | None, designs: list[str] = REQUIRED) -> dict:
    """Run the rule above; returns the log rows and the kept cells with their totals."""
    os.makedirs(WORK, exist_ok=True)

    def total_for(cells: list[dict], tag: str) -> tuple[float, dict]:
        lib = os.path.join(WORK, tag + ".lib")
        sha = ff.build_lib(cells, lib)
        areas = ff.map_all(lib, sha, designs, os.path.join(WORK, "logs"), jobs=jobs)
        return ff.best_total(areas, designs), areas

    base, _ = total_for([], "baseline")
    kept, kept_rows, log, current = [], [], [], base
    for req in reqs:
        if len(kept) >= max_cells:
            break
        tot, areas = total_for(kept + [req], "try_%02d_%s" % (len(log) + 1, req["request_id"]))
        gain = current - tot
        keep = gain > ff.EPS
        used = sum(sum(areas[d, s][1].values()) for d in designs for s in "AB")
        log.append({"try": len(log) + 1, "request_id": req["request_id"], "name": req["name"],
                    "truth_table": req["truth_table"], "estimated_area_um2": req["estimated_area_um2"],
                    "total_before_um2": round(current, 1), "total_after_um2": round(tot, 1),
                    "gain_um2": round(gain, 1), "decision": "keep" if keep else "drop",
                    "instances_all_mappings": used})
        print("%-4s %-22s total %.1f -> %.1f  (%+.1f)  %s" % (req["request_id"], req["name"], current, tot,
                                                              -gain, "KEEP" if keep else "drop"), flush=True)
        if keep:
            kept.append(req)
            current = tot
            kept_rows.append({"order": len(kept), "request_id": req["request_id"], "name": req["name"],
                              "total_um2": round(tot, 1), "reduction_pct": pct(base, tot)})
    return {"baseline_total_um2": round(base, 1), "final_total_um2": round(current, 1),
            "reduction_pct": pct(base, current), "kept": kept, "kept_rows": kept_rows, "log": log}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-cells", type=int, default=10)
    ap.add_argument("--jobs", type=int, default=None, help="parallel Yosys runs (default: all cores)")
    a = ap.parse_args(argv)
    reqs = ff.load_requests()
    if not reqs:
        sys.exit("no cell requests: run `make cell-requests` first")
    res = greedy(reqs, a.max_cells, a.jobs)
    res_dir = os.path.join(ROOT, "results")
    with open(os.path.join(res_dir, "greedy_log.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res["log"][0]))
        w.writeheader()
        w.writerows(res["log"])
    lib = os.path.join(ROOT, "libs", "hd_reduced_plus_final_set_est.lib")
    ff.build_lib(res["kept"], lib)
    with open(os.path.join(res_dir, "final_set.json"), "w") as f:
        json.dump({"rule": "greedy in ranked order; keep if the best-of-both total area of the required "
                           "designs drops by more than %.2f um2; at most %d cells" % (ff.EPS, a.max_cells),
                   "designs": REQUIRED, "baseline_total_um2": res["baseline_total_um2"],
                   "final_total_um2": res["final_total_um2"], "reduction_pct": res["reduction_pct"],
                   "cells": [r["name"] for r in res["kept"]], "steps": res["kept_rows"],
                   "requests": res["kept"]}, f, indent=1)
    print("final set: %d cells, total %.1f -> %.1f um2 (%.3f%%)"
          % (len(res["kept"]), res["baseline_total_um2"], res["final_total_um2"], res["reduction_pct"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
